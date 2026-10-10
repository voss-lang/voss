from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
import json
import math
import os
import re
import time
from typing import Literal
import uuid

import httpx

from ._config import RuntimeConfig, get_config
from .budget import BudgetScope, current_budget
from .exceptions import VossRuntimeError
from .probable import ProbableValue

JEV_URL = "https://api.typesafe.ai/v1/systemone"
USD_PER_INPUT_TOKEN = 0.042 / 1_000_000
MAX_REQUEST_TOKENS = 64_000
PROBABILITY_SUM_TOLERANCE = 0.02
RETRY_STATUSES = frozenset({429, 529})
DEFAULT_BACKOFF_S = 0.25
Outcome = Literal["answered", "abstained", "disabled", "unavailable", "budget_exhausted", "invalid_response"]
Description = str | dict | list
SAFE_ID = re.compile(r"[A-Za-z0-9_.:\-]{1,64}")
SAFE_PURPOSE = re.compile(r"[a-z][a-z0-9_.\-]{0,63}")
KILL_ENV = "VOSS_JUDGMENTS"
KEY_ENV = "TYPESAFE_API_KEY"
MISSING_KEY_MESSAGE = "TYPESAFE_API_KEY not set (env or keychain)"
KILLED_MESSAGE = "judgments disabled by VOSS_JUDGMENTS=off"


@dataclass(frozen=True)
class ChoiceQuestion:
    instructions: Description
    criteria: Mapping[str, Description | None]

    def __post_init__(self):
        if not isinstance(self.instructions, (str, dict, list)):
            raise ValueError("instructions must be a string, object, or array")
        if not isinstance(self.criteria, Mapping) or not 2 <= len(self.criteria) <= 255:
            raise ValueError("choice requires 2 to 255 options")
        if any(not isinstance(k, str) or not k or (v is not None and not isinstance(v, (str, dict, list))) for k, v in self.criteria.items()):
            raise ValueError("choice requires non-empty option IDs and descriptions or null")

    def to_wire(self) -> dict:
        return {"type": "choice", "instructions": self.instructions, "criteria": dict(self.criteria)}


@dataclass(frozen=True)
class ScoreQuestion:
    instructions: Description
    criteria: Sequence[Description]

    def __post_init__(self):
        if not isinstance(self.instructions, (str, dict, list)):
            raise ValueError("instructions must be a string, object, or array")
        if not isinstance(self.criteria, Sequence) or isinstance(self.criteria, str) or not 2 <= len(self.criteria) <= 10:
            raise ValueError("score requires 2 to 10 levels")
        if any(not isinstance(v, (str, dict, list)) for v in self.criteria):
            raise ValueError("score levels must be descriptions")

    def to_wire(self) -> dict:
        return {"type": "score", "instructions": self.instructions, "criteria": list(self.criteria)}


@dataclass(frozen=True)
class NoulQuestion:
    instructions: Description
    criteria: Mapping[str, Description] | None = None

    def __post_init__(self):
        if not isinstance(self.instructions, (str, dict, list)):
            raise ValueError("instructions must be a string, object, or array")
        if self.criteria is not None and (
            not isinstance(self.criteria, Mapping)
            or not set(self.criteria) <= {"true", "false"}
            or any(not isinstance(v, (str, dict, list)) for v in self.criteria.values())
        ):
            raise ValueError("noul criteria must contain only true/false descriptions")

    def to_wire(self) -> dict:
        question = {"type": "noul", "instructions": self.instructions}
        if self.criteria is not None:
            question["criteria"] = dict(self.criteria)
        return question


Question = ChoiceQuestion | ScoreQuestion | NoulQuestion


def question_from_wire(raw: object) -> Question:
    if not isinstance(raw, Mapping) or "instructions" not in raw:
        raise ValueError("each question needs an ID and instructions")
    kind = raw.get("type")
    criteria = raw.get("criteria")
    if kind == "choice":
        return ChoiceQuestion(raw["instructions"], criteria)
    if kind == "score":
        return ScoreQuestion(raw["instructions"], criteria)
    if kind == "noul":
        return NoulQuestion(raw["instructions"], criteria)
    raise ValueError("question type must be choice, score, or noul")


@dataclass(frozen=True)
class ChoiceResult:
    choice: str
    probabilities: dict[str, float]
    confidence: float
    type: str = field(default="choice", init=False)

    def to_probable(self) -> ProbableValue:
        return ProbableValue(self.choice, self.probabilities[self.choice])


@dataclass(frozen=True)
class ScoreResult:
    score: float
    probabilities: dict[str, float]
    confidence: float
    type: str = field(default="score", init=False)


@dataclass(frozen=True)
class NoulResult:
    noul: float
    type: str = field(default="noul", init=False)


Answer = ChoiceResult | ScoreResult | NoulResult


@dataclass(frozen=True)
class JudgmentResult:
    answers: dict[str, Answer]
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd_estimate: float
    attempts: int
    outcome: Outcome = "answered"
    receipt: JudgmentReceipt | None = None


@dataclass(frozen=True)
class JudgmentReceipt:
    call_id: str
    purpose: str
    rubric_version: str | None
    model_requested: str
    model_returned: str | None
    mode: str
    status: str
    fallback_reason: str | None
    attempts: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    held_usd: float
    latency_ms: float
    answers: dict
    artifact_revision: str | None
    schema_version: int = 1
    detail: dict | None = None


class JudgmentError(VossRuntimeError):
    def __init__(self, outcome: Outcome, message: str, *, status: int | None = None, attempts: int = 0):
        self.outcome = outcome
        self.status = status
        self.attempts = attempts
        self.receipt = None
        super().__init__(message)


@dataclass
class LedgerEntry:
    call_id: str
    reserved: float
    state: str
    cost_usd: float | None = None
    scope: BudgetScope | None = field(default=None, repr=False)


_current_ledger: ContextVar[JudgmentLedger | None] = ContextVar("_current_ledger", default=None)


def current_ledger() -> JudgmentLedger | None:
    return _current_ledger.get()


class JudgmentLedger:
    def __init__(self, max_calls: int, max_cost_usd: float):
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self.calls_used = 0
        self.entries: list[LedgerEntry] = []
        self.receipts: list[JudgmentReceipt] = []
        self._token = None

    @property
    def observed_usd(self) -> float:
        return sum(e.cost_usd for e in self.entries if e.state == "settled")

    @property
    def held_usd(self) -> float:
        return sum(e.reserved for e in self.entries if e.state in ("reserved", "unknown"))

    def reserve(self, call_id: str, amount: float) -> LedgerEntry:
        if self.calls_used >= self.max_calls or self.observed_usd + self.held_usd + amount > self.max_cost_usd:
            raise JudgmentError("budget_exhausted", "Jev attempt or cost allowance exhausted")
        scope = current_budget()
        if scope is not None and scope.cost_usd is not None and amount > scope.cost_usd - scope.cost_so_far:
            raise JudgmentError("budget_exhausted", "enclosing budget cannot cover the judgment reservation")
        self.calls_used += 1
        if scope is not None:
            scope.cost_so_far += amount
        entry = LedgerEntry(call_id, amount, "reserved", scope=scope)
        self.entries.append(entry)
        return entry

    def settle(self, entry: LedgerEntry, cost_usd: float) -> None:
        if entry.state != "reserved":
            return
        entry.state = "settled"
        entry.cost_usd = cost_usd
        if entry.scope is not None:
            entry.scope.cost_so_far += cost_usd - entry.reserved

    def release(self, call_id: str) -> None:
        for entry in self.entries:
            if entry.call_id == call_id and entry.state == "reserved":
                entry.state = "unknown"

    def receipt(self, call_id: str) -> JudgmentReceipt | None:
        return next((r for r in self.receipts if r.call_id == call_id), None)

    async def __aenter__(self) -> JudgmentLedger:
        self._token = _current_ledger.set(self)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        _current_ledger.reset(self._token)
        self._token = None
        return False


def _safe_id(value: str, fallback: str) -> str:
    return value if SAFE_ID.fullmatch(value) else fallback


def _receipt_answers(questions: Mapping[str, Question], answers: Mapping[str, Answer]) -> dict:
    out = {}
    for n, (qid, question) in enumerate(questions.items(), 1):
        answer = answers[qid]
        if isinstance(answer, ChoiceResult):
            ids = {o: _safe_id(o, f"opt{i}") for i, o in enumerate(question.criteria, 1)}
            entry = {"type": "choice", "choice": ids[answer.choice], "probabilities": {ids[o]: p for o, p in answer.probabilities.items()}}
        elif isinstance(answer, ScoreResult):
            entry = {"type": "score", "score": answer.score, "probabilities": dict(answer.probabilities)}
        else:
            entry = {"type": "noul", "noul": answer.noul}
        out[_safe_id(qid, f"q{n}")] = entry
    return out


def _number(value: object, maximum: float = 1) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise JudgmentError("invalid_response", "Jev response has an invalid numeric value")
    return value


def _probabilities(value: object, options: set[str]) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != options:
        raise JudgmentError("invalid_response", "Jev response has invalid probability options")
    for probability in value.values():
        _number(probability)
    if abs(sum(value.values()) - 1) > PROBABILITY_SUM_TOLERANCE:
        raise JudgmentError("invalid_response", "Jev probabilities do not sum to one")
    return dict(value)


def parse_response(body: object, questions: Mapping[str, Question]) -> tuple[dict[str, Answer], str, int, int]:
    if not isinstance(body, dict) or not isinstance(body.get("model"), str):
        raise JudgmentError("invalid_response", "Jev response is missing a model")
    usage = body.get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")):
        raise JudgmentError("invalid_response", "Jev response has invalid token usage")
    raw = body.get("answers")
    if not isinstance(raw, dict) or set(raw) != set(questions):
        raise JudgmentError("invalid_response", "Jev response has missing or extra answers")
    answers = {}
    for qid, question in questions.items():
        answer = raw[qid]
        expected = "choice" if isinstance(question, ChoiceQuestion) else "score" if isinstance(question, ScoreQuestion) else "noul"
        if not isinstance(answer, dict) or answer.get("type") != expected:
            raise JudgmentError("invalid_response", "Jev answer type does not match question")
        if isinstance(question, ChoiceQuestion):
            probabilities = _probabilities(answer.get("probabilities"), set(question.criteria))
            choice = answer.get("choice")
            if not isinstance(choice, str) or choice not in probabilities:
                raise JudgmentError("invalid_response", "Jev response chose an unknown option")
            answers[qid] = ChoiceResult(choice, probabilities, _number(answer.get("confidence")))
        elif isinstance(question, ScoreQuestion):
            probabilities = _probabilities(answer.get("probabilities"), {str(i) for i in range(len(question.criteria))})
            answers[qid] = ScoreResult(_number(answer.get("score"), len(question.criteria) - 1), probabilities, _number(answer.get("confidence")))
        else:
            answers[qid] = NoulResult(_number(answer.get("noul")))
    return answers, body["model"], usage["input_tokens"], usage["output_tokens"]


class JevClient:
    def __init__(
        self, api_key: str, *, model: str, timeout_ms: int, max_request_bytes: int,
        max_calls: int, max_cost_usd: float, client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        ledger: JudgmentLedger | None = None,
    ):
        self._api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self.max_request_bytes = max_request_bytes
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self._client = client
        self._owned = client is None
        self._sleep = sleep
        self._clock = clock
        self.ledger = ledger if ledger is not None else JudgmentLedger(max_calls, max_cost_usd)

    @property
    def calls_used(self) -> int:
        return self.ledger.calls_used

    @property
    def spent_usd(self) -> float:
        return self.ledger.observed_usd + self.ledger.held_usd

    async def evaluate(
        self, state: object, questions: Mapping[str, Question], *, call_id: str | None = None,
        purpose: str = "explicit", rubric_version: str | None = None, artifact_revision: str | None = None,
    ) -> JudgmentResult:
        if not SAFE_PURPOSE.fullmatch(purpose):
            raise ValueError("purpose must be a lowercase identifier")
        call_id = uuid.uuid4().hex if call_id is None else call_id
        payload = json.dumps({"model": self.model, "state": state, "questions": {qid: q.to_wire() for qid, q in questions.items()}}, allow_nan=False).encode()
        start = self._clock()
        status, result, error = "unavailable", None, None
        try:
            result = await self._dispatch(payload, questions, call_id, start)
            status = "answered"
            return result
        except JudgmentError as err:
            status, error = err.outcome, err
            raise
        except asyncio.CancelledError:
            status = "cancelled"
            raise
        finally:
            self.ledger.release(call_id)
            entries = [e for e in self.ledger.entries if e.call_id == call_id]
            receipt = JudgmentReceipt(
                call_id, purpose, rubric_version, self.model, result.model if result else None, "explicit", status, None,
                len(entries), result.input_tokens if result else None, result.output_tokens if result else None,
                next((e.cost_usd for e in entries if e.state == "settled"), None),
                sum(e.reserved for e in entries if e.state == "unknown"), (self._clock() - start) * 1000,
                _receipt_answers(questions, result.answers) if result else {}, artifact_revision,
            )
            self.ledger.receipts.append(receipt)
            if error is not None:
                error.receipt = receipt

    async def _dispatch(self, payload: bytes, questions: Mapping[str, Question], call_id: str, start: float) -> JudgmentResult:
        if len(payload) > self.max_request_bytes:
            raise JudgmentError("budget_exhausted", "request exceeds max_request_bytes")
        deadline = start + self.timeout_ms / 1000
        attempts = 0
        reservation = MAX_REQUEST_TOKENS * USD_PER_INPUT_TOKEN
        try:
            async with asyncio.timeout(self.timeout_ms / 1000):
                for attempt in range(2):
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        raise JudgmentError("unavailable", "Jev deadline exceeded", attempts=attempts)
                    try:
                        entry = self.ledger.reserve(call_id, reservation)
                    except JudgmentError as err:
                        err.attempts = attempts
                        raise
                    if self._client is None:
                        self._client = httpx.AsyncClient()
                    attempts += 1
                    response = await self._client.post(
                        JEV_URL, content=payload,
                        headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                        timeout=httpx.Timeout(remaining),
                    )
                    if response.status_code == 200:
                        try:
                            body = response.json()
                        except ValueError:
                            raise JudgmentError("invalid_response", "Jev response is not valid JSON", attempts=attempts) from None
                        try:
                            answers, model, input_tokens, output_tokens = parse_response(body, questions)
                        except JudgmentError as err:
                            err.attempts = attempts
                            raise
                        cost = input_tokens * USD_PER_INPUT_TOKEN
                        self.ledger.settle(entry, cost)
                        return JudgmentResult(answers, model, input_tokens, output_tokens, (self._clock() - start) * 1000, cost, attempts)
                    if response.status_code in RETRY_STATUSES and attempt == 0:
                        try:
                            delay = float(response.headers.get("Retry-After", DEFAULT_BACKOFF_S))
                        except ValueError:
                            delay = DEFAULT_BACKOFF_S
                        if not math.isfinite(delay) or delay < 0:
                            delay = DEFAULT_BACKOFF_S
                        if self._clock() + delay < deadline:
                            await self._sleep(delay)
                            continue
                    raise JudgmentError("unavailable", f"Jev request failed (HTTP {response.status_code})", status=response.status_code, attempts=attempts)
        except (TimeoutError, httpx.TimeoutException):
            raise JudgmentError("unavailable", "Jev request timed out", attempts=attempts) from None
        except httpx.TransportError:
            raise JudgmentError("unavailable", "Jev request failed", attempts=attempts) from None

    async def aclose(self) -> None:
        if self._owned and self._client is not None:
            await self._client.aclose()

    async def __aenter__(self) -> JevClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()


def is_killed() -> bool:
    return os.environ.get(KILL_ENV, "").strip().lower() in {"off", "0", "false"}


def to_probable(result: Answer) -> ProbableValue:
    if not isinstance(result, ChoiceResult):
        raise TypeError("only ChoiceResult converts to ProbableValue")
    return result.to_probable()


def _new_client(api_key: str, cfg: RuntimeConfig, ledger: JudgmentLedger) -> JevClient:
    return JevClient(
        api_key, model=cfg.judgments_model, timeout_ms=cfg.judgments_timeout_ms,
        max_request_bytes=cfg.judgments_max_request_bytes, max_calls=cfg.judgments_max_calls_per_turn,
        max_cost_usd=cfg.judgments_max_cost_usd, ledger=ledger,
    )


async def judge(
    state: object, questions: Mapping[str, Question | Mapping], *, purpose: str = "explicit",
    ledger: JudgmentLedger | None = None,
) -> JudgmentResult:
    if is_killed():
        raise JudgmentError("disabled", KILLED_MESSAGE)
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise JudgmentError("unavailable", MISSING_KEY_MESSAGE)
    coerced = {}
    for qid, question in questions.items():
        if isinstance(question, Mapping):
            coerced[qid] = question_from_wire(question)
        elif isinstance(question, (ChoiceQuestion, ScoreQuestion, NoulQuestion)):
            coerced[qid] = question
        else:
            raise TypeError("questions must be question objects or wire-format dicts")
    cfg = get_config()
    if ledger is None:
        ledger = current_ledger()
    if ledger is None:
        ledger = JudgmentLedger(cfg.judgments_max_calls_per_turn, cfg.judgments_max_cost_usd)
    call_id = uuid.uuid4().hex
    async with _new_client(key, cfg, ledger) as client:
        result = await client.evaluate(state, coerced, call_id=call_id, purpose=purpose)
    return replace(result, receipt=ledger.receipt(call_id))

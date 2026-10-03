from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
import json
import math
import time
from typing import Literal

import httpx

from .exceptions import VossRuntimeError

JEV_URL = "https://api.typesafe.ai/v1/systemone"
USD_PER_INPUT_TOKEN = 0.042 / 1_000_000
MAX_REQUEST_TOKENS = 64_000
PROBABILITY_SUM_TOLERANCE = 0.02
RETRY_STATUSES = frozenset({429, 529})
DEFAULT_BACKOFF_S = 0.25
Outcome = Literal["answered", "abstained", "disabled", "unavailable", "budget_exhausted", "invalid_response"]
Description = str | dict | list


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


@dataclass(frozen=True)
class ChoiceResult:
    choice: str
    probabilities: dict[str, float]
    confidence: float
    type: str = field(default="choice", init=False)


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


class JudgmentError(VossRuntimeError):
    def __init__(self, outcome: Outcome, message: str, *, status: int | None = None, attempts: int = 0):
        self.outcome = outcome
        self.status = status
        self.attempts = attempts
        super().__init__(message)


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
        self.calls_used = 0
        self.spent_usd = 0.0

    async def evaluate(self, state: object, questions: Mapping[str, Question]) -> JudgmentResult:
        payload = json.dumps({"model": self.model, "state": state, "questions": {qid: q.to_wire() for qid, q in questions.items()}}, allow_nan=False).encode()
        if len(payload) > self.max_request_bytes:
            raise JudgmentError("budget_exhausted", "request exceeds max_request_bytes")
        start = self._clock()
        deadline = start + self.timeout_ms / 1000
        attempts = 0
        reservation = MAX_REQUEST_TOKENS * USD_PER_INPUT_TOKEN
        try:
            async with asyncio.timeout(self.timeout_ms / 1000):
                for attempt in range(2):
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        raise JudgmentError("unavailable", "Jev deadline exceeded", attempts=attempts)
                    if self.calls_used >= self.max_calls or self.spent_usd + reservation > self.max_cost_usd:
                        raise JudgmentError("budget_exhausted", "Jev attempt or cost allowance exhausted", attempts=attempts)
                    if self._client is None:
                        self._client = httpx.AsyncClient()
                    self.calls_used += 1
                    self.spent_usd += reservation
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
                        self.spent_usd += cost - reservation
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

from __future__ import annotations

import asyncio
from contextvars import ContextVar
import dataclasses
import hashlib
import json
from typing import Literal
import uuid

from voss.harness import config, judgments
from voss.harness.code.semantic_index import Candidate
from voss.harness.memory_store import Hit
from voss_runtime.judgments import JudgmentError, JudgmentLedger, JudgmentReceipt, ScoreQuestion, is_killed

PURPOSE = "code_recall.rerank"
RUBRIC_VERSION = "code_recall.rerank.v1"
RERANK_DEADLINE_MS = 1500
TASK_CHARS = 2000
LEVELS = (
    "irrelevant: not needed for this task",
    "contextual: useful background only",
    "directly_useful: helps complete the task",
    "necessary: the task cannot be done without it",
)
TIMEOUT_MESSAGES = ("Jev request timed out", "Jev deadline exceeded")


def request_size(model: str, state: dict, questions: dict[str, ScoreQuestion]) -> int:
    return len(json.dumps({"model": model, "state": state, "questions": {qid: q.to_wire() for qid, q in questions.items()}}, allow_nan=False).encode())


def _cid(i: int) -> str:
    return f"c{i + 1:02d}"


def _state(candidates: list[Candidate], task: str, query: str | None, limit: int | None) -> dict:
    state: dict = {"task": task[:TASK_CHARS]}
    if query:
        state["query"] = query
    state["candidates"] = [
        {"id": _cid(i), "path": c.path, "lines": f"{c.line_start}-{c.line_end}", "text": c.text if limit is None else c.text[:limit]}
        for i, c in enumerate(candidates)
    ]
    return state


def _questions(candidates: list[Candidate], query: str | None) -> dict[str, ScoreQuestion]:
    search = " and the search in state.query" if query else ""
    return {
        _cid(i): ScoreQuestion(
            f"Rate how useful candidate {_cid(i)} ({c.path}:{c.line_start}-{c.line_end}) in state.candidates is for the task in state.task{search}. Judge only that candidate's text.",
            list(LEVELS),
        )
        for i, c in enumerate(candidates)
    }


def build_request(
    candidates: list[Candidate], task: str, query: str | None, *, model: str, max_bytes: int,
) -> tuple[dict, dict[str, ScoreQuestion], bool] | None:
    if not candidates:
        return None
    questions = _questions(candidates, query)
    state = _state(candidates, task, query, None)
    if request_size(model, state, questions) <= max_bytes:
        return state, questions, False
    lo, hi = 0, max(len(c.text) for c in candidates)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if request_size(model, _state(candidates, task, query, mid), questions) <= max_bytes:
            lo = mid
        else:
            hi = mid - 1
    if lo == 0:
        return None
    return _state(candidates, task, query, lo), questions, True


def expected_level(answer) -> float:
    return round(sum(int(k) * p for k, p in answer.probabilities.items()), 6)


def order_by_levels(levels: list[float]) -> list[int]:
    return sorted(range(len(levels)), key=lambda i: -levels[i])


def revision(candidates: list[Candidate]) -> str:
    lines = "\n".join(f"{c.hit.locator}:{hashlib.sha256(c.text.encode()).hexdigest()[:12]}" for c in candidates)
    return hashlib.sha256(lines.encode()).hexdigest()[:16]


def _finish(
    ledger: JudgmentLedger, call_id: str, candidates: list[Candidate], order: list[int], *, mode: str,
    reason: str | None, status: str = "unavailable", trimmed: bool = False, request_bytes: int = 0,
) -> list[int]:
    detail = {
        "order": [candidates[i].hit.locator for i in order], "trimmed": trimmed,
        "request_bytes": request_bytes, "pool_size": len(candidates),
    }
    for n, receipt in enumerate(ledger.receipts):
        if receipt.call_id == call_id:
            ledger.receipts[n] = dataclasses.replace(receipt, mode=mode, fallback_reason=reason, detail=detail)
            return order
    ledger.receipts.append(JudgmentReceipt(
        call_id, PURPOSE, RUBRIC_VERSION, config.get_judgments_config()["model"], None, mode, status, reason,
        0, None, None, None, 0.0, 0.0, {}, revision(candidates), detail=detail,
    ))
    return order


async def rerank(
    candidates: list[Candidate], *, task: str, query: str | None = None, mode: Literal["shadow", "active"],
    ledger: JudgmentLedger, call_id: str | None = None,
) -> list[int]:
    baseline = list(range(len(candidates)))
    call_id = uuid.uuid4().hex if call_id is None else call_id

    def fallback(reason: str, status: str = "unavailable", **sizes) -> list[int]:
        return _finish(ledger, call_id, candidates, baseline, mode=mode, reason=reason, status=status, **sizes)

    if not candidates:
        return fallback("empty")
    if not all(c.fresh for c in candidates):
        return fallback("stale_chunk")
    if is_killed():
        return fallback("disabled", "disabled")
    found = judgments.resolve_api_key()
    if found is None:
        return fallback("no_key")
    cfg = config.get_judgments_config()
    built = build_request(candidates, task, query, model=cfg["model"], max_bytes=cfg["max_request_bytes"])
    if built is None:
        return fallback("oversize")
    state, questions, trimmed = built
    sizes = {"trimmed": trimmed, "request_bytes": request_size(cfg["model"], state, questions)}
    client = judgments.make_client(found[0], timeout_ms=RERANK_DEADLINE_MS, ledger=ledger)
    try:
        async with client:
            result = await client.evaluate(
                state, questions, call_id=call_id, purpose=PURPOSE,
                rubric_version=RUBRIC_VERSION, artifact_revision=revision(candidates),
            )
    except JudgmentError as err:
        return fallback("timeout" if str(err) in TIMEOUT_MESSAGES else err.outcome, **sizes)
    except asyncio.CancelledError:
        fallback("cancelled", "cancelled", **sizes)
        raise
    order = order_by_levels([expected_level(result.answers[_cid(i)]) for i in baseline])
    return _finish(ledger, call_id, candidates, order, mode=mode, reason=None, **sizes)


_current_turn: ContextVar[TurnScope | None] = ContextVar("_current_turn", default=None)


def current_turn() -> TurnScope | None:
    return _current_turn.get()


class TurnScope:
    def __init__(self, cwd, task_text: str, mode: Literal["off", "shadow", "active"]):
        cfg = config.get_judgments_config()
        self.cwd = cwd
        self.task_text = task_text
        self.mode = mode
        self.ledger = JudgmentLedger(cfg["max_calls_per_turn"], cfg["max_cost_usd"])
        self._shadow: dict[str, tuple[asyncio.Task, list[Candidate]]] = {}
        self._token = None

    async def __aenter__(self) -> TurnScope:
        await self.ledger.__aenter__()
        self._token = _current_turn.set(self)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        try:
            for task, _ in self._shadow.values():
                task.cancel()
            await asyncio.gather(*(task for task, _ in self._shadow.values()), return_exceptions=True)
            for call_id, (task, candidates) in self._shadow.items():
                if task.cancelled() and self.ledger.receipt(call_id) is None:
                    _finish(self.ledger, call_id, candidates, list(range(len(candidates))), mode="shadow", reason="cancelled", status="cancelled")
        finally:
            _current_turn.reset(self._token)
            self._token = None
            await self.ledger.__aexit__(exc_type, exc, tb)
        return False

    def spawn_shadow(self, candidates: list[Candidate], *, query: str | None) -> asyncio.Task:
        call_id = uuid.uuid4().hex
        task = asyncio.create_task(rerank(candidates, task=self.task_text, query=query, mode="shadow", ledger=self.ledger, call_id=call_id))
        self._shadow[call_id] = (task, candidates)
        return task


async def recall(service, search_text: str, *, k: int, query: str | None = None) -> list[Hit] | None:
    scope = current_turn()
    if scope is None or scope.mode == "off":
        return None
    cands = await asyncio.to_thread(service.candidates, search_text)
    if cands is not None and scope.mode == "shadow":
        scope.spawn_shadow(cands, query=query)
    elif cands is not None:
        call_id = uuid.uuid4().hex
        order = await rerank(cands, task=scope.task_text, query=query, mode="active", ledger=scope.ledger, call_id=call_id)
        if scope.ledger.receipt(call_id).fallback_reason is None:
            return [cands[i].hit for i in order[:k]]
    return await asyncio.to_thread(service.query, search_text, top_k=k)

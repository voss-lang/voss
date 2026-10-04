"""J3-04 D-02/D-03/D-20/D-23: per-turn scope, shadow tasks and recall()."""
from __future__ import annotations

import asyncio
import time

import httpx

from voss.harness import config
from voss.harness.code import rerank as rr
from voss.harness.memory_store import Hit
from voss_runtime.judgments import current_ledger

from .conftest import make_candidates, score_body

FAVOR_C03 = {f"c{i:02d}": 3 if i == 3 else 2 if i == 7 else 0 for i in range(1, 16)}


class FakeService:
    def __init__(self, pool):
        self.pool = pool
        self.legacy = [Hit(source="code", locator=f"code:legacy/l{i}.py:000", score=1.0, excerpt="") for i in range(10)]
        self.queries = []

    def is_ready(self):
        return True

    def candidates(self, query):
        return self.pool

    def query(self, query, top_k=5):
        self.queries.append((query, top_k))
        return self.legacy[:top_k]


async def _until(predicate, timeout=2.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "condition not reached"
        await asyncio.sleep(0.01)


def _shadow_receipt(scope):
    return next((r for r in scope.ledger.receipts if r.mode == "shadow"), None)


async def test_current_turn_is_visible_in_gather_children_and_threads(tmp_path):
    assert rr.current_turn() is None
    async with rr.TurnScope(tmp_path, "task", "shadow") as scope:
        assert rr.current_turn() is scope

        async def child():
            return rr.current_turn()

        assert await asyncio.gather(child(), child()) == [scope, scope]
        assert await asyncio.to_thread(rr.current_turn) is scope
    assert rr.current_turn() is None


async def test_turn_scope_owns_the_turn_ledger(tmp_path):
    cfg = config.get_judgments_config()
    async with rr.TurnScope(tmp_path, "task", "active") as scope:
        assert current_ledger() is scope.ledger
        assert (scope.ledger.max_calls, scope.ledger.max_cost_usd) == (cfg["max_calls_per_turn"], cfg["max_cost_usd"])
    assert current_ledger() is None


async def test_shadow_returns_legacy_hits_without_waiting_then_records_would_have_order(jev, tmp_path):
    pool = make_candidates(15)
    svc = FakeService(pool)
    gate = asyncio.Event()

    async def blocked(request):
        await gate.wait()
        return httpx.Response(200, json=score_body(FAVOR_C03))

    jev.handler = blocked
    async with rr.TurnScope(tmp_path, "task", "shadow") as scope:
        hits = await rr.recall(svc, "q", k=5)
        assert hits == svc.legacy[:5]
        assert svc.queries == [("q", 5)]
        assert not gate.is_set() and scope.ledger.receipts == []
        gate.set()
        await _until(lambda: _shadow_receipt(scope) is not None)
        receipt = _shadow_receipt(scope)
        assert (receipt.status, receipt.fallback_reason) == ("answered", None)
        assert receipt.detail["order"][:2] == [pool[2].hit.locator, pool[6].hit.locator]
        assert sorted(receipt.detail["order"]) == sorted(c.hit.locator for c in pool)


async def test_shadow_timeout_records_timeout_and_still_returns_legacy_hits(jev, tmp_path, monkeypatch):
    monkeypatch.setattr(rr, "RERANK_DEADLINE_MS", 50)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=score_body(FAVOR_C03))

    jev.handler = slow
    svc = FakeService(make_candidates(15))
    async with rr.TurnScope(tmp_path, "task", "shadow") as scope:
        assert await rr.recall(svc, "q", k=5) == svc.legacy[:5]
        await _until(lambda: _shadow_receipt(scope) is not None)
        assert _shadow_receipt(scope).fallback_reason == "timeout"


async def test_shadow_still_pending_at_scope_exit_is_cancelled_with_one_receipt(jev, tmp_path):
    async def never(request):
        await asyncio.sleep(3600)

    jev.handler = never
    pool = make_candidates(15)
    async with rr.TurnScope(tmp_path, "task", "shadow") as scope:
        await rr.recall(FakeService(pool), "q", k=5)
        await _until(lambda: len(jev.requests) == 1)
        started = time.monotonic()
    assert time.monotonic() - started < 1.0
    [receipt] = scope.ledger.receipts
    assert (receipt.status, receipt.mode, receipt.fallback_reason) == ("cancelled", "shadow", "cancelled")
    assert receipt.detail["order"] == [c.hit.locator for c in pool]


async def test_shadow_cancelled_before_evaluate_starts_leaves_one_cancelled_receipt(jev, tmp_path):
    pool = make_candidates(15)
    async with rr.TurnScope(tmp_path, "task", "shadow") as scope:
        scope.spawn_shadow(pool, query=None)
    [receipt] = scope.ledger.receipts
    assert (receipt.status, receipt.mode, receipt.attempts) == ("cancelled", "shadow", 0)
    assert jev.requests == []


async def test_active_returns_reranked_pool_hits(jev, tmp_path):
    pool = make_candidates(15)
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C03))
    async with rr.TurnScope(tmp_path, "task", "active"):
        hits = await rr.recall(FakeService(pool), "q", k=3)
    assert hits == [pool[2].hit, pool[6].hit, pool[0].hit]


async def test_active_fallback_returns_legacy_hits(jev, tmp_path):
    jev.handler = lambda request: httpx.Response(500)
    svc = FakeService(make_candidates(15))
    async with rr.TurnScope(tmp_path, "task", "active") as scope:
        assert await rr.recall(svc, "q", k=5) == svc.legacy[:5]
    assert scope.ledger.receipts[0].fallback_reason == "unavailable"

    svc = FakeService(make_candidates(15, fresh=False))
    async with rr.TurnScope(tmp_path, "task", "active") as scope:
        assert await rr.recall(svc, "q", k=5) == svc.legacy[:5]
    assert scope.ledger.receipts[0].fallback_reason == "stale_chunk"
    assert len(jev.requests) == 1


async def test_recall_returns_none_without_scope_or_in_off_mode(jev, tmp_path):
    svc = FakeService(make_candidates(15))
    assert await rr.recall(svc, "q", k=5) is None
    async with rr.TurnScope(tmp_path, "task", "off"):
        assert await rr.recall(svc, "q", k=5) is None
    assert svc.queries == [] and jev.requests == []


async def test_recall_uses_legacy_hits_when_candidates_are_unavailable(jev, tmp_path):
    svc = FakeService(None)
    for mode in ("shadow", "active"):
        async with rr.TurnScope(tmp_path, "task", mode) as scope:
            assert await rr.recall(svc, "q", k=5) == svc.legacy[:5]
        assert scope.ledger.receipts == []
    assert jev.requests == []


async def test_pre_turn_and_tool_calls_share_the_turn_cap(jev, tmp_path, monkeypatch):
    monkeypatch.setattr(rr, "RERANK_DEADLINE_MS", 50)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=score_body(FAVOR_C03))

    jev.handler = slow
    svc = FakeService(make_candidates(15))
    async with rr.TurnScope(tmp_path, "task", "active") as scope:
        await rr.recall(svc, "task", k=5)
        await rr.recall(svc, "where is retry handled", k=5, query="where is retry handled")
        await rr.recall(svc, "json codec", k=5, query="json codec")
        assert len(jev.requests) == 3
        assert await rr.recall(svc, "cache", k=5, query="cache") == svc.legacy[:5]
    assert [r.fallback_reason for r in scope.ledger.receipts] == ["timeout", "timeout", "timeout", "budget_exhausted"]
    assert len(jev.requests) == 3

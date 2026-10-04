"""J3-06 S3.3/S3.4: the code_recall tool follows the turn's rerank policy and ledger."""
from __future__ import annotations

import asyncio
import json
import time

import httpx

from voss.harness.code import rerank as rr
from voss.harness.memory_store import Hit
from voss.harness.tools import attach_code_recall_tool

from .conftest import make_candidates, score_body, write_fixture_repo

FAVOR_C04 = {f"c{i:02d}": 3 if i == 4 else 0 for i in range(1, 16)}


class FakeService:
    def __init__(self, pool):
        self.pool = pool
        self.legacy = [
            Hit(source="code", locator=f"code:legacy/l{i}.py:000", score=1.0 / (i + 1), excerpt=f"line one {i}\nline two", line_start=i + 1)
            for i in range(10)
        ]
        self.queries = []

    def is_ready(self):
        return True

    def candidates(self, query):
        return self.pool

    def query(self, query, top_k=5):
        self.queries.append((query, top_k))
        return self.legacy[:top_k]


def _format_code_recall_hits(hits):
    lines = []
    for h in hits:
        path = h.locator.split(":")[1]
        lines.append(f"[code] {path}:{h.line_start} (score {h.score:.2f})")
        lines.append("  " + h.excerpt.replace("\n", " ")[:160])
    return "\n".join(lines)


def _tool(service):
    tools = {}
    attach_code_recall_tool(tools, code_index_service=service)
    return tools["code_recall"].descriptor


def _favor_c04(request):
    return httpx.Response(200, json=score_body(FAVOR_C04))


async def _until(predicate, timeout=30.0):
    end = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < end, "condition not reached"
        await asyncio.sleep(0.01)


async def test_without_a_scope_the_tool_output_is_unchanged(jev):
    svc = FakeService(make_candidates(15))
    out = await _tool(svc)(query="  retry  ", top_k=2)
    assert out == (
        "[code] legacy/l0.py:1 (score 1.00)\n  line one 0 line two\n"
        "[code] legacy/l1.py:2 (score 0.50)\n  line one 1 line two"
    )
    assert svc.queries == [("retry", 2)]
    assert jev.requests == []


async def test_off_mode_scope_keeps_the_legacy_output(jev, tmp_path):
    svc = FakeService(make_candidates(15))
    async with rr.TurnScope(tmp_path, "task", "off") as scope:
        out = await _tool(svc)(query="retry", top_k=5)
    assert out == _format_code_recall_hits(svc.legacy[:5])
    assert jev.requests == [] and scope.ledger.receipts == []


async def test_active_reorders_the_pool_keeping_top_k_and_line_format(jev, tmp_path):
    pool = make_candidates(15)
    jev.handler = _favor_c04
    async with rr.TurnScope(tmp_path, "task", "active"):
        out = await _tool(FakeService(pool))(query="retry", top_k=5)
    code_lines = [line for line in out.splitlines() if line.startswith("[code]")]
    assert len(code_lines) == 5
    assert code_lines[0] == "[code] pkg/m3.py:1 (score 0.25)"
    assert out == _format_code_recall_hits([pool[i].hit for i in (3, 0, 1, 2, 4)])


async def test_active_sends_the_agent_query_and_trimmed_task_on_the_turn_ledger(jev, tmp_path):
    task = "fix the retry loop " * 200
    jev.handler = _favor_c04
    async with rr.TurnScope(tmp_path, task, "active") as scope:
        await _tool(FakeService(make_candidates(15)))(query="where is retry handled", top_k=5)
    [request] = jev.requests
    state = json.loads(request.content)["state"]
    assert state["query"] == "where is retry handled"
    assert state["task"] == task[:2000]
    [receipt] = scope.ledger.receipts
    assert (receipt.purpose, receipt.mode, receipt.fallback_reason) == (rr.PURPOSE, "active", None)


async def test_shadow_shows_the_legacy_order_and_records_a_shadow_receipt(jev, tmp_path):
    svc = FakeService(make_candidates(15))
    jev.handler = _favor_c04
    async with rr.TurnScope(tmp_path, "task", "shadow") as scope:
        out = await _tool(svc)(query="retry", top_k=5)
        assert out == _format_code_recall_hits(svc.legacy[:5])
    [receipt] = scope.ledger.receipts
    assert receipt.mode == "shadow"


async def test_index_not_ready_keeps_degraded_bm25_output_in_active_mode(jev, tmp_path):
    write_fixture_repo(tmp_path)
    from voss.harness.code.index import build_index
    from voss.harness.code.semantic_index import CodeIndexService

    build_index(tmp_path)
    svc = CodeIndexService(tmp_path, session_id="test-session")
    assert {h.source for h in svc.query("retry backoff delay")} == {"code[degraded]"}
    legacy = await _tool(svc)(query="retry backoff delay")
    async with rr.TurnScope(tmp_path, "task", "active") as scope:
        out = await _tool(svc)(query="retry backoff delay")
    assert out == legacy and out.startswith("[code] alpha.py")
    assert jev.requests == [] and scope.ledger.receipts == []


async def test_chroma_query_failure_keeps_unmarked_bm25_output_in_active_mode(jev, indexed_fixture_repo, monkeypatch):
    from voss.harness.code.semantic_index import CodeIndex, CodeIndexService

    svc = CodeIndexService(indexed_fixture_repo, session_id="test-session")
    svc.ensure_background_build()
    await _until(svc.is_ready)

    def _boom(self, sem, query, top_k):
        raise RuntimeError("chroma down")

    monkeypatch.setattr(CodeIndex, "_chroma_query", _boom)
    assert {h.source for h in svc.query("retry backoff delay")} == {"code"}
    legacy = await _tool(svc)(query="retry backoff delay")
    async with rr.TurnScope(indexed_fixture_repo, "task", "active") as scope:
        out = await _tool(svc)(query="retry backoff delay")
    assert out == legacy and out.startswith("[code] alpha.py")
    assert jev.requests == [] and scope.ledger.receipts == []


async def test_gathered_tool_calls_still_see_the_turn_and_rerank(jev, tmp_path):
    pool = make_candidates(15)
    jev.handler = _favor_c04
    tool = _tool(FakeService(pool))
    async with rr.TurnScope(tmp_path, "task", "active") as scope:
        outs = await asyncio.gather(tool(query="a", top_k=1), tool(query="b", top_k=1))
    assert outs == [_format_code_recall_hits([pool[3].hit])] * 2
    assert len(scope.ledger.receipts) == 2


async def test_rerank_path_failure_returns_the_tool_error_string(jev, tmp_path):
    class Broken(FakeService):
        def candidates(self, query):
            raise RuntimeError("boom")

    async with rr.TurnScope(tmp_path, "task", "active"):
        out = await _tool(Broken(None))(query="retry")
    assert out == "<error: code recall failed: boom>"

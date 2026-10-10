"""J3-04 S3.2/S3.4: rerank request, trimming, ordering and fallbacks."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
import json

import httpx
import pytest

from voss.harness.code import rerank as rr
from voss_runtime.judgments import MAX_REQUEST_TOKENS, USD_PER_INPUT_TOKEN, JudgmentLedger, ScoreResult

from .conftest import make_candidates, score_body

RESERVATION = MAX_REQUEST_TOKENS * USD_PER_INPUT_TOKEN
MODEL = "jev-1.13.0"


def _all(levels: list) -> dict:
    return {f"c{i + 1:02d}": level for i, level in enumerate(levels)}


def _answer(probabilities: dict) -> ScoreResult:
    return ScoreResult(0.0, probabilities, 1.0)


def test_request_has_one_question_per_candidate_in_pool_order():
    pool = make_candidates(15)
    state, questions, trimmed = rr.build_request(pool, "fix the retry", None, model=MODEL, max_bytes=24000)

    assert list(questions) == [f"c{i:02d}" for i in range(1, 16)]
    for cid, c in zip(questions, pool):
        wire = questions[cid].to_wire()
        assert wire["type"] == "score"
        assert cid in wire["instructions"] and f"{c.path}:{c.line_start}-{c.line_end}" in wire["instructions"]
        assert wire["criteria"] == list(rr.LEVELS)
    assert [level.split(":")[0] for level in rr.LEVELS] == ["irrelevant", "contextual", "directly_useful", "necessary"]
    assert trimmed is False
    assert [s["id"] for s in state["candidates"]] == list(questions)


def test_request_state_carries_task_prefix_query_and_full_chunk_text():
    pool = make_candidates(3, texts=["a" * 900, "b\nc", "é"])
    task = "t" * 2500
    state, questions, _ = rr.build_request(pool, task, None, model=MODEL, max_bytes=24000)

    assert state["task"] == task[:2000] and "query" not in state
    assert all("state.query" not in q.instructions for q in questions.values())
    for entry, c in zip(state["candidates"], pool):
        assert entry == {"id": entry["id"], "path": c.path, "lines": f"{c.line_start}-{c.line_end}", "text": c.text}

    state, questions, _ = rr.build_request(pool, task, "where is retry handled", model=MODEL, max_bytes=24000)
    assert state["query"] == "where is retry handled"
    assert all("state.query" in q.instructions for q in questions.values())


def test_trim_cuts_every_chunk_to_one_shared_prefix_under_the_byte_cap():
    texts = [("é\n" * 2000) if i % 2 else ("x\n" * 2000) for i in range(13)] + ["short", "é\nshort"]
    pool = make_candidates(15, texts=texts)
    state, questions, trimmed = rr.build_request(pool, "task", "q", model=MODEL, max_bytes=24000)

    assert trimmed is True
    assert rr.request_size(MODEL, state, questions) <= 24000
    sent = [s["text"] for s in state["candidates"]]
    limit = max(len(t) for t in sent)
    assert 1 <= limit < 4000
    assert all(s == c.text[:limit] for s, c in zip(sent, pool))
    assert sent[-2:] == ["short", "é\nshort"]


def test_trim_leaves_a_small_pool_untouched():
    pool = make_candidates(4)
    state, _, trimmed = rr.build_request(pool, "task", None, model=MODEL, max_bytes=24000)

    assert trimmed is False
    assert [s["text"] for s in state["candidates"]] == [c.text for c in pool]


def test_trim_returns_none_for_empty_pool_or_when_only_empty_chunks_fit():
    assert rr.build_request([], "task", None, model=MODEL, max_bytes=24000) is None
    assert rr.build_request(make_candidates(15), "t" * 5000, None, model=MODEL, max_bytes=2000) is None


def test_order_sorts_by_level_descending():
    assert rr.order_by_levels([1.0, 3.0, 2.0]) == [1, 2, 0]


def test_order_ties_keep_baseline_order():
    assert rr.order_by_levels([2.0, 1.0, 2.0, 1.0]) == [0, 2, 1, 3]
    near = [rr.expected_level(_answer({"0": 0.25, "1": 0.25, "2": 0.25, "3": 0.25})),
            rr.expected_level(_answer({"0": 0.25 - 1e-8, "1": 0.25, "2": 0.25, "3": 0.25 + 1e-8}))]
    assert near[0] == near[1]
    assert rr.order_by_levels(near) == [0, 1]


def test_order_is_always_a_permutation():
    levels = [0.0, 3.0, 1.5, 1.5, 2.999999, 0.000001, 3.0]
    assert sorted(rr.order_by_levels(levels)) == list(range(len(levels)))


def test_expected_level_is_probability_weighted():
    assert rr.expected_level(_answer({"0": 0.1, "1": 0.2, "2": 0.3, "3": 0.4})) == 2.0


def test_revision_is_stable_and_content_sensitive():
    pool = make_candidates(5)
    rev = rr.revision(pool)

    assert rev == rr.revision(make_candidates(5))
    assert len(rev) == 16 and int(rev, 16) >= 0
    changed = [*pool[:2], replace(pool[2], text=pool[2].text + " "), *pool[3:]]
    assert rr.revision(changed) != rev


def _ok(levels: dict):
    return lambda request: httpx.Response(200, json=score_body(levels))


def _locators(pool, order):
    return [pool[i].hit.locator for i in order]


async def test_fallback_none_answered_call_reorders_and_annotates_receipt(jev):
    pool = make_candidates(15)
    jev.handler = _ok(_all([0, 1, 3, *([0] * 12)]))
    ledger = JudgmentLedger(4, 0.01)
    order = await rr.rerank(pool, task="task", mode="active", ledger=ledger)

    assert order[0] == 2 and sorted(order) == list(range(15))
    assert order == [2, 1, 0, *range(3, 15)]
    [receipt] = ledger.receipts
    assert (receipt.purpose, receipt.rubric_version, receipt.mode, receipt.status, receipt.fallback_reason) == (
        "code_recall.rerank", rr.RUBRIC_VERSION, "active", "answered", None)
    assert receipt.artifact_revision == rr.revision(pool)
    assert receipt.detail["order"] == _locators(pool, order)
    assert receipt.detail["pool_size"] == 15 and receipt.detail["request_bytes"] > 0
    assert receipt.detail["trimmed"] is False
    assert jev.timeouts == [rr.RERANK_DEADLINE_MS] == [1500]


async def test_fallback_timeout_keeps_baseline(jev, monkeypatch):
    monkeypatch.setattr(rr, "RERANK_DEADLINE_MS", 50)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=score_body(_all([3] * 15)))

    jev.handler = slow
    pool = make_candidates(15)
    ledger = JudgmentLedger(4, 0.01)

    assert await rr.rerank(pool, task="task", mode="active", ledger=ledger) == list(range(15))
    [receipt] = ledger.receipts
    assert receipt.fallback_reason == "timeout" and receipt.mode == "active"
    assert receipt.detail["order"] == _locators(pool, range(15))


async def test_fallback_timeout_reason_pins_both_runtime_timeout_messages(jev, monkeypatch):
    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=score_body(_all([3] * 3)))

    jev.handler = slow
    pool = make_candidates(3)
    for deadline_ms in (50, 0):
        monkeypatch.setattr(rr, "RERANK_DEADLINE_MS", deadline_ms)
        ledger = JudgmentLedger(4, 0.01)
        assert await rr.rerank(pool, task="task", mode="active", ledger=ledger) == [0, 1, 2]
        [receipt] = ledger.receipts
        assert receipt.fallback_reason == "timeout"
    assert len(jev.requests) == 1


@pytest.mark.parametrize("response, reason", [
    (httpx.Response(500), "unavailable"),
    (httpx.Response(200, content=b"not json"), "invalid_response"),
    (httpx.Response(200, json=score_body(_all([3] * 14))), "invalid_response"),
    (httpx.Response(200, json=score_body(_all([3] * 14 + [{"0": 0.5, "1": 0.1, "2": 0.1, "3": 0.1}]))), "invalid_response"),
])
async def test_fallback_bad_response_keeps_whole_list_in_baseline(jev, response, reason):
    jev.handler = lambda request: response
    pool = make_candidates(15)
    ledger = JudgmentLedger(4, 0.01)

    assert await rr.rerank(pool, task="task", mode="active", ledger=ledger) == list(range(15))
    [receipt] = ledger.receipts
    assert receipt.fallback_reason == reason
    assert receipt.detail["order"] == _locators(pool, range(15))


async def test_fallback_budget_exhausted_makes_no_request(jev):
    ledger = JudgmentLedger(4, 0.01)
    for n in range(3):
        ledger.reserve(f"held{n}", RESERVATION)
    pool = make_candidates(15)

    assert await rr.rerank(pool, task="task", mode="active", ledger=ledger) == list(range(15))
    [receipt] = ledger.receipts
    assert receipt.fallback_reason == "budget_exhausted"
    assert jev.requests == []


def _oversize_config(monkeypatch):
    from voss.harness import config

    cfg = {**config.get_judgments_config(), "max_request_bytes": 2000}
    monkeypatch.setattr(config, "get_judgments_config", lambda: cfg)


@pytest.mark.parametrize("case, reason, status", [
    ("stale", "stale_chunk", "unavailable"),
    ("empty", "empty", "unavailable"),
    ("oversize", "oversize", "unavailable"),
    ("killed", "disabled", "disabled"),
    ("no_key", "no_key", "unavailable"),
])
async def test_fallback_without_dispatch_leaves_one_zero_attempt_receipt(jev, monkeypatch, case, reason, status):
    pool = make_candidates(15)
    task = "task"
    if case == "stale":
        pool[4] = replace(pool[4], fresh=False)
    elif case == "empty":
        pool = []
    elif case == "oversize":
        _oversize_config(monkeypatch)
        task = "t" * 5000
    elif case == "killed":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    else:
        monkeypatch.delenv("TYPESAFE_API_KEY")
    ledger = JudgmentLedger(4, 0.01)

    assert await rr.rerank(pool, task=task, mode="active", ledger=ledger) == list(range(len(pool)))
    [receipt] = ledger.receipts
    assert (receipt.status, receipt.fallback_reason, receipt.mode, receipt.attempts) == (status, reason, "active", 0)
    assert (receipt.input_tokens, receipt.cost_usd, receipt.held_usd, receipt.answers) == (None, None, 0.0, {})
    assert receipt.detail == {"order": _locators(pool, range(len(pool))), "trimmed": False, "request_bytes": 0, "pool_size": len(pool)}
    assert jev.requests == [] and jev.timeouts == []


async def test_fallback_receipts_are_content_free(jev):
    texts = [f"def f{i}():\n    return 'SENTINEL-CHUNK-7'\n" for i in range(15)]
    task = "please fix SENTINEL-TASK-7"
    ledger = JudgmentLedger(4, 0.01)
    jev.handler = _ok(_all([i % 4 for i in range(15)]))
    await rr.rerank(make_candidates(15, texts=texts), task=task, query="SENTINEL-TASK-7 query", mode="active", ledger=ledger)
    jev.handler = lambda request: httpx.Response(500)
    await rr.rerank(make_candidates(15, texts=texts), task=task, mode="active", ledger=ledger)
    stale = make_candidates(15, texts=texts, fresh=False)
    await rr.rerank(stale, task=task, mode="active", ledger=ledger)

    dumped = json.dumps([asdict(r) for r in ledger.receipts])
    assert len(ledger.receipts) == 3
    assert "SENTINEL-TASK-7" not in dumped and "SENTINEL-CHUNK-7" not in dumped


async def test_fallback_shadow_mode_labels_receipts(jev):
    jev.handler = _ok(_all([1] * 5))
    ledger = JudgmentLedger(4, 0.01)
    await rr.rerank(make_candidates(5), task="task", mode="shadow", ledger=ledger)
    await rr.rerank([], task="task", mode="shadow", ledger=ledger)

    assert [r.mode for r in ledger.receipts] == ["shadow", "shadow"]

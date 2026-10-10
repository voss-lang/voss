"""J3-07 J2 D-01/D-14: per-turn receipts on the run record and the merged judgments.json sidecar."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from pathlib import Path

import httpx
import pytest

from tests.harness.audit.test_audit_judgments import _receipt
from voss.harness import cli
from voss.harness.code import rerank as rr
from voss.harness.session_tree import write_judgments_sidecar
from voss_runtime import judgments as j

from .conftest import make_candidates, score_body
from .test_rerank_entrypoints import FAVOR_C07, FakeService, TASK, enable, fake_run_turn

ROOT = "root_j307"


def _ledger(*receipts, observed: float = 0.0, held: float = 0.0) -> j.JudgmentLedger:
    ledger = j.JudgmentLedger(max_calls=4, max_cost_usd=0.01)
    ledger.receipts += receipts
    ledger.entries.append(j.LedgerEntry("s" * 20, 0.004, "settled", cost_usd=observed))
    ledger.entries.append(j.LedgerEntry("u" * 20, held, "unknown"))
    return ledger


def _sidecar(root: Path) -> Path:
    return root / ".voss" / "sessions" / ROOT / "judgments.json"


def test_first_write_is_the_single_turn_payload(tmp_path):
    ledger = _ledger(_receipt("a" * 20), observed=0.001, held=0.002)
    path = write_judgments_sidecar(tmp_path, ROOT, ledger)
    assert json.loads(path.read_text()) == {
        "schema_version": 1,
        "judgments_cost_usd": 0.001,
        "held_usd": 0.002,
        "receipts": [asdict(r) for r in ledger.receipts],
    }


def test_second_turn_appends_receipts_and_sums_spend(tmp_path):
    first = _ledger(_receipt("a" * 20), observed=0.001, held=0.002)
    second = _ledger(_receipt("b" * 20), _receipt("c" * 20), observed=0.003, held=0.004)
    write_judgments_sidecar(tmp_path, ROOT, first)
    path = write_judgments_sidecar(tmp_path, ROOT, second)
    data = json.loads(path.read_text())
    assert [r["call_id"] for r in data["receipts"]] == ["a" * 20, "b" * 20, "c" * 20]
    assert data["judgments_cost_usd"] == pytest.approx(0.004)
    assert data["held_usd"] == pytest.approx(0.006)
    assert path.stat().st_mode & 0o777 == 0o600


def test_same_call_id_is_replaced_not_duplicated(tmp_path):
    write_judgments_sidecar(tmp_path, ROOT, _ledger(_receipt("a" * 20, status="unavailable"), _receipt("b" * 20)))
    path = write_judgments_sidecar(tmp_path, ROOT, _ledger(_receipt("a" * 20, status="answered")))
    receipts = json.loads(path.read_text())["receipts"]
    assert [(r["call_id"], r["status"]) for r in receipts] == [("a" * 20, "answered"), ("b" * 20, "answered")]


@pytest.mark.parametrize("content", ["{not json", "[1, 2]", '{"receipts": "x"}', '{"receipts": [{"no_id": 1}]}', '"text"'])
def test_malformed_existing_file_is_replaced(tmp_path, content):
    path = _sidecar(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(content)
    ledger = _ledger(_receipt("a" * 20), observed=0.001)
    write_judgments_sidecar(tmp_path, ROOT, ledger)
    assert json.loads(path.read_text()) == {
        "schema_version": 1,
        "judgments_cost_usd": 0.001,
        "held_usd": 0.0,
        "receipts": [asdict(r) for r in ledger.receipts],
    }


async def test_active_turn_attaches_pre_turn_and_tool_receipts_to_the_run(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15))
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))
    seen = {}

    async def tool_call():
        seen["scope"] = rr.current_turn()
        await rr.recall(svc, "retry", k=5, query="retry")

    run_turn, calls = fake_run_turn(during=tool_call)
    result = await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, lambda recall: run_turn(TASK, **recall))
    ledger = seen["scope"].ledger
    assert len(jev.requests) == 2 and len(result.run.judgment_receipts) == 2
    assert result.run.judgment_receipts == [asdict(r) for r in ledger.receipts]
    assert result.run.judgments_cost_usd == ledger.observed_usd > 0
    assert json.loads(jev.requests[1].content)["state"]["query"] == "retry"


async def test_off_turn_leaves_run_judgment_fields_empty(jev, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: FakeService(make_candidates(15)))
    run_turn, _ = fake_run_turn()
    result = await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, lambda recall: run_turn(TASK, **recall), sidecar_root=ROOT)
    assert (result.run.judgment_receipts, result.run.judgments_cost_usd) == ([], 0.0)
    assert not _sidecar(tmp_path).exists()


async def test_pre_turn_and_tool_calls_share_the_turn_cap(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    monkeypatch.setattr(rr, "RERANK_DEADLINE_MS", 50)
    pool = make_candidates(15)
    svc = FakeService(pool)
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=score_body(FAVOR_C07))

    jev.handler = slow
    fourth = {}

    async def three_tool_calls():
        for query in ("retry", "codec"):
            await rr.recall(svc, query, k=5, query=query)
        fourth["hits"] = await rr.recall(svc, "cache", k=5, query="cache")

    run_turn, _ = fake_run_turn(during=three_tool_calls)
    result = await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, lambda recall: run_turn(TASK, **recall))
    receipts = result.run.judgment_receipts
    assert [r["fallback_reason"] for r in receipts] == ["timeout", "timeout", "timeout", "budget_exhausted"]
    assert receipts[3]["detail"]["order"] == [c.hit.locator for c in pool]
    assert fourth["hits"] == svc.legacy[:5]
    assert len(jev.requests) == 3


async def test_chat_turns_merge_into_one_sidecar(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15))
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))
    run_turn, _ = fake_run_turn()
    runs = [
        (await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, lambda recall: run_turn(TASK, **recall), sidecar_root=ROOT)).run
        for _ in range(2)
    ]
    data = json.loads(_sidecar(tmp_path).read_text())
    assert [r["call_id"] for r in data["receipts"]] == [run.judgment_receipts[0]["call_id"] for run in runs]
    assert data["judgments_cost_usd"] == pytest.approx(sum(run.judgments_cost_usd for run in runs))


async def test_interrupted_turn_still_writes_the_sidecar(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15))
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))

    async def boom(task, *, code_recall_text=None):
        raise RuntimeError("turn failed")

    with pytest.raises(RuntimeError):
        await cli._scoped_turn(tmp_path, TASK, "sess", boom, lambda recall: boom(TASK, **recall), sidecar_root=ROOT)
    assert len(json.loads(_sidecar(tmp_path).read_text())["receipts"]) == 1


async def test_no_sidecar_root_writes_nothing(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15))
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C07))
    run_turn, _ = fake_run_turn()
    result = await cli._scoped_turn(tmp_path, TASK, "sess", run_turn, lambda recall: run_turn(TASK, **recall))
    assert len(result.run.judgment_receipts) == 1
    assert not (tmp_path / ".voss" / "sessions").exists()

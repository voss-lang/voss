"""J3-10 S3.3/S3.4/D-21: server turns rerank through _scoped_turn; swarm builders never do."""
from __future__ import annotations

import asyncio
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.code_recall import conftest as recall_conftest
from tests.code_recall.conftest import make_candidates, score_body
from tests.code_recall.test_rerank_entrypoints import FakeService, enable
from voss.harness import cli
from voss.harness.agent import Plan, TurnResult
from voss.harness.code.rerank import current_turn
from voss.harness.memory_store import Hit, MemoryStore
from voss.harness.server import app as appmod
from voss.harness.session import RunRecord

jev = recall_conftest.jev

TOKEN = "test-token-rerank"
TASK = "where is retry backoff handled"
FAVOR_C05 = {f"c{i:02d}": 3 if i == 5 else 0 for i in range(1, 16)}


class _FakeRes:
    source = "test"
    detail = "fake creds"


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _recording_run_turn():
    calls: list[dict] = []

    async def run_turn(text, *, renderer, code_recall_text=None, **kw):
        calls.append({"code_recall_text": code_recall_text, "scope": current_turn()})
        return TurnResult(
            plan=Plan(rationale="r", steps=[], confidence=0.9),
            confidence=0.9,
            final="ok",
            tool_results=[],
            cost_usd=0.0,
            run=RunRecord(id="run", started_at="", ended_at=""),
        )

    return run_turn, calls


def _build_app(monkeypatch, svc):
    run_turn, calls = _recording_run_turn()
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))
    monkeypatch.setattr(appmod, "run_turn", run_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    monkeypatch.setattr(cli, "_get_code_recall_service", lambda cwd, session_id=None: svc)
    return appmod.create_app(TOKEN), calls


def _wait_idle(client, sid, timeout=10.0):
    end = time.monotonic() + timeout
    while client.get(f"/session/{sid}", headers=_auth()).json()["busy"]:
        assert time.monotonic() < end, "turn did not finish"
        time.sleep(0.02)


def _message(client, sid):
    r = client.post(f"/session/{sid}/message", json={"parts": [{"type": "text", "text": TASK}]}, headers=_auth())
    assert r.status_code == 202, r.text


def _new_session(client, tmp_path) -> str:
    r = client.post("/session", json={"cwd": str(tmp_path)}, headers=_auth())
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_swarm_builder_keeps_scoped_recall_and_never_reranks(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = FakeService(make_candidates(15))
    app, calls = _build_app(monkeypatch, svc)

    def fake_recall(self, query, *, top_k=5, source=None):
        return [
            Hit(source="code", locator="code:a.py:0", score=1.0, excerpt="AAA"),
            Hit(source="code", locator="code:b.py:0", score=0.9, excerpt="BBB"),
        ]

    monkeypatch.setattr(MemoryStore, "recall", fake_recall)
    s = app.state.sessions.create(cwd=tmp_path, model="m", provider=object())
    s.swarm_owned_files = ["a.py"]
    await appmod._run_turn(s, TASK, "plan")
    expected = appmod._swarm_recall_text(s, TASK)
    assert "code:a.py:0" in expected and "code:b.py:0" not in expected
    assert calls == [{"code_recall_text": expected, "scope": None}]
    assert jev.requests == [] and svc.candidate_calls == 0
    [run] = s.record.runs
    assert run["judgment_receipts"] == [] and run["judgments_cost_usd"] == 0.0


def test_active_reranks_and_records_receipts_and_cost(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    pool = make_candidates(15)
    app, calls = _build_app(monkeypatch, FakeService(pool))
    jev.handler = lambda request: httpx.Response(200, json=score_body(FAVOR_C05))
    with TestClient(app) as client:
        sid = _new_session(client, tmp_path)
        _message(client, sid)
        _wait_idle(client, sid)
        cost = client.get(f"/session/{sid}/cost", headers=_auth()).json()
        [run] = client.app.state.sessions.get(sid).record.runs
    [call] = calls
    assert call["code_recall_text"] == cli._format_code_recall_section([pool[i].hit for i in (4, 0, 1, 2, 3)])
    assert call["code_recall_text"].split("\n")[2].startswith("- pkg/m4.py:1 (score ")
    assert call["scope"] is not None and call["scope"].mode == "active"
    [receipt] = run["judgment_receipts"]
    assert receipt["mode"] == "active" and receipt["fallback_reason"] is None
    assert run["judgments_cost_usd"] > 0
    assert cost["judgments_usd"] == pytest.approx(run["judgments_cost_usd"])
    assert len(jev.requests) == 1


async def test_off_injects_the_legacy_section_and_calls_nothing(jev, tmp_path, monkeypatch):
    svc = FakeService(make_candidates(15))
    app, calls = _build_app(monkeypatch, svc)
    s = app.state.sessions.create(cwd=tmp_path, model="m", provider=object())
    await appmod._run_turn(s, TASK, "plan")
    expected = cli._render_code_recall_text(tmp_path, TASK)
    assert expected and calls == [{"code_recall_text": expected, "scope": None}]
    assert jev.requests == [] and svc.candidate_calls == 0


@pytest.mark.parametrize("mode", ["off", "shadow", "active"])
async def test_unready_index_injects_nothing(jev, tmp_path, monkeypatch, mode):
    if mode != "off":
        enable(tmp_path, mode)
    svc = FakeService(make_candidates(15), ready=False)
    app, calls = _build_app(monkeypatch, svc)
    s = app.state.sessions.create(cwd=tmp_path, model="m", provider=object())
    await appmod._run_turn(s, TASK, "plan")
    assert [c["code_recall_text"] for c in calls] == [""]
    assert jev.requests == [] and svc.candidate_calls == 0


class _SlowService(FakeService):
    def __init__(self, pool):
        super().__init__(pool)
        self.started = threading.Event()

    def candidates(self, query):
        self.started.set()
        time.sleep(0.5)
        return super().candidates(query)


def test_server_stays_responsive_while_candidates_and_jev_are_pending(jev, tmp_path, monkeypatch):
    enable(tmp_path, "active")
    svc = _SlowService(make_candidates(15))
    app, calls = _build_app(monkeypatch, svc)

    async def slow(request):
        await asyncio.sleep(1.0)
        return httpx.Response(200, json=score_body(FAVOR_C05))

    jev.handler = slow

    def timed_get(client, sid):
        t0 = time.monotonic()
        r = client.get(f"/session/{sid}", headers=_auth())
        return r, time.monotonic() - t0

    with TestClient(app) as client:
        sid = _new_session(client, tmp_path)
        _message(client, sid)
        r, elapsed = timed_get(client, sid)
        assert r.status_code == 200 and elapsed < 0.3
        assert svc.started.wait(5.0)
        r, elapsed = timed_get(client, sid)
        assert r.json()["busy"] and elapsed < 0.3
        end = time.monotonic() + 5.0
        while not jev.requests:
            assert time.monotonic() < end, "Jev request never sent"
            time.sleep(0.01)
        r, elapsed = timed_get(client, sid)
        assert r.json()["busy"] and elapsed < 0.3
        _wait_idle(client, sid)
    assert jev.timeouts == [1500]
    assert calls[0]["code_recall_text"].split("\n")[2].startswith("- pkg/m4.py:1 (score ")

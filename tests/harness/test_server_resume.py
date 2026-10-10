"""
H4.1 + H4.2 — resume + prior-context (M2 fix).
Covers the M2 prior-context renderer (single dict back-compat + multi-run list)
"""

from __future__ import annotations

from concurrent.futures import Future

from fastapi.testclient import TestClient

from voss.harness import session as session_store
from voss.harness.agent import _compose_prior_context_block
from voss.harness.server import app as appmod
from voss_runtime import EpisodicMemory

TOKEN = "t-resume"


class _FakeRes:
    source = "test"
    detail = "fake"


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


# --- M2 prior-context renderer --------------------------------------------


def test_compose_single_run_is_backcompat():
    block = _compose_prior_context_block(
        {"goal": "do x", "plan": {"rationale": "because"}, "decisions": [{"title": "d1"}]}
    )
    assert block.startswith("Prior context (most-recent turn):")
    assert "do x" in block and "because" in block and "d1" in block


def test_compose_multi_run_list_renders_all_newest_first():
    # distinct goals that don't collide with header words ("newest first")
    block = _compose_prior_context_block([{"goal": "GOAL_ALPHA"}, {"goal": "GOAL_OMEGA"}])
    assert block.startswith("Prior context (resumed session")
    assert "GOAL_ALPHA" in block and "GOAL_OMEGA" in block
    assert "[most-recent turn]" in block and "[turn -2]" in block
    # newest first: the last run (OMEGA) renders before the earlier run (ALPHA)
    assert block.index("GOAL_OMEGA") < block.index("GOAL_ALPHA")


def test_compose_empty_inputs():
    assert _compose_prior_context_block(None) == ""
    assert _compose_prior_context_block([]) == ""


# --- server resume ---------------------------------------------------------


def test_resume_loads_saved_session(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))

    rec = session_store.SessionRecord.new(cwd=tmp_path, model="m", name="prev")
    rec.runs.append({"goal": "earlier goal", "plan": {"rationale": "r"}})
    hist = EpisodicMemory(capacity=40)
    hist.add("hello", role="user")
    hist.add("hi back", role="assistant")
    session_store.save(rec, hist)

    c = TestClient(appmod.create_app(TOKEN))

    saved = c.get(
        "/sessions/saved", params={"cwd": str(tmp_path)}, headers=_auth()
    ).json()
    assert next(s for s in saved["sessions"] if s["id"] == rec.id)["first_task"] == "hello"

    r = c.post(
        "/session", json={"resume": rec.id, "cwd": str(tmp_path)}, headers=_auth()
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["resumed"] is True
    assert body["id"] == rec.id

    s = c.app.state.sessions.get(rec.id)
    assert s.prior_context == rec.runs  # all prior runs forwarded
    assert len(s.history.turns) == 2  # transcript rehydrated

    r = c.get(f"/session/{rec.id}/history", headers=_auth())
    assert r.status_code == 200
    assert r.json() == {"v": 1, "turns": [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi back"},
    ]}


def test_resume_missing_returns_404(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))
    c = TestClient(appmod.create_app(TOKEN))
    r = c.post(
        "/session", json={"resume": "nope", "cwd": str(tmp_path)}, headers=_auth()
    )
    assert r.status_code == 404


def test_history_only_returns_conversation_fields(tmp_path):
    c = TestClient(appmod.create_app(TOKEN))
    s = c.app.state.sessions.create(cwd=tmp_path, model="m", provider=object())
    s.history.add("user prompt", role="user")
    s.history.add("system note", role="system")
    s.history.add("private tool payload", role="tool")
    s.history.add("assistant answer", role="assistant")
    s.record.runs.append({"tool_calls": ["private tool payload"]})
    r = c.get(f"/session/{s.id}/history", headers=_auth())
    assert r.json() == {"v": 1, "turns": [
        {"role": "user", "content": "user prompt"},
        {"role": "system", "content": "system note"},
        {"role": "assistant", "content": "assistant answer"},
    ]}
    assert c.get(f"/session/{s.id}/history").status_code == 401
    assert c.get("/session/missing/history", headers=_auth()).status_code == 404


def test_clear_drops_active_context_without_erasing_saved_session(tmp_path):
    c = TestClient(appmod.create_app(TOKEN))
    s = c.app.state.sessions.create(cwd=tmp_path, model="m", provider=object())
    s.history.add("old prompt", role="user")
    s.history.summary = "old summary"
    s.record.runs.append({"goal": "old goal", "cost_usd": 0.5})
    s.prior_context = s.record.runs
    session_store.save(s.record, s.history)

    assert c.post(f"/session/{s.id}/clear").status_code == 401
    s.switching = True
    assert c.post(f"/session/{s.id}/clear", headers=_auth()).status_code == 409
    assert len(s.history.turns) == 1
    s.switching = False
    s.task = Future()
    assert c.post(f"/session/{s.id}/clear", headers=_auth()).status_code == 409
    assert len(s.history.turns) == 1
    s.task = None

    assert c.post(f"/session/{s.id}/clear", headers=_auth()).status_code == 204
    assert c.get(f"/session/{s.id}/history", headers=_auth()).json()["turns"] == []
    assert s.history.summary == ""
    assert s.prior_context is None
    assert c.get(f"/session/{s.id}/cost", headers=_auth()).json()["total_usd"] == 0.5
    _, saved_history = session_store.load(s.id, tmp_path)
    assert saved_history.turns[0].content == "old prompt"
    assert c.post("/session/missing/clear", headers=_auth()).status_code == 404

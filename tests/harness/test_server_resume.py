"""H4.1 + H4.2 — resume + prior-context (M2 fix).

Covers the M2 prior-context renderer (single dict back-compat + multi-run list)
and the server resume path (load a saved session, forward all prior runs as
prior_context, rehydrate history).
"""

from __future__ import annotations

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
    assert any(s["id"] == rec.id for s in saved["sessions"])

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


def test_resume_missing_returns_404(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))
    c = TestClient(appmod.create_app(TOKEN))
    r = c.post(
        "/session", json={"resume": "nope", "cwd": str(tmp_path)}, headers=_auth()
    )
    assert r.status_code == 404

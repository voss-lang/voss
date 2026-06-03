"""H1.5-H1.10 + H1.14 verification.

Drives the FastAPI app via TestClient with run_turn + provider resolution
monkeypatched (no live API, no disk writes). Covers: bearer auth, session
CRUD, message->SSE event stream, abort, permission reply, OpenAPI event union.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voss.harness.agent import Plan, TurnResult
from voss.harness.server import app as appmod

TOKEN = "test-token-abc123"


class _FakeRes:
    source = "test"
    detail = "fake creds"


async def _fake_run_turn(text, *, renderer, **kw):
    renderer.show_thinking("planning 1/8")
    renderer.show_plan(Plan(rationale="r", steps=[], confidence=0.9), cost_usd=0.0)
    renderer.stream_delta("hello ")
    renderer.stream_delta("world")
    renderer.finalize_stream(role="assistant", confidence=0.9, cost_usd=0.01)
    return TurnResult(
        plan=Plan(rationale="r", steps=[], confidence=0.9),
        confidence=0.9,
        final="hello world",
        tool_results=[],
        cost_usd=0.01,
        run=None,
    )


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))
    monkeypatch.setattr(appmod, "run_turn", _fake_run_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    # make_toolset/PermissionStore.load run for real on a tmp cwd (harmless).
    app = appmod.create_app(TOKEN)
    c = TestClient(app)
    c._cwd = str(tmp_path)  # type: ignore[attr-defined]
    return c


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _new_session(client) -> str:
    r = client.post("/session", json={"cwd": client._cwd}, headers=_auth())
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_unauthorized_rejected(client):
    assert client.post("/session", json={}).status_code == 401
    assert client.get("/session").status_code == 401


def test_session_crud(client):
    sid = _new_session(client)
    listing = client.get("/session", headers=_auth()).json()
    assert any(s["id"] == sid for s in listing["sessions"])
    assert client.get(f"/session/{sid}", headers=_auth()).status_code == 200
    assert client.delete(f"/session/{sid}", headers=_auth()).status_code == 204
    assert client.get(f"/session/{sid}", headers=_auth()).status_code == 404


async def test_turn_publishes_event_sequence_to_queue(monkeypatch, tmp_path):
    # Drive _run_turn directly and drain the session queue. Verifies the real
    # renderer -> queue -> event flow + ordering + session.idle terminator,
    # without HTTP transport (over-the-wire SSE is verified in H2 with the
    # Rust client). server.connected is emitted by the SSE generator, not by
    # the turn, so it is correctly absent here.
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))
    monkeypatch.setattr(appmod, "run_turn", _fake_run_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)

    app = appmod.create_app(TOKEN)
    mgr = app.state.sessions
    s = mgr.create(cwd=tmp_path, model="m", provider=object())

    await appmod._run_turn(s, "hi", "plan")

    seen: list[str] = []
    while not s.queue.empty():
        seen.append(s.queue.get_nowait().type)

    assert seen[0] == "user"
    assert "plan" in seen
    assert "stream.delta" in seen
    assert "final" in seen
    assert seen[-1] == "session.idle"
    assert s.task is None  # cleared in the finally block


def test_empty_message_rejected(client):
    sid = _new_session(client)
    r = client.post(
        f"/session/{sid}/message",
        json={"parts": [{"type": "text", "text": "   "}]},
        headers=_auth(),
    )
    assert r.status_code == 422


def test_abort_endpoint(client):
    sid = _new_session(client)
    assert client.post(f"/session/{sid}/abort", headers=_auth()).status_code == 202


def test_permission_reply_resolves_future(client):
    from concurrent.futures import Future

    sid = _new_session(client)
    s = client.app.state.sessions.get(sid)
    fut: Future = Future()
    s.pending["req1"] = fut
    r = client.post(
        f"/session/{sid}/permission",
        json={"id": "req1", "choice": "a"},
        headers=_auth(),
    )
    assert r.json()["status"] == "ok"
    assert fut.result(timeout=1) == "a"
    # unknown id -> stale
    r2 = client.post(
        f"/session/{sid}/permission",
        json={"id": "nope", "choice": "d"},
        headers=_auth(),
    )
    assert r2.json()["status"] == "stale"


def test_no_credentials_returns_400(client, monkeypatch):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), None))
    r = client.post("/session", json={"cwd": client._cwd}, headers=_auth())
    assert r.status_code == 400


def test_openapi_exposes_event_union(client):
    spec = client.get("/openapi.json", headers=_auth()).json()
    schemas = spec["components"]["schemas"]
    assert "EventEnvelope" in schemas
    assert "StreamDelta" in schemas
    assert "SessionIdle" in schemas

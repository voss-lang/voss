"""
H1.5-H1.10 + H1.14 verification.
Drives the FastAPI app via TestClient with run_turn + provider resolution
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


def test_session_env_defaults_for_sdk_clients(client, monkeypatch):
    """E4: SDK createSession surfaces post only {cwd}. The serve owner pins
    session defaults via env; an explicit body value always wins."""
    seen: list[str] = []
    monkeypatch.setattr(
        appmod,
        "_resolve_provider",
        lambda pref: (seen.append(pref), (_FakeRes(), object()))[1],
    )
    monkeypatch.setenv("VOSS_SERVE_DEFAULT_AUTH", "codex")
    monkeypatch.setenv("VOSS_SERVE_DEFAULT_MODEL", "gpt-5.5")

    r = client.post("/session", json={"cwd": client._cwd}, headers=_auth())
    assert r.status_code == 201, r.text
    assert seen[-1] == "codex"  # auto -> env default
    sid = r.json()["id"]
    info = client.get(f"/session/{sid}", headers=_auth()).json()
    assert info["model"] == "gpt-5.5"  # body.model absent -> env default

    r2 = client.post(
        "/session",
        json={"cwd": client._cwd, "auth": "claude", "model": "claude-x"},
        headers=_auth(),
    )
    assert r2.status_code == 201, r2.text
    assert seen[-1] == "claude"  # explicit body wins over env
    info2 = client.get(f"/session/{r2.json()['id']}", headers=_auth()).json()
    assert info2["model"] == "claude-x"


def _init_project(root, **voss_files: str) -> None:
    (root / "VOSS.md").write_text("# Project\n")
    (root / ".voss").mkdir(exist_ok=True)
    for name, body in voss_files.items():
        (root / ".voss" / f"{name}.yml").write_text(body)


async def _server_turn_decision(monkeypatch, cwd, tool: str, args: dict) -> dict:
    """Run one server turn whose agent attempts a single tool call."""
    seen: dict = {}

    async def _run(text, *, renderer, permissions, cognition=None, **kw):
        seen["decision"] = permissions.check(tool, args, is_mutating=True)
        seen["cognition"] = cognition
        return TurnResult(
            plan=Plan(rationale="r", steps=[], confidence=0.9),
            confidence=0.9,
            final="done",
            tool_results=[],
            cost_usd=0.0,
            run=None,
        )

    monkeypatch.setattr(appmod, "run_turn", _run)
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    app = appmod.create_app(TOKEN)
    s = app.state.sessions.create(cwd=cwd, model="m", provider=object())
    await appmod._run_turn(s, "go", "auto")
    seen["events"] = []
    while not s.queue.empty():
        seen["events"].append(s.queue.get_nowait())
    return seen


async def test_server_turn_denies_tools_the_project_permissions_deny(monkeypatch, tmp_path):
    write = ("fs_write", {"path": "notes.txt", "content": "x"})
    before = await _server_turn_decision(monkeypatch, tmp_path, *write)
    assert before["decision"][0] is True

    _init_project(tmp_path, permissions="tool_policy:\n  deny: [fs_write]\n")
    after = await _server_turn_decision(monkeypatch, tmp_path, *write)
    assert after["decision"] == (False, "denied by .voss/permissions.yml")
    assert after["cognition"].initialized


async def test_server_turn_denies_irreversible_actions_under_the_safety_policy(
    monkeypatch, tmp_path
):
    write = ("fs_write", {"path": "infra/prod/app.yml", "content": "x"})
    before = await _server_turn_decision(monkeypatch, tmp_path, *write)
    assert before["decision"][0] is True

    _init_project(
        tmp_path,
        safety=(
            "runbooks:\n  - name: prod-deploy\n    steps: [plan, apply]\n"
            "factory_only_paths:\n  - id: prod-paths\n    glob: 'infra/prod/**'\n"
            "    runbook: prod-deploy\n    classes: [prod, irreversible]\n"
        ),
    )
    after = await _server_turn_decision(monkeypatch, tmp_path, *write)
    allowed, why = after["decision"]
    assert allowed is False
    assert why.startswith("safety:")


async def test_server_turn_warns_when_project_policy_fails_to_load(monkeypatch, tmp_path):
    _init_project(tmp_path, permissions="not_a_field: true\n")
    seen = await _server_turn_decision(
        monkeypatch, tmp_path, "fs_write", {"path": "notes.txt", "content": "x"}
    )
    warnings = [e for e in seen["events"] if e.type == "warning"]
    assert any("permissions.yml" in e.model_dump_json() for e in warnings)

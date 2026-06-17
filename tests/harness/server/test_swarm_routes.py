"""V25-04: /swarm routes, overlap 4xx, per-role routing, spawn-gate, fan-out SSE.

Mirrors tests/harness/test_server_app.py — TestClient with _resolve_provider +
run_turn monkeypatched; app.state.swarm_store redirected to a tmp event-log dir.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voss.harness.agent import Plan, TurnResult
from voss.harness.server import app as appmod

TOKEN = "test-token-swarm"


class _FakeRes:
    source = "test"
    detail = "fake creds"


async def _fake_run_turn(text, *, renderer, **kw):
    renderer.stream_delta("ok")
    renderer.finalize_stream(role="assistant", confidence=0.9, cost_usd=0.0)
    return TurnResult(
        plan=Plan(rationale="r", steps=[], confidence=0.9),
        confidence=0.9,
        final="ok",
        tool_results=[],
        cost_usd=0.0,
        run=None,
    )


def _build_app(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (_FakeRes(), object()))
    monkeypatch.setattr(appmod, "run_turn", _fake_run_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    app = appmod.create_app(TOKEN)
    app.state.swarm_store = appmod.SwarmStore(cwd=tmp_path)
    return app


@pytest.fixture
def client(monkeypatch, tmp_path):
    app = _build_app(monkeypatch, tmp_path)
    c = TestClient(app)
    c._cwd = str(tmp_path)  # type: ignore[attr-defined]
    return c


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


# ---------------------------------------------------------------------------
# Task 1
# ---------------------------------------------------------------------------
def test_swarm_auth(client):
    # 401 without a token on every route.
    assert client.post("/swarm", json={"goal": "g"}).status_code == 401
    assert client.get("/swarm/none").status_code == 401
    assert client.post("/swarm/none/task", json={"goal": "t"}).status_code == 401
    assert client.post("/swarm/none/message", json={}).status_code == 401

    # With a token the routes work.
    r = client.post("/swarm", json={"goal": "ship", "cwd": client._cwd}, headers=_auth())
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    assert client.get(f"/swarm/{sid}", headers=_auth()).status_code == 200
    assert client.get("/swarm/nope", headers=_auth()).status_code == 404

    rt = client.post(
        f"/swarm/{sid}/task",
        json={"goal": "do A", "owned_files": ["src/a.py"]},
        headers=_auth(),
    )
    assert rt.status_code == 201, rt.text

    rm = client.post(
        f"/swarm/{sid}/message",
        json={"kind": "message", "text": "hi"},
        headers=_auth(),
    )
    assert rm.status_code == 202, rm.text


def test_overlap_rejected(client):
    sid = client.post(
        "/swarm", json={"goal": "g", "cwd": client._cwd}, headers=_auth()
    ).json()["id"]

    r1 = client.post(
        f"/swarm/{sid}/task",
        json={"goal": "A", "owned_files": ["src/shared.py"]},
        headers=_auth(),
    )
    assert r1.status_code == 201
    first_id = r1.json()["task"]["id"]

    # Same file, no ordering → 4xx overlap.
    r2 = client.post(
        f"/swarm/{sid}/task",
        json={"goal": "B", "owned_files": ["src/shared.py"]},
        headers=_auth(),
    )
    assert r2.status_code == 409, r2.text

    # Same file, ordered via depends_on → accepted.
    r3 = client.post(
        f"/swarm/{sid}/task",
        json={"goal": "B", "owned_files": ["src/shared.py"], "depends_on": [first_id]},
        headers=_auth(),
    )
    assert r3.status_code == 201, r3.text


def test_per_role_model_routing(client):
    roster = [
        {"name": "coordinator", "model": "model-coord"},
        {"name": "builder-1", "model": "model-build"},
        {"name": "reviewer", "model": "model-review"},
    ]
    r = client.post(
        "/swarm",
        json={"goal": "g", "cwd": client._cwd, "roster": roster},
        headers=_auth(),
    )
    assert r.status_code == 201, r.text
    spawned = r.json()["sessions"]
    assert len(spawned) == 3
    assert {s["model"] for s in spawned} == {"model-coord", "model-build", "model-review"}
    # The sessions really exist with those models.
    listing = client.get("/session", headers=_auth()).json()["sessions"]
    models = {s["model"] for s in listing}
    assert {"model-coord", "model-build", "model-review"} <= models


# ---------------------------------------------------------------------------
# Task 2
# ---------------------------------------------------------------------------
async def test_spawn_gate_zero_turns_before_assign(monkeypatch, tmp_path):
    calls = {"n": 0}

    async def _counting_run_turn(text, *, renderer, **kw):
        calls["n"] += 1
        renderer.finalize_stream(role="assistant", confidence=0.9, cost_usd=0.0)
        return TurnResult(
            plan=Plan(rationale="r", steps=[], confidence=0.9),
            confidence=0.9,
            final="ok",
            tool_results=[],
            cost_usd=0.0,
            run=None,
        )

    app = _build_app(monkeypatch, tmp_path)
    # Override run_turn AFTER _build_app (which set the default fake) so the
    # counter is the one actually invoked.
    monkeypatch.setattr(appmod, "run_turn", _counting_run_turn)
    mgr = app.state.sessions
    s = mgr.create(cwd=tmp_path, model="m", provider=object())
    s.gate_event = asyncio.Event()  # gated builder, unsignaled

    task = asyncio.create_task(appmod._run_turn(s, "hi", "plan"))
    await asyncio.sleep(0)  # let it reach the gate wait
    assert calls["n"] == 0  # ZERO turns before assign — no timing tolerance

    s.gate_event.set()  # coordinator's swarm.assign equivalent
    await task
    assert calls["n"] == 1  # exactly one turn after assign


def test_swarm_sse_event_types(client):
    # Spawn a default-roster swarm (coordinator + 2 builders + reviewer).
    r = client.post(
        "/swarm", json={"goal": "g", "cwd": client._cwd}, headers=_auth()
    ).json()
    sid = r["id"]
    spawned = r["sessions"]
    coord = next(s["session_id"] for s in spawned if s["role"] == "coordinator")
    builder = next(s["session_id"] for s in spawned if s["role"].startswith("builder"))

    task_id = client.post(
        f"/swarm/{sid}/task",
        json={"goal": "A", "owned_files": ["src/a.py"]},
        headers=_auth(),
    ).json()["task"]["id"]

    # Script all 5 swarm event kinds over the message route — no nudge file,
    # no stdin injection; delivery is via EventBusRenderer.emit only.
    msgs = [
        {"kind": "assign", "task_id": task_id, "session_id": builder},
        {"kind": "worker_done", "task_id": task_id, "session_id": builder, "summary": "x"},
        {"kind": "gate", "task_id": task_id, "gate_type": "reviewer_reject", "detail": "no"},
        {"kind": "needs_operator", "task_id": task_id, "session_id": builder,
         "tool_name": "fs_write", "path": "src/x.py"},
        {"kind": "complete", "summary": "done"},
    ]
    for m in msgs:
        assert client.post(f"/swarm/{sid}/message", json=m, headers=_auth()).status_code == 202

    # The coordinator (a registered swarm session) received all 5 via fan-out.
    q = client.app.state.sessions.get(coord).queue
    seen = set()
    while not q.empty():
        seen.add(q.get_nowait().type)
    assert {
        "swarm.assign", "swarm.worker_done", "swarm.gate",
        "swarm.needs_operator", "swarm.complete",
    } <= seen

    # No nudge file was written for delivery (events flow through queues only).
    assert not (Path(client._cwd) / ".voss" / "swarm" / sid / "nudge").exists()

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from contextlib import contextmanager

import httpx
import pytest
import uvicorn

from voss.harness.server import app as appmod
from voss.harness.server.renderer import EventBusRenderer
from voss.harness.server.task_journal import TaskJournal

TOKEN = "synthetic-replay"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@contextmanager
def serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", timeout_graceful_shutdown=1))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started:
        assert thread.is_alive() and time.monotonic() < deadline
        time.sleep(0.01)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{sock.getsockname()[1]}", headers=HEADERS, timeout=5) as api:
            yield api
    finally:
        server.should_exit = True
        thread.join(5)
        assert not thread.is_alive()
        sock.close()


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")
    starts = []

    async def turn(session, text, mode):
        starts.append((session.id, text))
        renderer = EventBusRenderer(session.queue, session_id=session.id)
        renderer.show_warning("nonfatal synthetic warning")
        renderer.session_idle()
        if text == "wait":
            await asyncio.Event().wait()
        await asyncio.sleep(0.1)
        if text == "fail":
            raise RuntimeError("synthetic failure")
        if text == "clarify":
            renderer.show_clarify("Which file?", 0.5)
        session.turn_outcome = "done"

    monkeypatch.setattr(appmod, "_run_turn", turn)
    return tmp_path, starts


def create(api, cwd):
    response = api.post("/session", json={"cwd": str(cwd)})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def submit(api, sid, text, key):
    return api.post(f"/session/{sid}/message", json={"parts": [{"text": text}], "command_id": key})


def entries(response):
    for line in response.iter_lines():
        if line.startswith("data: "):
            yield json.loads(line[6:])


def settled(api, sid, phase):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        snapshot = api.get(f"/session/{sid}/task").json()
        if snapshot["phase"] == phase:
            return snapshot
        time.sleep(0.01)
    pytest.fail(f"expected {phase}, received {snapshot}")


def test_two_viewers_disconnect_replay_and_second_turn(setup):
    cwd, starts = setup
    app = appmod.create_app(TOKEN)
    with serve(app) as api:
        sid = create(api, cwd)
        url = f"/session/{sid}/task-events"
        with api.stream("GET", url) as first, api.stream("GET", url) as second:
            assert submit(api, sid, "hello", "one").status_code == 202
            a, b = entries(first), entries(second)
            initial = [next(a), next(a), next(a)]
            assert [next(b), next(b), next(b)] == initial
            assert all(entry["snapshot"]["phase"] == "active" for entry in initial)
        snapshot = settled(api, sid, "completed")
        with api.stream("GET", url, params={"after": initial[-1]["cursor"]}) as replay:
            stream = entries(replay)
            completion = next(stream)
            assert completion["cursor"] == snapshot["watermark"]
            assert completion["snapshot"]["phase"] == "completed"
            assert submit(api, sid, "second", "two").status_code == 202
            assert next(stream)["snapshot"]["phase"] == "active"
            for event in stream:
                if event["snapshot"]["phase"] == "completed":
                    break
        settled(api, sid, "completed")
        assert len(starts) == 2
        assert api.get(url, params={"after": 999}).status_code == 409


def test_duplicate_command_and_stale_replies_do_not_launch_work(setup):
    cwd, starts = setup
    with serve(appmod.create_app(TOKEN)) as api:
        sid = create(api, cwd)
        first = submit(api, sid, "wait", "one")
        assert first.json() == submit(api, sid, "wait", "one").json()
        assert submit(api, sid, "different", "one").status_code == 409
        assert submit(api, sid, "other", "two").status_code == 409
        for command, body in [("permission", {"id": "stale", "choice": "a"}), ("diff", {"id": "stale", "decisions": []})]:
            assert api.post(f"/session/{sid}/{command}", json=body).json()["status"] == "stale"
        assert api.post(f"/session/{sid}/abort").json()["status"] == "cancelled"
        settled(api, sid, "cancelled")
        assert api.post(f"/session/{sid}/abort").json()["status"] == "not_running"
        assert first.json() == submit(api, sid, "wait", "one").json()
        assert len(starts) == 1


def test_failure_and_clarification_are_explicit_outcomes(setup):
    cwd, _ = setup
    with serve(appmod.create_app(TOKEN)) as api:
        sid = create(api, cwd)
        submit(api, sid, "fail", "one")
        assert settled(api, sid, "failed")["outcome"] == "error"
        submit(api, sid, "clarify", "two")
        assert settled(api, sid, "waiting")["pending_actions"] == [{"kind": "clarify"}]


def test_quit_and_reopen_read_history_without_provider_or_worker(setup, monkeypatch):
    cwd, starts = setup
    with serve(appmod.create_app(TOKEN)) as api:
        sid = create(api, cwd)
        ack = submit(api, sid, "wait", "one").json()
        settled(api, sid, "active")
    monkeypatch.setattr(appmod, "_resolve_provider", lambda *_: pytest.fail("reopen must not resolve credentials"))
    with serve(appmod.create_app(TOKEN)) as api:
        snapshot = settled(api, sid, "interrupted")
        assert snapshot["run_id"] == ack["run_id"]
        assert snapshot["pending_actions"] == []
        assert submit(api, sid, "wait", "one").json() == ack
        assert len(starts) == 1
        with api.stream("GET", f"/session/{sid}/task-events") as response:
            assert next(entries(response))["cursor"] == 1


def test_crash_recovery_and_exclusive_journal_ownership(tmp_path):
    path = tmp_path / "journal.sqlite3"
    journal = TaskJournal(path)
    journal.register("synthetic")
    ack = journal.begin("synthetic", "one", {"text": "fixture"})
    journal.emit("synthetic", {"type": "permission.updated", "id": "pending"})
    other = TaskJournal(path)
    assert other.snapshot("synthetic") is None
    other.register("second-server")
    other.begin("second-server", "one", {"text": "fixture"})
    assert other.snapshot("second-server").phase == "active"
    assert journal.snapshot("synthetic").phase == "waiting"
    assert journal.snapshot("second-server") is None
    other.close()
    journal.close()  # simulates process exit without lifecycle cleanup
    recovered = TaskJournal(path)
    snapshot = recovered.snapshot("synthetic")
    assert snapshot.phase == "interrupted"
    assert snapshot.pending_actions == []
    assert snapshot.attempt_id == ack.attempt_id
    assert [event.cursor for event in recovered.replay("synthetic", 0)] == [1, 2, 3]
    recovered.close()


@pytest.mark.parametrize("outcome,phase", [("candidate", "candidate_ready"), ("error", "failed"), ("incomplete", "waiting")])
def test_swarm_state_maps_to_coordinator_and_duplicate_run_is_not_reexecuted(setup, monkeypatch, outcome, phase):
    from voss.harness import swarm_runtime
    cwd, _ = setup
    calls = []

    async def members(store, repo_root, swarm_id, *, spawn_fn, on_event, preflight_fn=None):
        assert preflight_fn is None
        calls.append(swarm_id)
        if outcome == "error":
            raise RuntimeError("synthetic worker failure")
        if outcome == "incomplete":
            return [swarm_runtime.MemberResult(role="builder-1", task_id="fixture", exit_code=0)]
        task = store.get(swarm_id).tasks[0]
        store.mark_candidate_ready(swarm_id, task.id, branch="synthetic", worktree="synthetic", head="fixture")
        on_event({"type": "swarm.candidates_ready", "swarm_id": swarm_id, "candidate_count": 1})
        return [swarm_runtime.MemberResult(role="builder-1", task_id="fixture", exit_code=0, candidate_ready=True)]

    monkeypatch.setattr(swarm_runtime, "run_cli_swarm", members)
    app = appmod.create_app(TOKEN)
    with serve(app) as api:
        created = api.post("/swarm", json={"goal": "fixture", "cwd": str(cwd), "roster": [
            {"name": "coordinator", "agent": "voss"}, {"name": "builder-1", "agent": "codex"},
        ]}).json()
        sid, swarm_id = created["sessions"][0]["session_id"], created["id"]
        app.state.swarm_store.add_task(swarm_id, "fixture", owned_files=["fixture.py"])
        ack = api.post(f"/swarm/{swarm_id}/run").json()
        snapshot = settled(api, sid, phase)
        assert snapshot["task_id"] == snapshot["swarm_id"] == swarm_id
        assert snapshot["session_id"] == sid
        assert snapshot["attempt_id"] == ack["attempt_id"]
        assert api.post(f"/swarm/{swarm_id}/run").json() == ack
        assert calls == [swarm_id]

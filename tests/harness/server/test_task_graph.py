import asyncio
from types import SimpleNamespace

import httpx
import pytest

from voss.harness.server import app as appmod, task_graph
from voss.harness.server.task_journal import TaskJournal
from voss.harness.swarm_store import SwarmStore


def branching(tmp_path):
    store = SwarmStore(cwd=tmp_path)
    swarm = store.create("branching fixture")
    a = store.add_task(swarm.id, "Foundation", ["a"])
    b = store.add_task(swarm.id, "Left", ["b"], [a.id])
    c = store.add_task(swarm.id, "Right", ["c"], [a.id])
    d = store.add_task(swarm.id, "Integrate", ["d"], [b.id, c.id])
    return swarm, (a, b, c, d)


def test_attempt_identity_dependencies_retry_and_changed_candidate_survive_replay(
    tmp_path,
):
    journal = TaskJournal(tmp_path / "journal.sqlite3")
    journal.register("owner")
    journal.begin("owner", "start", {})
    swarm, (a, b, c, d) = branching(tmp_path)
    graph = task_graph.swarm_state(swarm, None, journal.snapshot("owner"))
    assert graph.nodes[3].blocked_by == [b.id, c.id]

    def event(kind, task, attempt, **fields):
        nonlocal graph
        graph = task_graph.swarm_state(
            swarm,
            graph,
            journal.snapshot("owner"),
            {
                "type": kind,
                "task_id": task.id,
                "attempt_id": attempt,
                "role": "builder",
                "harness": "codex",
                "model": "synthetic",
                **fields,
            },
        )
        journal.update("owner", graph=graph.model_dump())

    event("swarm.assign", a, "foundation", launched=True)
    event("swarm.worker_done", a, "foundation")
    event("swarm.assign", b, "left-1", launched=True)
    event("swarm.assign", c, "right-1", launched=True)
    assert graph.nodes[1].blocked_by == graph.nodes[2].blocked_by == []
    assert graph.nodes[1].attempts[0].id != graph.nodes[2].attempts[0].id
    event(
        "swarm.gate", b, "left-1", gate_type="member_failed", detail="Synthetic failure"
    )
    assert graph.nodes[1].state == "failed" and graph.nodes[3].blocked_by == [
        b.id,
        c.id,
    ]
    event("swarm.assign", b, "left-2", launched=True)
    event(
        "swarm.candidate_ready",
        b,
        "left-2",
        head="candidate-a",
        branch="feature",
        worktree="/synthetic/tree",
    )
    event("swarm.assign", b, "left-2", launched=True)
    assert (
        len(graph.nodes[1].attempts) == 2 and graph.nodes[1].state == "candidate_ready"
    )
    event("swarm.gate", b, "left-2", gate_type="review_reject", detail="Needs a test")
    assert graph.nodes[1].attempts[-1].review_state == "changes_requested"
    event(
        "swarm.candidate_ready",
        b,
        "left-2",
        head="candidate-b",
        branch="feature",
        worktree="/synthetic/tree",
    )
    assert graph.nodes[1].attempts[-1].candidate_revision == "candidate-b"
    assert graph.nodes[1].attempts[-1].review_state == "pending"
    assert graph.nodes[1].attempts[0].state == "failed"
    assert {attempt.run_id for node in graph.nodes for attempt in node.attempts} == {
        graph.run_id
    }
    before = journal.snapshot("owner").graph.model_dump()
    assert journal.replay("owner", 0)[-1].snapshot.graph.model_dump() == before
    journal.close()
    reopened = TaskJournal(tmp_path / "journal.sqlite3")
    restored = reopened.snapshot("owner")
    assert restored.phase == "interrupted"
    assert restored.graph.nodes[2].attempts[0].state == "interrupted"
    assert restored.graph.nodes[1].attempts[-1].candidate_revision == "candidate-b"
    reopened.close()


def test_authentication_only_blocks_the_affected_harness(tmp_path):
    journal = TaskJournal(tmp_path / "journal.sqlite3")
    journal.register("owner")
    journal.begin("owner", "start", {})
    swarm, nodes = branching(tmp_path)
    graph = None
    for i, harness in enumerate(["codex", "claude"]):
        graph = task_graph.swarm_state(
            swarm,
            graph,
            journal.snapshot("owner"),
            {
                "type": "swarm.assign",
                "task_id": nodes[i].id,
                "attempt_id": harness,
                "harness": harness,
                "launched": True,
            },
        )
    snapshot = journal.update(
        "owner",
        graph=graph.model_dump(),
        phase="waiting",
        pending_actions=[
            {"kind": "authentication", "harness": "codex", "message": "Sign in again"}
        ],
    )
    assert [node.state for node in snapshot.graph.nodes[:2]] == ["waiting", "running"]
    assert snapshot.graph.nodes[0].blockers == ["Sign in again"]
    journal.close()


@pytest.mark.asyncio
async def test_output_is_bounded_to_explicit_attempt_and_never_starts_a_session(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    app = appmod.create_app("synthetic-graph")
    journal = app.state.sessions.journal
    for sid in ["owner", "worker"]:
        journal.register(sid)
    journal.begin("worker", "first", {})
    start = journal.snapshot("worker").watermark
    journal.emit("worker", {"type": "stream.delta", "text": "first attempt"})
    end = journal.snapshot("worker").watermark
    journal.begin("worker", "second", {})
    journal.emit("worker", {"type": "stream.delta", "text": "another attempt"})
    graph = task_graph.Graph(
        source="swarm",
        plan_id="plan",
        revision="r1",
        owner_session_id="owner",
        nodes=[
            task_graph.Node(
                id="node",
                goal="Scoped output",
                attempts=[
                    task_graph.Attempt(
                        id="first",
                        plan_revision="r1",
                        session_id="worker",
                        output_after=start,
                        output_through=end,
                    )
                ],
            )
        ],
    )
    journal.update("owner", graph=graph.model_dump())
    before = journal.snapshot("owner").watermark
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer synthetic-graph"},
    ) as api:
        path = "/session/owner/graph-output"
        for _ in range(2):
            result = (
                await api.get(path, params={"node_id": "node", "attempt_id": "first"})
            ).json()
            assert [row["event"]["text"] for row in result["events"]] == [
                "first attempt"
            ]
            assert not result["has_more"] and result["next_cursor"] == end
        assert (
            await api.get(path, params={"node_id": "node", "attempt_id": "unknown"})
        ).json()["status"] == "unavailable"
        assert (
            await api.get(
                path, params={"node_id": "node", "attempt_id": "first", "after": end}
            )
        ).json()["events"] == []
        journal._db.execute(
            "DELETE FROM events WHERE id=? AND cursor=?", ("worker", end)
        )
        journal._db.commit()
        assert (
            await api.get(path, params={"node_id": "node", "attempt_id": "first"})
        ).json()["status"] == "unavailable"
    assert app.state.sessions.list() == []
    assert journal.snapshot("owner").watermark == before
    journal.close()


@pytest.mark.asyncio
async def test_same_role_native_workers_and_readers_keep_separate_attempts(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        appmod,
        "_resolve_provider",
        lambda pref: (SimpleNamespace(source="test"), object()),
    )
    starts = []
    waiting, release = asyncio.Event(), asyncio.Event()

    async def turn(session, text, mode):
        starts.append(session.id)
        session.journal.emit(session.id, {"type": "stream.delta", "text": text})
        if text == "A":
            session.journal.emit(
                session.id, {"type": "permission.updated", "id": "synthetic-permission"}
            )
            waiting.set()
            await release.wait()
            session.journal.resolve(session.id, "synthetic-permission")
        await asyncio.sleep(0)
        session.turn_outcome = "done"

    monkeypatch.setattr(appmod, "_run_turn", turn)
    app = appmod.create_app("synthetic-graph")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer synthetic-graph"},
    ) as api:
        response = await api.post(
            "/swarm",
            json={
                "goal": "Parallel fixture",
                "cwd": str(tmp_path),
                "roster": [
                    {"name": "coordinator", "agent": "voss"},
                    {"name": "builder", "agent": "voss"},
                    {"name": "builder", "agent": "voss"},
                ],
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()
        sid = result["id"]
        owner = next(
            row["session_id"]
            for row in result["sessions"]
            if row["role"] == "coordinator"
        )
        for name in ["A", "B"]:
            assert (
                await api.post(
                    f"/swarm/{sid}/task", json={"goal": name, "owned_files": [name]}
                )
            ).status_code == 201
        assert (await api.post(f"/swarm/{sid}/run")).status_code == 202
        running = app.state.sessions.get(owner).task
        await asyncio.wait_for(waiting.wait(), 2)
        blocked = (await api.get(f"/session/{owner}/task")).json()["graph"]["nodes"][0]
        assert blocked["state"] == "waiting" and blocked["blockers"] == [
            "permission.updated"
        ]
        assert len(starts) == 2
        release.set()
        if running:
            await running
        snapshot = (await api.get(f"/session/{owner}/task")).json()
        assert snapshot["phase"] == "completed"
        nodes = snapshot["graph"]["nodes"]
        assert len(nodes) == 2 and all(node["state"] == "completed" for node in nodes)
        attempts = [node["attempts"][0] for node in nodes]
        assert len({a["id"] for a in attempts}) == 2
        assert {a["role"] for a in attempts} == {"builder"}
        assert {a["run_id"] for a in attempts} == {snapshot["run_id"]}
        for _ in range(2):
            for node in nodes:
                result = (
                    await api.get(
                        f"/session/{owner}/graph-output",
                        params={
                            "node_id": node["id"],
                            "attempt_id": node["attempts"][0]["id"],
                        },
                    )
                ).json()
                assert result["status"] == "available"
                assert [
                    row["event"]["text"]
                    for row in result["events"]
                    if row["event"]["type"] == "stream.delta"
                ] == [node["goal"]]
        assert len(starts) == 2
        assert (await api.post(f"/swarm/{sid}/run")).json()["run_id"] == snapshot[
            "run_id"
        ]
        assert len(starts) == 2
    app.state.sessions.journal.close()

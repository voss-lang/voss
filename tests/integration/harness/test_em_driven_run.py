"""Driven EM run: tickets become cards, workers run, reviewers gate Done."""
from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from voss.harness.agent import TurnResult
from voss.harness.board.machine import Board
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.em.handle import EMBoardHandle
from voss.harness.em.loop import em_loop
from voss.harness.em.schema import CreateTicketOp, DispatchCardOp, EMPlanResponse, NoopOp
from voss.harness.permissions import PermissionGate
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode


class SnapshotEM:
    """Creates one ticket, then dispatches whatever the snapshot says is waiting."""

    def __init__(self) -> None:
        self.snapshots: list[str] = []

    async def plan(self, *, idea, snapshot, **_):
        self.snapshots.append(snapshot)
        if snapshot == "no tickets yet":
            return EMPlanResponse(ops=[CreateTicketOp(original_idea=idea, worker_role="backend")])
        waiting = re.search(r"- (\w+) \[backend\] Backlog \(awaiting dispatch\)", snapshot)
        if waiting:
            return EMPlanResponse(ops=[DispatchCardOp(
                card_id=waiting.group(1), role_id="backend", task=idea,
                rationale_text="backend owns the API",
            )])
        return EMPlanResponse(ops=[NoopOp(reason="in flight")])


def _worker(tasks: list[str], tool_results: list[str]):
    async def run_turn(task, **_):
        tasks.append(task)
        plan = SimpleNamespace(confidence=0.9, steps=[])
        return TurnResult(
            plan=plan, confidence=0.9, final="added GET /health",
            tool_results=tool_results, cost_usd=0.0, run=None,
        )
    return run_turn


def _handle(tmp_path, tiny_team, tiny_registry, run_turn, *, b_verdict="pass"):
    root = SessionTreeNode.create_root(cwd=tmp_path, limit=1_000_000)
    manager = SessionTreeManager(root, reserve=0, cwd=tmp_path)
    board = Board.from_team_config(
        tiny_team,
        recorder=manager,
        reviewer_a=DeterministicReviewerStub(verdict="pass", source="A"),
        reviewer_b=DeterministicReviewerStub(verdict=b_verdict, source="B"),
        cwd=tmp_path,
    )
    return EMBoardHandle(
        board=board, registry=tiny_registry, team_config=tiny_team,
        manager=manager, base_gate=PermissionGate(mode="auto", auto_yes=True),
        cwd=tmp_path, run_turn_fn=run_turn,
    )


@pytest.mark.asyncio
async def test_goal_reaches_done_through_worker_and_review(tmp_path, tiny_team, tiny_registry):
    tasks: list[str] = []
    handle = _handle(tmp_path, tiny_team, tiny_registry, _worker(tasks, ["pytest [exit 0]"]))
    em = SnapshotEM()

    rf = await em_loop(idea="build API", em_handle=handle, em_agent=em, max_iterations=10)

    assert em.snapshots[0] == "no tickets yet"
    assert rf.total_cards == 1
    assert rf.done_count == 1
    assert rf.em_iterations == 2
    assert len(tasks) == 1 and "build API" in tasks[0]
    card = handle.snapshot().cards[0]
    assert card.artifact.artifact_text == "added GET /health"


@pytest.mark.asyncio
async def test_rejected_review_retries_with_notes_then_blocks(tmp_path, tiny_team, tiny_registry):
    tasks: list[str] = []
    handle = _handle(
        tmp_path, tiny_team, tiny_registry, _worker(tasks, ["pytest [exit 0]"]), b_verdict="fail",
    )

    rf = await em_loop(idea="build API", em_handle=handle, em_agent=SnapshotEM(), max_iterations=10)

    assert rf.done_count == 0
    assert rf.blocked_count == 1
    assert len(tasks) > 1
    assert "previous attempt was rejected" in tasks[1]
    assert "reviewer_b" in tasks[1]


@pytest.mark.asyncio
async def test_worker_without_passing_tests_never_reaches_done(tmp_path, tiny_team, tiny_registry):
    handle = _handle(tmp_path, tiny_team, tiny_registry, _worker([], []))

    rf = await em_loop(idea="build API", em_handle=handle, em_agent=SnapshotEM(), max_iterations=10)

    assert rf.done_count == 0
    assert rf.blocked_count == 1


def test_worker_gate_refuses_writes_outside_ceiling_scope(tmp_path, tiny_team, tiny_registry):
    handle = _handle(tmp_path, tiny_team, tiny_registry, _worker([], []))
    gate = handle._derive_role_gate("backend")

    assert gate.check("fs_write", {"path": "src/api.py", "content": "x"})[0] is True
    assert gate.check("fs_write", {"path": "README.md", "content": "x"}) == (False, "out-of-scope denied")

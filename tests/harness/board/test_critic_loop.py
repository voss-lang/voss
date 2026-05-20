"""O3-04 Task 2: Critic loop — InReview fail → InProgress + RetryNote; ceiling → Blocked."""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.verdict import ReviewerVerdict

from .conftest import build_test_team


def _fail_verdict(round_num: int) -> ReviewerVerdict:
    return ReviewerVerdict(
        conf=0.99, source="B", tier="strong", verdict="fail",
        notes=f"round-{round_num}-notes", evidence_refs=(),
    )


class TestCriticLoop:
    @pytest.mark.asyncio
    async def test_4_fails_on_ceiling_3_lands_blocked(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="fail")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(risk_tier="low")
        artifact = SimpleNamespace(tests_passed=True, scope_violations=())
        card = dataclasses.replace(card, artifact=artifact)
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]

        # Drive to InReview.
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        card = board.move(card, to="InReview")

        # Critic rounds 1, 2, 3.
        for r in range(1, 4):
            card = board.critic_step(card, _fail_verdict(r))
            assert card.column == "InProgress"
            assert card.retry_count == r
            # Move back to InReview for next round.
            card = board.move(card, to="InReview")

        # Round 4 — ceiling hit.
        card = board.critic_step(card, _fail_verdict(4))
        assert card.column == "Blocked"

        # RetryNotes: 3 entries (rounds 1-3; round 4 hit ceiling before append).
        node = manager.get_node(card.node_id)
        assert len(node.retry_notes) == 3
        for i, note in enumerate(node.retry_notes):
            assert note["round"] == i + 1
            assert f"round-{i + 1}-notes" in note["notes"]

    @pytest.mark.asyncio
    async def test_blocked_delta_and_terminal_state(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="fail")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(risk_tier="low")
        artifact = SimpleNamespace(tests_passed=True, scope_violations=())
        card = dataclasses.replace(card, artifact=artifact)
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]

        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        card = board.move(card, to="InReview")

        for r in range(1, 4):
            card = board.critic_step(card, _fail_verdict(r))
            card = board.move(card, to="InReview")

        card = board.critic_step(card, _fail_verdict(4))

        node = manager.get_node(card.node_id)
        # Last forced transition.
        forced = [d for d in node.transitions if d["outcome"] == "forced"]
        assert len(forced) >= 1
        last_forced = forced[-1]
        assert last_forced["reason"] == "retry_ceiling"
        assert last_forced["to"] == "Blocked"
        # Terminal state maps retry_ceiling → "max-iter".
        assert node.terminal_state["exit_reason"] == "max-iter"


class TestCriticBlockVerdict:
    @pytest.mark.asyncio
    async def test_block_verdict_forces_terminal(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="block")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(risk_tier="low")
        artifact = SimpleNamespace(tests_passed=True, scope_violations=())
        card = dataclasses.replace(card, artifact=artifact)
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]

        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        card = board.move(card, to="InReview")

        block_verdict = ReviewerVerdict(
            conf=0.99, source="B", tier="strong", verdict="block",
            notes="abort lineage", evidence_refs=(),
        )
        card = board.critic_step(card, block_verdict)
        assert card.column == "Blocked"

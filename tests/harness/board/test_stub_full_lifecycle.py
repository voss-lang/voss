"""O3-03 Task 2: Full Backlog→Done lifecycle with DeterministicReviewerStub."""
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


class TestCodeLifecycle:
    @pytest.mark.asyncio
    async def test_backlog_to_done_with_passing_artifact(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        # Attach passing code artifact before InReview.
        card = dataclasses.replace(
            card, artifact=SimpleNamespace(tests_passed=True, scope_violations=()),
        )
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
        card = board.move(card, to="InReview")
        card = board.move(card, to="Done")
        assert card.column == "Done"

        node = manager.get_node(card.node_id)
        assert node is not None
        assert len(node.transitions) == 4  # Planned, InProgress, InReview, Done

        # Non-artifact transitions have verdict_snapshot=None.
        assert node.transitions[0]["verdict_snapshot"] is None  # Backlog→Planned
        assert node.transitions[1]["verdict_snapshot"] is None  # Planned→InProgress
        # Artifact transitions have verdict_snapshot populated.
        assert node.transitions[2]["verdict_snapshot"] is not None  # InProgress→InReview
        assert node.transitions[2]["verdict_snapshot"]["conf"] == 0.99
        assert node.transitions[3]["verdict_snapshot"] is not None  # InReview→Done


class TestAILifecycle:
    @pytest.mark.asyncio
    async def test_ai_card_uses_eval_meets_threshold(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        # AI artifact: has eval_score but NOT tests_passed.
        card = dataclasses.replace(
            card,
            artifact=SimpleNamespace(eval_score=0.95, scope_violations=()),
            eval_threshold=0.9,
        )
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
        card = board.move(card, to="InReview")
        card = board.move(card, to="Done")
        assert card.column == "Done"

    @pytest.mark.asyncio
    async def test_ai_card_below_threshold_refused(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        # AI artifact with eval_score below threshold.
        card = dataclasses.replace(
            card,
            artifact=SimpleNamespace(eval_score=0.5, scope_violations=()),
            eval_threshold=0.9,
        )
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
        card = board.move(card, to="InReview")
        with pytest.raises(BoardGateError) as exc:
            board.move(card, to="Done")
        assert "eval" in exc.value.failing_clauses

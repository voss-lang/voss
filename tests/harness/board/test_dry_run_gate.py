"""O3-03 Task 2: dry_run_gate non-destructive + refused-move delta emission."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


class TestDryRunGate:
    @pytest.mark.asyncio
    async def test_passing_returns_true_empty(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        passed, failing = board.dry_run_gate(card, ("InProgress", "InReview"))
        assert passed is True
        assert failing == []

    @pytest.mark.asyncio
    async def test_conf_failing_returns_false_with_clause(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.5)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="high")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        passed, failing = board.dry_run_gate(card, ("InProgress", "InReview"))
        assert passed is False
        assert "conf" in failing

    @pytest.mark.asyncio
    async def test_dry_run_does_not_mutate_state(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.5)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="high")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        node = manager.get_node(card.node_id)
        deltas_before = len(node.transitions)
        cards_before = board.cards()

        board.dry_run_gate(card, ("InProgress", "InReview"))

        assert len(node.transitions) == deltas_before
        assert board.cards() == cards_before
        assert card.column == "InProgress"  # unchanged


class TestRefusedMoveEmitsDelta:
    @pytest.mark.asyncio
    async def test_gate_refusal_emits_refused_delta(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.5)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="high")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        with pytest.raises(BoardGateError) as exc:
            board.move(card, to="InReview")
        assert "conf" in exc.value.failing_clauses
        node = manager.get_node(card.node_id)
        # 2 passed (Planned, InProgress) + 1 refused = 3 total
        assert len(node.transitions) == 3
        last = node.transitions[-1]
        assert last["outcome"] == "refused"
        assert "conf" in last["failing_clauses"]

    @pytest.mark.asyncio
    async def test_scope_violation_refuses_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        # Give artifact with scope violation.
        import dataclasses
        card = dataclasses.replace(
            card, artifact=SimpleNamespace(tests_passed=True, scope_violations=("/etc",)),
        )
        # Manually update card in board so move sees it.
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
        card = board.move(card, to="InReview")
        passed, failing = board.dry_run_gate(card, ("InReview", "Done"))
        assert passed is False
        assert "scope" in failing

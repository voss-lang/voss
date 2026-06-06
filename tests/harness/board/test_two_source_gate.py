"""VREV-03/04/07 RED scaffold: two-source (A+B) Done gate + B-block + slot back-compat.

RED until V6 adds reviewer_a/reviewer_b slots to Board, the a_verification_passes
and b_passes gate predicates, and the terminal B-block routing. These tests fail
at runtime (missing slots / gate behavior), NOT at collection.
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


def _clean_code_artifact():
    return SimpleNamespace(tests_passed=True, scope_violations=())


async def _to_inreview(board, *, risk_tier="low"):
    """Drive a card Backlog→InReview with a clean code artifact attached."""
    card = await board.spawn_card(risk_tier=risk_tier)
    card = board.move(card, to="Planned")
    card = board.move(card, to="InProgress")
    card = dataclasses.replace(card, artifact=_clean_code_artifact())
    board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
    card = board.move(card, to="InReview")
    return card


class TestBoardSlotBackCompat:
    @pytest.mark.asyncio
    async def test_legacy_reviewer_alias_satisfies_both_slots(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        # D-01 back-compat: single-slot construction fans out to both slots.
        assert board._reviewer_a is stub
        assert board._reviewer_b is stub


class TestTwoSourceGate:
    @pytest.mark.asyncio
    async def test_both_pass_reaches_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
        stub_b = DeterministicReviewerStub(conf=0.95, verdict="pass", source="B", tier="strong")
        board = Board.from_team_config(
            build_test_team(), recorder=manager,
            reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
        )
        card = await _to_inreview(board)
        card = board.move(card, to="Done")
        assert card.column == "Done"

    @pytest.mark.asyncio
    async def test_a_fail_refuses_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub_a = DeterministicReviewerStub(conf=0.99, verdict="fail", source="A", tier="fast")
        stub_b = DeterministicReviewerStub(conf=0.95, verdict="pass", source="B", tier="strong")
        board = Board.from_team_config(
            build_test_team(), recorder=manager,
            reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
        )
        card = await _to_inreview(board)
        with pytest.raises(BoardGateError):
            board.move(card, to="Done")

    @pytest.mark.asyncio
    async def test_b_fail_refuses_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
        stub_b = DeterministicReviewerStub(conf=0.95, verdict="fail", source="B", tier="strong")
        board = Board.from_team_config(
            build_test_team(), recorder=manager,
            reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
        )
        card = await _to_inreview(board)
        with pytest.raises(BoardGateError):
            board.move(card, to="Done")


class TestBBlockAtGate:
    @pytest.mark.asyncio
    async def test_b_block_routes_to_blocked_terminal(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
        stub_b = DeterministicReviewerStub(conf=0.95, verdict="block", source="B", tier="strong")
        board = Board.from_team_config(
            build_test_team(), recorder=manager,
            reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
        )
        card = await _to_inreview(board)
        # D-03: B-block at the Done gate is terminal, not retry-able.
        card = board.move(card, to="Done")
        assert card.column == "Blocked"
        node = manager.get_node(card.node_id)
        assert node is not None
        assert node.terminal_state["exit_reason"] == "max-iter"

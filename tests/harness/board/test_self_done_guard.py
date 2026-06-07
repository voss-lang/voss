"""VBOARD-07 self-Done independence guard — Wave 0 RED scaffold.

Drives the REAL planned behavior (V5-02): move(card,"Done") on a Board built
with reviewer=None raises BoardGateError carrying "no-reviewer" in
failing_clauses. Today the gate refuses with ["conf"] (the explicit guard is
missing), so the no-reviewer assertion is RED until V5-02 lands.

The positive path (valid reviewer permits Done) and the structural
no-verdict-injection tripwire are GREEN now and pin invariants.

No xfail/skip masking — failures are genuine.
"""
from __future__ import annotations

import dataclasses
import inspect
from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


def _rebind(board: Board, card):
    """Replace the live card in board._cards by node_id (lifecycle helper)."""
    board._cards = [card if c.node_id == card.node_id else c for c in board._cards]


class TestSelfDoneGuard:
    @pytest.mark.asyncio
    async def test_reviewer_none_raises_board_gate_error(self, tmp_recorder):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=None, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        # With reviewer=None the conf gate blocks InProgress→InReview, so place
        # the card in InReview directly (bypassing the gate) to isolate the
        # Done independence guard under test.
        card = dataclasses.replace(
            card,
            column="InReview",
            artifact=SimpleNamespace(tests_passed=True, scope_violations=()),
        )
        _rebind(board, card)
        with pytest.raises(BoardGateError) as exc_info:
            board.move(card, to="Done")
        # RED now: current refusal is ["conf"], not ["no-reviewer"].
        assert "no-reviewer" in exc_info.value.failing_clauses

    @pytest.mark.asyncio
    async def test_valid_reviewer_allows_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        card = dataclasses.replace(
            card, artifact=SimpleNamespace(tests_passed=True, scope_violations=()),
        )
        _rebind(board, card)
        card = board.move(card, to="InReview")
        card = board.move(card, to="Done")
        assert card.column == "Done"

    @pytest.mark.asyncio
    async def test_no_verdict_injection_path(self, tmp_recorder):
        # Structural tripwire (T-V5-02 Spoofing): Board.move has no `verdict`
        # parameter — a worker/EM cannot inject a self-authored verdict. The
        # only verdict source is the Board's injected Reviewer. GREEN now.
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=None, cwd=cwd,
        )
        params = inspect.signature(board.move).parameters
        assert "verdict" not in params

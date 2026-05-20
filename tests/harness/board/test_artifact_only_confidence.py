"""O3-03 Task 2: Artifact-only confidence — reviewer never called for non-artifact transitions."""
from __future__ import annotations

import pytest

from voss.harness.board import Board
from voss.harness.board.verdict import ReviewerVerdict

from .conftest import build_test_team


class _RaisingReviewer:
    """Raises AssertionError if invoked. Proves non-artifact transitions skip the reviewer."""
    def review(self, card: object) -> ReviewerVerdict:
        raise AssertionError("reviewer should not be invoked for this transition")


class TestArtifactOnlyConfidence:
    @pytest.mark.asyncio
    async def test_backlog_to_planned_skips_reviewer(self, tmp_recorder):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=_RaisingReviewer(), cwd=cwd,
        )
        card = await board.spawn_card()
        # Should NOT invoke the reviewer.
        card = board.move(card, to="Planned")
        assert card.column == "Planned"

    @pytest.mark.asyncio
    async def test_planned_to_inprogress_skips_reviewer(self, tmp_recorder):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=_RaisingReviewer(), cwd=cwd,
        )
        card = await board.spawn_card()
        card = board.move(card, to="Planned")
        # Should NOT invoke the reviewer.
        card = board.move(card, to="InProgress")
        assert card.column == "InProgress"

    @pytest.mark.asyncio
    async def test_inprogress_to_inreview_invokes_reviewer(self, tmp_recorder):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=_RaisingReviewer(), cwd=cwd,
        )
        card = await board.spawn_card()
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        # SHOULD invoke the reviewer — expect the assertion error.
        with pytest.raises(AssertionError, match="reviewer should not be invoked"):
            board.move(card, to="InReview")

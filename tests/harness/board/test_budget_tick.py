"""O3-04 Task 1: Budget exhaustion → Blocked(budget) via _tick_once."""
from __future__ import annotations

import pytest

from voss.harness.board import Board
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.session_tree import mutate_envelope

from .conftest import build_test_team


class TestBudgetTick:
    @pytest.mark.asyncio
    async def test_budget_drain_forces_blocked_budget(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(per_card_budget=1000)
        node = manager.get_node(card.node_id)
        assert node is not None

        # Drain the envelope.
        mutate_envelope(node, -1000, cwd)

        board._tick_once(fake_clock())

        cards = board.cards()
        assert cards[0].column == "Blocked"

        last_delta = node.transitions[-1]
        assert last_delta["outcome"] == "forced"
        assert last_delta["reason"] == "budget"
        assert node.terminal_state["exit_reason"] == "budget"

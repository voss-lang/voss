"""O3-04 Task 1: Wall-clock deadline → Blocked(timeout) via _tick_once."""
from __future__ import annotations

import pytest

from voss.harness.board import Board
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


class TestTimeoutTick:
    @pytest.mark.asyncio
    async def test_deadline_elapse_forces_blocked_timeout(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(deadline_override=fake_clock() + 30.0)
        assert card.column == "Backlog"

        fake_clock.advance(31.0)
        board._tick_once(fake_clock())

        cards = board.cards()
        assert len(cards) == 1
        assert cards[0].column == "Blocked"

        node = manager.get_node(card.node_id)
        last_delta = node.transitions[-1]
        assert last_delta["outcome"] == "forced"
        assert last_delta["reason"] == "timeout"
        assert last_delta["to"] == "Blocked"
        assert node.terminal_state == {"exit_reason": "timeout", "final": ""}

    @pytest.mark.asyncio
    async def test_tick_once_idempotent(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(deadline_override=fake_clock() + 10.0)
        fake_clock.advance(11.0)

        board._tick_once(fake_clock())
        node = manager.get_node(card.node_id)
        delta_count_after_first = len(node.transitions)

        board._tick_once(fake_clock())
        assert len(node.transitions) == delta_count_after_first

    @pytest.mark.asyncio
    async def test_already_terminal_cards_skipped(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99)
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
            clock=fake_clock,
        )
        card = await board.spawn_card(deadline_override=fake_clock() + 5.0)
        # Force to Blocked first.
        fake_clock.advance(6.0)
        board._tick_once(fake_clock())
        assert board.cards()[0].column == "Blocked"

        # Now even with further time advance, no new transition.
        node = manager.get_node(card.node_id)
        count_before = len(node.transitions)
        fake_clock.advance(100.0)
        board._tick_once(fake_clock())
        assert len(node.transitions) == count_before

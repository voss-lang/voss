"""O3-02 Task 2: transition-delta count == transition-attempt count (SPEC L123)."""
from __future__ import annotations

import pytest

from voss.harness.board import Board, BoardGateError, BoardWIPError

from .conftest import build_test_team


class TestTransitionCountInvariant:
    @pytest.mark.asyncio
    async def test_mixed_lifecycle_delta_count_equals_attempt_count(
        self, tmp_recorder, stub_reviewer,
    ):
        """20-transition mixed lifecycle across 5 cards.

        Every move attempt — passed or refused — appends exactly one delta
        to the card's session-tree node. Sum of per-node transition counts
        must equal total attempts.
        """
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub_reviewer, cwd=cwd,
        )

        attempts: dict[str, int] = {}

        def attempt(card, to):
            attempts[card.node_id] = attempts.get(card.node_id, 0) + 1
            try:
                return board.move(card, to=to)
            except (BoardGateError, BoardWIPError):
                return card  # card unchanged on refusal

        cards = [await board.spawn_card(risk_tier="low") for _ in range(5)]

        # card 0: Backlog → Planned → InProgress → InReview + 1 unknown = 4 attempts
        c = cards[0]
        c = attempt(c, "Planned")
        c = attempt(c, "InProgress")
        c = attempt(c, "InReview")
        attempt(c, "Foo")  # refused — unknown column

        # card 1: Backlog → Planned → InProgress = 2 attempts
        c = cards[1]
        c = attempt(c, "Planned")
        c = attempt(c, "InProgress")

        # card 2: Backlog → InProgress = 1 attempt
        c = cards[2]
        c = attempt(c, "InProgress")

        # card 3: Backlog → InProgress (4th InProgress → WIP refusal) = 1 attempt
        c = cards[3]
        attempt(c, "InProgress")  # refused — WIP cap

        # card 4: 12 mixed attempts to reach 20 total
        c = cards[4]
        c = attempt(c, "Planned")
        c = attempt(c, "Done")
        attempt(c, "Foo")
        attempt(c, "Bar")
        attempt(c, "Baz")
        attempt(c, "InProgress")  # WIP may or may not refuse depending on state
        attempt(c, "InProgress")
        attempt(c, "InReview")
        attempt(c, "Blocked")
        attempt(c, "Done")
        attempt(c, "Qux")
        attempt(c, "Zap")

        total_attempts = sum(attempts.values())
        assert total_attempts == 4 + 2 + 1 + 1 + 12

        # Invariant: per-node transition count == per-card attempt count.
        for card in board.cards():
            node = manager.get_node(card.node_id)
            assert node is not None
            assert len(node.transitions) == attempts.get(card.node_id, 0), (
                f"card {card.node_id}: "
                f"expected {attempts.get(card.node_id, 0)} deltas, "
                f"got {len(node.transitions)}"
            )

        # Cards that were refused and never moved: check their original nodes too.
        for nid, count in attempts.items():
            node = manager.get_node(nid)
            assert node is not None
            assert len(node.transitions) == count

        # Global sum.
        total_deltas = sum(
            len(manager.get_node(nid).transitions)
            for nid in attempts
            if manager.get_node(nid) is not None
        )
        assert total_deltas == total_attempts

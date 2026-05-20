"""O3-02 Task 2: 6-column acceptance + unknown-column rejection + delta emission."""
from __future__ import annotations

import pytest

from voss.harness.board import Board, BoardGateError

from .conftest import build_test_team

_COLUMNS = ("Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done")


class TestColumnAcceptance:
    @pytest.mark.asyncio
    async def test_all_6_columns_accepted(self, tmp_recorder, stub_reviewer):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub_reviewer, cwd=cwd,
        )
        for col in _COLUMNS:
            card = await board.spawn_card(risk_tier="low")
            moved = board.move(card, to=col)
            assert moved.column == col
            node = manager.get_node(card.node_id)
            assert node is not None
            assert node.transitions[-1]["to"] == col
            assert node.transitions[-1]["outcome"] == "passed"


class TestUnknownColumn:
    @pytest.mark.asyncio
    async def test_unknown_column_raises_gate_error(self, tmp_recorder, stub_reviewer):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub_reviewer, cwd=cwd,
        )
        card = await board.spawn_card()
        with pytest.raises(BoardGateError) as exc:
            board.move(card, to="Foo")
        assert "unknown column: Foo" in str(exc.value)

    @pytest.mark.asyncio
    async def test_refused_move_emits_delta(self, tmp_recorder, stub_reviewer):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub_reviewer, cwd=cwd,
        )
        card = await board.spawn_card()
        with pytest.raises(BoardGateError):
            board.move(card, to="Foo")
        node = manager.get_node(card.node_id)
        assert node is not None
        assert len(node.transitions) == 1
        delta = node.transitions[0]
        assert delta["outcome"] == "refused"
        assert delta["failing_clauses"] == ["unknown-column"]

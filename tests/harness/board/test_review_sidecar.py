"""VREV-09 RED scaffold: .review.json sidecar persistence on the Done gate.

RED until V6 adds _write_review_sidecar (0o600 JSON with a_verification /
b_verdict / final_outcome) on the InReview->Done transition. Fails at runtime
(sidecar absent), NOT at collection.
"""

from __future__ import annotations

import dataclasses
import json
from types import SimpleNamespace

import pytest

from voss.harness.board import Board
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team


class TestReviewSidecar:
    @pytest.mark.asyncio
    async def test_sidecar_written_on_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
        stub_b = DeterministicReviewerStub(conf=0.95, verdict="pass", source="B", tier="strong")
        board = Board.from_team_config(
            build_test_team(), recorder=manager,
            reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        card = dataclasses.replace(
            card, artifact=SimpleNamespace(tests_passed=True, scope_violations=()),
        )
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
        card = board.move(card, to="InReview")
        card = board.move(card, to="Done")
        assert card.column == "Done"

        node = manager.get_node(card.node_id)
        assert node is not None
        sidecar = cwd / ".voss" / "sessions" / node.root_id / f"{card.node_id}.review.json"
        assert sidecar.exists(), "review sidecar not written"
        assert oct(sidecar.stat().st_mode)[-3:] == "600"

        data = json.loads(sidecar.read_text())
        assert "a_verification" in data
        assert "b_verdict" in data
        assert "final_outcome" in data
        assert data["final_outcome"] == "Done"

"""VBOARD-03 Card field completeness — Wave 0 RED scaffold.

Drives the REAL planned API (V5-02):
  - Card gains additive fields: idea / role / acceptance_criteria /
    verification_requirement, all defaulting to "".
  - Module-level helpers card_status(card) and card_budget(envelope).

RED until V5-02 implements those symbols/fields. Failures are genuine
(AttributeError / unexpected-keyword / ImportError) — no xfail/skip masking.
"""
from __future__ import annotations

import dataclasses

import pytest

from voss.harness.board import Card


class TestCardFieldsV5:
    def test_new_fields_have_defaults(self):
        card = Card(
            node_id="n1", column="Backlog", risk_tier="med",
            retry_count=0, deadline=999.0,
        )
        # RED now: Card has no such fields → AttributeError on access.
        assert card.idea == ""
        assert card.role == ""
        assert card.acceptance_criteria == ""
        assert card.verification_requirement == ""

    def test_card_is_still_frozen(self):
        card = Card(
            node_id="n1", column="Backlog", risk_tier="med",
            retry_count=0, deadline=999.0,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            card.idea = "something"  # type: ignore[misc]

    def test_old_construction_paths_unchanged(self):
        # RED now: `idea` is an unexpected keyword until V5-02.
        card = Card(
            node_id="n1", column="Backlog", risk_tier="med",
            retry_count=0, deadline=999.0, idea="test idea",
        )
        moved = dataclasses.replace(card, column="Planned")
        assert moved.column == "Planned"
        assert moved.idea == "test idea"  # carries through replace


class TestCardStatus:
    def test_card_status_returns_column(self):
        # RED now: helper does not exist → ImportError at method scope.
        from voss.harness.board.machine import card_status

        card = Card(
            node_id="n1", column="InProgress", risk_tier="med",
            retry_count=0, deadline=999.0,
        )
        assert card_status(card) == "InProgress"


class TestCardBudget:
    def test_card_budget_reads_envelope(self):
        # RED now: helper does not exist → ImportError at method scope.
        from voss.harness.board.machine import card_budget

        spent, limit = card_budget({"spent": 100, "limit": 1000})
        assert spent == 100
        assert limit == 1000
        # Missing-keys default to (0, 0).
        assert card_budget({}) == (0, 0)

"""O4-01 RED scaffold for full board lifecycle with real reviewers (ORVW-10).

This test FAILS until O4-04 wires ReviewerA + ReviewerB into a Board run.
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(strict=True, reason="ORVW-10: ReviewerA+B integration not implemented")
def test_board_lifecycle_with_real_reviewers():
    """Full board lifecycle with ReviewerA+B stubs drives card to Done."""
    pytest.fail("RED — implement in O4-04")

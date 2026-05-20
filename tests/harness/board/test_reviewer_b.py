"""O4-01 RED scaffolds for Reviewer B (ORVW-04, 05, 06, 07, 09).

These tests FAIL until O4-02 implements ReviewerB. All xfail(strict=True).

Preflight finding: Reviewer.review is SYNC (not async). ReviewerB impl
must be sync or wrap its async internals before returning ReviewerVerdict.
"""
from __future__ import annotations

import pytest

from voss.harness.board.verdict import ReviewerVerdict, Reviewer


@pytest.mark.xfail(strict=True, reason="ORVW-04: ReviewerB not implemented")
def test_b_message_isolation():
    """B receives only [artifact, acceptance, repo, original_idea,
    a_verification_summary] — no EM narrative."""
    pytest.fail("RED — implement in O4-02")


@pytest.mark.xfail(strict=True, reason="ORVW-05: ReviewerB not implemented")
def test_b_tier_selection():
    """B uses fast model at intermediate gate."""
    pytest.fail("RED — implement in O4-02")


@pytest.mark.xfail(strict=True, reason="ORVW-06: ReviewerB not implemented")
def test_b_tier_strong():
    """B uses strong model at Done gate."""
    pytest.fail("RED — implement in O4-02")


@pytest.mark.xfail(strict=True, reason="ORVW-07: ReviewerB not implemented")
def test_b_residual_2_block():
    """B returns verdict='block' when A-verification diverges from idea
    (Residual-2 invariant)."""
    pytest.fail("RED — implement in O4-02")


@pytest.mark.xfail(strict=True, reason="ORVW-09: ReviewerB not implemented")
def test_b_implements_protocol():
    """ReviewerB is an instance of the Reviewer Protocol."""
    pytest.fail("RED — implement in O4-02")

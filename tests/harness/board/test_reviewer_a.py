"""O4-01 RED scaffolds for Reviewer A (ORVW-01, 02, 03, 08, 09).

These tests FAIL until O4-03 implements ReviewerA. All are xfail(strict=True)
so they surface as XPASS the moment the implementation lands — no manual
un-skip needed.

Preflight finding (O4-01-SUMMARY): Card does NOT carry original_idea, domain,
artifact_path, artifact_text, file_diff, a_verification_summary. O4-02/O4-03
must wrap Card in a richer ReviewContext before calling review(). The
Reviewer.review(card: object) Protocol is duck-typed for exactly this reason.
"""
from __future__ import annotations

import pytest

from voss.harness.board.verdict import ReviewerVerdict, Reviewer


@pytest.mark.xfail(strict=True, reason="ORVW-01: ReviewerA not implemented")
def test_a_uses_original_idea():
    """A derives bar from original idea, not EM AC."""
    pytest.fail("RED — implement in O4-03")


@pytest.mark.xfail(strict=True, reason="ORVW-02: ReviewerA not implemented")
def test_a_authors_test_file():
    """A authors tests for code cards; exit code is verdict."""
    pytest.fail("RED — implement in O4-03")


@pytest.mark.xfail(strict=True, reason="ORVW-03: ReviewerA not implemented")
def test_a_ai_card_eval():
    """A uses judge_run for AI cards (rubric → Verdict)."""
    pytest.fail("RED — implement in O4-03")


@pytest.mark.xfail(strict=True, reason="ORVW-08: ReviewerA not implemented")
def test_a_memory_fresh_per_card():
    """EpisodicMemory is fresh per review() call, no cross-card bleed."""
    pytest.fail("RED — implement in O4-03")


@pytest.mark.xfail(strict=True, reason="ORVW-09: ReviewerA not implemented")
def test_a_implements_protocol():
    """ReviewerA is an instance of the Reviewer Protocol."""
    pytest.fail("RED — implement in O4-03")

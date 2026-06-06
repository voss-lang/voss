"""VREV-06 RED scaffold: ReviewerVerdict.domain_inferred (7th field).

RED until V6-02 adds the `domain_inferred` field to ReviewerVerdict and the
clamp to {code,ai,docs,unknown} in ReviewerB._to_verdict. These tests fail at
runtime (missing field / attribute), NOT at collection.
"""

from __future__ import annotations

from dataclasses import fields

from voss.harness.board.reviewer_b import ReviewerB, _ReviewerBOutput
from voss.harness.board.verdict import ReviewerVerdict

_ALLOWED = {"code", "ai", "docs", "unknown"}


class TestDomainInferred:
    def test_defaults_to_unknown(self):
        # Keyword construction without domain_inferred -> default "unknown".
        v = ReviewerVerdict(
            conf=0.9, source="B", tier="fast", verdict="pass",
            notes="ok", evidence_refs=(),
        )
        assert v.domain_inferred == "unknown"

    def test_exactly_7_fields(self):
        names = {f.name for f in fields(ReviewerVerdict)}
        assert names == {
            "conf", "source", "tier", "verdict", "notes", "evidence_refs",
            "domain_inferred",
        }

    def test_b_populates_clamped_domain(self):
        # B infers a domain; out-of-set values clamp to "unknown".
        from .test_reviewer_b import FakeReviewerBProvider

        canned = _ReviewerBOutput(
            conf=0.95, verdict="pass", notes="ok", evidence_refs=["api.py:1"],
        )
        provider = FakeReviewerBProvider(canned)
        b = ReviewerB(provider=provider, fast_model="test-fast", strong_model="test-strong")

        from types import SimpleNamespace

        card = SimpleNamespace(
            original_idea="x", acceptance_criteria="y", artifact="z",
            artifact_text="z", file_diff="+z", a_verification_summary="s",
            node_id="n", column="InReview", risk_tier="med",
        )
        v = b.review(card)
        assert v.domain_inferred in _ALLOWED

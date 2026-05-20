"""DeterministicReviewerStub — O3 test reviewer.

Production code must NOT import this module. The O3-04 stress test enforces
this via a repo-wide grep gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .verdict import ReviewerVerdict


@dataclass
class DeterministicReviewerStub:
    """Returns a fixed ReviewerVerdict for every review call.

    Test-only. Satisfies the Reviewer Protocol structurally.
    """
    conf: float = 0.99
    verdict: str = "pass"
    tier: str = "strong"
    source: str = "B"

    def review(self, card: object) -> ReviewerVerdict:
        return ReviewerVerdict(
            conf=self.conf,
            source=self.source,       # type: ignore[arg-type]
            tier=self.tier,           # type: ignore[arg-type]
            verdict=self.verdict,     # type: ignore[arg-type]
            notes="(deterministic stub)",
            evidence_refs=(),
        )

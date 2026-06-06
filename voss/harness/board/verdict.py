"""O4 plug-in contract. ZERO transitive harness imports — verified by test.

Adding any import beyond `typing`, `dataclasses`, `__future__` here breaks the
contract that O4's Reviewer A/B impls can import this module without circular
dependencies. See O3-SPEC.md acceptance L124.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ReviewerVerdict:
    """Frozen 7-field verdict shape (SPEC OBRD-07 + VREV-06).

    Fields:
        conf:           [0.0, 1.0] confidence score from Reviewer B
        source:         which reviewer authored this verdict (A or B)
        tier:           B.fast at intermediate gates; B.strong at ->Done
        verdict:        pass | fail | block (block = abort lineage)
        notes:          reviewer-authored text; appended to retry_notes on fail
        evidence_refs:  pointers (file:line, test names, eval refs)
        domain_inferred: inferred work domain; B populates (clamped), A defaults
    """
    conf: float
    source: Literal["A", "B"]
    tier: Literal["fast", "strong"]
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: tuple[str, ...]
    # VREV-06 (D-06): additive, defaulted, MUST be last on this frozen+slots
    # dataclass. B clamps the LLM value to this set; A leaves the default.
    domain_inferred: Literal["code", "ai", "docs", "unknown"] = "unknown"


@runtime_checkable
class Reviewer(Protocol):
    """The injectable reviewer interface.

    O3 ships DeterministicReviewerStub in stub.py (planned in O3-03); O4 will
    ship Reviewer A + Reviewer B production impls. `card` is typed as `object`
    to keep this module zero-deps; concrete impls may use stricter typing.
    """
    def review(self, card: object) -> ReviewerVerdict: ...

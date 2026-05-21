"""Frozen value-objects for the EM's audit trail (O5 OEM-01/07/10).

Every record is `frozen=True, slots=True` so the EM cannot mutate emitted
audit records. The `kind` field carries a `Literal["em.*"]` discriminator
so O6's audit surface can distinguish EM records from O3's `board.*` records.

Imports: typing + dataclasses only (mirrors O3 verdict.py's zero-deps discipline).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Ticket:
    """A work item authored by the EM from the human idea."""
    id: str
    card_node_id: str
    original_idea: str
    acceptance: str
    dod: str
    worker_role: str
    routing_rationale_id: str
    created_at: str
    lineage_parent_id: Optional[str] = None
    domain: Literal["code", "ai"] = "code"
    risk_tier: Literal["low", "med", "high"] = "med"
    kind: Literal["em.ticket"] = "em.ticket"

    def __post_init__(self) -> None:
        assert self.kind == "em.ticket", f"kind must be 'em.ticket', got {self.kind!r}"


# ---------------------------------------------------------------------------
# RoutingRationale
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RoutingRationale:
    """Why the EM dispatched a card to a specific roster role."""
    id: str
    card_id: str
    chosen_role: str
    candidates_considered: tuple[str, ...]
    rationale_text: str
    ts: str
    confidence_hint: Optional[float] = None
    kind: Literal["em.routing"] = "em.routing"

    def __post_init__(self) -> None:
        assert self.kind == "em.routing", f"kind must be 'em.routing', got {self.kind!r}"
        if self.confidence_hint is not None:
            if not (0.0 <= self.confidence_hint <= 1.0):
                raise ValueError(
                    f"confidence_hint must be in [0, 1], got {self.confidence_hint}"
                )


# ---------------------------------------------------------------------------
# KillRecord
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KillRecord:
    """Record of the EM killing a card. Never deletes the session-tree node."""
    killed_node_id: str
    rationale_text: str
    evidence_refs: tuple[str, ...]
    killed_at: str
    lineage_parent_id: Optional[str] = None
    successor_card_id: Optional[str] = None
    kind: Literal["em.kill"] = "em.kill"

    def __post_init__(self) -> None:
        assert self.kind == "em.kill", f"kind must be 'em.kill', got {self.kind!r}"
        if self.lineage_parent_id is not None and self.lineage_parent_id == self.killed_node_id:
            raise ValueError("self-parented kill: lineage_parent_id == killed_node_id")


# ---------------------------------------------------------------------------
# RescopeRecord
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RescopeRecord:
    """Record of the EM rescoping a card — creates a new card linked to the old."""
    predecessor_card_id: str
    successor_card_id: str
    diff_summary: str
    rationale_text: str
    rescoped_at: str
    new_acceptance: tuple[str, ...] = field(default_factory=tuple)
    new_dod: tuple[str, ...] = field(default_factory=tuple)
    kind: Literal["em.rescope"] = "em.rescope"

    def __post_init__(self) -> None:
        assert self.kind == "em.rescope", f"kind must be 'em.rescope', got {self.kind!r}"
        if self.predecessor_card_id == self.successor_card_id:
            raise ValueError("self-rescope: predecessor_card_id == successor_card_id")


# ---------------------------------------------------------------------------
# RunFinal
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RunFinal:
    """Summary record emitted when the EM loop terminates."""
    root_id: str
    idea: str
    total_cards: int
    done_count: int
    blocked_count: int
    killed_count: int
    rescope_count: int
    em_iterations: int
    ts: str
    kind: Literal["em.run_final"] = "em.run_final"

    def __post_init__(self) -> None:
        assert self.kind == "em.run_final", f"kind must be 'em.run_final', got {self.kind!r}"
        for name in ("total_cards", "done_count", "blocked_count",
                     "killed_count", "rescope_count", "em_iterations"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative, got {getattr(self, name)}")

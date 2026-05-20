"""Voss EM (Engineering Manager) subpackage (O5).

Frozen value-objects for the EM's audit trail: tickets, routing rationale,
kill/rescope lineage, and run-final summaries. Every record carries a
`kind="em.*"` discriminator distinct from O3's `board.*` records.
"""
from .tickets import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal
from .errors import EMCageViolation

__all__ = [
    "Ticket", "KillRecord", "RescopeRecord", "RoutingRationale",
    "RunFinal", "EMCageViolation",
]

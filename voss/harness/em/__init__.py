"""Voss EM (Engineering Manager) subpackage (O5).

Frozen value-objects for the EM's audit trail: tickets, routing rationale,
kill/rescope lineage, and run-final summaries. Every record carries a
`kind="em.*"` discriminator distinct from O3's `board.*` records.

EMBoardHandle is the cage-bounded facade — the EM's ONLY board API.
"""
from .tickets import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal
from .errors import EMCageViolation
from .protocols import BoardProtocol, CardProtocol, Column
from .handle import EMBoardHandle, BoardSnapshot

__all__ = [
    "Ticket", "KillRecord", "RescopeRecord", "RoutingRationale",
    "RunFinal", "EMCageViolation",
    "BoardProtocol", "CardProtocol", "Column",
    "EMBoardHandle", "BoardSnapshot",
]

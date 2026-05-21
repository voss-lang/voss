"""Voss EM (Engineering Manager) subpackage (O5).

Frozen value-objects for the EM's audit trail: tickets, routing rationale,
kill/rescope lineage, and run-final summaries. Every record carries a
`kind="em.*"` discriminator distinct from O3's `board.*` records.

EMBoardHandle is the cage-bounded facade — the EM's ONLY board API.
EMPlanResponse + em_plan provide the LLM structured-output surface.
DeterministicEMStub is for tests only.
"""
from .tickets import Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal
from .errors import EMCageViolation
from .protocols import BoardProtocol, CardProtocol, Column
from .handle import EMBoardHandle, BoardSnapshot
from .schema import (
    EMPlanResponse, EMOp,
    CreateTicketOp, DispatchCardOp, KillCardOp, RescopeCardOp,
    SetACOp, SetDoDOp, NoopOp,
)
from .llm import em_plan
from .stub import DeterministicEMStub

__all__ = [
    "Ticket", "KillRecord", "RescopeRecord", "RoutingRationale",
    "RunFinal", "EMCageViolation",
    "BoardProtocol", "CardProtocol", "Column",
    "EMBoardHandle", "BoardSnapshot",
    "EMPlanResponse", "EMOp",
    "CreateTicketOp", "DispatchCardOp", "KillCardOp", "RescopeCardOp",
    "SetACOp", "SetDoDOp", "NoopOp",
    "em_plan", "DeterministicEMStub",
]

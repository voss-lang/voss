"""EM structured-output schema — pydantic v2 LENIENT (O5-03, OEM-03).

LENIENT posture (extra="ignore"): hallucinated LLM fields drop silently
at parse. The cage is enforced by the EMBoardHandle facade (W2), NOT by
the schema. This mirrors voss/eval/judge.py's Verdict posture and
contrasts with voss/harness/cognition_schemas.py's STRICT ("extra=forbid")
used for harness config files.

The 7 Op models form a discriminated union routed on the `op` field.
EMPlanResponse.ops has max_length=20 to bound per-iteration blast radius.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


LENIENT = ConfigDict(extra="ignore")


class CreateTicketOp(BaseModel):
    model_config = LENIENT
    op: Literal["create_ticket"] = "create_ticket"
    original_idea: str = Field(description="The original human idea for this work item")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Acceptance criteria derived from the idea")
    dod: list[str] = Field(default_factory=list, description="Definition of done checklist")
    worker_role: str = Field(description="Roster role to assign (e.g. backend, frontend, ai)")
    domain: Literal["code", "ai"] = Field(default="code", description="Work domain: code or ai")
    risk_tier: Literal["low", "med", "high"] = Field(default="med", description="Risk tier for confidence gating")


class DispatchCardOp(BaseModel):
    model_config = LENIENT
    op: Literal["dispatch_card"] = "dispatch_card"
    card_id: str = Field(description="ID of the card to dispatch")
    role_id: str = Field(description="Roster role to dispatch to")
    task: str = Field(description="Task description for the specialist")
    rationale_text: str = Field(description="Why this role was chosen")
    candidates_considered: list[str] = Field(default_factory=list, description="Roles that were considered")
    confidence_hint: Optional[float] = Field(default=None, ge=0, le=1, description="Optional routing confidence [0,1]")


class KillCardOp(BaseModel):
    model_config = LENIENT
    op: Literal["kill_card"] = "kill_card"
    card_id: str = Field(description="ID of the card to kill")
    rationale_text: str = Field(description="Reason for killing this card")


class RescopeCardOp(BaseModel):
    model_config = LENIENT
    op: Literal["rescope_card"] = "rescope_card"
    card_id: str = Field(description="ID of the card to rescope")
    new_worker_role: str = Field(description="New roster role for the rescoped card")
    new_scope: Optional[str] = Field(default=None, description="New scope glob pattern")
    new_acceptance: list[str] = Field(default_factory=list, description="Updated acceptance criteria")
    rationale_text: str = Field(description="Reason for rescoping")


class SetACOp(BaseModel):
    model_config = LENIENT
    op: Literal["set_ac"] = "set_ac"
    card_id: str = Field(description="ID of the card to update")
    acceptance_criteria: list[str] = Field(description="New acceptance criteria")


class SetDoDOp(BaseModel):
    model_config = LENIENT
    op: Literal["set_dod"] = "set_dod"
    card_id: str = Field(description="ID of the card to update")
    dod: list[str] = Field(description="New definition of done")


class NoopOp(BaseModel):
    model_config = LENIENT
    op: Literal["noop"] = "noop"
    reason: str = Field(default="", description="Why no action was taken this iteration")


EMOp = Annotated[
    Union[CreateTicketOp, DispatchCardOp, KillCardOp, RescopeCardOp, SetACOp, SetDoDOp, NoopOp],
    Field(discriminator="op"),
]


class EMPlanResponse(BaseModel):
    """Structured EM planner output — list of typed ops the harness executes."""
    model_config = LENIENT
    ops: list[EMOp] = Field(default_factory=list, max_length=20)
    reasoning: str = Field(default="", description="EM scratchpad for audit trail")

"""Observe event models: BOS3 envelope specializations for command capture.

Observe events ARE the BOS3 envelope (ADR 0001): same top-level shape as
`voss.harness.bos_events` projections, narrowed to `category="command"` with
an adapter source_ref and a per-event-type payload. `ingest_time` is assigned
by the store at write time, not by the adapter.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from voss.harness.bos_events import BOS_SCHEMA_VERSION

OBSERVE_EVENT_TYPES = (
    "command.started",
    "command.completed",
    "command.failed",
    "test.failed",
)

OBSERVE_ACTORS = ("developer", "voss", "external", "unknown")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_event_id() -> str:
    return uuid.uuid4().hex


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["adapter"] = "adapter"
    ref: str  # adapter_session_id


class CommandStartedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argv: list[str]
    argv_text: str
    cwd: str


class CommandCompletedPayload(CommandStartedPayload):
    exit_code: int
    duration_ms: int = 0
    truncated: bool = False


class CommandFailedPayload(CommandCompletedPayload):
    error_signature: str = ""


class TestFailedPayload(CommandFailedPayload):
    __test__ = False  # not a pytest class

    runner: str
    failed_tests: list[str] = Field(default_factory=list)


class _ObserveBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = BOS_SCHEMA_VERSION
    event_id: str = Field(default_factory=_new_event_id)
    category: Literal["command"] = "command"
    event_time: str = Field(default_factory=_now_iso)
    ingest_time: str | None = None
    trace_id: str | None = None
    parent_event_id: str | None = None
    caused_by: str | None = None
    actor: Literal["developer", "voss", "external", "unknown"] = "unknown"
    source_ref: SourceRef
    external_identity_ref: None = None
    repository_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    worktree_id: str
    adapter_id: str
    command_id: str
    repository_state_id: str
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _default_trace_id(self):
        if self.trace_id is None:
            self.trace_id = self.command_id
        return self


class CommandStartedEvent(_ObserveBase):
    event_type: Literal["command.started"] = "command.started"
    payload: CommandStartedPayload


class CommandCompletedEvent(_ObserveBase):
    event_type: Literal["command.completed"] = "command.completed"
    payload: CommandCompletedPayload


class CommandFailedEvent(_ObserveBase):
    event_type: Literal["command.failed"] = "command.failed"
    payload: CommandFailedPayload


class TestFailedEvent(_ObserveBase):
    __test__ = False  # not a pytest class

    event_type: Literal["test.failed"] = "test.failed"
    payload: TestFailedPayload


ObserveEvent = Annotated[
    Union[
        CommandStartedEvent,
        CommandCompletedEvent,
        CommandFailedEvent,
        TestFailedEvent,
    ],
    Field(discriminator="event_type"),
]

ObserveEventAdapter: TypeAdapter[ObserveEvent] = TypeAdapter(ObserveEvent)


__all__ = [
    "OBSERVE_ACTORS",
    "OBSERVE_EVENT_TYPES",
    "CommandCompletedEvent",
    "CommandCompletedPayload",
    "CommandFailedEvent",
    "CommandFailedPayload",
    "CommandStartedEvent",
    "CommandStartedPayload",
    "ObserveEvent",
    "ObserveEventAdapter",
    "SourceRef",
    "TestFailedEvent",
    "TestFailedPayload",
]

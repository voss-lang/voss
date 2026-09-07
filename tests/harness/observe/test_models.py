from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

import voss.harness.observe
from voss.harness.observe.models import (
    CommandCompletedEvent,
    CommandFailedEvent,
    CommandStartedEvent,
    ObserveEventAdapter,
    TestFailedEvent,
)


def _base(**overrides):
    fields = {
        "command_id": "cmd-1",
        "repository_id": "repo-1",
        "worktree_id": "wt-1",
        "adapter_id": "voss-pty",
        "repository_state_id": "head:abc:def",
        "source_ref": {"source": "adapter", "ref": "pane-1"},
    }
    fields.update(overrides)
    return fields


def _started(**overrides) -> CommandStartedEvent:
    payload = overrides.pop(
        "payload", {"argv": ["pnpm", "test"], "argv_text": "pnpm test", "cwd": "/repo"}
    )
    return CommandStartedEvent(**_base(**overrides), payload=payload)


def _completed(**overrides) -> CommandCompletedEvent:
    payload = overrides.pop(
        "payload",
        {
            "argv": ["pnpm", "test"],
            "argv_text": "pnpm test",
            "cwd": "/repo",
            "exit_code": 1,
            "duration_ms": 1200,
        },
    )
    return CommandCompletedEvent(**_base(**overrides), payload=payload)


def test_envelope_is_bos3_command_specialization() -> None:
    event = _started()
    assert event.schema_version == 1
    assert event.category == "command"
    assert event.event_type == "command.started"
    assert event.source_ref.source == "adapter"
    assert event.source_ref.ref == "pane-1"
    assert event.actor == "unknown"
    assert event.external_identity_ref is None
    assert event.evidence_refs == []
    assert event.ingest_time is None


def test_trace_id_defaults_to_command_id() -> None:
    assert _started().trace_id == "cmd-1"
    assert _started(trace_id="trace-9").trace_id == "trace-9"


def test_event_id_and_event_time_generated() -> None:
    a, b = _started(), _started()
    assert a.event_id and b.event_id and a.event_id != b.event_id
    assert a.event_time


@pytest.mark.parametrize(
    "event",
    [
        _started(),
        _completed(),
        CommandFailedEvent(
            **_base(),
            payload={
                "argv": ["make", "build"],
                "argv_text": "make build",
                "cwd": "/repo",
                "exit_code": 2,
                "error_signature": "sig",
            },
        ),
        TestFailedEvent(
            **_base(),
            caused_by="ev-0",
            payload={
                "argv": ["pytest"],
                "argv_text": "pytest",
                "cwd": "/repo",
                "exit_code": 1,
                "error_signature": "sig",
                "runner": "pytest",
                "failed_tests": ["test_x"],
            },
        ),
    ],
)
def test_union_round_trip_discriminates(event) -> None:
    parsed = ObserveEventAdapter.validate_python(event.model_dump(mode="json"))
    assert type(parsed) is type(event)
    assert parsed == event


def test_unknown_event_type_rejected() -> None:
    data = _started().model_dump(mode="json")
    data["event_type"] = "command.bogus"
    with pytest.raises(ValidationError):
        ObserveEventAdapter.validate_python(data)


def test_actor_vocabulary_enforced() -> None:
    with pytest.raises(ValidationError):
        _started(actor="root")
    for actor in ("developer", "voss", "external", "unknown"):
        assert _started(actor=actor).actor == actor


def test_source_ref_must_be_adapter() -> None:
    with pytest.raises(ValidationError):
        _started(source_ref={"source": "session", "ref": "s-1"})


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        _started(unexpected="nope")


def test_completed_payload_requires_exit_code() -> None:
    with pytest.raises(ValidationError):
        _completed(
            payload={"argv": ["ls"], "argv_text": "ls", "cwd": "/repo"}
        )


def test_schema_generation_deterministic() -> None:
    first = ObserveEventAdapter.json_schema()
    second = ObserveEventAdapter.json_schema()
    assert first == second
    defs = first["$defs"]
    for name in (
        "CommandStartedEvent",
        "CommandCompletedEvent",
        "CommandFailedEvent",
        "TestFailedEvent",
    ):
        assert name in defs


_FORBIDDEN_IMPORT_PARTS = frozenset(
    {
        "providers",
        "agent",
        "model_router",
        "model_catalog",
        "model_prefs",
        "claude_agent_provider",
        "litellm",
        "anthropic",
        "openai",
        "swarm_runtime",
    }
)


def test_observe_package_has_no_model_or_agent_imports() -> None:
    package_dir = Path(voss.harness.observe.__file__).parent
    offenders: list[str] = []
    for path in sorted(package_dir.glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if _FORBIDDEN_IMPORT_PARTS & set(module.split(".")):
                    offenders.append(f"{path.name}: {module}")
    assert offenders == []

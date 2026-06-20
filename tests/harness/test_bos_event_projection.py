"""BOSI1: projection of existing harness records into BOS event records."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import jsonschema
import pytest

from voss.harness.bos_events import (
    project_run_file_events,
    project_run_record,
    project_session_record,
    project_swarm_log_event,
)
from voss.harness.session import RunRecord, SessionRecord
from voss.harness.swarm.events import SwarmEventLog
from voss.harness.swarm_store import SwarmStore

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / ".planning" / "schemas" / "bos-events.schema.json"
INGEST_TIME = "2026-06-20T12:00:00+00:00"


@pytest.fixture(scope="module")
def validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def test_session_record_projects_to_valid_bos_event(
    validator: jsonschema.Draft202012Validator, tmp_path: Path
) -> None:
    session = SessionRecord(
        id="sess-123",
        name="session",
        cwd=str(tmp_path),
        model="stub",
        started_at="2026-06-20T11:00:00+00:00",
        updated_at="2026-06-20T11:05:00+00:00",
        turns=[{"role": "user", "content": "do not project raw transcript"}],
    )

    event = project_session_record(session, ingest_time=INGEST_TIME)

    validator.validate(event)
    assert event["event_type"] == "session.started"
    assert event["trace_id"] == "sess-123"
    assert event["payload"]["turn_count"] == 1
    assert "turns" not in event["payload"]
    assert "raw transcript" not in json.dumps(event)


def test_run_record_projects_task_and_file_events(
    validator: jsonschema.Draft202012Validator,
) -> None:
    run = RunRecord(
        id="run-123",
        started_at="2026-06-20T11:00:00+00:00",
        ended_at="2026-06-20T11:10:00+00:00",
        goal="project a BOS event",
        changed=["src/a.py"],
        inspected=["README.md"],
        avoided=[{"path": "secrets.env", "reason": "out of scope"}],
        diff_summary="1 file changed",
        cost_usd=0.12,
        exit_reason="max-iter",
    )

    task_event = project_run_record(
        run, session_id="sess-123", ingest_time=INGEST_TIME
    )
    file_events = project_run_file_events(
        asdict(run), session_id="sess-123", ingest_time=INGEST_TIME
    )

    validator.validate(task_event)
    assert task_event["payload"]["exit_reason"] == "timeout"
    assert task_event["payload"]["changed"] == ["src/a.py"]

    assert [event["payload"]["operation"] for event in file_events] == [
        "modified",
        "inspected",
        "avoided",
    ]
    for event in file_events:
        validator.validate(event)
        assert event["parent_event_id"] == "run-123"
        assert event["caused_by"] == "run-123"
        assert "reason" not in event["payload"]


def test_swarm_log_events_project_to_valid_bos_events(
    validator: jsonschema.Draft202012Validator, tmp_path: Path
) -> None:
    store = SwarmStore(cwd=tmp_path)
    swarm = store.create(goal="ship BOSI", cwd=str(tmp_path))
    task = store.add_task(swarm.id, goal="wire projection", owned_files=["src/a.py"])
    store.mark_assigned(swarm.id, task.id, session_id="sess-builder")
    store.mark_done(swarm.id, task.id, summary="done")

    source_events = SwarmEventLog(tmp_path).read_events(swarm.id)
    projected = [
        project_swarm_log_event(event, ingest_time=INGEST_TIME)
        for event in source_events
    ]

    assert [event["event_type"] for event in projected] == [
        "swarm.create",
        "task.created",
        "swarm.assign",
        "task.completed",
    ]
    assert [event["category"] for event in projected] == [
        "swarm",
        "task",
        "swarm",
        "task",
    ]
    for event in projected:
        validator.validate(event)
        assert event["trace_id"] == swarm.id
        assert event["source_ref"]["source"] == "swarm_log"

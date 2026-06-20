"""BOS3: local append-only BOS event ledger."""
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
from voss.harness.bos_ledger import BosEventLedger, append_event, read_events
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


def _projected_session_events(tmp_path: Path) -> list[dict]:
    session = SessionRecord(
        id="sess-ledger",
        name="ledger session",
        cwd=str(tmp_path),
        model="stub",
        started_at="2026-06-20T11:00:00+00:00",
        updated_at="2026-06-20T11:03:00+00:00",
    )
    run = RunRecord(
        id="run-ledger",
        started_at="2026-06-20T11:01:00+00:00",
        ended_at="2026-06-20T11:02:00+00:00",
        goal="append projected events",
        changed=["src/a.py"],
        inspected=["README.md"],
        cost_usd=0.04,
        exit_reason="done",
    )
    return [
        project_session_record(session, ingest_time=INGEST_TIME),
        project_run_record(run, session_id=session.id, ingest_time=INGEST_TIME),
        *project_run_file_events(
            asdict(run), session_id=session.id, ingest_time=INGEST_TIME
        ),
    ]


def test_projected_events_append_and_replay_with_filters(
    validator: jsonschema.Draft202012Validator,
    tmp_path: Path,
) -> None:
    ledger = BosEventLedger(tmp_path)
    events = _projected_session_events(tmp_path)

    assert ledger.append_many(events) == len(events)

    assert ledger.path == tmp_path / ".voss" / "bos" / "events.jsonl"
    replayed = ledger.read_events()
    assert [event["event_id"] for event in replayed] == [
        event["event_id"] for event in events
    ]
    for event in replayed:
        validator.validate(event)

    assert [event["event_id"] for event in ledger.read_events(trace_id="sess-ledger")] == [
        "sess-ledger",
        "run-ledger",
        "run-ledger:file:modified:0",
        "run-ledger:file:inspected:1",
    ]
    assert [event["event_id"] for event in ledger.read_events(event_type="task.completed")] == [
        "run-ledger"
    ]
    assert [event["event_id"] for event in ledger.read_events(category="file")] == [
        "run-ledger:file:modified:0",
        "run-ledger:file:inspected:1",
    ]


def test_duplicate_event_id_is_noop_and_preserves_file_bytes(tmp_path: Path) -> None:
    event = _projected_session_events(tmp_path)[0]

    assert append_event(tmp_path, event) is True
    before = (tmp_path / ".voss" / "bos" / "events.jsonl").read_bytes()

    assert append_event(tmp_path, dict(event)) is False
    after = (tmp_path / ".voss" / "bos" / "events.jsonl").read_bytes()

    assert after == before


def test_read_events_tolerates_torn_trailing_line(tmp_path: Path) -> None:
    event = _projected_session_events(tmp_path)[0]
    ledger_path = tmp_path / ".voss" / "bos" / "events.jsonl"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n{\"event_id\":")

    assert read_events(tmp_path) == [event]


def test_swarm_projection_append_does_not_modify_source_log(
    validator: jsonschema.Draft202012Validator,
    tmp_path: Path,
) -> None:
    store = SwarmStore(cwd=tmp_path)
    swarm = store.create(goal="record BOS events", cwd=str(tmp_path))
    task = store.add_task(swarm.id, goal="wire ledger", owned_files=["src/a.py"])
    store.mark_assigned(swarm.id, task.id, session_id="sess-builder")
    store.mark_done(swarm.id, task.id, summary="done")

    source_path = tmp_path / ".voss" / "swarm" / swarm.id / "events" / "events.jsonl"
    before = source_path.read_bytes()
    source_events = SwarmEventLog(tmp_path).read_events(swarm.id)
    projected = [
        project_swarm_log_event(event, ingest_time=INGEST_TIME)
        for event in source_events
    ]

    ledger = BosEventLedger(tmp_path)
    assert ledger.append_many(projected) == len(projected)

    assert source_path.read_bytes() == before
    assert [event["event_type"] for event in ledger.read_events(trace_id=swarm.id)] == [
        "swarm.create",
        "task.created",
        "swarm.assign",
        "task.completed",
    ]
    for event in ledger.read_events():
        validator.validate(event)

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from voss.harness.observe.models import CommandStartedEvent
from voss.harness.observe.store import MIGRATIONS, ObserveStore, db_path


def _event(event_id: str = "ev-1", **overrides) -> CommandStartedEvent:
    fields = {
        "event_id": event_id,
        "command_id": "cmd-1",
        "repository_id": "repo-1",
        "worktree_id": "wt-1",
        "adapter_id": "voss-pty",
        "repository_state_id": "head:abc:def",
        "source_ref": {"source": "adapter", "ref": "pane-1"},
        "payload": {"argv": ["ls"], "argv_text": "ls", "cwd": "/repo"},
    }
    fields.update(overrides)
    return CommandStartedEvent(**fields)


@pytest.fixture
def store(tmp_path: Path):
    store = ObserveStore("repo-1", state_dir=tmp_path)
    yield store
    store.close()


def test_db_path_under_app_state(tmp_path: Path) -> None:
    assert db_path("repo-1", state_dir=tmp_path) == tmp_path / "observe" / "repo-1.sqlite"


def test_default_state_dir_uses_xdg_state_home() -> None:
    expected = (
        Path(os.environ["XDG_STATE_HOME"]) / "voss" / "observe" / "repo-1.sqlite"
    )
    assert db_path("repo-1") == expected


def test_migrations_applied_and_idempotent(tmp_path: Path) -> None:
    with ObserveStore("repo-1", state_dir=tmp_path) as store:
        version = store._conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == len(MIGRATIONS)
        tables = {
            row[0]
            for row in store._conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"events", "evidence", "admissions", "investigations", "findings"} <= tables
    with ObserveStore("repo-1", state_dir=tmp_path) as reopened:
        version = reopened._conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == len(MIGRATIONS)


def test_insert_event_dedupes_on_event_id(store: ObserveStore) -> None:
    assert store.insert_event(_event()) is True
    assert store.insert_event(_event()) is False
    assert store.has_event("ev-1")
    assert not store.has_event("ev-2")


def test_insert_event_assigns_ingest_time(store: ObserveStore) -> None:
    store.insert_event(_event())
    row = store.get_event("ev-1")
    assert row is not None
    assert row["event"]["ingest_time"]
    assert row["event"]["event_id"] == "ev-1"


def test_list_events_cursor_pagination(store: ObserveStore) -> None:
    for i in range(5):
        store.insert_event(_event(event_id=f"ev-{i}"))
    first_page = store.list_events(after_seq=0, limit=2)
    assert [row["event"]["event_id"] for row in first_page] == ["ev-0", "ev-1"]
    rest = store.list_events(after_seq=first_page[-1]["seq"], limit=10)
    assert [row["event"]["event_id"] for row in rest] == ["ev-2", "ev-3", "ev-4"]


def test_evidence_round_trip(store: ObserveStore) -> None:
    store.insert_event(_event())
    content = b"command output bytes"
    digest = store.put_evidence("evd-1", "ev-1", "command_output", content, truncated=True)
    assert digest == hashlib.sha256(content).hexdigest()
    row = store.get_evidence("evd-1")
    assert row is not None
    assert row["content"] == content
    assert row["truncated"] is True
    assert row["kind"] == "command_output"
    assert store.get_evidence("missing") is None


def test_admissions_recorded_and_latest(store: ObserveStore) -> None:
    store.record_admission(
        event_id="ev-1",
        fingerprint="fp",
        decision="queue",
        reason="queued",
        policy_version="observe-admission-v1",
        decided_at=100.0,
    )
    store.record_admission(
        event_id="ev-2",
        fingerprint="fp",
        decision="suppress",
        reason="cooldown",
        policy_version="observe-admission-v1",
        decided_at=130.0,
    )
    latest = store.latest_admission("fp")
    assert latest is not None
    assert latest["decision"] == "suppress"
    latest_queued = store.latest_admission("fp", decisions=("queue",))
    assert latest_queued is not None
    assert latest_queued["event_id"] == "ev-1"
    assert store.latest_admission("other") is None
    assert [a["event_id"] for a in store.admissions(event_id="ev-1")] == ["ev-1"]
    assert len(store.admissions()) == 2


def test_investigation_queue_per_worktree(store: ObserveStore) -> None:
    store.enqueue_investigation(
        investigation_id="inv-1",
        worktree_id="wt-1",
        trigger_event_id="ev-1",
        fingerprint="fp-1",
    )
    store.enqueue_investigation(
        investigation_id="inv-2",
        worktree_id="wt-1",
        trigger_event_id="ev-2",
        fingerprint="fp-2",
    )
    store.enqueue_investigation(
        investigation_id="inv-3",
        worktree_id="wt-2",
        trigger_event_id="ev-3",
        fingerprint="fp-1",
    )
    assert store.count_pending("wt-1") == 2
    assert store.count_pending("wt-2") == 1
    pending = store.pending_by_fingerprint("wt-1", "fp-1")
    assert pending is not None
    assert pending["investigation_id"] == "inv-1"
    assert store.pending_by_fingerprint("wt-1", "fp-3") is None
    assert [row["investigation_id"] for row in store.pending_investigations("wt-1")] == [
        "inv-1",
        "inv-2",
    ]


def test_finding_upsert_and_get(store: ObserveStore) -> None:
    store.upsert_finding(
        finding_id="f-1",
        worktree_id="wt-1",
        title="missing import",
        status="new",
        body={"confidence": {"label": "high"}},
        investigation_id="inv-1",
    )
    found = store.get_finding("f-1")
    assert found is not None
    assert found["title"] == "missing import"
    assert found["body"] == {"confidence": {"label": "high"}}
    assert found["repository_id"] == "repo-1"

    store.upsert_finding(
        finding_id="f-1",
        worktree_id="wt-1",
        title="missing import",
        status="dismissed",
        body={"confidence": {"label": "high"}},
    )
    updated = store.get_finding("f-1")
    assert updated is not None
    assert updated["status"] == "dismissed"
    assert store.get_finding("missing") is None


def test_event_id_unique_constraint(store: ObserveStore) -> None:
    store.insert_event(_event())
    with pytest.raises(sqlite3.IntegrityError):
        with store._conn:
            store._conn.execute(
                "INSERT INTO events (event_id, event_type, repository_id, worktree_id,"
                " event_time, ingest_time, body) VALUES ('ev-1', 'command.started',"
                " 'repo-1', 'wt-1', 't', 't', '{}')"
            )

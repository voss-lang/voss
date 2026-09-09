from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from voss.harness.bos_events import emit_live
from voss.harness.bos_ledger import BosEventLedger
from voss.harness.observe.bos_drain import (
    drain_outbox,
    outbox_backlog,
    reconcile,
    recover_outbox,
)
from voss.harness.observe.models import CommandStartedEvent
from voss.harness.observe.store import ObserveStore


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
    store = ObserveStore("repo-1", state_dir=tmp_path / "state")
    yield store
    store.close()


@pytest.fixture
def ledger(tmp_path: Path) -> BosEventLedger:
    return BosEventLedger(tmp_path / "proj")


def _ledger_bytes(ledger: BosEventLedger) -> bytes:
    return ledger.path.read_bytes() if ledger.path.exists() else b""


def test_emit_live_assigns_ingest_time_at_write(tmp_path: Path) -> None:
    event = {"event_id": "ev-1", "event_type": "command.completed"}
    assert emit_live(tmp_path, event) is True
    (stored,) = BosEventLedger(tmp_path).read_events()
    assert stored["ingest_time"]
    assert stored["event_id"] == "ev-1"
    assert "ingest_time" not in event


def test_emit_live_idempotent_on_event_id(tmp_path: Path) -> None:
    event = {"event_id": "ev-1", "event_type": "command.completed"}
    assert emit_live(tmp_path, event) is True
    before = _ledger_bytes(BosEventLedger(tmp_path))
    assert emit_live(tmp_path, event) is False
    assert _ledger_bytes(BosEventLedger(tmp_path)) == before
    assert len(BosEventLedger(tmp_path).read_events()) == 1


def test_insert_event_writes_outbox_row_atomically(store: ObserveStore) -> None:
    assert store.insert_event(_event()) is True
    (row,) = store.outbox_rows()
    assert row["event_id"] == "ev-1"
    assert row["attempts"] == 0
    assert row["last_error"] is None
    assert row["delivered_at"] is None


def test_outbox_write_failure_rolls_back_event(store: ObserveStore) -> None:
    store._conn.execute("DROP TABLE bos_outbox")
    with pytest.raises(sqlite3.OperationalError):
        store.insert_event(_event())
    assert not store.has_event("ev-1")


def test_duplicate_event_does_not_add_outbox_row(store: ObserveStore) -> None:
    assert store.insert_event(_event()) is True
    assert store.insert_event(_event()) is False
    assert len(store.outbox_rows()) == 1


def test_drain_delivers_in_event_id_order_and_marks(
    store: ObserveStore, ledger: BosEventLedger
) -> None:
    for event_id in ("ev-c", "ev-a", "ev-b"):
        store.insert_event(_event(event_id=event_id))
    result = drain_outbox(store, ledger, sleep=lambda _: None)
    assert result == {"delivered": 3, "failed": 0, "remaining": 0}
    assert [e["event_id"] for e in ledger.read_events()] == ["ev-a", "ev-b", "ev-c"]
    assert all(row["delivered_at"] for row in store.outbox_rows())
    assert outbox_backlog(store)["pending"] == 0


def test_drain_preserves_store_ingest_time(
    store: ObserveStore, ledger: BosEventLedger
) -> None:
    store.insert_event(_event())
    stored = store.get_event("ev-1")
    assert stored is not None
    drain_outbox(store, ledger, sleep=lambda _: None)
    (event,) = ledger.read_events()
    assert event["ingest_time"] == stored["event"]["ingest_time"]


class _AppendThenCrashLedger(BosEventLedger):
    def __init__(self, cwd: Path) -> None:
        super().__init__(cwd)
        self.crashed = False

    def append_event(self, event: dict) -> bool:
        appended = super().append_event(event)
        if not self.crashed:
            self.crashed = True
            raise RuntimeError("crash after append")
        return appended


def test_crash_between_append_and_mark_yields_no_duplicate_row(
    store: ObserveStore, tmp_path: Path
) -> None:
    ledger = _AppendThenCrashLedger(tmp_path / "proj")
    store.insert_event(_event())
    first = drain_outbox(store, ledger, max_attempts=1, sleep=lambda _: None)
    assert first["failed"] == 1
    assert store.outbox_rows()[0]["delivered_at"] is None
    second = drain_outbox(store, ledger, max_attempts=1, sleep=lambda _: None)
    assert second["delivered"] == 1
    assert [e["event_id"] for e in ledger.read_events()] == ["ev-1"]
    assert store.outbox_rows()[0]["delivered_at"] is not None


class _FailingLedger(BosEventLedger):
    def append_event(self, event: dict) -> bool:
        raise RuntimeError("ledger unavailable")


def test_drain_bounded_retries_with_backoff(store: ObserveStore, tmp_path: Path) -> None:
    ledger = _FailingLedger(tmp_path / "proj")
    store.insert_event(_event())
    delays: list[float] = []
    result = drain_outbox(
        store, ledger, max_attempts=3, base_delay_s=0.25, sleep=delays.append
    )
    assert result == {"delivered": 0, "failed": 1, "remaining": 1}
    assert delays == [0.25, 0.5]
    row = store.outbox_rows()[0]
    assert row["attempts"] == 3
    assert row["last_error"] == "ledger unavailable"
    assert row["delivered_at"] is None
    assert ledger.read_events() == []


def test_outbox_backlog_reporting(store: ObserveStore, ledger: BosEventLedger) -> None:
    assert outbox_backlog(store) == {
        "pending": 0,
        "delivered": 0,
        "oldest_pending": None,
        "last_error": None,
    }
    store.insert_event(_event(event_id="ev-a"))
    store.insert_event(_event(event_id="ev-b"))
    store.record_outbox_failure("ev-b", "boom")
    backlog = outbox_backlog(store)
    assert backlog["pending"] == 2
    assert backlog["delivered"] == 0
    assert backlog["oldest_pending"] == "ev-a"
    assert backlog["last_error"] == "boom"
    drain_outbox(store, ledger, sleep=lambda _: None)
    backlog = outbox_backlog(store)
    assert backlog["pending"] == 0
    assert backlog["delivered"] == 2


def test_recover_outbox_drains_backlog_left_by_failed_delivery(
    store: ObserveStore, tmp_path: Path
) -> None:
    failing = _FailingLedger(tmp_path / "proj")
    store.insert_event(_event())
    assert drain_outbox(store, failing, sleep=lambda _: None)["failed"] == 1
    result = recover_outbox(store, BosEventLedger(tmp_path / "proj"))
    assert result == {"delivered": 1, "failed": 0, "remaining": 0}
    assert [e["event_id"] for e in BosEventLedger(tmp_path / "proj").read_events()] == [
        "ev-1"
    ]


def test_reconcile_replays_undelivered_and_is_repeat_safe(
    store: ObserveStore, ledger: BosEventLedger
) -> None:
    store.insert_event(_event(event_id="ev-a"))
    store.insert_event(_event(event_id="ev-b"))
    first = reconcile(store, ledger)
    assert first == {"replayed": 2, "pending": 0, "delivered": 2}
    before = _ledger_bytes(ledger)
    second = reconcile(store, ledger)
    assert second["replayed"] == 0
    assert _ledger_bytes(ledger) == before


def test_reconcile_marks_row_already_in_ledger(
    store: ObserveStore, ledger: BosEventLedger
) -> None:
    store.insert_event(_event())
    record = store.get_event("ev-1")
    assert record is not None
    ledger.append_event(record["event"])
    result = reconcile(store, ledger)
    assert result["replayed"] == 0
    assert store.outbox_rows()[0]["delivered_at"] is not None
    assert len(ledger.read_events()) == 1


def test_reconcile_reappends_delivered_row_missing_from_ledger(
    store: ObserveStore, ledger: BosEventLedger
) -> None:
    store.insert_event(_event())
    store.mark_outbox_delivered("ev-1")
    assert ledger.read_events() == []
    result = reconcile(store, ledger)
    assert result["replayed"] == 1
    assert [e["event_id"] for e in ledger.read_events()] == ["ev-1"]

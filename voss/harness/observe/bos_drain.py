"""Drain the Observe bos_outbox into the append-only BOS ledger.

ADR 0001 handoff contract: the Observe store commits the event row and the
outbox row in one transaction; this module delivers undelivered rows to the
ledger in `event_id` order with bounded retries and exponential backoff, and
marks `delivered_at`. Ledger appends are idempotent on `event_id`, so a crash
between append and mark yields a duplicate attempt, not a duplicate row.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from voss.harness.bos_ledger import BosEventLedger
from voss.harness.observe.store import ObserveStore


def outbox_backlog(store: ObserveStore) -> dict[str, Any]:
    """Backlog summary for `voss observe status`."""

    rows = store.outbox_rows()
    pending = [row for row in rows if row["delivered_at"] is None]
    last_error = next(
        (row["last_error"] for row in reversed(pending) if row["last_error"]),
        None,
    )
    return {
        "pending": len(pending),
        "delivered": len(rows) - len(pending),
        "oldest_pending": pending[0]["event_id"] if pending else None,
        "last_error": last_error,
    }


def drain_outbox(
    store: ObserveStore,
    ledger: BosEventLedger,
    *,
    max_attempts: int = 3,
    base_delay_s: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, int]:
    """Deliver undelivered outbox rows to the ledger in `event_id` order."""

    delivered = 0
    failed = 0
    for row in store.outbox_rows(undelivered_only=True):
        if _deliver(
            store,
            ledger,
            row["event_id"],
            max_attempts=max_attempts,
            base_delay_s=base_delay_s,
            sleep=sleep,
        ):
            delivered += 1
        else:
            failed += 1
    return {
        "delivered": delivered,
        "failed": failed,
        "remaining": len(store.outbox_rows(undelivered_only=True)),
    }


def recover_outbox(store: ObserveStore, ledger: BosEventLedger) -> dict[str, int]:
    """Sidecar-start recovery: drain the outbox before new events are admitted."""

    return drain_outbox(store, ledger)


def reconcile(store: ObserveStore, ledger: BosEventLedger) -> dict[str, int]:
    """Replay outbox rows missing from the ledger; safe to run repeatedly."""

    ledger_ids = {
        str(event.get("event_id")) for event in ledger.read_events()
    }
    replayed = 0
    for row in store.outbox_rows():
        event_id = row["event_id"]
        if event_id in ledger_ids:
            if row["delivered_at"] is None:
                store.mark_outbox_delivered(event_id)
            continue
        record = store.get_event(event_id)
        if record is None:
            continue
        ledger.append_event(record["event"])
        ledger_ids.add(event_id)
        store.mark_outbox_delivered(event_id)
        replayed += 1
    backlog = outbox_backlog(store)
    return {
        "replayed": replayed,
        "pending": backlog["pending"],
        "delivered": backlog["delivered"],
    }


def _deliver(
    store: ObserveStore,
    ledger: BosEventLedger,
    event_id: str,
    *,
    max_attempts: int,
    base_delay_s: float,
    sleep: Callable[[float], None],
) -> bool:
    record = store.get_event(event_id)
    if record is None:
        store.record_outbox_failure(event_id, "event row missing")
        return False
    event = record["event"]
    for attempt in range(max_attempts):
        try:
            ledger.append_event(event)
        except Exception as exc:
            store.record_outbox_failure(event_id, str(exc))
            if attempt + 1 < max_attempts:
                sleep(base_delay_s * (2**attempt))
            continue
        store.mark_outbox_delivered(event_id)
        return True
    return False


__all__ = ["drain_outbox", "outbox_backlog", "reconcile", "recover_outbox"]

"""Local append-only BOS event ledger.

The ledger stores projected Behavioral OS events at `.voss/bos/events.jsonl`.
It is intentionally local-only: projection remains pure, and source session or
swarm logs are not modified when BOS events are appended here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import portalocker

_LOCK_TIMEOUT_S = 10.0


def ledger_path(cwd: Path) -> Path:
    """Return the canonical local BOS event ledger path for a project cwd."""

    return Path(cwd).resolve() / ".voss" / "bos" / "events.jsonl"


class BosEventLedger:
    """Append-only JSONL writer and replay reader for BOS events."""

    def __init__(self, cwd: Path) -> None:
        self.path = ledger_path(cwd)

    def append_event(self, event: dict[str, Any]) -> bool:
        """Append one event unless its `event_id` is already present.

        Returns True when a new line was written and False when the event was a
        duplicate. Duplicate detection is performed under the same file lock as
        the append so a re-append does not change file bytes.
        """

        return self.append_many([event]) == 1

    def append_many(self, events: list[dict[str, Any]]) -> int:
        """Append events in order, skipping already-seen `event_id` values."""

        if not events:
            return 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with portalocker.Lock(
            str(self.path),
            mode="a+",
            flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
            timeout=_LOCK_TIMEOUT_S,
        ) as f:
            f.seek(0)
            seen = _read_event_ids(f)
            appended = 0
            for event in events:
                event_id = _event_id(event)
                if event_id in seen:
                    continue
                f.write(json.dumps(event, sort_keys=True) + "\n")
                seen.add(event_id)
                appended += 1
        self.path.chmod(0o600)
        return appended

    def read_events(
        self,
        *,
        trace_id: str | None = None,
        event_type: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Replay events in append order, optionally filtering by top-level fields.

        A torn trailing line is ignored so an interrupted writer does not make
        the whole ledger unreadable.
        """

        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        with self.path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    break
                if _matches(
                    event,
                    trace_id=trace_id,
                    event_type=event_type,
                    category=category,
                ):
                    out.append(event)
        return out


def append_event(cwd: Path, event: dict[str, Any]) -> bool:
    return BosEventLedger(cwd).append_event(event)


def append_many(cwd: Path, events: list[dict[str, Any]]) -> int:
    return BosEventLedger(cwd).append_many(events)


def read_events(
    cwd: Path,
    *,
    trace_id: str | None = None,
    event_type: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    return BosEventLedger(cwd).read_events(
        trace_id=trace_id,
        event_type=event_type,
        category=category,
    )


def _event_id(event: dict[str, Any]) -> str:
    event_id = event.get("event_id")
    if not event_id:
        raise ValueError("BOS ledger event missing event_id")
    return str(event_id)


def _read_event_ids(f: Any) -> set[str]:
    seen: set[str] = set()
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            break
        event_id = event.get("event_id")
        if event_id:
            seen.add(str(event_id))
    return seen


def _matches(
    event: dict[str, Any],
    *,
    trace_id: str | None,
    event_type: str | None,
    category: str | None,
) -> bool:
    if trace_id is not None and event.get("trace_id") != trace_id:
        return False
    if event_type is not None and event.get("event_type") != event_type:
        return False
    if category is not None and event.get("category") != category:
        return False
    return True


__all__ = [
    "BosEventLedger",
    "append_event",
    "append_many",
    "ledger_path",
    "read_events",
]

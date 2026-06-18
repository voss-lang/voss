"""Append-only JSONL event log for swarm runtime state (VSWARM-01 / VSWARM-11).

The event log under `.voss/swarm/<id>/events/events.jsonl` is the *source of
truth*: SwarmStore state is rebuildable purely by replaying it (D-04). Writes
mirror `memory_store.py:write_turn` discipline — portalocker advisory lock +
`open("a")` + `json.dumps(evt) + "\n"`. The file is NEVER rewritten in place
(no `path.write_text` on an events file — research Anti-Patterns).

Swarm coordination events must not be silently dropped, so this writer takes a
*blocking* exclusive lock (with a bounded timeout) rather than the
skip-on-contention pattern memory_store uses for lossy turn logs.
"""
from __future__ import annotations

import json
from pathlib import Path

import portalocker

# Bounded wait so a stuck writer surfaces instead of hanging the loop forever.
_LOCK_TIMEOUT_S = 10.0


class SwarmEventLog:
    """Append-only JSONL writer + replay reader, scoped to a project cwd."""

    def __init__(self, cwd: Path) -> None:
        self.root = Path(cwd).resolve() / ".voss" / "swarm"

    def _events_path(self, swarm_id: str) -> Path:
        return self.root / swarm_id / "events" / "events.jsonl"

    def append(self, swarm_id: str, event: dict) -> None:
        """Atomically append one event envelope as a single JSONL line.

        Serialization is `json.dumps` only — no string formatting — so crafted
        goal/task text cannot inject a forged line (T-V25-01-02).
        """
        path = self._events_path(swarm_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event) + "\n"
        # LOCK_NB + timeout → portalocker polls up to the timeout (a bounded
        # wait). Plain LOCK_EX blocks forever and ignores timeout.
        with portalocker.Lock(
            str(path),
            mode="a",
            flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
            timeout=_LOCK_TIMEOUT_S,
        ) as f:
            f.write(line)
        path.chmod(0o600)

    def read_events(self, swarm_id: str) -> list[dict]:
        """Read all events in append order. Tolerates a trailing partial line.

        A torn final write (process killed mid-append) leaves an unparseable
        last line; replay must survive it rather than crash (T-V25-01-01).
        """
        path = self._events_path(swarm_id)
        if not path.exists():
            return []
        out: list[dict] = []
        with path.open("r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # Trailing partial line from an interrupted append — stop.
                    break
        return out

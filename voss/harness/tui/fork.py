"""Pure session-fork primitive."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from voss_runtime import EpisodicMemory

from voss.harness.session import SessionRecord, save


def fork_session(
    record: SessionRecord, turn_index: int, cwd: Path
) -> SessionRecord:
    """Create + persist a new SessionRecord forked at `turn_index`.

    Raises ValueError if turn_index is outside [0, len(record.turns)).
    """
    if turn_index < 0 or turn_index >= len(record.turns):
        raise ValueError(
            f"turn_index {turn_index} out of range for "
            f"{len(record.turns)} turns"
        )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new = SessionRecord(
        id=uuid.uuid4().hex[:12],
        name=f"fork-of-{record.id[:8]}-t{turn_index}",
        cwd=record.cwd,
        model=record.model,
        started_at=now,
        updated_at=now,
        total_cost_usd=0.0,
        turns=list(record.turns[: turn_index + 1]),
        runs=[],
        parent_id=record.id,
        parent_turn_index=turn_index,
    )
    history = EpisodicMemory(capacity=40)
    for t in new.turns:
        history.add(t.get("content", ""), role=t.get("role", "user"))
    save(new, history)
    return new

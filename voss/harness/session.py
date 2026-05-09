"""Persisted session snapshots.

Sessions live at $XDG_STATE_HOME/voss/sessions/<id>.json (default
~/.local/state/voss/sessions). Each snapshot stores the episodic transcript,
cwd, model, and total cost. Provider keys are never serialized.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from voss_runtime import EpisodicMemory


def _state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "voss" / "sessions"


@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)

    @classmethod
    def new(cls, *, cwd: Path, model: str, name: str = "") -> "SessionRecord":
        sid = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(
            id=sid,
            name=name or f"session-{sid[:8]}",
            cwd=str(cwd.resolve()),
            model=model,
            started_at=now,
            updated_at=now,
        )

    def first_task(self) -> str:
        for t in self.turns:
            if t.get("role") == "user":
                return t.get("content", "")[:60]
        return "(empty)"


def session_path(session_id: str) -> Path:
    return _state_dir() / f"{session_id}.json"


def save(record: SessionRecord, history: EpisodicMemory) -> Path:
    record.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record.turns = history.last(10_000)  # full transcript
    path = session_path(record.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2))
    return path


def load(session_id_or_name: str) -> tuple[SessionRecord, EpisodicMemory]:
    """Resolve by id prefix or name, return record + rehydrated memory."""
    matches = []
    for p in _state_dir().glob("*.json"):
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if data["id"].startswith(session_id_or_name) or data.get("name") == session_id_or_name:
            matches.append(data)
    if not matches:
        raise FileNotFoundError(f"no session: {session_id_or_name}")
    if len(matches) > 1:
        names = ", ".join(m["id"][:8] for m in matches)
        raise ValueError(f"ambiguous session id; candidates: {names}")
    data = matches[0]
    record = SessionRecord(**{k: v for k, v in data.items() if k != "turns"}, turns=data.get("turns", []))
    history = EpisodicMemory(capacity=40)
    for t in record.turns:
        history.add(t.get("content", ""), role=t.get("role", "user"))
    return record, history


def list_sessions() -> list[SessionRecord]:
    out: list[SessionRecord] = []
    if not _state_dir().exists():
        return out
    for p in sorted(_state_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        out.append(
            SessionRecord(**{k: v for k, v in data.items() if k != "turns"}, turns=data.get("turns", []))
        )
    return out


def delete(session_id: str) -> bool:
    path = session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False

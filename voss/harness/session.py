"""Persisted session snapshots.

Sessions live at <cwd>/.voss/sessions/<id>.json. Legacy pre-M2 sessions remain
readable in place at $XDG_STATE_HOME/voss/sessions/ but are never written to.
Each snapshot stores the episodic transcript, cwd, model, total cost, and a
per-turn list of RunRecords.

Storage location
----------------
Sessions live at <cwd>/.voss/sessions/<id>.json. Legacy pre-M2 sessions remain
readable in place at $XDG_STATE_HOME/voss/sessions/ but are never written to.

Redaction guarantee
-------------------
SessionRecord is a fixed-field dataclass. Save serializes via dataclasses.asdict,
which means nothing outside the schema gets written. Provider credentials
(API keys, OAuth access/refresh tokens, Bearer headers, anthropic-beta marker)
are NEVER fields on this record and therefore cannot be saved.

User-provided prompt text is allowed to contain anything — including strings
that look like secrets — because EpisodicMemory.content is part of the
allowlist by design (the user typed it). The guarantee is specifically about
what the harness itself attaches to the record (it attaches nothing
secret-shaped).

This invariant is enforced at build time by tests/harness/test_session_redaction.py.
Adding a new SessionRecord field that could carry creds is a breaking change
and must be paired with an explicit redaction step.

RunRecord follows the same fixed-field allowlist. Adding a RunRecord field
that could carry creds is a breaking change and must be paired with an
explicit redaction step. The invariant is enforced by
tests/harness/test_session_redaction.py over both SessionRecord and RunRecord
field values.
"""
from __future__ import annotations

import dataclasses
import json
import os
import uuid
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from voss_runtime import EpisodicMemory


def _sessions_dir(cwd: Path) -> Path:
    return (cwd / ".voss" / "sessions").resolve()


def _legacy_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "voss" / "sessions"


@dataclass
class RunRecord:
    id: str
    started_at: str
    ended_at: str
    goal: str = ""
    plan: Optional[dict] = None
    inspected: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    avoided: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    validation: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    diff_summary: str = ""
    follow_ups: list[str] = field(default_factory=list)
    cost_usd: float = 0.0


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
    runs: list[dict] = field(default_factory=list)

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


_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}


def _hydrate(data: dict) -> SessionRecord:
    kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
    kept.setdefault("turns", [])
    kept.setdefault("runs", [])
    return SessionRecord(**kept)


def session_path(session_id: str, cwd: Optional[Path] = None) -> Path:
    if cwd is None:
        warnings.warn(
            "session_path() without cwd is deprecated; pass cwd explicitly",
            DeprecationWarning,
            stacklevel=2,
        )
        cwd = Path.cwd()
    return _sessions_dir(cwd) / f"{session_id}.json"


def save(record: SessionRecord, history: EpisodicMemory) -> Path:
    record.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record.turns = history.last(10_000)  # full transcript
    cwd = Path(record.cwd)
    path = _sessions_dir(cwd) / f"{record.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2))
    path.chmod(0o600)
    return path


def _scan_dir(dir_path: Path, session_id_or_name: str) -> list[tuple[dict, Path]]:
    out: list[tuple[dict, Path]] = []
    if not dir_path.exists():
        return out
    for p in dir_path.glob("*.json"):
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("id", "").startswith(session_id_or_name) or data.get("name") == session_id_or_name:
            out.append((data, p))
    return out


def load(
    session_id_or_name: str,
    cwd: Optional[Path] = None,
) -> tuple[SessionRecord, EpisodicMemory]:
    """Resolve by id prefix or name, return record + rehydrated memory.

    Scans <cwd>/.voss/sessions first, then falls back to the legacy XDG dir.
    Legacy hits are tagged via `_legacy = True`.
    """
    primary: list[tuple[dict, Path]] = []
    if cwd is not None:
        primary = _scan_dir(_sessions_dir(cwd), session_id_or_name)
    legacy = _scan_dir(_legacy_state_dir(), session_id_or_name)

    if primary:
        matches = primary
        is_legacy = False
    elif legacy:
        matches = legacy
        is_legacy = True
    else:
        raise FileNotFoundError(f"no session: {session_id_or_name}")

    if len(matches) > 1:
        names = ", ".join(m[0]["id"][:8] for m in matches)
        raise ValueError(f"ambiguous session id; candidates: {names}")

    data = matches[0][0]
    record = _hydrate(data)
    if is_legacy:
        record._legacy = True  # type: ignore[attr-defined]
    history = EpisodicMemory(capacity=40)
    for t in record.turns:
        history.add(t.get("content", ""), role=t.get("role", "user"))
    return record, history


def list_sessions(
    cwd: Path,
    *,
    include_legacy: bool = False,
) -> list[SessionRecord]:
    out: list[SessionRecord] = []
    primary_dir = _sessions_dir(cwd)
    if primary_dir.exists():
        for p in primary_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            out.append(_hydrate(data))

    if include_legacy:
        legacy_dir = _legacy_state_dir()
        if legacy_dir.exists():
            for p in legacy_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                rec = _hydrate(data)
                rec._legacy = True  # type: ignore[attr-defined]
                out.append(rec)

    out.sort(key=lambda r: r.updated_at, reverse=True)
    return out


def delete(session_id: str, cwd: Optional[Path] = None) -> bool:
    if cwd is None:
        cwd = Path.cwd()
    primary_dir = _sessions_dir(cwd)
    if primary_dir.exists():
        for p in primary_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("id", "").startswith(session_id) or data.get("name") == session_id:
                p.unlink()
                return True
    # Refuse to delete legacy files.
    legacy_dir = _legacy_state_dir()
    if legacy_dir.exists():
        for p in legacy_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("id", "").startswith(session_id) or data.get("name") == session_id:
                warnings.warn(
                    f"refusing to delete legacy session at {p}; legacy dir is read-only",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return False
    return False

"""Durable, single-server task snapshots and ordered event replay."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Literal

import portalocker
from pydantic import BaseModel, Field

Phase = Literal["idle", "active", "waiting", "candidate_ready", "completed", "failed", "cancelled", "interrupted"]
TERMINAL = {"idle", "candidate_ready", "completed", "failed", "cancelled", "interrupted"}


class TaskSnapshot(BaseModel):
    v: Literal[1] = 1
    task_id: str
    session_id: str
    swarm_id: str | None = None
    swarm_task_id: str | None = None
    run_id: str | None = None
    attempt_id: str | None = None
    phase: Phase = "idle"
    outcome: str | None = None
    pending_actions: list[dict] = Field(default_factory=list)
    watermark: int = 0


class TaskEvent(BaseModel):
    v: Literal[1] = 1
    cursor: int
    snapshot: TaskSnapshot
    event: dict


class CommandAck(BaseModel):
    v: Literal[1] = 1
    status: str
    run_id: str | None = None
    attempt_id: str | None = None


class TaskJournal:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._db: sqlite3.Connection | None = None
        self._owner = None

    def _connect(self):
        if self._db is not None:
            return self._db
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._owner = portalocker.Lock(str(self.path) + ".lock", timeout=0)
        self._owner.acquire()
        db = sqlite3.connect(self.path, check_same_thread=False)
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, snapshot TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                id TEXT NOT NULL, cursor INTEGER NOT NULL, envelope TEXT NOT NULL,
                PRIMARY KEY (id, cursor));
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT NOT NULL, key TEXT NOT NULL, digest TEXT NOT NULL, ack TEXT NOT NULL,
                PRIMARY KEY (id, key));
        """)
        self._db = db
        for (raw,) in db.execute("SELECT snapshot FROM tasks").fetchall():
            snapshot = TaskSnapshot.model_validate_json(raw)
            if snapshot.phase not in TERMINAL:
                self.update(snapshot.session_id, phase="interrupted", outcome="engine_stopped", pending_actions=[])
        return db

    def close(self):
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
            if self._owner is not None:
                self._owner.release()
                self._owner = None

    def snapshot(self, sid: str) -> TaskSnapshot | None:
        with self._lock:
            if self._db is None and not self.path.exists():
                return None
            row = self._connect().execute("SELECT snapshot FROM tasks WHERE id=?", (sid,)).fetchone()
            return TaskSnapshot.model_validate_json(row[0]) if row else None

    def register(self, sid: str):
        with self._lock:
            db = self._connect()
            with db:
                db.execute("INSERT OR IGNORE INTO tasks VALUES (?, ?)",
                           (sid, TaskSnapshot(task_id=sid, session_id=sid).model_dump_json()))

    def _append(self, db, snapshot: TaskSnapshot, event: dict):
        snapshot.watermark += 1
        envelope = TaskEvent(cursor=snapshot.watermark, snapshot=snapshot, event=event)
        db.execute("UPDATE tasks SET snapshot=? WHERE id=?", (snapshot.model_dump_json(), snapshot.session_id))
        db.execute("INSERT INTO events VALUES (?, ?, ?)",
                   (snapshot.session_id, snapshot.watermark, envelope.model_dump_json()))
        return envelope

    def update(self, sid: str, **changes) -> TaskSnapshot:
        with self._lock:
            snapshot = self.snapshot(sid)
            if snapshot is None:
                raise KeyError(sid)
            snapshot = TaskSnapshot.model_validate({**snapshot.model_dump(), **changes})
            with self._connect() as db:
                self._append(db, snapshot, {"v": 1, "type": "task.state"})
            return snapshot

    def emit(self, sid: str, event: dict):
        with self._lock:
            snapshot = self.snapshot(sid)
            if snapshot is None:
                raise KeyError(sid)
            kind = event["type"]
            if snapshot.phase not in TERMINAL and kind in ("permission.updated", "diff.proposed"):
                snapshot.pending_actions.append({"kind": kind, "id": event["id"]})
                snapshot.phase = "waiting"
            elif snapshot.phase not in TERMINAL and kind == "clarify":
                snapshot.pending_actions = [{"kind": "clarify"}]
                snapshot.phase = "waiting"
            with self._connect() as db:
                self._append(db, snapshot, event)

    def resolve(self, sid: str, action_id: str):
        with self._lock:
            snapshot = self.snapshot(sid)
            if snapshot is not None and snapshot.phase not in TERMINAL and any(p.get("id") == action_id for p in snapshot.pending_actions):
                pending = [p for p in snapshot.pending_actions if p.get("id") != action_id]
                self.update(sid, pending_actions=pending, phase="waiting" if pending else "active")

    def receipt(self, sid: str, key: str, payload: dict) -> CommandAck | None:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self._lock:
            row = self._connect().execute("SELECT digest, ack FROM commands WHERE id=? AND key=?", (sid, key)).fetchone()
            if row and row[0] != digest:
                raise ValueError("command_id was already used for a different request")
            return CommandAck.model_validate_json(row[1]) if row else None

    def begin(self, sid: str, key: str, payload: dict, *, swarm_id: str | None = None, swarm_task_id: str | None = None) -> CommandAck:
        with self._lock:
            previous = self.receipt(sid, key, payload)
            if previous:
                return previous
            snapshot = self.snapshot(sid)
            if snapshot is None:
                raise KeyError(sid)
            snapshot.run_id = uuid.uuid4().hex
            snapshot.attempt_id = uuid.uuid4().hex
            snapshot.swarm_id = swarm_id
            snapshot.swarm_task_id = swarm_task_id
            snapshot.task_id = swarm_task_id or swarm_id or sid
            snapshot.phase, snapshot.outcome, snapshot.pending_actions = "active", None, []
            ack = CommandAck(status="accepted", run_id=snapshot.run_id, attempt_id=snapshot.attempt_id)
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            with self._connect() as db:
                self._append(db, snapshot, {"v": 1, "type": "task.state"})
                db.execute("INSERT INTO commands VALUES (?, ?, ?, ?)", (sid, key, digest, ack.model_dump_json()))
            return ack

    def replay(self, sid: str, after: int, limit: int = 256) -> list[TaskEvent]:
        with self._lock:
            rows = self._connect().execute(
                "SELECT envelope FROM events WHERE id=? AND cursor>? ORDER BY cursor LIMIT ?", (sid, after, limit)
            ).fetchall()
            return [TaskEvent.model_validate_json(row[0]) for row in rows]

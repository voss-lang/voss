"""SQLite observe store: one database per repository under the app-state dir.

Path: `<app-state>/observe/<repository_id>.sqlite` (app-state from
`voss.harness.config.app_state_dir`). Migrations are numbered entries in
MIGRATIONS applied in order and tracked with `PRAGMA user_version`.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from voss.harness.config import app_state_dir
from voss.harness.observe.models import ObserveEvent

_MIGRATION_1 = """
CREATE TABLE events (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id       TEXT NOT NULL UNIQUE,
    event_type     TEXT NOT NULL,
    repository_id  TEXT NOT NULL,
    worktree_id    TEXT NOT NULL,
    command_id     TEXT,
    trace_id       TEXT,
    caused_by      TEXT,
    actor          TEXT,
    event_time     TEXT NOT NULL,
    ingest_time    TEXT NOT NULL,
    fingerprint    TEXT,
    body           TEXT NOT NULL
);
CREATE INDEX idx_events_worktree ON events (worktree_id, seq);
CREATE INDEX idx_events_fingerprint ON events (fingerprint);

CREATE TABLE evidence (
    evidence_id  TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL REFERENCES events (event_id),
    kind         TEXT NOT NULL,
    content      BLOB NOT NULL,
    truncated    INTEGER NOT NULL DEFAULT 0,
    sha256       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE INDEX idx_evidence_event ON evidence (event_id);

CREATE TABLE admissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT NOT NULL,
    fingerprint     TEXT NOT NULL,
    decision        TEXT NOT NULL,
    reason          TEXT NOT NULL,
    policy_version  TEXT NOT NULL,
    decided_at      REAL NOT NULL
);
CREATE INDEX idx_admissions_fingerprint ON admissions (fingerprint, id);
CREATE INDEX idx_admissions_event ON admissions (event_id);

CREATE TABLE investigations (
    investigation_id  TEXT PRIMARY KEY,
    repository_id     TEXT NOT NULL,
    worktree_id       TEXT NOT NULL,
    trigger_event_id  TEXT NOT NULL,
    fingerprint       TEXT NOT NULL,
    status            TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE INDEX idx_investigations_worktree ON investigations (worktree_id, status);

CREATE TABLE findings (
    finding_id        TEXT PRIMARY KEY,
    repository_id     TEXT NOT NULL,
    worktree_id       TEXT NOT NULL,
    investigation_id  TEXT,
    title             TEXT NOT NULL,
    status            TEXT NOT NULL,
    body              TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
"""

MIGRATIONS: list[str] = [_MIGRATION_1]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def observe_dir(state_dir: Path | None = None) -> Path:
    return (state_dir or app_state_dir()) / "observe"


def db_path(repository_id: str, *, state_dir: Path | None = None) -> Path:
    return observe_dir(state_dir) / f"{repository_id}.sqlite"


class ObserveStore:
    def __init__(self, repository_id: str, *, state_dir: Path | None = None) -> None:
        self.repository_id = repository_id
        self.path = db_path(repository_id, state_dir=state_dir)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), timeout=5.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        for number, sql in enumerate(MIGRATIONS, start=1):
            if number > version:
                self._conn.executescript(sql)
                self._conn.execute(f"PRAGMA user_version={number}")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ObserveStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- events -------------------------------------------------------------

    def insert_event(self, event: ObserveEvent, *, fingerprint: str | None = None) -> bool:
        """Insert one event; returns False when `event_id` is already stored."""
        body = event.model_dump(mode="json")
        ingest_time = body.get("ingest_time") or _now_iso()
        body["ingest_time"] = ingest_time
        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO events (
                        event_id, event_type, repository_id, worktree_id,
                        command_id, trace_id, caused_by, actor,
                        event_time, ingest_time, fingerprint, body
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.event_type,
                        event.repository_id,
                        event.worktree_id,
                        event.command_id,
                        event.trace_id,
                        event.caused_by,
                        event.actor,
                        event.event_time,
                        ingest_time,
                        fingerprint,
                        json.dumps(body, sort_keys=True),
                    ),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def has_event(self, event_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT seq, body FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return {"seq": row["seq"], "event": json.loads(row["body"])}

    def list_events(self, *, after_seq: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT seq, body FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
            (after_seq, limit),
        ).fetchall()
        return [{"seq": row["seq"], "event": json.loads(row["body"])} for row in rows]

    # -- evidence -----------------------------------------------------------

    def put_evidence(
        self,
        evidence_id: str,
        event_id: str,
        kind: str,
        content: bytes,
        *,
        truncated: bool = False,
    ) -> str:
        digest = hashlib.sha256(content).hexdigest()
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO evidence (
                    evidence_id, event_id, kind, content, truncated, sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    event_id,
                    kind,
                    content,
                    1 if truncated else 0,
                    digest,
                    _now_iso(),
                ),
            )
        return digest

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "evidence_id": row["evidence_id"],
            "event_id": row["event_id"],
            "kind": row["kind"],
            "content": bytes(row["content"]),
            "truncated": bool(row["truncated"]),
            "sha256": row["sha256"],
            "created_at": row["created_at"],
        }

    # -- admissions ---------------------------------------------------------

    def record_admission(
        self,
        *,
        event_id: str,
        fingerprint: str,
        decision: str,
        reason: str,
        policy_version: str,
        decided_at: float,
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO admissions (
                    event_id, fingerprint, decision, reason, policy_version, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, fingerprint, decision, reason, policy_version, decided_at),
            )

    def admissions(self, *, event_id: str | None = None) -> list[dict[str, Any]]:
        if event_id is None:
            rows = self._conn.execute(
                "SELECT * FROM admissions ORDER BY id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM admissions WHERE event_id = ? ORDER BY id", (event_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_admission(
        self, fingerprint: str, *, decisions: tuple[str, ...] | None = None
    ) -> dict[str, Any] | None:
        if decisions is None:
            row = self._conn.execute(
                "SELECT * FROM admissions WHERE fingerprint = ? ORDER BY id DESC LIMIT 1",
                (fingerprint,),
            ).fetchone()
        else:
            placeholders = ", ".join("?" for _ in decisions)
            row = self._conn.execute(
                f"SELECT * FROM admissions WHERE fingerprint = ? "
                f"AND decision IN ({placeholders}) ORDER BY id DESC LIMIT 1",
                (fingerprint, *decisions),
            ).fetchone()
        return dict(row) if row is not None else None

    # -- investigations -----------------------------------------------------

    def enqueue_investigation(
        self,
        *,
        investigation_id: str,
        worktree_id: str,
        trigger_event_id: str,
        fingerprint: str,
    ) -> None:
        now = _now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO investigations (
                    investigation_id, repository_id, worktree_id,
                    trigger_event_id, fingerprint, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (
                    investigation_id,
                    self.repository_id,
                    worktree_id,
                    trigger_event_id,
                    fingerprint,
                    now,
                    now,
                ),
            )

    def pending_investigations(self, worktree_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM investigations WHERE worktree_id = ? AND status = 'queued' "
            "ORDER BY created_at",
            (worktree_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_pending(self, worktree_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM investigations "
            "WHERE worktree_id = ? AND status = 'queued'",
            (worktree_id,),
        ).fetchone()
        return int(row["n"])

    def pending_by_fingerprint(
        self, worktree_id: str, fingerprint: str
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM investigations WHERE worktree_id = ? AND fingerprint = ? "
            "AND status = 'queued' ORDER BY created_at LIMIT 1",
            (worktree_id, fingerprint),
        ).fetchone()
        return dict(row) if row is not None else None

    # -- findings -----------------------------------------------------------

    def upsert_finding(
        self,
        *,
        finding_id: str,
        worktree_id: str,
        title: str,
        status: str,
        body: dict[str, Any],
        investigation_id: str | None = None,
    ) -> None:
        now = _now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO findings (
                    finding_id, repository_id, worktree_id, investigation_id,
                    title, status, body, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (finding_id) DO UPDATE SET
                    status = excluded.status,
                    body = excluded.body,
                    updated_at = excluded.updated_at
                """,
                (
                    finding_id,
                    self.repository_id,
                    worktree_id,
                    investigation_id,
                    title,
                    status,
                    json.dumps(body, sort_keys=True),
                    now,
                    now,
                ),
            )

    def get_finding(self, finding_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM findings WHERE finding_id = ?", (finding_id,)
        ).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["body"] = json.loads(out["body"])
        return out


__all__ = ["MIGRATIONS", "ObserveStore", "db_path", "observe_dir"]

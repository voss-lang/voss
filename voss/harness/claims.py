"""V17 claims engine — advisory pre-edit conflict guards (VBUS-01/02).

Pure overlap algorithms (glob + URI), serverless SQLite storage at
<cwd>/.voss-cache/claims.sqlite (D-02 locked location), and the atomic
check-and-stake transaction. The click CLI verbs land in V17-03 on top of
this engine.

Overlap is conservative static pattern-vs-pattern analysis: no filesystem
reads (D-05). URIs (`card://123`, `port://8080`) overlap on exact match or
path-prefix at `/` boundaries (D-06). Same-agent self-overlap is never a
conflict — re-stake is an idempotent refresh (D-04).

Concurrency: WAL + `BEGIN IMMEDIATE` acquires the write lock at transaction
start, so N processes racing to stake an overlapping pattern get exactly one
winner. Never use `with conn:` for the stake transaction (deferred BEGIN
allows a double-grant) and never `:memory:` (per-process isolation).
"""
from __future__ import annotations

import fnmatch
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path, PurePosixPath

DEFAULT_TTL_SECONDS = 1800

_GLOB_CHARS = set("*?[{")


# ---------------------------------------------------------------------------
# Overlap engine (pure — no filesystem reads, D-05)
# ---------------------------------------------------------------------------


def _is_uri(pattern: str) -> bool:
    return "://" in pattern


def _extract_base_and_tail(pattern: str) -> tuple[PurePosixPath, str]:
    """Split a glob at the first segment containing a glob char.

    "src/api/**" -> (src/api, "**"); "src/api/handlers.py" -> (src/api/handlers.py, "").
    """
    parts = PurePosixPath(pattern).parts
    base: list[str] = []
    tail: list[str] = []
    in_glob = False
    for part in parts:
        if not in_glob and not any(c in part for c in _GLOB_CHARS):
            base.append(part)
        else:
            in_glob = True
            tail.append(part)
    base_path = PurePosixPath(*base) if base else PurePosixPath(".")
    tail_str = str(PurePosixPath(*tail)) if tail else ""
    return base_path, tail_str


def glob_patterns_overlap(p1: str, p2: str) -> bool:
    """Conservative static check: could p1 and p2 match the same file?"""
    b1, t1 = _extract_base_and_tail(p1)
    b2, t2 = _extract_base_and_tail(p2)
    try:
        b1.relative_to(b2)
    except ValueError:
        try:
            b2.relative_to(b1)
        except ValueError:
            return False
    if not t1 or t1 in ("**", "*", "**/*"):
        return True
    if not t2 or t2 in ("**", "*", "**/*"):
        return True
    return fnmatch.fnmatch(t2, t1) or fnmatch.fnmatch(t1, t2)


def uri_overlap(u1: str, u2: str) -> bool:
    """Exact match or path-prefix at a `/` boundary (D-06)."""
    u1, u2 = u1.rstrip("/"), u2.rstrip("/")
    if u1 == u2:
        return True
    return u2.startswith(u1 + "/") or u1.startswith(u2 + "/")


def patterns_overlap(set_a: list[str], set_b: list[str]) -> bool:
    """Any-vs-any across two pattern sets; URI pairs vs glob pairs, never mixed."""
    for a in set_a:
        for b in set_b:
            a_uri, b_uri = _is_uri(a), _is_uri(b)
            if a_uri and b_uri:
                if uri_overlap(a, b):
                    return True
            elif not a_uri and not b_uri:
                if glob_patterns_overlap(a, b):
                    return True
    return False


def canonicalize_pattern(pattern: str, cwd: Path) -> str:
    """Resolve a non-URI pattern from the invoking cwd; reject traversal.

    Mirrors sandbox.rs::validate_scope discipline: empty and `..`-containing
    patterns are rejected outright; the normalized form must stay under cwd.
    URIs pass through unchanged. Raises ValueError on rejection.
    """
    if _is_uri(pattern):
        return pattern
    if not pattern.strip():
        raise ValueError("empty pattern")
    if ".." in pattern:
        raise ValueError(f"traversal rejected: {pattern!r}")
    root = Path(cwd).resolve()
    raw = pattern if os.path.isabs(pattern) else os.path.join(str(root), pattern)
    norm = os.path.normpath(raw)
    if norm != str(root) and not norm.startswith(str(root) + os.sep):
        raise ValueError(f"pattern escapes cwd: {pattern!r}")
    return norm


# ---------------------------------------------------------------------------
# SQLite storage (serverless, concurrent-safe — VBUS-02)
# ---------------------------------------------------------------------------

_CLAIMS_SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id          TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    patterns    TEXT NOT NULL,
    expires_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_expires ON claims (expires_at);
CREATE INDEX IF NOT EXISTS idx_claims_agent ON claims (agent_id);
"""


def _get_db_path(cwd: Path) -> Path:
    # D-02: .voss-cache/claims.sqlite — locked deviation from SPEC's .voss/.
    return Path(cwd).resolve() / ".voss-cache" / "claims.sqlite"


def open_claims_db(cwd: Path) -> sqlite3.Connection:
    db_path = _get_db_path(cwd)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_CLAIMS_SCHEMA)
    conn.commit()
    return conn


def new_claim_id() -> str:
    return uuid.uuid4().hex[:12]


def atomic_stake(
    conn: sqlite3.Connection,
    agent_id: str,
    claim_id: str,
    patterns: list[str],
    ttl: float = DEFAULT_TTL_SECONDS,
) -> tuple[bool, list[sqlite3.Row | tuple]]:
    """Atomically check-and-stake. Returns (won, conflicting_rows).

    BEGIN IMMEDIATE takes the write lock before the conflict scan, so
    concurrent overlapping stakes serialize: exactly one winner. Same-agent
    rows are excluded from the scan (D-04 idempotent refresh).
    """
    now = time.time()
    expires_at = now + ttl
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute(
            "SELECT id, agent_id, patterns, expires_at FROM claims "
            "WHERE agent_id != ? AND expires_at > ?",
            (agent_id, now),
        ).fetchall()
        conflicts = [
            row for row in rows if patterns_overlap(patterns, json.loads(row[2]))
        ]
        if conflicts:
            conn.rollback()
            return False, conflicts
        conn.execute(
            "INSERT OR REPLACE INTO claims (id, agent_id, patterns, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (claim_id, agent_id, json.dumps(patterns), expires_at),
        )
        conn.commit()
        return True, []
    except BaseException:
        conn.rollback()
        raise


def active_claims(
    conn: sqlite3.Connection,
    exclude_agent: str | None = None,
    now: float | None = None,
) -> list[tuple]:
    """All unexpired claims, optionally excluding one agent's own."""
    now = time.time() if now is None else now
    if exclude_agent is None:
        return conn.execute(
            "SELECT id, agent_id, patterns, expires_at FROM claims "
            "WHERE expires_at > ? ORDER BY expires_at",
            (now,),
        ).fetchall()
    return conn.execute(
        "SELECT id, agent_id, patterns, expires_at FROM claims "
        "WHERE agent_id != ? AND expires_at > ? ORDER BY expires_at",
        (exclude_agent, now),
    ).fetchall()


def all_claims(conn: sqlite3.Connection) -> list[tuple]:
    """Every row including expired — backs `list --all`."""
    return conn.execute(
        "SELECT id, agent_id, patterns, expires_at FROM claims ORDER BY expires_at"
    ).fetchall()


def release_claims(
    conn: sqlite3.Connection, agent_id: str, claim_id: str | None = None
) -> int:
    """Delete one claim by id, or all of the agent's claims (D-03)."""
    if claim_id is None:
        cur = conn.execute("DELETE FROM claims WHERE agent_id = ?", (agent_id,))
    else:
        cur = conn.execute(
            "DELETE FROM claims WHERE agent_id = ? AND id = ?",
            (agent_id, claim_id),
        )
    conn.commit()
    return cur.rowcount


def extend_claim(
    conn: sqlite3.Connection,
    agent_id: str,
    claim_id: str,
    ttl: float = DEFAULT_TTL_SECONDS,
) -> bool:
    """Refresh expires_at for an unexpired claim owned by agent_id (D-03)."""
    now = time.time()
    cur = conn.execute(
        "UPDATE claims SET expires_at = ? "
        "WHERE agent_id = ? AND id = ? AND expires_at > ?",
        (now + ttl, agent_id, claim_id, now),
    )
    conn.commit()
    return cur.rowcount > 0


def prune_expired(conn: sqlite3.Connection, now: float | None = None) -> int:
    """Drop expired rows (discretionary hygiene; queries already filter)."""
    now = time.time() if now is None else now
    cur = conn.execute("DELETE FROM claims WHERE expires_at <= ?", (now,))
    conn.commit()
    return cur.rowcount

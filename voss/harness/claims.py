"""V17 claims engine — advisory pre-edit conflict guards (VBUS-01/02).

Pure overlap algorithms (glob + URI), serverless SQLite storage at
<cwd>/.voss-cache/claims.sqlite (D-02 locked location), the atomic
check-and-stake transaction, and the `voss claims` click verbs
(stake/check/release/extend/list — exit 0 clear, 1 conflict, 2 identity/usage).

Overlap is conservative static pattern-vs-pattern analysis: no filesystem
reads (D-05). URIs (`card://123`, `port://8080`) overlap on exact match or
path-prefix at `/` boundaries (D-06). Same-agent self-overlap is never a
conflict — re-stake is an idempotent refresh (D-04).

Concurrency: WAL + `BEGIN IMMEDIATE` acquires the write lock at transaction
start, so N processes racing to stake an overlapping pattern get exactly one
winner. Never use `with conn:` for the stake transaction (deferred BEGIN
allows a double-grant) and never an in-memory database (per-process
isolation would make claims invisible across CLI processes).
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path, PurePosixPath

import click

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
    claim_id: str | None = None,
    ttl: float = DEFAULT_TTL_SECONDS,
) -> bool:
    """Refresh expires_at for unexpired claims owned by agent_id (D-03).

    With claim_id, refreshes that one claim set; bare, refreshes all of the
    agent's unexpired claims.
    """
    now = time.time()
    if claim_id is None:
        cur = conn.execute(
            "UPDATE claims SET expires_at = ? "
            "WHERE agent_id = ? AND expires_at > ?",
            (now + ttl, agent_id, now),
        )
    else:
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


# ---------------------------------------------------------------------------
# CLI verbs (VBUS-01) — exit contract: 0 clear/success, 1 conflict, 2 usage/identity
# ---------------------------------------------------------------------------


def _resolve_agent_id() -> str:
    agent_id = os.environ.get("VOSS_AGENT_ID", "").strip()
    if not agent_id:
        click.echo(
            "VOSS_AGENT_ID not set. Set it to your agent id "
            "(e.g. export VOSS_AGENT_ID=claude-1), or run inside a "
            "voss-managed pane.",
            err=True,
        )
        sys.exit(2)
    return agent_id


def _canonicalize_all(patterns: tuple[str, ...], cwd: Path) -> list[str]:
    try:
        return [canonicalize_pattern(p, cwd) for p in patterns]
    except ValueError as exc:
        click.echo(f"invalid pattern: {exc}", err=True)
        sys.exit(2)


def _claim_id_for(agent_id: str, canonical: list[str]) -> str:
    """Deterministic per pattern-set: re-staking the same set refreshes (D-04)."""
    digest = hashlib.sha1(json.dumps(sorted(canonical)).encode()).hexdigest()[:8]
    return f"{agent_id}:{digest}"


def _advice_for_conflict(
    owner: str, requested: tuple[str, ...], verb_args: list[str]
) -> list[str]:
    # D-07/VBUS-06: first entry is a runnable bus message naming the owner.
    want = requested[0] if requested else "this scope"
    return [
        f'voss bus send "@{owner} I need {want} — when are you done?"',
        "voss claims check " + " ".join(verb_args),
    ]


def _find_conflicts(
    conn: sqlite3.Connection, agent_id: str, canonical: list[str]
) -> list[tuple]:
    return [
        row
        for row in active_claims(conn, exclude_agent=agent_id)
        if patterns_overlap(canonical, json.loads(row[2]))
    ]


def _emit_conflict(
    conflicts: list[tuple],
    requested: tuple[str, ...],
    verb_args: list[str],
    json_mode: bool,
) -> None:
    owner = conflicts[0][1]
    if json_mode:
        for row in conflicts:
            click.echo(
                json.dumps(
                    {
                        "conflict": True,
                        "claim_id": row[0],
                        "owner": row[1],
                        "patterns": json.loads(row[2]),
                        "expires_at": row[3],
                        "advice": _advice_for_conflict(owner, requested, verb_args),
                    }
                )
            )
    else:
        for row in conflicts:
            click.echo(
                f"conflict: {row[1]} holds claim {row[0]} on "
                f"{', '.join(json.loads(row[2]))}"
            )
    sys.exit(1)


@click.group("claims")
def claims_group() -> None:
    """Advisory pre-edit conflict guards (file globs + card://-style URIs)."""


@claims_group.command("stake")
@click.argument("patterns", nargs=-1, required=True)
@click.option("--ttl", default=DEFAULT_TTL_SECONDS, type=float, show_default=True,
              help="Claim lifetime in seconds.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def claims_stake_cmd(patterns: tuple[str, ...], ttl: float, cwd_str: str,
                     json_mode: bool) -> None:
    """Register a claim; atomically rejected on overlap with another agent."""
    agent_id = _resolve_agent_id()
    cwd = Path(cwd_str)
    canonical = _canonicalize_all(patterns, cwd)
    conn = open_claims_db(cwd)
    claim_id = _claim_id_for(agent_id, canonical)
    won, conflicts = atomic_stake(conn, agent_id, claim_id, canonical, ttl)
    if not won:
        _emit_conflict(conflicts, patterns, list(patterns), json_mode)
    if json_mode:
        click.echo(json.dumps({
            "staked": True,
            "claim_id": claim_id,
            "agent_id": agent_id,
            "patterns": canonical,
            "ttl": ttl,
        }))
    else:
        click.echo(f"staked {claim_id}: {', '.join(patterns)} (ttl {ttl:.0f}s)")


@claims_group.command("check")
@click.argument("patterns", nargs=-1, required=True)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def claims_check_cmd(patterns: tuple[str, ...], cwd_str: str,
                     json_mode: bool) -> None:
    """Pre-edit guard: exit 0 when clear, 1 when another agent's claim overlaps."""
    agent_id = _resolve_agent_id()
    cwd = Path(cwd_str)
    canonical = _canonicalize_all(patterns, cwd)
    conn = open_claims_db(cwd)
    conflicts = _find_conflicts(conn, agent_id, canonical)
    if conflicts:
        _emit_conflict(conflicts, patterns, list(patterns), json_mode)
    if json_mode:
        click.echo(json.dumps({"conflict": False, "patterns": canonical}))
    else:
        click.echo("clear")


@claims_group.command("release")
@click.argument("claim_id", required=False)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def claims_release_cmd(claim_id: str | None, cwd_str: str, json_mode: bool) -> None:
    """Free one claim by id, or all own claims when no id is given (D-03)."""
    agent_id = _resolve_agent_id()
    conn = open_claims_db(Path(cwd_str))
    released = release_claims(conn, agent_id, claim_id)
    if json_mode:
        click.echo(json.dumps({"released": released, "agent_id": agent_id}))
    else:
        click.echo(f"released {released} claim(s)")


@claims_group.command("extend")
@click.argument("claim_id", required=False)
@click.option("--ttl", default=DEFAULT_TTL_SECONDS, type=float, show_default=True,
              help="New lifetime in seconds from now.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def claims_extend_cmd(claim_id: str | None, ttl: float, cwd_str: str,
                      json_mode: bool) -> None:
    """Refresh the TTL of one claim by id, or all own unexpired claims."""
    agent_id = _resolve_agent_id()
    conn = open_claims_db(Path(cwd_str))
    refreshed = extend_claim(conn, agent_id, claim_id, ttl)
    if not refreshed:
        click.echo("no matching unexpired claim to extend", err=True)
        sys.exit(2)
    if json_mode:
        click.echo(json.dumps({"extended": True, "claim_id": claim_id, "ttl": ttl}))
    else:
        click.echo(f"extended (ttl {ttl:.0f}s)")


@claims_group.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include expired claims.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def claims_list_cmd(show_all: bool, cwd_str: str, json_mode: bool) -> None:
    """Show active claims (expired hidden unless --all)."""
    _resolve_agent_id()
    conn = open_claims_db(Path(cwd_str))
    rows = all_claims(conn) if show_all else active_claims(conn)
    now = time.time()
    for row in rows:
        if json_mode:
            click.echo(json.dumps({
                "claim_id": row[0],
                "agent_id": row[1],
                "patterns": json.loads(row[2]),
                "expires_at": row[3],
            }))
        else:
            expires_in = row[3] - now
            state = f"{expires_in:.0f}s" if expires_in > 0 else "expired"
            click.echo(
                f"{row[0]}  {row[1]}  {', '.join(json.loads(row[2]))}  {state}"
            )

"""VBOARD-10 read-only board renderer.

Renders the board from persisted session-tree node JSON
(``<cwd>/.voss/sessions/<root_id>/<node_id>.json``) without constructing a
live ``Board`` or ``SessionTreeManager``. Mirrors the read-only column
derivation rule in ``voss/harness/audit/load.py`` (lines 206-220) exactly.

Root selection defaults to the most-recently-modified root directory
(by ``st_mtime``, NOT lexical name — UUID-hex root ids are not chronologically
sortable). A user-supplied ``root_id`` is validated for path traversal before
any filesystem access.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

# Redeclared locally (do NOT import from machine.py — avoids pulling in the
# full board state-machine import chain for this read-only view).
_COLUMNS: tuple[str, ...] = (
    "Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done",
)


def _read_node_file(path: Path) -> dict[str, Any] | None:
    """Defensively read a persisted node JSON file.

    Mirrors ``audit/load.py._read_node_file`` but tolerant: returns ``None``
    for unreadable / non-dict / malformed JSON rather than raising, so a single
    bad file does not crash the read-only view.
    """
    try:
        text = path.read_text()
    except OSError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if "id" not in data:
        return None
    return data


def _derive_column(data: dict[str, Any]) -> str:
    """Derive the card's column from persisted transitions + terminal_state.

    Copied VERBATIM from ``audit/load.py`` lines 206-220.
    """
    transitions = data.get("transitions", [])
    column = "Backlog"
    for t in transitions:
        if t.get("kind") == "board.transition":
            column = t.get("to", column)

    terminal = data.get("terminal_state")
    if terminal is not None:
        exit_reason = terminal.get("exit_reason", "")
        if exit_reason == "timeout":
            column = "Blocked"
        elif exit_reason == "killed":
            column = "Blocked"
        elif exit_reason == "done":
            column = "Done"
    return column


def _derive_risk(data: dict[str, Any]) -> str:
    """Risk tier from the node's em.ticket transition, falling back to 'med'."""
    for t in data.get("transitions", []):
        if t.get("kind") == "em.ticket":
            return t.get("risk_tier", "med")
    return "med"


def render_board(cwd: Path, root_id: str | None = None) -> int:
    """Render the board read-only from persisted node JSON.

    Returns 0 on a successful render (output on stdout), non-zero on:
    missing sessions dir, unknown root, empty sessions dir, or a path-traversal
    / separator-bearing ``root_id`` (with a ``click.echo(..., err=True)``
    message). The caller (``board_cmd``) translates the code to ``Exit``.
    """
    sessions_dir = cwd / ".voss" / "sessions"
    if not sessions_dir.is_dir():
        click.echo(
            f"<error: no sessions directory at {sessions_dir}>", err=True
        )
        return 1

    if root_id is not None:
        # T-V5-03: reject traversal BEFORE touching the filesystem.
        if "/" in root_id or "\\" in root_id or ".." in root_id:
            click.echo(
                f"<error: invalid root_id {root_id!r}>", err=True
            )
            return 1
        candidate = (sessions_dir / root_id).resolve()
        sessions_resolved = sessions_dir.resolve()
        # Confirm the resolved candidate is a child of the sessions dir.
        if candidate.parent != sessions_resolved:
            click.echo(
                f"<error: invalid root_id {root_id!r}>", err=True
            )
            return 1
        if not candidate.is_dir():
            click.echo(
                f"<error: unknown root {root_id!r}>", err=True
            )
            return 1
        root_dir = sessions_dir / root_id
    else:
        root_dirs = sorted(
            (d for d in sessions_dir.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        if not root_dirs:
            click.echo(
                f"<error: no session roots under {sessions_dir}>", err=True
            )
            return 1
        root_dir = root_dirs[0]

    # Read every node JSON and bucket into columns.
    columns: dict[str, list[dict[str, Any]]] = {c: [] for c in _COLUMNS}
    for nf in sorted(root_dir.glob("*.json")):
        data = _read_node_file(nf)
        if data is None:
            continue
        column = _derive_column(data)
        envelope = data.get("envelope") or {}
        card = {
            "id": data["id"],
            "role": data.get("role", ""),
            "risk": _derive_risk(data),
            "status": column,
            "spent": envelope.get("spent", 0),
            "limit": envelope.get("limit", 0),
        }
        columns.setdefault(column, []).append(card)

    click.echo(f"Board: {root_dir.name}")
    for col in _COLUMNS:
        cards = columns.get(col, [])
        click.echo(f"\n{col} ({len(cards)})")
        for c in cards:
            click.echo(
                f"  {c['id']:<16}  {c['role']:<10}  {c['risk']:<5}  "
                f"{c['status']:<11}  {c['spent']}/{c['limit']}"
            )
    return 0

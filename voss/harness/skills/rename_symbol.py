"""SKL-01 `rename-symbol`: deterministic, mutating, gate-enforced rename.

ZERO provider calls (D-08) — no LLM, no agent loop. Mutating (D-09,
`mutating=True`). Every write flows through the gated `fs_edit` tool, and
because this skill runs OUTSIDE the agent loop the central permission gate is
NOT applied automatically (RESEARCH landmine #3 / Pitfall 2) — so the skill
MUST self-enforce it: an explicit `gate.check("fs_edit", ..., is_mutating=
True)` before every edit, with an immediate clean return (no retry, no
escalation, no fallback) when the gate denies. In `plan` mode the first
check returns `(False, "denied by mode plan")` and the skill exits having
changed nothing.

Scoping engine: anchor + `fs_grep`/`fs_edit` heuristic (RESEARCH discretion
call — verified zero `ast` usage in the codebase; cross-file AST resolution
is unwarranted complexity here). Whole-token (`\bold\b`) matches only.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import click


def run(
    *,
    cwd: Path,
    provider,  # unused — deterministic skill, no LLM
    history,  # unused
    record,  # unused
    renderer,  # unused
    tools,
    gate,
    args: list[str] | None = None,
) -> None:
    if args is None or len(args) < 2:
        click.echo("usage: rename-symbol <old> <new>", err=True)
        return
    old, new = args[0], args[1]

    # Discovery — read-only (fs_grep is_mutating=False, no gate.check needed).
    hits_raw = asyncio.run(
        tools["fs_grep"].invoke(pattern=rf"\b{re.escape(old)}\b", glob="**/*.py")
    )
    if not hits_raw or hits_raw == "<no matches>" or hits_raw.startswith("<error"):
        click.echo(f"no occurrences of {old!r} found", err=True)
        return

    # Parse "relpath:lineno: text" lines into a deduplicated, sorted file set.
    files: list[str] = []
    seen: set[str] = set()
    for line in hits_raw.splitlines():
        rel = line.split(":", 1)[0].strip()
        if rel and rel not in seen:
            seen.add(rel)
            files.append(rel)
    files.sort()

    word = re.compile(rf"\b{re.escape(old)}\b")
    changed: list[str] = []
    for rel in files:
        # Gate self-enforcement BEFORE any mutation (landmine #3 / Pitfall 2).
        allowed, reason = gate.check(
            "fs_edit",
            {"path": rel, "old": old, "new": new},
            is_mutating=True,
        )
        if not allowed:
            # plan-mode clean refusal: stop immediately, mutate nothing.
            click.echo(f"rename-symbol: {reason}", err=True)
            return

        original = asyncio.run(tools["fs_read"].invoke(path=rel))
        if not isinstance(original, str) or original.startswith("<error"):
            continue
        replaced = word.sub(new, original)
        if replaced == original:
            continue
        # Whole-file old/new → unambiguous single match for fs_edit's
        # unique-match contract; the cwd jail in fs_edit confines the write.
        asyncio.run(
            tools["fs_edit"].invoke(path=rel, old=original, new=replaced)
        )
        changed.append(rel)

    if changed:
        click.echo(
            f"renamed {old!r} -> {new!r} in {len(changed)} file(s): "
            + ", ".join(changed)
        )
    else:
        click.echo(f"no whole-token occurrences of {old!r} to rename", err=True)

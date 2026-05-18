"""SKL-05 `audit-cognition`: agentic, read-only cognition-drift auditor.

Agentic (D-07) — drives a model turn via `run_turn`. Read-only (D-10,
`mutating=False`).

HARD INVARIANT (D-05 / D-10 / Pitfall 3): this skill only PROPOSES an
update to the project's architecture description. It NEVER writes the
architecture file or the project doc (or any file). A human or a separate
flow applies the proposal. The no-write guarantee is defended in three
layers: (1) the prompt explicitly forbids file writes and demands a
`PROPOSAL:`-prefixed paragraph; (2) this module reaches no write API at all
(no edit/write tool helper imported or called); (3) the smoke test
byte-compares the cognition file before and after the run.

The `.voss` companion at voss/harness/skills/voss/audit-cognition.voss is a
dogfood demonstration (D-05), NOT the runtime exec path.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import click

from .. import cognition
from ..agent import run_turn


def run(
    *,
    cwd: Path,
    provider,
    history,
    record,
    renderer,
    tools,
    gate,
) -> None:
    bundle = cognition.load(cwd)
    if not bundle.initialized:
        click.echo(
            "cognition not initialized — run /analyze first", err=True
        )
        return
    if bundle.architecture_frontmatter is None:
        click.echo(
            "no architecture frontmatter — run /analyze first", err=True
        )
        return

    drift = cognition.drift_check(cwd, bundle.architecture_frontmatter)
    reason = drift.reason if drift.reason else "none"

    prompt = (
        "You are auditing this project's recorded architecture summary for "
        "drift against the live codebase.\n\n"
        f"Cognition stale: {drift.is_stale}. Drift signals: {reason}.\n\n"
        "Propose a single one-paragraph replacement for the architecture "
        "description that reflects the current state of the project.\n\n"
        "Do NOT write to any file. Output your proposal as a single "
        "paragraph starting with 'PROPOSAL:'."
    )

    asyncio.run(
        run_turn(
            prompt,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=record.model,
            provider=provider,
            history=history,
            permissions=gate,
            cognition=None,
            session_id=record.id,
        )
    )

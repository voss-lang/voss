"""
`audit-cognition`: agentic, read-only cognition-drift auditor
Agentic drives a model turn via `run_turn`. Read-only (
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

    result = asyncio.run(
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
    # Surface the proposal (read-only stdout only, never a file write)
    final = getattr(result, "final", "") or ""
    if final.strip():
        click.echo(final)

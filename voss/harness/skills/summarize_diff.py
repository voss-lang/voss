"""
`summarize-diff`: agentic, read-only PR-diff summarizer
Agentic drives a model turn via `run_turn`; the agent calls the
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import click

from voss.template_render import render_package_template

from ..agent import run_turn

_PROMPT = render_package_template(
    "voss",
    "templates/prompts/skill_summarize_diff.txt.jinja",
    {},
)


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
    result = asyncio.run(
        run_turn(
            _PROMPT,
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
    # The PR markdown is this skill's deliverable. run_turn streams a
    # live provider's answer via the renderer but does not re-emit the final
    # so surface it explicitly read-only (stdout only, no file write)
    final = getattr(result, "final", "") or ""
    if final.strip():
        click.echo(final)

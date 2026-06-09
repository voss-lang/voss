"""SKL-03 `summarize-diff`: agentic, read-only PR-diff summarizer.

Agentic (D-07) — drives a model turn via `run_turn`; the agent calls the
`git_diff` tool and composes the answer. Read-only (D-10, `mutating=False`):
this skill performs NO file changes — the meaningful effect is the printed
markdown, surfaced by the turn's renderer. Per D-12 the output uses the
STABLE PR section headers `## Title`, `## Summary`, `## Changes` (these three
strings are a contract; downstream tooling matches on them).

The `.voss` companion at voss/harness/skills/voss/summarize-diff.voss is a
dogfood demonstration of composability (D-05), NOT the runtime exec path.
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
    # The PR markdown is this skill's deliverable (D-12). run_turn streams a
    # live provider's answer via the renderer but does not re-emit the final,
    # so surface it explicitly — read-only (stdout only, no file write).
    final = getattr(result, "final", "") or ""
    if final.strip():
        click.echo(final)

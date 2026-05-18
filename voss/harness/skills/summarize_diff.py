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

from ..agent import run_turn

_PROMPT = (
    "Summarize the current working-tree changes as a pull-request "
    "description.\n\n"
    "First call the `git_diff` tool to obtain the unstaged diff. Then write "
    "the PR description as your final answer.\n\n"
    "Output ONLY structured markdown with EXACTLY these three sections, in "
    "this order, using these exact headers:\n"
    "## Title\n"
    "(a one-line summary)\n"
    "## Summary\n"
    "(a short paragraph on why the change exists)\n"
    "## Changes\n"
    "(a bullet list of the notable changes)\n\n"
    "Do not write or modify any file. The markdown response is the only "
    "deliverable."
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
    asyncio.run(
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

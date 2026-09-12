"""
`add-test`: agentic, mutating pytest-test generator
Agentic drives a model turn via `run_turn`. Mutating (
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from voss.template_render import render_package_template

from ..agent import run_turn

_PROMPT = render_package_template(
    "voss",
    "templates/prompts/skill_add_test.txt.jinja",
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

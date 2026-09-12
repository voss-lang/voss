"""
`port-py-to-voss`: agentic, mutating Python→.voss translator
Agentic drives a model turn via `run_turn`. Mutating (
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import click

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
    source: str | None = None,
) -> None:
    if source is None:
        click.echo("usage: port-py-to-voss <source.py>", err=True)
        return

    prompt = (
        "Translate a Python source file to the Voss language.\n\n"
        f"1. Read the Python source at the project-relative path `{source}` "
        "using the available read tool.\n"
        "2. Translate it to `.voss`, choosing the closest of these sample "
        "shapes as a guide: classify (simple fn + probable<T> + confidence "
        "gate), support (prompt + memory.episodic + match similar), or "
        "research (agent + spawn + gather + within/fallback + try/catch).\n"
        "3. Write the translated Voss to a sibling path with the same stem "
        "and a `.voss` extension, INSIDE the project root, using the "
        "`fs_write` tool.\n"
        "4. Do NOT write anywhere outside the project directory. Do NOT use "
        "any shell command. The output must be valid enough that "
        "`voss check` succeeds on it.\n\n"
        "When the .voss file is written, you are done."
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

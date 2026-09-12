"""
Skill-execution bridge for the MCP server
Thin adapter: given a skill id + `args: list[str]`, build a `SimpleNamespace`
"""
from __future__ import annotations

import asyncio
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable


def make_skill_dispatch(
    *,
    cwd: Path,
    provider,
    history,
    record,
    renderer,
    tools,
    gate,
    skill_registry,
) -> Callable[[str, list[str]], Awaitable[str]]:
    async def dispatch(name: str, args: list[str]) -> str:
        entry = skill_registry.get(name)
        if entry is None:
            raise KeyError(f"unknown skill: {name}")
        ctx = SimpleNamespace(
            cwd=cwd,
            provider=provider,
            history=history,
            record=record,
            renderer=renderer,
            tools=tools,
            gate=gate,
            skill_registry=skill_registry,
        )
        buf = io.StringIO()

        def _run() -> None:
            with contextlib.redirect_stdout(buf):
                entry.handler(ctx, list(args))

        # run the sync handler in a worker thread so a blocking
        # asyncio.run(run_turn(...)) inside an agentic skill cannot deadlock
        # the server's event loop
        await asyncio.to_thread(_run)
        return buf.getvalue()

    return dispatch

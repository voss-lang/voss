#!/usr/bin/env python
"""DIAG-A: direct agent-loop / provider instrumentation for the bare-idle bug.

Isolates provider vs loop for the failing task ("Analyze the codebase in depth",
mode=plan, codex-oauth). Scratch diagnostic — NOT shipped, NOT imported by voss/.

Run:  .venv/bin/python scripts/diag_plan_direct.py [--full]

Probes (decisive data printed first):
  1. provider.stream(REPRO_MODEL)   — what the SERVER actually sent. Captures the
     raw provider response / error for a non-gpt-5 model on the codex backend.
  2. provider.stream(CONTROL_MODEL) — gpt-5.5 (valid codex model). Captures a real
     parsed Plan: steps / confidence / open_question / final_when_done.
  3. run_turn(REPRO_MODEL) loop     — proves the end-to-end behaviour: does the
     loop raise (swallowed → bare idle) and which renderer events fire?
  --full also runs the run_turn loop on CONTROL_MODEL (slower; real tool reads).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from voss_runtime import get_config

from voss.harness import auth
from voss.harness.agent import Plan, _compose_loop_system, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import (
    Done,
    OpenAIOAuthProvider,
    ParsedPlan,
    TextDelta,
    Usage,
)
from voss.harness.server.renderer import EventBusRenderer
from voss.harness.tools import make_toolset

PROMPT = "Analyze the codebase in depth"
REPRO_MODEL = "claude-sonnet-4-5"  # voss_runtime/_config default_model — what the session used
CONTROL_MODEL = "gpt-5.5"          # ~/.codex/config.toml model — valid for the codex backend


def _provider() -> OpenAIOAuthProvider:
    creds = auth.load_codex()
    if creds is None or not creds.has_oauth:
        sys.exit("no codex-oauth creds (~/.codex/auth.json) — cannot reproduce")
    return OpenAIOAuthProvider(creds)


def _hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}", flush=True)


async def probe_provider(model: str) -> dict:
    """Call provider.stream directly with response_format=Plan; dump everything."""
    _hr(f"PROBE 1/2 — provider.stream  model={model}")
    provider = _provider()
    cwd = Path.cwd()
    loop_system = _compose_loop_system(get_config().max_iterations)
    user_prompt = f"Task:\n{PROMPT}\n\nWorking directory: {cwd}\n"
    messages = [
        {"role": "system", "content": loop_system},
        {"role": "user", "content": user_prompt},
    ]

    raw: list[str] = []
    parsed = None
    usage = None
    done = None
    error = None
    try:
        async for ev in provider.stream(
            messages=messages,
            model=model,
            response_format=Plan,
            temperature=0.2,
            max_tokens=2048,
        ):
            if isinstance(ev, TextDelta):
                raw.append(ev.text)
            elif isinstance(ev, ParsedPlan):
                parsed = ev.plan
            elif isinstance(ev, Usage):
                usage = ev
            elif isinstance(ev, Done):
                done = ev
    except Exception as e:  # noqa: BLE001 — the whole point is to capture it
        error = f"{type(e).__name__}: {e}"
    finally:
        await provider.aclose()

    raw_text = "".join(raw)
    print(f"error              : {error}")
    print(f"raw provider text  : {len(raw_text)} chars")
    if raw_text:
        print(f"  first 800 chars  : {raw_text[:800]!r}")
    print(f"ParsedPlan emitted : {parsed is not None}")
    if parsed is not None:
        print(f"  steps            : {len(parsed.steps)} -> {[s.name for s in parsed.steps]}")
        print(f"  confidence       : {parsed.confidence}")
        print(f"  open_question    : {parsed.open_question!r}")
        print(f"  final_when_done  : {parsed.final_when_done[:400]!r}")
    print(f"usage              : {usage}")
    print(f"done.stop_reason   : {getattr(done, 'stop_reason', None)}")

    return {
        "model": model,
        "error": error,
        "raw_text_len": len(raw_text),
        "raw_text_head": raw_text[:400],
        "parsed_plan": parsed is not None,
        "steps": [s.name for s in parsed.steps] if parsed else None,
        "confidence": parsed.confidence if parsed else None,
        "open_question": parsed.open_question if parsed else None,
        "final_when_done": (parsed.final_when_done[:400] if parsed else None),
        "stop_reason": getattr(done, "stop_reason", None),
    }


async def probe_loop(model: str) -> dict:
    """Drive the real run_turn loop; record whether it raises + which events fire."""
    _hr(f"PROBE 3 — run_turn loop  model={model}")
    provider = _provider()
    cwd = Path.cwd()
    q: asyncio.Queue = asyncio.Queue()
    renderer = EventBusRenderer(q, session_id="diag", loop=None)
    tools = make_toolset(cwd, renderer=renderer)
    gate = PermissionGate(mode="plan", auto_yes=True)

    raised = None
    final = None
    try:
        renderer.show_user(PROMPT)
        result = await run_turn(
            PROMPT,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=model,
            provider=provider,
            permissions=gate,
            session_id="diag",
        )
        final = result.final
    except BaseException as e:  # noqa: BLE001 — capture the swallowed exception
        raised = f"{type(e).__name__}: {e}"
    finally:
        await provider.aclose()

    events: list[str] = []
    while not q.empty():
        events.append(type(q.get_nowait()).__name__)

    final_disp = final if final is None else final[:400]
    print(f"run_turn raised    : {raised}")
    print(f"final              : {final_disp!r}")
    print(f"events emitted     : {events}")
    has_final = "FinalEvent" in events
    has_status = "StatusEvent" in events
    print(f"FinalEvent emitted : {has_final}   StatusEvent emitted: {has_status}")
    print(
        "=> matches bare-idle symptom"
        if (raised and not has_final and not has_status)
        else "=> turn produced output"
    )
    return {
        "model": model,
        "raised": raised,
        "final_head": (final[:400] if final else final),
        "events": events,
        "final_event": has_final,
        "status_event": has_status,
    }


async def main() -> None:
    full = "--full" in sys.argv
    summary: dict = {}
    summary["provider_repro"] = await probe_provider(REPRO_MODEL)
    summary["provider_control"] = await probe_provider(CONTROL_MODEL)
    summary["loop_repro"] = await probe_loop(REPRO_MODEL)
    if full:
        summary["loop_control"] = await probe_loop(CONTROL_MODEL)

    _hr("JSON SUMMARY (for Coordinator)")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

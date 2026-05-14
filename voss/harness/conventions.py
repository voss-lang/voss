"""Convention extraction service: D-09 signal pre-filter + D-10 LLM call + D-11 review UX.

Owned by M8-03 (MEM-04). ConventionCandidate schema and regex constants are
concretely defined here.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter
from typing import Iterable

import click
from pydantic import BaseModel, Field, ValidationError

from voss_runtime.memory import EpisodicMemory


_SIGNAL_RE = re.compile(
    r"\b(?:no,?\s*use|always|never|prefer|let'?s|don'?t)\b",
    re.IGNORECASE,
)

DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 8.0


class ConventionCandidate(BaseModel):
    statement: str = Field(..., min_length=1, max_length=500)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_quote: str = Field(..., min_length=1)
    evidence_turn_idx: int = Field(..., ge=0)


def _turn_role(t) -> str:
    role = getattr(t, "role", None)
    if role is not None:
        return role
    if isinstance(t, dict):
        return t.get("role", "")
    return ""


def _turn_content(t) -> str:
    content = getattr(t, "content", None)
    if content is not None:
        return content
    if isinstance(t, dict):
        return t.get("content", "")
    return ""


def has_signal(turns: Iterable, *, runs=None) -> bool:
    """D-09 + Pitfall 5 quorum.

    Returns True when:
      (a) at least one user turn matches _SIGNAL_RE AND user-turn count >= 2, OR
      (b) at least two runs share a changed file (repeat-edit detection).
    """
    user_turns = [t for t in turns if _turn_role(t) == "user"]
    signal_a = (
        len(user_turns) >= 2
        and any(_SIGNAL_RE.search(_turn_content(t)) for t in user_turns)
    )

    signal_b = False
    if runs:
        counter: Counter = Counter()
        for run in runs:
            changed = getattr(run, "changed", None)
            if changed is None and isinstance(run, dict):
                changed = run.get("changed", [])
            for path in changed or []:
                counter[path] += 1
        signal_b = any(c >= 2 for c in counter.values())

    return signal_a or signal_b


_EXTRACTION_PROMPT = """You are reviewing a coding-agent session for durable user conventions.

A "convention" is a rule, preference, or workflow instruction the USER stated
that should apply to ALL future sessions in this project (not just this one).
Examples: "always use snake_case in Python", "never store secrets in env",
"prefer pytest fixtures over setUp methods".

NOT conventions: one-off facts about this codebase, debugging context,
task-specific instructions, assistant restatements.

Output ONLY a JSON array (no prose, no markdown). Each element is an object
with exactly these fields:
- statement (string, 1-500 chars): the convention restated imperatively
- confidence (float 0.0..1.0): how confident you are this is a durable rule
- evidence_quote (string): verbatim user quote that supports it
- evidence_turn_idx (int >= 0): 0-based index of the user turn in the transcript

Emit [] if no conventions are present.

Transcript:
{transcript}
"""


def _render_transcript(history) -> str:
    if isinstance(history, EpisodicMemory):
        msgs = history.render()
    else:
        msgs = [{"role": _turn_role(t), "content": _turn_content(t)} for t in history]
    lines: list[str] = []
    idx = 0
    for msg in msgs:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"[turn {idx}] user: {content}")
            idx += 1
        else:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def extract_conventions(
    history,
    provider,
    model: str,
    *,
    timeout: float = DEFAULT_EXTRACTION_TIMEOUT_SECONDS,
) -> list[ConventionCandidate]:
    """D-10 LLM call wrapped in asyncio.wait_for(timeout).

    Returns [] on:
      - TimeoutError after `timeout` seconds
      - JSONDecodeError from the provider's response text
      - pydantic ValidationError on any element
      - Any provider exception (logged to stderr).
    """
    transcript = _render_transcript(history)
    prompt = _EXTRACTION_PROMPT.format(transcript=transcript)
    messages = [{"role": "user", "content": prompt}]

    try:
        resp = await asyncio.wait_for(
            provider.complete(messages=messages, model=model),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return []
    except Exception as exc:  # noqa: BLE001
        print(f"conventions extraction provider error: {exc}", file=sys.stderr)
        return []

    text = getattr(resp, "text", None)
    if text is None and isinstance(resp, str):
        text = resp
    if not text:
        return []

    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(raw, list):
        return []

    out: list[ConventionCandidate] = []
    for elem in raw:
        try:
            out.append(ConventionCandidate.model_validate(elem))
        except ValidationError:
            return []
    return out


def review_candidates(
    candidates: list[ConventionCandidate],
    *,
    interactive: bool = True,
    selection: str | None = None,
) -> list[int]:
    """D-11 numbered list UX; returns selected 0-based indices."""
    if not candidates:
        return []

    if not interactive:
        if selection is None:
            return []
        return _parse_selection(selection, len(candidates))

    click.echo("Candidate conventions from this session:")
    for i, c in enumerate(candidates, start=1):
        click.echo(f"  [{i}] {c.statement}  (conf {c.confidence:.2f})")
        click.echo(f'      evidence: "{c.evidence_quote}" (turn {c.evidence_turn_idx})')

    try:
        raw = input('Persist which? (e.g. "1 3", or empty for none): ')
    except (EOFError, KeyboardInterrupt):
        click.echo()
        return []

    return _parse_selection(raw, len(candidates))


def _parse_selection(raw: str, n: int) -> list[int]:
    indices: list[int] = []
    for token in raw.split():
        if not token.strip().isdigit():
            continue
        i = int(token) - 1
        if 0 <= i < n and i not in indices:
            indices.append(i)
    return indices


def run_on_clean_exit(ctx, *, history, record, memory_store) -> int:
    """End-of-session hook; returns count of conventions persisted.

    Reads optional `.voss/config.yml` for `memory.extract_conventions` (default
    True) and `memory.extraction_timeout_seconds` (default 8.0). Wraps all
    work in a top-level try/except so the REPL exit is never blocked.
    """
    from pathlib import Path

    try:
        cwd = getattr(ctx, "cwd", None) or Path(".")
        cfg = _load_memory_config(Path(cwd))
        if not cfg.get("extract_conventions", True):
            return 0
        timeout = float(cfg.get("extraction_timeout_seconds", DEFAULT_EXTRACTION_TIMEOUT_SECONDS))

        turns = list(getattr(history, "turns", history) or [])
        runs = list(getattr(record, "runs", []) or [])
        if not has_signal(turns, runs=runs):
            return 0

        provider = getattr(ctx, "provider", None)
        model = getattr(ctx, "model", None) or getattr(ctx, "default_model", None)
        if provider is None or model is None:
            click.echo("conventions extraction skipped: no provider/model on ctx", err=True)
            return 0

        candidates = asyncio.run(
            extract_conventions(history, provider, model, timeout=timeout)
        )
        if not candidates:
            return 0

        interactive = sys.stdin.isatty()
        selected = review_candidates(
            candidates,
            interactive=interactive,
            selection=getattr(ctx, "persist_conventions_selection", None),
        )

        persisted = 0
        for idx in selected:
            try:
                memory_store.write_convention(candidates[idx], session_id=record.id)
                persisted += 1
            except Exception as exc:  # noqa: BLE001
                click.echo(
                    f"conventions write failed for [{idx + 1}]: {exc}",
                    err=True,
                )
        return persisted
    except Exception as exc:  # noqa: BLE001
        click.echo(f"conventions extraction skipped: {exc}", err=True)
        return 0


def _load_memory_config(cwd) -> dict:
    """Load the optional `.voss/config.yml` memory section; never raises."""
    from pathlib import Path

    config_path = Path(cwd) / ".voss" / "config.yml"
    if not config_path.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:  # noqa: BLE001
        return {}
    memory = data.get("memory") if isinstance(data, dict) else None
    return memory if isinstance(memory, dict) else {}


__all__ = [
    "ConventionCandidate",
    "DEFAULT_EXTRACTION_TIMEOUT_SECONDS",
    "_SIGNAL_RE",
    "extract_conventions",
    "has_signal",
    "review_candidates",
    "run_on_clean_exit",
]

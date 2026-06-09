"""Read-only inspection helpers for persisted Voss run records.

This module intentionally derives views only from fields already saved on
SessionRecord/RunRecord payloads. It does not inspect runtime state, recorder
state, or budget/probable primitives.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voss.harness import session as session_store
from voss.template_render import render_package_template


@dataclass(frozen=True)
class DecisionView:
    index: int
    title: str
    body: str
    confidence: Any
    previous_index: int | None
    next_index: int | None


@dataclass(frozen=True)
class BudgetFrame:
    index: int
    prompt_tokens: int
    completion_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    total_tokens: int
    cumulative_tokens: int
    cost_usd: float
    exit_reason: str | None


def _get(obj: object, key: str, default: Any = None) -> Any:
    """Return a value from a dict or object/dataclass attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def decision_sequence(run: object) -> list[DecisionView]:
    """Return recorded decisions as an ordered sequence, not a DAG."""
    decisions = _get(run, "decisions", []) or []
    last_index = len(decisions) - 1
    out: list[DecisionView] = []
    for index, decision in enumerate(decisions):
        out.append(
            DecisionView(
                index=index,
                title=str(_get(decision, "title", "")),
                body=str(_get(decision, "body", "")),
                confidence=_get(decision, "confidence"),
                previous_index=index - 1 if index > 0 else None,
                next_index=index + 1 if index < last_index else None,
            )
        )
    return out


def budget_timeline(run: object) -> list[BudgetFrame]:
    """Return recorded budget usage as an agent-iteration timeline."""
    iterations = _get(run, "iterations", []) or []
    cumulative_tokens = 0
    out: list[BudgetFrame] = []
    for fallback_index, iteration in enumerate(iterations):
        prompt_tokens = _int(_get(iteration, "prompt_tokens", 0))
        completion_tokens = _int(_get(iteration, "completion_tokens", 0))
        cache_creation_input_tokens = _int(
            _get(iteration, "cache_creation_input_tokens", 0)
        )
        cache_read_input_tokens = _int(_get(iteration, "cache_read_input_tokens", 0))
        total_tokens = (
            prompt_tokens
            + completion_tokens
            + cache_creation_input_tokens
            + cache_read_input_tokens
        )
        cumulative_tokens += total_tokens
        out.append(
            BudgetFrame(
                index=_int(_get(iteration, "index", fallback_index)),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_creation_input_tokens=cache_creation_input_tokens,
                cache_read_input_tokens=cache_read_input_tokens,
                total_tokens=total_tokens,
                cumulative_tokens=cumulative_tokens,
                cost_usd=_float(_get(iteration, "cost_usd", 0.0)),
                exit_reason=_get(iteration, "exit_reason"),
            )
        )
    return out


def render_decision_sequence(run: object, decision_index: int | None = None) -> str:
    """Render recorded decisions as plain text."""
    sequence = decision_sequence(run)
    if not sequence:
        return "No recorded decisions."

    if decision_index is None:
        return render_package_template(
            "voss",
            "templates/inspect/decision_sequence.txt.jinja",
            {
                "heading": f"Recorded decision sequence ({len(sequence)} decisions)",
                "previous_label": None,
                "next_label": None,
                "decisions": [_decision_context(view) for view in sequence],
            },
        ).removesuffix("\n")

    selected = _find_decision(sequence, decision_index)
    return render_package_template(
        "voss",
        "templates/inspect/decision_sequence.txt.jinja",
        {
            "heading": f"Recorded decision {selected.index}",
            "previous_label": _context_label(
                "Previous", sequence, selected.previous_index
            ),
            "next_label": _context_label("Next", sequence, selected.next_index),
            "decisions": [_decision_context(selected)],
        },
    ).removesuffix("\n")


def render_budget_timeline(run: object) -> str:
    """Render recorded per-iteration budget usage as plain text."""
    frames = budget_timeline(run)
    if not frames:
        return "No recorded budget timeline."

    rows = []
    for frame in frames:
        exit_reason = frame.exit_reason or "-"
        if frame.exit_reason == "budget":
            exit_reason = "budget (budget exhausted)"
        rows.append({"frame": frame, "exit_reason": exit_reason})
    return render_package_template(
        "voss",
        "templates/inspect/budget_timeline.txt.jinja",
        {"frames": rows},
    ).removesuffix("\n")


def load_run(cwd: Path, session_id_or_name: str, run_index: int = -1) -> object:
    """Load one persisted run from a cwd-scoped session."""
    record, _history = session_store.load(session_id_or_name, cwd=cwd)
    runs = _get(record, "runs", []) or []
    if not runs:
        raise IndexError(f"session {session_id_or_name!r} has no runs")
    try:
        return runs[run_index]
    except IndexError as exc:
        raise IndexError(
            f"run_index {run_index} out of range for session {session_id_or_name!r}"
        ) from exc


def _find_decision(sequence: list[DecisionView], decision_index: int) -> DecisionView:
    for view in sequence:
        if view.index == decision_index:
            return view
    raise IndexError(f"decision_index {decision_index} out of range")


def _decision_context(view: DecisionView) -> dict[str, Any]:
    return {
        "index": view.index,
        "title": view.title or "(untitled decision)",
        "confidence": _format_confidence(view.confidence),
        "previous": _format_index(view.previous_index),
        "next": _format_index(view.next_index),
        "body": view.body,
    }


def _context_label(
    label: str, sequence: list[DecisionView], index: int | None
) -> str:
    if index is None:
        return f"{label}: none"
    view = _find_decision(sequence, index)
    return f"{label}: [{view.index}] {view.title or '(untitled decision)'}"


def _format_confidence(confidence: Any) -> str:
    if confidence is None:
        return "unknown"
    return str(confidence)


def _format_index(index: int | None) -> str:
    if index is None:
        return "none"
    return str(index)


def _int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


__all__ = [
    "BudgetFrame",
    "DecisionView",
    "_get",
    "budget_timeline",
    "decision_sequence",
    "load_run",
    "render_budget_timeline",
    "render_decision_sequence",
]

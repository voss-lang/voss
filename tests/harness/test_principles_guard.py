"""V2-03 guards (VPRIN-03 + schema-freeze hard constraint).

GUARD 1 — principles are OPAQUE text: no harness/agent code path may branch
(if / comparison / match-case) on an individual principle key or default text.
The literal keys/texts may appear only in DATA positions (the DEFAULT_PRINCIPLES
constant, dict/tuple construction), never as a conditional operand.

GUARD 2 — schema freeze: RunRecord / SessionRecord / BudgetScope field-name
sets are frozen here. V2 must add ZERO fields (audit recording of principles is
V9). Any add/remove fails, protecting the O1/V4 redaction invariant.
"""
from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

from voss.harness.principles import DEFAULT_PRINCIPLES

_REPO = Path(__file__).resolve().parents[2]
_SCANNED = (
    _REPO / "voss" / "harness" / "principles.py",
    _REPO / "voss" / "harness" / "agent.py",
)

_FORBIDDEN = {k for k, _ in DEFAULT_PRINCIPLES} | {t for _, t in DEFAULT_PRINCIPLES}


def _branch_hits(path: Path) -> list[tuple[int, str]]:
    """Return (lineno, literal) for any principle key/text used as a branch
    operand (Compare operand or match-case value)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for op in operands:
                if (
                    isinstance(op, ast.Constant)
                    and isinstance(op.value, str)
                    and op.value in _FORBIDDEN
                ):
                    hits.append((node.lineno, op.value))
        elif isinstance(node, ast.Match):
            for case in node.cases:
                for pat in ast.walk(case.pattern):
                    if (
                        isinstance(pat, ast.MatchValue)
                        and isinstance(pat.value, ast.Constant)
                        and isinstance(pat.value.value, str)
                        and pat.value.value in _FORBIDDEN
                    ):
                        hits.append((pat.lineno, pat.value.value))
    return hits


def test_no_control_flow_branches_on_principles() -> None:
    all_hits: dict[str, list[tuple[int, str]]] = {}
    for path in _SCANNED:
        hits = _branch_hits(path)
        if hits:
            all_hits[str(path.relative_to(_REPO))] = hits
    assert not all_hits, f"principle key/text used in a branch (must be opaque): {all_hits}"


# ---- GUARD 2: schema freeze ------------------------------------------------

_RUN_RECORD_FIELDS = {
    "id", "started_at", "ended_at", "goal", "plan", "inspected", "changed",
    "avoided", "assumptions", "decisions", "risks", "validation", "failures",
    "diff_summary", "follow_ups", "cost_usd", "iterations", "iteration_count",
    "exit_reason", "iteration_total_prompt_tokens",
    "iteration_total_completion_tokens", "skill_events", "scope_denials",
    "capability_invocations",
}

_SESSION_RECORD_FIELDS = {
    "id", "name", "cwd", "model", "started_at", "updated_at", "total_cost_usd",
    "turns", "runs", "parent_id", "parent_turn_index",
}

_BUDGET_SCOPE_FIELDS = {
    "token_limit", "latency_ms", "cost_usd", "name", "tokens_so_far",
    "cost_so_far", "_start", "_token",
}


def test_run_record_schema_frozen() -> None:
    from voss.harness.session import RunRecord

    assert {f.name for f in dataclasses.fields(RunRecord)} == _RUN_RECORD_FIELDS


def test_session_record_schema_frozen() -> None:
    from voss.harness.session import SessionRecord

    assert {f.name for f in dataclasses.fields(SessionRecord)} == _SESSION_RECORD_FIELDS


def test_budget_scope_schema_frozen() -> None:
    from voss_runtime.budget import BudgetScope

    assert {f.name for f in dataclasses.fields(BudgetScope)} == _BUDGET_SCOPE_FIELDS

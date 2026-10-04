"""Paired A/B comparison of two eval runs."""
from __future__ import annotations

import math
from collections import defaultdict

from .retrieval import paired_bootstrap

CAVEAT = "A 30-task pilot cannot establish general non-regression."


def task_score(row: dict) -> int:
    return int(row.get("gate_pass") is True and not row.get("capped"))


def _by_task(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    return grouped


def compare(a_rows: list[dict], b_rows: list[dict]) -> dict:
    a, b = _by_task(a_rows), _by_task(b_rows)
    one_sided = sorted(set(a) ^ set(b))
    if one_sided:
        raise ValueError(f"tasks present on one side only: {', '.join(one_sided)}")
    skipped = {t for t in a if any(r.get("skipped") for r in a[t] + b[t])}
    tasks = sorted(set(a) - skipped)
    if not tasks:
        raise ValueError("no comparable tasks")

    a_first = [task_score(a[t][0]) for t in tasks]
    b_first = [task_score(b[t][0]) for t in tasks]
    diffs = [float(y - x) for x, y in zip(a_first, b_first)]
    ci_low, ci_high = paired_bootstrap(diffs)

    regressions, unconfirmed = [], []
    for t in tasks:
        if all(map(task_score, a[t])) and not any(map(task_score, b[t])):
            (regressions if min(len(a[t]), len(b[t])) >= 2 else unconfirmed).append(t)

    a_only = [t for t, d in zip(tasks, diffs) if d < 0]
    b_only = [t for t, d in zip(tasks, diffs) if d > 0]
    return {
        "n_tasks": len(tasks),
        "n_skipped": len(skipped),
        "a_pass_rate": sum(a_first) / len(tasks),
        "b_pass_rate": sum(b_first) / len(tasks),
        "mean_diff": math.fsum(diffs) / len(tasks),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "a_only": a_only,
        "b_only": b_only,
        "disagreements": sorted(a_only + b_only),
        "regressions": regressions,
        "unconfirmed": unconfirmed,
        "no_difference": not any(diffs),
        "passed": not regressions and not unconfirmed,
    }


def _tasks(ids: list[str]) -> str:
    return ", ".join(ids) or "none"


def render(result: dict, *, a_label: str, b_label: str) -> str:
    lines = [
        f"## {a_label} vs {b_label}",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Tasks compared | {result['n_tasks']} ({result['n_skipped']} skipped) |",
        f"| {a_label} pass rate | {result['a_pass_rate']:.3f} |",
        f"| {b_label} pass rate | {result['b_pass_rate']:.3f} |",
        f"| Mean difference ({b_label} - {a_label}) | {result['mean_diff']:+.3f} |",
        f"| 95% interval | [{result['ci_low']:+.3f}, {result['ci_high']:+.3f}] |",
        "",
        f"- Passed only with {a_label}: {_tasks(result['a_only'])}",
        f"- Passed only with {b_label}: {_tasks(result['b_only'])}",
        f"- Reproducible regressions: {_tasks(result['regressions'])}",
        f"- Unconfirmed disagreements (never rerun): {_tasks(result['unconfirmed'])}",
        "",
    ]
    if result["no_difference"]:
        lines.append("Result: no observed difference on these tasks.")
    lines.append(f"Task-impact gate: {'PASS' if result['passed'] else 'FAIL'}")
    lines.append(CAVEAT)
    return "\n".join(lines) + "\n"

"""Paired A/B comparison of two eval runs."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

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


def run_ab(
    *,
    suite: str,
    setting: str,
    a: str,
    b: str,
    out: Path,
    metadata: dict | None = None,
    **run_suite_kwargs,
) -> Path:
    from .runner import run_suite
    from .summary import _read_rows

    def run(value: str, dest: Path, **kwargs) -> list[dict]:
        run_suite(
            suite=suite,
            out=dest,
            overrides={setting: value},
            judge=False,
            **run_suite_kwargs,
            **kwargs,
        )
        return _read_rows(dest / "runs.jsonl")

    a_rows = run(a, out / "a")
    b_rows = run(b, out / "b")
    a_by, b_by = _by_task(a_rows), _by_task(b_rows)
    for task in sorted(a_by.keys() & b_by.keys()):
        if task_score(a_by[task][0]) != task_score(b_by[task][0]):
            a_rows += run(a, out / "rerun" / "a" / task, task=task)
            b_rows += run(b, out / "rerun" / "b" / task, task=task)

    result = compare(a_rows, b_rows)
    payload = {
        "schema_version": 1,
        "setting": setting,
        "a": a,
        "b": b,
        **(metadata or {}),
        "a_judgment_receipts": sum(r.get("judgment_receipt_count", 0) for r in a_rows),
        "b_judgment_receipts": sum(r.get("judgment_receipt_count", 0) for r in b_rows),
        "compare": result,
        "passed": result["passed"],
    }
    (out / "ab.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "ab.md").write_text(
        render(result, a_label=f"{setting}={a}", b_label=f"{setting}={b}")
    )
    return out

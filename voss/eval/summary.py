"""Markdown summary generator + Pearson r aggregator (M5 D-15, EVAL-04)."""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from voss.template_render import render_package_template


def _read_rows(jsonl_path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in jsonl_path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _pearson(rows: list[dict]) -> tuple[float | None, int]:
    pairs = [
        (row["confidence"], 1.0 if row["success"] else 0.0)
        for row in rows
        if row.get("confidence") is not None and row.get("success") is not None
    ]
    if len(pairs) < 2:
        return None, len(pairs)

    confidences, successes = zip(*pairs)
    if len(set(confidences)) < 2 or len(set(successes)) < 2:
        return None, len(pairs)
    return statistics.correlation(confidences, successes), len(pairs)


def _mean_cost(rows: list[dict]) -> float | None:
    costs = [row["cost_usd"] for row in rows if row.get("cost_usd") is not None]
    return sum(costs) / len(costs) if costs else None


def _common_value(rows: list[dict], key: str) -> str:
    values = {row.get(key) for row in rows}
    if not values:
        return "n/a"
    if len(values) == 1:
        return str(next(iter(values)))
    return "mixed"


def write_summary(jsonl_path: Path, summary_path: Path) -> Path:
    rows = _read_rows(jsonl_path)
    by_task: defaultdict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)

    total = len(rows)
    scored = [row for row in rows if row.get("success") is not None]
    passes = sum(1 for row in scored if row["success"])
    overall_rate = passes / len(scored) if scored else 0.0

    gate_rows = [r for r in rows if r.get("gate_pass") is not None]
    gate_passes = sum(1 for r in gate_rows if r["gate_pass"])
    gate_rate = gate_passes / len(gate_rows) if gate_rows else None

    judge_rows = [
        r for r in rows if r.get("judge_verdict") not in (None, "skipped", "error")
    ]
    judge_passes = sum(1 for r in judge_rows if r.get("judge_verdict") == "pass")
    judge_rate = judge_passes / len(judge_rows) if judge_rows else None

    mean_cost = _mean_cost(rows)
    corr, n = _pearson(rows)
    provider = _common_value(rows, "provider")
    model = _common_value(rows, "model")

    tasks: list[dict[str, str | int]] = []
    for task_id in sorted(by_task):
        task_rows = by_task[task_id]
        task_scored = [row for row in task_rows if row.get("success") is not None]
        task_passes = sum(1 for row in task_scored if row["success"])
        rate = f"{task_passes / len(task_scored):.0%}" if task_scored else "n/a"
        task_gate_rows = [row for row in task_rows if row.get("gate_pass") is not None]
        task_gate_passes = sum(1 for row in task_gate_rows if row["gate_pass"])
        gate_pass_rate = (
            f"{task_gate_passes / len(task_gate_rows):.0%}" if task_gate_rows else "n/a"
        )
        task_mean_cost = _mean_cost(task_rows)
        cost_s = f"${task_mean_cost:.4f}" if task_mean_cost is not None else "n/a"
        tasks.append(
            {
                "id": task_id,
                "runs": len(task_rows),
                "gate_pass_rate": gate_pass_rate,
                "pass_rate": rate,
                "mean_cost": cost_s,
            }
        )

    rendered = render_package_template(
        "voss",
        "templates/eval/summary.md.jinja",
        {
            "run_name": jsonl_path.parent.name,
            "total": total,
            "provider": provider,
            "model": model,
            "overall_rate": f"{overall_rate:.0%}",
            "passes": passes,
            "scored_count": len(scored),
            "gate_rate": f"{gate_rate:.0%}" if gate_rate is not None else "n/a",
            "gate_passes": gate_passes,
            "gate_total": len(gate_rows),
            "judge_rate": f"{judge_rate:.0%}" if judge_rate is not None else "n/a",
            "judge_passes": judge_passes,
            "judge_total": len(judge_rows),
            "mean_cost": f"${mean_cost:.4f}" if mean_cost is not None else "n/a",
            "conf_corr_r": f"{corr:.3f}" if corr is not None else "n/a",
            "corr_n": n,
            "tasks": tasks,
        },
    )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(rendered)
    return summary_path


__all__ = ["write_summary", "_pearson", "_read_rows"]

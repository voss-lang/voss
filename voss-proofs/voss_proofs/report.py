"""Metrics and Markdown evidence reports. Raw dimensions only, no composite score."""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from .spec import RunRecord
from .store import read_runs

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def summarize(records: list[RunRecord]) -> dict[str, dict]:
    by_config: dict[str, list[RunRecord]] = defaultdict(list)
    for r in records:
        by_config[r.config.name].append(r)
    out = {}
    for name, rows in sorted(by_config.items()):
        done = [r for r in rows if not r.skipped]
        graded = [r for r in done if r.verified is not None]
        k = sum(r.verified for r in graded)
        costs = [r.usage.cost_usd for r in done if r.usage.cost_usd is not None]
        durations = [r.duration_s for r in done if r.duration_s is not None]
        out[name] = {
            "adapter": rows[0].config.adapter,
            "live": rows[0].live,
            "runs": len(rows),
            "skipped": len(rows) - len(done),
            "graded": len(graded),
            "verified": k,
            "rate": k / len(graded) if graded else None,
            "ci95": wilson(k, len(graded)) if graded else None,
            "false_claims": sum(1 for r in graded if r.claimed_complete and not r.verified),
            "claims": sum(1 for r in done if r.claimed_complete),
            "cost_known": len(costs),
            "cost_mean": sum(costs) / len(costs) if costs else None,
            "duration_mean": sum(durations) / len(durations) if durations else None,
            "errors": sum(1 for r in done if r.errors),
        }
    return out


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render(records: list[RunRecord], title: str) -> str:
    summary = summarize(records)
    lines = [f"# {title}", ""]
    lines.append(f"{len(records)} runs, {len({r.scenario_id for r in records})} scenarios, "
                 f"evaluator `{records[0].evaluator_version if records else 'n/a'}`.")
    lines.append("")
    for live in (False, True):
        names = [n for n, s in summary.items() if s["live"] is live]
        if not names:
            continue
        lines += [f"## {'Live-model' if live else 'Deterministic'} configurations", ""]
        if not live:
            lines += ["These runs used no live model. They test the benchmark and pipeline, "
                      "not model capability.", ""]
        lines += [
            "| config | adapter | runs | skipped | verified / graded | rate | 95% CI (Wilson) "
            "| claimed but not verified | mean cost | mean duration |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for n in names:
            s = summary[n]
            ci = "n/a" if s["ci95"] is None else f"{_pct(s['ci95'][0])}–{_pct(s['ci95'][1])}"
            cost = (f"${s['cost_mean']:.4f} ({s['cost_known']} known)" if s["cost_mean"] is not None
                    else "unknown")
            dur = "n/a" if s["duration_mean"] is None else f"{s['duration_mean']:.2f}s"
            lines.append(
                f"| {n} | {s['adapter']} | {s['runs']} | {s['skipped']} | {s['verified']} / "
                f"{s['graded']} | {_pct(s['rate'])} | {ci} | {s['false_claims']} of {s['claims']} claims "
                f"| {cost} | {dur} |"
            )
        if live:
            models = {n: sorted({r.model or "unknown" for r in records
                                 if r.config.name == n and not r.skipped}) for n in names}
            if len({m for ms in models.values() for m in ms}) > 1:
                lines += ["", "**Models differ across live configs**, so a difference between them mixes model "
                          "and architecture: " + "; ".join(f"{n}: {', '.join(ms)}" for n, ms in models.items()) + "."]
        lines.append("")

    configs = list(summary)
    cells: dict[tuple[str, str], list[RunRecord]] = defaultdict(list)
    for r in records:
        cells[(r.scenario_id, r.config.name)].append(r)
    lines += ["## Per scenario (verified / graded)", "",
              "| scenario | category | " + " | ".join(configs) + " |",
              "|---|---|" + "---|" * len(configs)]
    for sid in sorted({r.scenario_id for r in records}):
        cat = next((r.category for r in records if r.scenario_id == sid), None) or ""
        row = []
        for c in configs:
            rs = cells.get((sid, c), [])
            if rs and all(r.skipped for r in rs):
                row.append("skipped")
                continue
            graded = [r for r in rs if r.verified is not None]
            row.append(f"{sum(r.verified for r in graded)}/{len(graded)}" if graded else "–")
        lines.append(f"| {sid} | {cat} | " + " | ".join(row) + " |")
    lines.append("")

    missing = []
    skipped = sorted({f"{r.scenario_id}: {r.skip_reason}" for r in records if r.skipped})
    if skipped:
        missing.append("Skipped (not counted as failures): " + "; ".join(skipped) + ".")
    unknown_cost = sum(1 for r in records if not r.skipped and r.usage.cost_usd is None)
    if unknown_cost:
        missing.append(f"{unknown_cost} runs have unknown cost (recorded as missing, not zero).")
    errored = [r for r in records if r.errors]
    for r in errored[:10]:
        missing.append(f"{r.scenario_id} x {r.config.name}#{r.run_idx}: {'; '.join(r.errors)[:200]}")
    if missing:
        lines += ["## Missing data and errors", ""] + [f"- {m}" for m in missing] + [""]
    lines += ["## Reading this report", "",
              "- *verified* means every visible, hidden and scope check passed. A model "
              "judgment never overrides a failing check.",
              "- *claimed but not verified* counts runs where the system reported completion "
              "but the checks disagreed.",
              "- The confidence intervals cover sampling error only. They don't cover benchmark "
              "representativeness, and n is small."]
    return "\n".join(lines) + "\n"


def write_report(results: Path) -> Path:
    records = read_runs(results)
    out = results / "report.md"
    out.write_text(render(records, f"VossProofs report: {results.name}"))
    return out


def outcome_key(r: RunRecord) -> tuple:
    return (
        r.skipped, r.verified, r.claimed_complete, r.exit_reason,
        tuple((c.name, c.kind, c.passed) for c in r.checks),
        r.artifacts.get("diff"),
    )


def compare(a: list[RunRecord], b: list[RunRecord]) -> list[str]:
    """Outcome differences between two experiments (timings and ids excluded)."""
    def index(rs):
        return {(r.scenario_id, r.config.name, r.run_idx): outcome_key(r) for r in rs}
    ia, ib = index(a), index(b)
    diffs = []
    for key in sorted(set(ia) | set(ib)):
        if ia.get(key) != ib.get(key):
            diffs.append(f"{key[0]} x {key[1]}#{key[2]}: {ia.get(key)} != {ib.get(key)}")
    return diffs

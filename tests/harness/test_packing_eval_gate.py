"""V18 VOPT-07: M5 quality-preservation eval gate (GREEN targets, Plan 05).

Token metric note (Plan 05 Task 1): runs.jsonl rows now carry an additive
`input_tokens` field summed from per-iteration prompt_tokens, so the
mean input-token half of VOPT-07 is measured from a real figure (the
Plan-01 TODO(Plan 05) marker is resolved — no inference from cost).

Biting proof note (RESEARCH Assumption A9, encoded in V18-05-PLAN Task 2):
the hermetic stub golden suite stays below recent_full_k iterations, so
even an over-aggressive profile (recent_full_k=1) cannot regress it.
Per the plan's explicit fallback, the biting test asserts the gate's
rejection clauses directly against a synthesized regressed on/off pair —
the requirement is that a regressing profile is PROVABLY rejected, not
that K=1 specifically regresses the stub suite.
"""
from __future__ import annotations

import json
from pathlib import Path

TOLERANCE = 0.05


def _success_rate(runs_path: Path) -> float:
    rows = [json.loads(line) for line in runs_path.read_text().splitlines() if line.strip()]
    assert rows, f"no eval rows at {runs_path}"
    return sum(1 for r in rows if r["success"] is True) / len(rows)


def test_quality_preservation_gate(tmp_path, monkeypatch) -> None:
    """VOPT-07: golden-suite success with packing on >= off − TOLERANCE."""
    from voss.harness.packing_eval import run_packing_gate

    monkeypatch.delenv("VOSS_NO_PACK", raising=False)
    verdict = run_packing_gate(
        suite="golden", stub=True, out_dir=tmp_path, tolerance=TOLERANCE
    )

    assert verdict.passed, verdict
    assert verdict["success_on"] >= verdict["success_off"] - TOLERANCE
    # input_tokens is a real measured field in both runs.jsonl files.
    on_rows = [
        json.loads(line)
        for line in (tmp_path / "on" / "runs.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert all("input_tokens" in r for r in on_rows)
    assert _success_rate(tmp_path / "on" / "runs.jsonl") >= (
        _success_rate(tmp_path / "off" / "runs.jsonl") - TOLERANCE
    )


def test_aggressive_profile_fails_gate() -> None:
    """VOPT-07 biting gate: a regressing profile is provably REJECTED.

    Synthesized on/off pair representing what an over-aggressive profile
    (recent_full_k=1, digest_cutoff_m=2) produces on a real history: one
    golden task drops. The gate must return passed=False — proving it is
    enforced, not decorative.
    """
    from voss.harness.packing_eval import compare_runs

    off_rows = [
        {"success": True, "input_tokens": 9000},
        {"success": True, "input_tokens": 9000},
    ]
    regressed_on = [
        {"success": False, "input_tokens": 3000},
        {"success": True, "input_tokens": 3000},
    ]
    verdict = compare_runs(regressed_on, off_rows, tolerance=TOLERANCE)
    assert verdict["passed"] is False, "gate must reject a success regression"

    # Token-inflation clause also bites: success held but tokens UP -> fail.
    inflated_on = [
        {"success": True, "input_tokens": 12000},
        {"success": True, "input_tokens": 12000},
    ]
    verdict = compare_runs(inflated_on, off_rows, tolerance=TOLERANCE)
    assert verdict["passed"] is False, "gate must reject token inflation"

    # And the healthy case still passes (success held, tokens down).
    healthy_on = [
        {"success": True, "input_tokens": 5000},
        {"success": True, "input_tokens": 5000},
    ]
    assert compare_runs(healthy_on, off_rows, tolerance=TOLERANCE)["passed"] is True

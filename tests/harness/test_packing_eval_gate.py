"""V18-01 Wave-1 RED scaffold: M5 quality-preservation eval gate (VOPT-07).

RED until Plan 05: `voss.harness.packing_eval.compare_runs` does not exist
(ImportError). No non-strict xfail.

NOTE (verified runner.py:358-377): runs.jsonl rows carry success /
cost_usd / judge_verdict but NO prompt_tokens field today. The
"mean input tokens drop" half of VOPT-07 must be sourced by Plan 05 —
either extend the eval row or read the persisted SessionRecord iterations.
# TODO(Plan 05): assert mean input-token reduction once eval row carries tokens
"""
from __future__ import annotations

import json
from pathlib import Path

TOLERANCE = 0.05


def _success_rate(runs_path: Path) -> float:
    rows = [json.loads(line) for line in runs_path.read_text().splitlines() if line.strip()]
    assert rows, f"no eval rows at {runs_path}"
    return sum(1 for r in rows if r["success"]) / len(rows)


def test_quality_preservation_gate(tmp_path, monkeypatch) -> None:
    """VOPT-07: golden-suite success with packing on >= off − TOLERANCE."""
    from voss.harness.packing_eval import compare_runs  # RED until Plan 05
    from voss.eval.runner import run_suite

    monkeypatch.setenv("VOSS_NO_PACK", "1")
    run_suite(suite="golden", stub=True, out=tmp_path / "off")
    monkeypatch.delenv("VOSS_NO_PACK")
    run_suite(suite="golden", stub=True, out=tmp_path / "on")

    on_runs = tmp_path / "on" / "runs.jsonl"
    off_runs = tmp_path / "off" / "runs.jsonl"
    assert _success_rate(on_runs) >= _success_rate(off_runs) - TOLERANCE

    verdict = compare_runs(on=on_runs, off=off_runs, tolerance=TOLERANCE)
    assert verdict.passed


def test_aggressive_profile_fails_gate(tmp_path, monkeypatch) -> None:
    """VOPT-07 biting gate: an over-aggressive profile must be REJECTED.

    recent_full_k=1 / digest_cutoff_m=2 (RESEARCH Assumption A9) starves the
    replay tail; the gate proves it bites by failing this profile rather
    than waving everything through.
    """
    from voss.harness.packing_eval import compare_runs  # RED until Plan 05
    from voss.eval.runner import run_suite

    monkeypatch.setenv("VOSS_NO_PACK", "1")
    run_suite(suite="golden", stub=True, out=tmp_path / "off")
    monkeypatch.delenv("VOSS_NO_PACK")
    monkeypatch.setenv("VOSS_PACK_RECENT_K", "1")
    monkeypatch.setenv("VOSS_PACK_DIGEST_M", "2")
    run_suite(suite="golden", stub=True, out=tmp_path / "aggressive")

    verdict = compare_runs(
        on=tmp_path / "aggressive" / "runs.jsonl",
        off=tmp_path / "off" / "runs.jsonl",
        tolerance=TOLERANCE,
    )
    assert not verdict.passed, "gate must reject the over-aggressive profile"

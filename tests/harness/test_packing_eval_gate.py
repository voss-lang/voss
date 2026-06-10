"""V18 VOPT-07: M5 quality-preservation eval gate.

Token metric note: runs.jsonl rows carry an additive `input_tokens` field
summed from per-iteration prompt_tokens, so the mean input-token half of
VOPT-07 is measured from a real figure.

Biting proof note (RESEARCH Assumption A9, encoded in V18-05-PLAN Task 2):
the hermetic stub golden suite stays below recent_full_k iterations, so
even an over-aggressive profile (recent_full_k=1) cannot regress it.
The biting tests assert the rejection clauses directly against synthesized
on/off pairs so the gate cannot pass on a failed or no-savings run.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

TOLERANCE = 0.05


def _success_rate(runs_path: Path) -> float:
    rows = [
        json.loads(line)
        for line in runs_path.read_text().splitlines()
        if line.strip()
    ]
    assert rows, f"no eval rows at {runs_path}"
    return sum(1 for r in rows if r["success"] is True) / len(rows)


def test_quality_preservation_gate_rejects_no_savings(tmp_path, monkeypatch) -> None:
    """VOPT-07: the real gate rejects a no-savings stub run."""
    from voss.harness.packing_eval import run_packing_gate

    monkeypatch.delenv("VOSS_NO_PACK", raising=False)
    verdict = run_packing_gate(
        suite="golden", stub=True, out_dir=tmp_path, tolerance=TOLERANCE
    )

    assert verdict.passed is False
    assert verdict["token_reduction"] <= 0
    # input_tokens is a real measured field in both runs.jsonl files.
    on_rows = [
        json.loads(line)
        for line in (tmp_path / "on" / "runs.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert all("input_tokens" in r for r in on_rows)
    assert _success_rate(tmp_path / "off" / "runs.jsonl") == verdict["success_off"]


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


def test_failed_baseline_cannot_pass_gate() -> None:
    """VOPT-07: identical failed runs are not a valid quality-preservation pass."""
    from voss.harness.packing_eval import compare_runs

    rows = [
        {"success": False, "input_tokens": 1000},
        {"success": None, "input_tokens": 1000},
    ]

    verdict = compare_runs(rows, rows, tolerance=TOLERANCE)

    assert verdict["passed"] is False
    assert verdict["baseline_ok"] is False


def test_equal_tokens_cannot_pass_gate() -> None:
    """VOPT-07: success parity without token reduction is not a savings gate pass."""
    from voss.harness.packing_eval import compare_runs

    off_rows = [{"success": True, "input_tokens": 1000}]
    on_rows = [{"success": True, "input_tokens": 1000}]

    verdict = compare_runs(on_rows, off_rows, tolerance=TOLERANCE)

    assert verdict["passed"] is False
    assert verdict["tokens_ok"] is False


def test_run_packing_gate_can_inject_profile(tmp_path, monkeypatch) -> None:
    """VOPT-07: aggressive profiles can be exercised through the gate driver."""
    from voss.eval import runner
    from voss.harness.context_allocator import PackingProfile
    from voss.harness.packing_eval import run_packing_gate

    calls: list[dict] = []

    def fake_run_suite(*, out, **kwargs):
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        config_text = (
            Path(os.environ["XDG_CONFIG_HOME"]) / "voss" / "config.toml"
        ).read_text()
        is_off = os.environ.get("VOSS_NO_PACK") == "1"
        calls.append({"is_off": is_off, "config": config_text, "kwargs": kwargs})
        row = {
            "success": True,
            "input_tokens": 900 if is_off else 400,
        }
        (out / "runs.jsonl").write_text(json.dumps(row) + "\n")

    monkeypatch.setattr(runner, "run_suite", fake_run_suite)

    verdict = run_packing_gate(
        out_dir=tmp_path,
        profile=PackingProfile(recent_full_k=1, digest_cutoff_m=2),
    )

    assert verdict.passed is True
    assert [c["is_off"] for c in calls] == [True, False]
    assert all("recent_full_k = 1" in c["config"] for c in calls)
    assert all(c["kwargs"]["auth_pref"] == "none" for c in calls)

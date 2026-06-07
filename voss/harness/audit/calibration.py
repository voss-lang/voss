"""V9 reviewer calibration telemetry (VAUD-CAL).

Read-only aggregation over the persisted ``.review.json`` sidecars across ALL
runs under a sessions dir. Derives the false-pass rate (Reviewer-A said pass but
Reviewer-B failed/blocked) and the slop-rejection rate (Reviewer-B blocked),
plus a deterministic sampled spot-audit selection hook for human review.

Stdlib only (json, random). Imports nothing from the board / EM / CLI layers.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from voss.harness.audit.model import CalibrationReport


def _select_spot_audit(paths: list[Path], k: int, seed: int | None) -> list[Path]:
    """Deterministic-given-seed sample of up to ``k`` sidecar paths."""
    rng = random.Random(seed)
    population = list(paths)
    return rng.sample(population, min(k, len(population)))


def compute_calibration(
    sessions_dir: Path, spot_k: int = 3, seed: int | None = None
) -> CalibrationReport:
    """Aggregate reviewer calibration across every ``.review.json`` sidecar.

    false_pass = A.result=="pass" AND B.verdict in {"fail","block"};
                 denominator = sidecars carrying BOTH an A and a B verdict.
    slop_reject = B.verdict=="block"; denominator = sidecars with a B verdict.
    Rates default to 0.0 when their denominator is 0 (no division-by-zero).
    Missing sessions dir / corrupt sidecars are tolerated (skipped).
    """
    try:
        all_sidecars = sorted(sessions_dir.rglob("*.review.json"))
    except OSError:
        all_sidecars = []

    total = 0
    false_pass = 0
    b_total = 0
    slop_reject = 0

    for path in all_sidecars:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        a_result = (data.get("a_verification") or {}).get("result", "")
        b_verdict = (data.get("b_verdict") or {}).get("verdict", "")
        if a_result and b_verdict:
            total += 1
            if a_result == "pass" and b_verdict in ("fail", "block"):
                false_pass += 1
        if b_verdict:
            b_total += 1
            if b_verdict == "block":
                slop_reject += 1

    spot = _select_spot_audit(all_sidecars, spot_k, seed)
    return CalibrationReport(
        total_pairs=total,
        false_pass_count=false_pass,
        slop_rejection_count=slop_reject,
        false_pass_rate=false_pass / total if total else 0.0,
        slop_rejection_rate=slop_reject / b_total if b_total else 0.0,
        spot_audit_paths=tuple(str(p) for p in spot),
    )

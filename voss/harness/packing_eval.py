"""V18 VOPT-07: M5 quality-preservation gate for context packing.

Runs the golden eval suite twice — packing OFF (VOSS_NO_PACK=1) vs
packing ON — and gates on two clauses:

  1. success_rate(on) >= success_rate(off) - tolerance
  2. mean input tokens must not inflate (tokens_on <= tokens_off; a
     measurable drop is the goal on real multi-iteration histories, but
     hermetic stub runs that stay below recent_full_k are byte-identical
     by design, so equality is acceptable there)

The savings % is an OUTPUT of this gate (token_reduction), never an
input. A profile that regresses golden-task success beyond the locked
tolerance is REJECTED (the biting proof lives in
tests/harness/test_packing_eval_gate.py).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

TOLERANCE = 0.05


class GateResult(dict):
    """Gate verdict: a plain dict with `.passed` attribute sugar."""

    @property
    def passed(self) -> bool:
        return bool(self["passed"])


def _read_runs(path: Path | str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]


def _success_rate(rows: list[dict]) -> float:
    """Fraction of rows with success is True (None/crash = not-success)."""
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get("success") is True) / len(rows)


def _mean_input_tokens(rows: list[dict]) -> float:
    vals = [
        r["input_tokens"]
        for r in rows
        if isinstance(r.get("input_tokens"), (int, float))
    ]
    return sum(vals) / len(vals) if vals else 0.0


def _coerce_rows(rows_or_path: Iterable[dict] | Path | str) -> list[dict]:
    if isinstance(rows_or_path, (str, Path)):
        return _read_runs(rows_or_path)
    return list(rows_or_path)


def compare_runs(
    on: Iterable[dict] | Path | str,
    off: Iterable[dict] | Path | str,
    tolerance: float = TOLERANCE,
) -> GateResult:
    """Gate decision: packing must hold success and must not inflate tokens."""
    on_rows = _coerce_rows(on)
    off_rows = _coerce_rows(off)
    success_on = _success_rate(on_rows)
    success_off = _success_rate(off_rows)
    tokens_on = _mean_input_tokens(on_rows)
    tokens_off = _mean_input_tokens(off_rows)
    success_ok = success_on >= success_off - tolerance
    tokens_ok = tokens_on <= tokens_off
    return GateResult(
        passed=success_ok and tokens_ok,
        success_on=success_on,
        success_off=success_off,
        mean_tokens_on=tokens_on,
        mean_tokens_off=tokens_off,
        token_reduction=tokens_off - tokens_on,
    )


def run_packing_gate(
    *,
    suite: str = "golden",
    stub: bool = True,
    out_dir: Path | str,
    tolerance: float = TOLERANCE,
) -> GateResult:
    """Drive the suite packing-off vs packing-on and return the gate verdict.

    VOSS_NO_PACK is restored to its prior value even if the off-run raises.
    """
    from voss.eval.runner import run_suite

    out_dir = Path(out_dir)
    prev = os.environ.get("VOSS_NO_PACK")
    try:
        os.environ["VOSS_NO_PACK"] = "1"
        run_suite(suite=suite, stub=stub, out=out_dir / "off")
    finally:
        if prev is None:
            os.environ.pop("VOSS_NO_PACK", None)
        else:
            os.environ["VOSS_NO_PACK"] = prev
    run_suite(suite=suite, stub=stub, out=out_dir / "on")
    return compare_runs(
        out_dir / "on" / "runs.jsonl",
        out_dir / "off" / "runs.jsonl",
        tolerance,
    )

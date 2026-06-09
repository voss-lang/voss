"""Repair engine for `voss doctor --fix`.

D-13 default is unchanged: plain `voss doctor` never mutates. Repairs run
only behind the explicit `--fix` opt-in, gated per-check by RepairTier:

- MANUAL (or no `repair` callable): never executed; fix text only.
- CONFIRM: requires the interactive confirmation; skipped under `--yes`.
- SAFE: runs whenever the `--fix` plan is approved (or under `--yes`).

Every executed repair is verified by re-running its check through the
diagnostics REGISTRY; a repair only counts as fixed when the re-check
comes back OK.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .diagnostics import (
    REGISTRY,
    Check,
    CheckResult,
    RepairResult,
    RepairTier,
)


@dataclass
class RepairOutcome:
    check: Check
    executed: bool
    skipped_reason: str = ""
    result: RepairResult | None = None
    recheck: Check | None = None

    @property
    def verified(self) -> bool:
        """Repair ran, reported ok, and the re-run check is OK."""
        return (
            self.executed
            and self.result is not None
            and self.result.ok
            and self.recheck is not None
            and self.recheck.result is CheckResult.OK
        )


def repair_candidates(results: list[Check]) -> list[Check]:
    """Non-OK checks carrying an executable repair."""
    return [
        c
        for c in results
        if c.result is not CheckResult.OK
        and c.repair is not None
        and c.tier is not RepairTier.MANUAL
    ]


def recheck(check: Check, cwd: Path) -> Check | None:
    """Re-run a check via its REGISTRY spec; None when id is unknown."""
    spec = next((s for s in REGISTRY if s.id == check.id), None)
    if spec is None:
        return None
    fresh = spec.run(cwd)
    if not fresh.id:
        fresh.id = spec.id
    if fresh.category is None:
        fresh.category = spec.category
    return fresh


def execute_repairs(
    candidates: list[Check], cwd: Path, *, assume_yes: bool
) -> list[RepairOutcome]:
    outcomes: list[RepairOutcome] = []
    for c in candidates:
        if assume_yes and c.tier is RepairTier.CONFIRM:
            outcomes.append(
                RepairOutcome(
                    c,
                    executed=False,
                    skipped_reason="confirm tier; re-run --fix without --yes",
                )
            )
            continue
        if c.repair is None:  # repair_candidates filters these; belt-and-braces
            continue
        try:
            result = c.repair()
        except Exception as exc:  # a broken repair must never crash doctor
            result = RepairResult(ok=False, detail=f"repair raised: {exc}")
        rc = recheck(c, cwd) if result.ok else None
        outcomes.append(RepairOutcome(c, executed=True, result=result, recheck=rc))
    return outcomes


def merge_results(results: list[Check], outcomes: list[RepairOutcome]) -> list[Check]:
    """Post-repair check states: re-checked rows replace their originals
    so exit-code aggregation reflects what repairs actually achieved."""
    by_id = {o.check.id: o for o in outcomes}
    merged: list[Check] = []
    for c in results:
        o = by_id.get(c.id)
        merged.append(o.recheck if (o and o.recheck is not None) else c)
    return merged

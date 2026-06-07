---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 05
type: execute
status: complete
wave: 4
---

# V9-05 Summary — Reviewer Calibration

## Outcome

New `voss/harness/audit/calibration.py` computes false-pass / slop-rejection
rates across all `.review.json` sidecars + a deterministic spot-audit hook.
`test_calibration.py` GREEN (5/5); the V9-01 calibration-import guard now GREEN.
Audit suite: **71 passed, 3 RED** (signoff only → V9-06).

## `voss/harness/audit/calibration.py` (new)

- `compute_calibration(sessions_dir, spot_k=3, seed=None) -> CalibrationReport`
  — `sorted(rglob("*.review.json"))` over ALL runs; per-file try/except skip;
  missing dir → empty.
  - `false_pass`: A.result=="pass" AND B.verdict in {fail,block}; denom = pairs
    with both A+B verdicts. Rate 0.0 when denom 0.
  - `slop_reject`: B.verdict=="block"; denom = sidecars with a B verdict. Rate
    0.0 when denom 0.
- `_select_spot_audit(paths, k, seed)` — `random.Random(seed).sample(paths,
  min(k, len(paths)))`; deterministic given a seed.
- Import-clean (gate = 0); stdlib (json, random) + `CalibrationReport` only.

## Deviation: CLI must seed calibration for VAUD-08 determinism

Wiring real calibration into `audit_cmd` (V9-04 had passed `None`) broke
`test_audit_cli.py::test_deterministic_output`: `compute_calibration(sessions_dir)`
defaults `seed=None`, so `random.Random(None).sample(...)` produced a different
`spot_audit_paths` on each CLI invocation → non-identical JSON. VAUD-08 requires
reproducible audit output. Fixed by passing a fixed seed in the CLI:
`compute_calibration(sessions_dir, seed=0)`. The function default stays
`seed=None` (per plan); only the CLI pins it for deterministic export.

This was a latent V9-04 wiring gap that only surfaced once calibration existed —
the render-layer determinism tests passed because they used `calibration=None`
(empty spot list).

## Verification

- `pytest tests/harness/audit/test_calibration.py` — 5 passed.
- `pytest tests/harness/audit/ -k "not signoff"` — green (all prior waves + calibration; CLI determinism restored).
- Import-clean grep gate (board/em/cli) on calibration.py = 0.
- Calibration-import guard (`TestNoLiveImports`) GREEN.

## Remaining RED

signoff gate (3, V9-06) — the only wave left.

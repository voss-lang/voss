---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 02
type: execute
status: complete
wave: 1
---

# V9-02 Summary — Loader + Model Foundation

## Outcome

`load.py` gained the `run_id` parameter, latest-by-mtime fallback, and the two
separate readers; `model.py` gained the `AuditReport` + `CalibrationReport`
frozen dataclasses. The Wave-0 loader RED tests are now GREEN. Audit suite:
**48 passed, 26 RED** (all RED belong to later waves V9-03/04/05/06).

## Changes

### `voss/harness/audit/load.py`
- `load_audit_snapshot(root, run_id=None)` — named run when `run_id` given
  (`AuditLoadError("unknown run_id: …")` if the dir is absent); latest-by-mtime
  (`max(root_dirs, key=mtime)`) when `None`, replacing the old alphabetical
  `root_dirs[0]` pick.
- Node glob already filtered `run-final.json` + `*.review.json` in V9-01 (the
  landmine fix, pulled forward); left in place.
- `_load_run_final_file(run_dir)` — reads the separate `run-final.json`, returns
  dict or `None`, swallows OSError/JSONDecodeError.
- `_load_review_sidecars(run_dir)` — `{node_id: dict}` from `*.review.json`,
  corrupt sidecar → `{}`.
- `run_final` now **merges** the file over the root `em.run_final` transition
  (file fields win; transition-only keys like `kind` preserved) — see deviation.
- Import-clean: no `voss.harness.board/.em/.cli` import (grep gate = 0).

### `voss/harness/audit/model.py`
- `CalibrationReport(total_pairs, false_pass_count, slop_rejection_count,
  false_pass_rate, slop_rejection_rate, spot_audit_paths)` — frozen+slots.
- `AuditReport(run_id, idea, principles, team_config, snapshot, review_sidecars,
  run_final, signoff_ack, calibration, sections_missing, unsupported_claims=())`
  — frozen+slots; `unsupported_claims` defaults to `()` (populated by V9-03).
- Existing dataclasses untouched; import-clean (grep gate = 0).

## Deviation: run_final merge instead of plain override

The plan said the file should be "preferred … falling back to the transition
(keep both)". A plain override broke the pre-existing
`test_run_final_present`, which asserts `snap.run_final["kind"] == "em.run_final"`
— the fixture's `run-final.json` has no `kind` (real run-final files don't). I
merged (`{**transition, **file}`) so file fields win while the transition's
`kind` survives. Real runs (no transition) still get the file verbatim. This
satisfies "file authoritative for real runs" and keeps the baseline test green.

## Known carried-forward RED (not a V9-02 regression)

`TestNoLiveImports::test_calibration_module_has_no_board_imports` (added RED in
V9-01) stays RED — `voss.harness.audit.calibration` lands in V9-05. The plan's
Task-1 acceptance (`pytest test_snapshot_loader.py -x` exits 0) and Task-2
verify (`-k NoLiveImports`) don't account for this V9-01-seeded guard; every
other loader test in the file is green. Substantive goal met: loader RED →
green, zero baseline regression.

`AuditNode.rejected_raises` deliberately NOT added (frozen-schema discipline per
the plan); `rejected_raises` stays on the raw node dict for report.py (V9-03) to
surface. `test_scope_denials` remains RED until V9-03.

## Verification

- `pytest tests/harness/audit/test_snapshot_loader.py` — 30 passed, 1 RED (calibration guard).
- `pytest tests/harness/audit/ -k "not report and not render and not cli and not calibration and not signoff"` — green (no baseline regression).
- Import-clean grep gates: load.py = 0, model.py = 0.
- Model frozen + `unsupported_claims` default `()` verified.

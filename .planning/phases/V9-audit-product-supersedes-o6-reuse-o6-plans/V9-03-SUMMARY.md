---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 03
type: execute
status: complete
wave: 2
---

# V9-03 Summary — AuditReport Aggregate

## Outcome

New `voss/harness/audit/report.py` assembles the full PRD §9 `AuditReport`
read-only. `test_audit_report.py` fully GREEN (8/8). Audit suite: **56 passed,
18 RED** (all RED in later waves V9-04/05/06). Import-clean gate = 0.

## `voss/harness/audit/report.py` (new)

- `build_audit_report(cwd, run_id=None, calibration=None) -> AuditReport` —
  calls `load_audit_snapshot`, reads `run-final.json` / `*.review.json` /
  `.signoff-ack.json` separately, resolves principles + team, never writes.
- `_resolve_principles(cwd)` — `resolve_principles(cwd).principles`, falls back
  to `DEFAULT_PRINCIPLES` on any error. (`resolve_principles` returns a
  `PrinciplesConfig`, not a bare tuple — interface note in plan was imprecise;
  used `.principles`.)
- `_load_team_config_dict(cwd)` — parses `.voss/team.voss` via `parse` +
  `compile_team`; on absence/error returns `{"source": "default roster (not
  persisted)", "roster_ids": []}`. team.py import allowed; board/em/cli not.
- `_load_signoff_ack(run_dir)` — `.signoff-ack.json` → dict or None, graceful.
- `scope_denials(snapshot, run_dir)` — re-reads node JSONs for
  `rejected_raises` (lives on the raw node dict, not the frozen `AuditNode`);
  returns flattened `{node_id, attempted_delta, reason, attempted_at}` sorted.
- `_unsupported_claims(snapshot, sidecars)` — VAUD-03 rule: non-root node with
  an `em.ticket` transition but absent/empty sidecar (or both `a_verification`
  and `b_verdict` falsy) → flagged. Result → `AuditReport.unsupported_claims`.
- `_residual_risk(snapshot)` — VAUD-10: reuse `audit.leak6` marker when present,
  else synthesize `accepted_gap` ("no standup-to-memory writer in V2-V7
  substrate"). Read-only; frozen snapshot never mutated.
- `sections_missing` — `"goal"` when run-final absent; always `"diff_summary"` +
  `"tests_evals"` (no persisted source per SPEC).

## Deviation: Wave-0 test_scope_denials realigned to planned surface

My V9-01 `test_scope_denials` asserted `report.snapshot.nodes[…].rejected_raises`
— but V9-02/V9-03 deliberately do NOT add `rejected_raises` to the frozen
`AuditNode` (frozen-schema discipline). The plan specifies a module-level
`scope_denials(snapshot, run_dir)` helper instead. Realigned the test to assert
against `scope_denials(...)` (node_id + reason + attempted_delta). This is the
gsd-scaffold-fictional-api pattern: a Wave-0 scaffold pinned to a guessed API,
corrected to the real planned surface in its implementation wave. No xfail.

## Verification

- `pytest tests/harness/audit/test_audit_report.py` — 8 passed (VAUD-02/03/07/10).
- `pytest tests/harness/audit/ -k "not render and not cli and not calibration and not signoff"` — green (loader + report + baseline, no regression).
- Import-clean grep gate (board/em/cli) on report.py = 0. (Reworded the module
  docstring so the bare gate string didn't false-positive; the real
  `TestNoLiveImports` matches `from`/`import` statements only.)
- Read-only preserved (report tests mirror TestReadOnly mtime invariant).

## Remaining RED (later waves)

cli (6, V9-04), render (4, V9-04), calibration compute (4, V9-05), signoff
(3, V9-06), calibration-import guard (1, V9-05). `_residual_risk` /
`scope_denials` are exposed for the V9-04 render layer to consume.

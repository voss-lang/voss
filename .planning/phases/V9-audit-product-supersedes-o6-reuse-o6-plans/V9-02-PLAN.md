---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 02
type: execute
wave: 1
depends_on: ["V9-01"]
files_modified:
  - voss/harness/audit/load.py
  - voss/harness/audit/model.py
autonomous: true
requirements: [VAUD-01, VAUD-02, VAUD-04, VAUD-05, VAUD-06, VAUD-07]

must_haves:
  truths:
    - "load_audit_snapshot accepts an optional run_id and selects a named run, or latest-by-mtime when None"
    - "load_audit_snapshot filters run-final.json AND *.review.json out of the node glob (no AuditLoadError on a real run dir)"
    - "_load_review_sidecars and _load_run_final_file read the sidecar and run-final files separately, gracefully"
    - "model.py defines frozen AuditReport and CalibrationReport dataclasses"
    - "load.py imports nothing from voss.harness.board/.em/.cli (TestNoLiveImports stays green)"
  artifacts:
    - path: "voss/harness/audit/load.py"
      provides: "run_id param, glob-landmine filter, sidecar + run-final readers"
      contains: "run_id"
    - path: "voss/harness/audit/model.py"
      provides: "AuditReport + CalibrationReport frozen dataclasses"
      contains: "class AuditReport"
  key_links:
    - from: "voss/harness/audit/load.py"
      to: "run-final.json / *.review.json"
      via: "name-based filter before _read_node_file"
      pattern: "run-final.json"
---

<objective>
The foundational data layer. Fix the `load.py` glob landmine (run-final.json + .review.json crash the node glob via the missing-`id` check), add the `run_id` parameter with latest-by-mtime fallback, add separate readers for the run-final file and review sidecars, and add the two new frozen dataclasses (`AuditReport`, `CalibrationReport`) that the report/render/calibration waves consume.

Purpose: Everything downstream (report assembly, render, CLI, calibration) depends on a loader that does not crash on a real `voss team run` directory and a model that can hold the full PRD §9 surface. This unblocks Waves 2-4.
Output: Modified `load.py` (run_id + filters + readers) and `model.py` (+2 dataclasses). The Wave-0 loader RED tests turn GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-SPEC.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-PATTERNS.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-RESEARCH.md

<interfaces>
Existing load.py contracts (do not break):
  AuditLoadError(path, reason)            # raised on unreadable/invalid/missing-id node
  _read_node_file(path) -> dict           # requires "id"; used only for node JSONs
  load_audit_snapshot(root: Path) -> AuditSnapshot   # CURRENT signature (extend, non-breaking)
  Node glob today (line 263): node_files = sorted(tree_dir.glob("*.json"))   # the landmine

Existing model.py frozen dataclasses (pattern to mirror — all frozen=True, slots=True, typing.Optional):
  AuditSnapshot(root_id, nodes, cards, kills, rescopes, routings, verdicts, liveness, leak6, run_final=None)
  AuditNode(id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at,
            transitions=(), cards=(), liveness_events=())

Latest-by-mtime reference (voss/harness/cli.py:2451-2459):
  max(roots, key=lambda d: d.stat().st_mtime)   # mirror this for run_id=None

review-sidecar schema (voss/harness/board/review_persistence.py — authoritative):
  {"a_verification": {...}|None, "b_verdict": {...}|None, "final_outcome": "Done"|"Blocked"}
run-final.json schema (voss/harness/cli.py:_persist_run_final — authoritative):
  asdict(RunFinal) + optional "sign_off"; has NO "id" key → must be filtered + read separately
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix load.py — run_id param, glob-landmine filter, sidecar + run-final readers</name>
  <files>voss/harness/audit/load.py</files>
  <behavior>
    - load_audit_snapshot(root, run_id="root_aabbcc0001") loads that run; run_id="missing" raises AuditLoadError.
    - load_audit_snapshot(root) with multiple run dirs selects the most-recently-modified (mtime), not alphabetical first.
    - load_audit_snapshot on a tree containing run-final.json + *.review.json does NOT raise (those are excluded from the node glob).
    - _load_review_sidecars(run_dir) returns {node_id: dict}; corrupt sidecar → {}.
    - _load_run_final_file(run_dir) returns the run-final dict or None when absent/corrupt.
    - load.py source contains no `voss.harness.board`/`.em`/`.cli` import.
  </behavior>
  <read_first>
    - voss/harness/audit/load.py:243-343 (the function being modified; glob at 263, root-dir selection 254-262, `_read_node_file` 35-48) — self-extension analog
    - voss/harness/cli.py:2451-2459 (`_latest_root_id` — mtime-latest pattern to mirror)
    - V9-PATTERNS.md "voss/harness/audit/load.py (modify)" (signature, filter, _load_run_final_file, _load_review_sidecars excerpts lines 27-89) and "Landmines" (lines 637-643)
    - tests/harness/audit/test_snapshot_loader.py (the Wave-0 RED tests this task must satisfy: TestLandmineGlobFilter, TestRunIdParameter, TestSidecarLoad, TestRunFinalSeparateRead)
  </read_first>
  <action>
    Change the signature to `load_audit_snapshot(root: Path, run_id: str | None = None) -> AuditSnapshot`. Run-dir selection: when `run_id` is not None, `tree_dir = sessions_dir / run_id`; if not `tree_dir.is_dir()` raise `AuditLoadError(sessions_dir, f"unknown run_id: {run_id}")`. When `run_id` is None, select `max(root_dirs, key=lambda d: d.stat().st_mtime)` (latest-by-mtime, replacing the current `root_dirs[0]` alphabetical pick at line 262). Filter the node glob (line 263) to exclude the landmines: keep only `p` where `p.name != "run-final.json" and not p.name.endswith(".review.json")` before `_read_node_file`. Add module-level helpers `_load_run_final_file(run_dir)` (read `run-final.json`, return dict or None; swallow OSError/json.JSONDecodeError → None) and `_load_review_sidecars(run_dir)` (glob `*.review.json`, key by `path.name[:-len(".review.json")]`, value the parsed dict or `{}` on read error). Wire `_load_run_final_file` so the snapshot's `run_final` is preferred from the separate file when present, falling back to the existing `_extract_run_final` transition path (keep both — the file is authoritative for real runs, the transition for the fixture's `em.run_final`). Surface `rejected_raises` for VAUD-05: AuditNode currently has no scope-denial field — do NOT add a field to AuditNode (frozen-schema discipline for the audit model would force test churn); instead keep `rejected_raises` reachable via the raw transitions/node dicts that report.py reads. Concretely: leave AuditNode as-is, and rely on report.py (V9-03) reading `rejected_raises` from the node JSONs. Document in a comment that rejected_raises lives on the raw node dict, surfaced by report.py. Do NOT import principles or team — those belong to report.py (TestNoLiveImports forbids them in load.py).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_snapshot_loader.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/audit/test_snapshot_loader.py -x` exits 0 (Wave-0 loader RED tests now GREEN; existing loader tests still pass).
    - `grep -v '^#' voss/harness/audit/load.py | grep -c "voss.harness.board\|voss.harness.em\|voss.harness.cli"` returns 0 (no live imports).
    - Source assertion: `load.py` node glob excludes `run-final.json` and `*.review.json` (grep for `run-final.json` shows the filter predicate).
    - The 37 pre-existing audit tests remain green: `.venv/bin/python -m pytest tests/harness/audit/ -x -k "not report and not render and not cli and not calibration and not signoff"` exits 0.
  </acceptance_criteria>
  <done>load.py accepts run_id, selects latest-by-mtime, filters the landmines, reads sidecars + run-final separately, stays import-clean; loader RED tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add AuditReport + CalibrationReport frozen dataclasses to model.py</name>
  <files>voss/harness/audit/model.py</files>
  <behavior>
    - `from voss.harness.audit.model import AuditReport, CalibrationReport` succeeds.
    - Both are `frozen=True, slots=True`; instances are immutable (assigning a field raises).
    - AuditReport carries: run_id, idea, principles, team_config, snapshot, review_sidecars, run_final, signoff_ack, calibration, sections_missing.
    - CalibrationReport carries: total_pairs, false_pass_count, slop_rejection_count, false_pass_rate, slop_rejection_rate, spot_audit_paths.
    - model.py source contains no board/em/cli import (TestNoLiveImports::test_model_module_has_no_board_imports stays green).
  </behavior>
  <read_first>
    - voss/harness/audit/model.py:1-122 (the file being modified; existing frozen dataclass style, `Optional` import at line 10, `AuditSnapshot` lines 110-122) — self-extension analog
    - V9-PATTERNS.md "voss/harness/audit/model.py (modify)" (AuditReport + CalibrationReport excerpts lines 96-143)
    - tests/harness/audit/test_audit_report.py + test_calibration.py (Wave-0 RED tests asserting these fields)
  </read_first>
  <action>
    Add two frozen+slots dataclasses to `model.py`, mirroring the existing style (primitives/tuples/dicts only, `Optional` from typing, no board/em/cli imports). `CalibrationReport`: `total_pairs: int`, `false_pass_count: int`, `slop_rejection_count: int`, `false_pass_rate: float`, `slop_rejection_rate: float`, `spot_audit_paths: tuple[str, ...]`. `AuditReport`: `run_id: str`, `idea: str`, `principles: tuple[tuple[str, str], ...]`, `team_config: dict`, `snapshot: AuditSnapshot`, `review_sidecars: dict`, `run_final: Optional[dict]`, `signoff_ack: Optional[dict]`, `calibration: CalibrationReport`, `sections_missing: tuple[str, ...]`. Reference `AuditSnapshot` directly (defined earlier in the same module) and `CalibrationReport` (define it BEFORE `AuditReport`). Add an `unsupported_claims: tuple[str, ...] = ()` field to `AuditReport` (default empty) so the claims-vs-evidence test (VAUD-03) has a structural home; populated by report.py in V9-03. Do NOT modify any existing dataclass.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_snapshot_loader.py -k NoLiveImports -x && .venv/bin/python -c "from voss.harness.audit.model import AuditReport, CalibrationReport; import dataclasses; assert dataclasses.is_dataclass(AuditReport)"</automated>
  </verify>
  <acceptance_criteria>
    - `from voss.harness.audit.model import AuditReport, CalibrationReport` imports without error.
    - Both dataclasses are frozen: attempting field assignment raises `dataclasses.FrozenInstanceError`.
    - `grep -v '^#' voss/harness/audit/model.py | grep -c "voss.harness.board\|voss.harness.em\|voss.harness.cli"` returns 0.
    - `.venv/bin/python -m pytest tests/harness/audit/test_snapshot_loader.py -k NoLiveImports -x` exits 0.
    - AuditReport exposes `unsupported_claims` (tuple, default empty).
  </acceptance_criteria>
  <done>model.py defines frozen AuditReport (with unsupported_claims) + CalibrationReport; import-clean; existing dataclasses untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| persisted JSON → loader | Untrusted/malformed persisted data (oversized, corrupt, missing keys) crosses into the loader |
| run_id (caller) → filesystem path | run_id is used to form a sessions-dir path (path-traversal surface — guarded at the CLI in V9-04, loader assumes a validated name) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-02-01 | Denial of Service | malformed/oversized run-final.json or .review.json | mitigate | `_load_run_final_file`/`_load_review_sidecars` swallow OSError/JSONDecodeError → None/`{}`; loader renders "none", never crashes (the glob-landmine fix itself) |
| T-V9-02-02 | Tampering | run-final.json / .review.json masquerading as node JSON | mitigate | Name-based filter excludes them from the node glob before `_read_node_file`'s `id` check |
| T-V9-02-03 | Tampering | run_id path traversal at the loader | accept | Loader treats run_id as a dir name under sessions_dir; the path-traversal guard is enforced at the CLI boundary (V9-04). Loader-internal `sessions_dir / run_id` with a CLI-validated run_id is the documented contract |
| T-V9-02-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies; stdlib only — no install step |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/test_snapshot_loader.py -x` — all loader tests (incl. Wave-0 RED) green.
- `.venv/bin/python -m pytest tests/harness/audit/ -x -k "not report and not render and not cli and not calibration and not signoff"` — no regression in the 37 baseline tests.
- Import-clean grep gates above return 0.
</verification>

<success_criteria>
- load.py: run_id param + latest-by-mtime + landmine filter + sidecar/run-final readers; import-clean.
- model.py: AuditReport (with unsupported_claims) + CalibrationReport; import-clean; existing dataclasses untouched.
- Wave-0 loader RED tests turn GREEN; 37 baseline tests preserved.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-02-SUMMARY.md` when done.
</output>

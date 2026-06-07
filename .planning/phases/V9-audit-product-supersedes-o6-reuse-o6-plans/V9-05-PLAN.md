---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 05
type: execute
wave: 4
depends_on: ["V9-02"]
files_modified:
  - voss/harness/audit/calibration.py
autonomous: true
requirements: [VAUD-CAL]

must_haves:
  truths:
    - "compute_calibration aggregates over ALL .review.json sidecars under sessions_dir (not one run)"
    - "false_pass_rate = |A=pass AND B in {fail,block}| / |cards with both A+B verdicts|"
    - "slop_rejection_rate = |B=block| / |cards with a B verdict|"
    - "a sampled spot-audit selection hook exists and is deterministic given a seed"
    - "empty sessions dir → rates 0.0 with no division-by-zero"
    - "calibration.py imports nothing from board/.em/.cli"
  artifacts:
    - path: "voss/harness/audit/calibration.py"
      provides: "compute_calibration + deterministic spot-audit hook"
      contains: "def compute_calibration"
  key_links:
    - from: "voss/harness/audit/calibration.py"
      to: ".voss/sessions/**/*.review.json"
      via: "rglob aggregation"
      pattern: "review.json"
---

<objective>
Reviewer calibration telemetry (VAUD-CAL): derive false-pass and slop-rejection rates from the persisted `.review.json` sidecars across ALL runs, plus a deterministic sampled spot-audit hook for human review.

Purpose: Calibration measures reviewer reliability (Reviewer-B verdict vs Reviewer-A verification outcome) — the last O6 residual the V9 audit product absorbs. It is a pure read-only aggregation, independent of report assembly, so it runs in parallel with the sign-off work (V9-06).
Output: New `voss/harness/audit/calibration.py`. Wave-0 `test_calibration.py` turns GREEN.
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
From V9-02:
  voss/harness/audit/model.py: CalibrationReport(total_pairs, false_pass_count,
    slop_rejection_count, false_pass_rate, slop_rejection_rate, spot_audit_paths)

review-sidecar schema (voss/harness/board/review_persistence.py — AUTHORITATIVE):
  {"a_verification": {"result": "pass"|"fail", ...} | None,
   "b_verdict": {"verdict": "pass"|"fail"|"block", ...} | None,
   "final_outcome": "Done"|"Blocked"}

Formula (V9-RESEARCH §6):
  false_pass = A.result=="pass" AND B.verdict in {"fail","block"}     ; denom = pairs with BOTH A+B
  slop_reject = B.verdict=="block"                                    ; denom = sidecars with a B verdict
  rates 0.0 when denom == 0 (no div-by-zero)
Spot-audit hook: random.Random(seed).sample(paths, min(k, len(paths))) — deterministic given seed.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create calibration.py — compute_calibration + deterministic spot-audit hook</name>
  <files>voss/harness/audit/calibration.py</files>
  <behavior>
    - compute_calibration(sessions_dir) aggregates over every .review.json under sessions_dir (rglob, all runs).
    - false_pass_count counts A=pass AND B in {fail,block}; false_pass_rate divides by pairs with both A+B verdicts.
    - slop_rejection_count counts B=block; slop_rejection_rate divides by sidecars with a B verdict.
    - empty/missing sessions dir → CalibrationReport with zeros and 0.0 rates (no exception).
    - compute_calibration(..., spot_k=2, seed=7) twice → identical spot_audit_paths.
    - corrupt sidecar → skipped, no crash.
  </behavior>
  <read_first>
    - voss/harness/audit/model.py (CalibrationReport fields from V9-02)
    - voss/harness/board/review_persistence.py (AUTHORITATIVE a_verification.result / b_verdict.verdict keys)
    - voss/harness/cli.py:2506-2516 (review_cmd sidecar glob + graceful read analog)
    - V9-PATTERNS.md "voss/harness/audit/calibration.py (new)" (compute_calibration + _select_spot_audit excerpts lines 349-426)
    - V9-RESEARCH.md §6 (formula, denominators, k=3 default)
    - tests/harness/audit/test_calibration.py (Wave-0 RED tests)
  </read_first>
  <action>
    Create `voss/harness/audit/calibration.py`. Module docstring: read-only aggregation, stdlib only, no board/.em/.cli imports. `compute_calibration(sessions_dir: Path, spot_k: int = 3, seed: int | None = None) -> CalibrationReport`: `all_sidecars = sorted(sessions_dir.rglob("*.review.json"))` (sorted for determinism; tolerate a non-existent dir → empty list). Iterate: parse each (try/except OSError+json.JSONDecodeError → skip); read `a_result = (data.get("a_verification") or {}).get("result","")` and `b_verdict = (data.get("b_verdict") or {}).get("verdict","")`. When both truthy: `total += 1`, and `false_pass += 1` if `a_result=="pass" and b_verdict in ("fail","block")`. When `b_verdict` truthy: `b_total += 1`, and `slop_reject += 1` if `b_verdict=="block"`. Rates: `false_pass/total if total else 0.0`; `slop_reject/b_total if b_total else 0.0`. Spot-audit: module-level `_select_spot_audit(paths, k, seed)` using `random.Random(seed).sample(list(paths), min(k, len(paths)))`. Return `CalibrationReport(total_pairs=total, false_pass_count=false_pass, slop_rejection_count=slop_reject, false_pass_rate=..., slop_rejection_rate=..., spot_audit_paths=tuple(str(p) for p in spot))`. Import only `CalibrationReport` from `voss.harness.audit.model` + stdlib (`json`, `random`, `pathlib.Path`).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_calibration.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/audit/test_calibration.py -x` exits 0 (false-pass, slop-rejection, deterministic spot-audit, zero-pairs all green).
    - With the V9-01 fixture (A=pass/B=fail misroute pair) `false_pass_count >= 1`; the A=pass/B=block pair contributes to `slop_rejection_count`.
    - Empty sessions dir → `false_pass_rate == 0.0` and `slop_rejection_rate == 0.0`, no exception.
    - `compute_calibration(sd, spot_k=2, seed=7)` twice → identical `spot_audit_paths`.
    - `grep -v '^#' voss/harness/audit/calibration.py | grep -c "voss.harness.board\|voss.harness.em\|voss.harness.cli"` returns 0.
  </acceptance_criteria>
  <done>calibration.py computes false-pass / slop-rejection rates across all runs + a deterministic spot-audit hook; import-clean; test_calibration.py green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| persisted .review.json (all runs) → calibration aggregator | Untrusted/corrupt sidecars from any run cross into the aggregator |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-05-01 | Denial of Service | corrupt/oversized .review.json | mitigate | Per-file try/except → skip; missing sessions dir → empty list; rates default 0.0 (no div-by-zero) |
| T-V9-05-02 | Tampering | non-deterministic spot-audit selection | mitigate | `random.Random(seed)` + sorted input paths → deterministic given seed (calibration is read-only telemetry, no decision authority) |
| T-V9-05-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies; stdlib (json, random) only |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/test_calibration.py -x` — VAUD-CAL green.
- `.venv/bin/python -m pytest tests/harness/audit/ -x -k "not signoff"` — calibration + prior waves green, 37 baseline preserved.
- Import-clean grep gate returns 0.
</verification>

<success_criteria>
- compute_calibration aggregates across all runs; correct false-pass / slop-rejection formulas; zero-safe.
- Deterministic seeded spot-audit hook.
- Import-clean; test_calibration.py green; baseline preserved.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-05-SUMMARY.md` when done.
</output>

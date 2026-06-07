---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 07
type: execute
wave: 5
depends_on: ["V9-05", "V9-06"]
files_modified:
  - voss/harness/cli.py
  - .planning/ROADMAP.md
autonomous: false
requirements: [VAUD-01, VAUD-02, VAUD-08, VAUD-CAL, VAUD-SIGNOFF]

must_haves:
  truths:
    - "audit_cmd wires real calibration (compute_calibration) into the report so voss audit shows calibration rates"
    - "git diff shows zero field changes on RunRecord, SessionRecord, and BudgetScope"
    - "the full harness audit suite is green and the 37 pre-existing audit tests are preserved"
    - "O6 is marked superseded in ROADMAP bookkeeping; V9 plan list reflects the shipped plans"
    - "a human verifies voss audit Markdown legibility and the sign-off forcing-function UX on a real run"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "audit_cmd calibration wiring (compute_calibration passed into build_audit_report)"
      contains: "compute_calibration"
    - path: ".planning/ROADMAP.md"
      provides: "V9 plan list + O6-superseded bookkeeping"
  key_links:
    - from: "voss/harness/cli.py audit_cmd"
      to: "voss.harness.audit.calibration.compute_calibration"
      via: "import + pass into build_audit_report"
      pattern: "compute_calibration"
---

<objective>
Phase closeout: finish wiring calibration into the audit CLI (now that `calibration.py` exists), run the full regression, prove zero frozen-schema drift, complete the O6-superseded ROADMAP bookkeeping, and hold the human verification checkpoint for Markdown legibility + the sign-off forcing-function UX.

Purpose: This is the goal-backward gate. Every acceptance criterion in V9-SPEC must be demonstrably met, the existing 37 audit tests + full harness suite must be green, and the schema-freeze constraint (zero field changes to RunRecord/SessionRecord/BudgetScope) must be proven by `git diff`.
Output: Calibration wired into `audit_cmd`, full suite green, frozen-diff clean, ROADMAP updated, human sign-off recorded.
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
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-VALIDATION.md

<interfaces>
From prior waves (now landed):
  voss/harness/audit/calibration.py: compute_calibration(sessions_dir, spot_k=3, seed=None) -> CalibrationReport
  voss/harness/audit/report.py: build_audit_report(cwd, run_id=None, calibration=None) -> AuditReport
  voss/harness/cli.py: audit_cmd (V9-04) currently may pass calibration=None

Frozen-schema diff gate (V9-SPEC acceptance #10):
  git diff must show ZERO field changes on RunRecord (voss/harness/recorder.py or session.py),
  SessionRecord (voss/harness/session.py), BudgetScope (voss/harness/voss_runtime). Guarded also by
  tests/harness/test_session_redaction.py (must remain UNMODIFIED + green).

O6 bookkeeping: ROADMAP.md O6 row already banners "⊘ SUPERSEDED by V9"; update the V9 row to list the
  7 shipped plans and mark phase COMPLETE per project convention (see V5/V6/V7 rows for the format).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire real calibration into audit_cmd; run full regression + frozen-schema diff guard</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py audit_cmd (V9-04) — the call to build_audit_report where calibration is passed
    - voss/harness/audit/calibration.py (compute_calibration signature from V9-05)
    - V9-VALIDATION.md "Per-Requirement Verification Map" + "Sampling Rate" (full-suite gate)
    - V9-SPEC.md Acceptance Criteria (the 10 pass/fail items, esp. #10 frozen diff)
    - tests/harness/test_session_redaction.py (the schema-freeze guard — must stay green, UNMODIFIED)
  </read_first>
  <action>
    In `audit_cmd`, replace the `calibration=None` placeholder with a real call: import `compute_calibration` from `voss.harness.audit.calibration` (local function-body import) and pass `calibration=compute_calibration(sessions_dir)` into `build_audit_report(...)`, so the rendered audit (text/markdown/json) includes calibration rates. Keep the import local to the command body. Then run the full regression and prove the schema freeze: run the full harness audit suite and the broader harness suite; run `git diff` against the phase base commit on the frozen-schema files and confirm ZERO field changes. Do NOT modify recorder.py / session.py / voss_runtime — if the diff shows any change there, revert it (V9 is a read-only consumer + one new governance sidecar only). Confirm `tests/harness/test_session_redaction.py` is unmodified and green.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/ -x && .venv/bin/python -m pytest tests/harness/test_session_redaction.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `voss audit --format json` output contains calibration fields (`false_pass_rate`, `slop_rejection_rate`) sourced from `compute_calibration`, not zeros-by-default.
    - `.venv/bin/python -m pytest tests/harness/audit/ -x` exits 0 (all V9 tests + the 37 baseline green together).
    - `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x` exits 0; the file is UNMODIFIED (git diff on it is empty).
    - Frozen-schema gate: `git diff <phase-base>..HEAD -- voss/harness/session.py voss/harness/recorder.py voss/harness/voss_runtime` shows zero field changes to RunRecord/SessionRecord/BudgetScope (ideally an empty diff on those declarations).
    - The full broader harness suite shows no V9-caused regression (pre-existing unrelated reds, if any, are documented in the SUMMARY, not introduced here).
  </acceptance_criteria>
  <done>Calibration wired into voss audit; full audit suite + redaction guard green; zero frozen-schema drift proven by git diff.</done>
</task>

<task type="auto">
  <name>Task 2: ROADMAP bookkeeping — V9 plan list + O6-superseded confirmation</name>
  <files>.planning/ROADMAP.md</files>
  <read_first>
    - .planning/ROADMAP.md (the V9 phase row + the O6 row already bannered SUPERSEDED) — see V5/V6/V7 rows for the COMPLETE format
    - V9-SPEC.md (the 9 locked requirements + acceptance criteria, to summarize accurately)
  </read_first>
  <action>
    Update the ROADMAP V9 row/block: list the 7 shipped plans (V9-01 RED scaffolds + fixtures → V9-02 load/model → V9-03 report → V9-04 render+CLI → V9-05 calibration → V9-06 sign-off → V9-07 closeout), their wave structure, and mark the phase per project convention once the human checkpoint (Task 3) passes. Confirm the O6 row retains its "⊘ SUPERSEDED by V9" banner (it already does — do not duplicate; just verify). Do NOT touch other phase rows. Keep the edit surgical (match existing row formatting).
  </action>
  <verify>
    <automated>grep -c "V9-0" .planning/ROADMAP.md</automated>
  </verify>
  <acceptance_criteria>
    - ROADMAP V9 row lists all 7 plans with their objectives + wave structure.
    - The O6 row still shows "⊘ SUPERSEDED by V9".
    - No unrelated ROADMAP rows changed (git diff scoped to the V9/O6 lines).
    - `grep -c "V9-0" .planning/ROADMAP.md` returns >= 7.
  </acceptance_criteria>
  <done>ROADMAP reflects the 7 V9 plans + waves; O6-superseded banner confirmed; edit surgical.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    The complete `voss audit` product: a read-only `voss audit [run_id]` CLI that renders a deterministic
    audit (idea → principles → team → budget → scope denials → board → reviewers A/B → lineage →
    residual risk/Leak-6 → calibration → final status) as text/Markdown/JSON, plus a hard sign-off
    forcing function in `voss team run` that blocks approve until the killed-card + misroute diff is
    acknowledged (recorded in a new `.signoff-ack.json` governance sidecar).
  </what-built>
  <how-to-verify>
    1. Run a real `voss team run "<some goal>"` (use `.venv/bin/python -m voss.harness ...` or the installed `voss`).
       If the run produces killed cards or low-confidence routings, confirm the sign-off prompt FIRST
       displays the killed-card / misroute risk summary and requires typing `yes` before the approve/reject
       prompt appears; typing anything else aborts non-zero. Confirm `.voss/sessions/<root_id>/.signoff-ack.json`
       was written (0o600) and that `run-final.json` + node JSONs were NOT modified by the ack.
    2. Run `voss audit` (no arg) → confirm it renders the latest run and the sections are legible.
    3. Run `voss audit --format markdown` → confirm each PRD §9 section has a header; sections with no
       persisted source (diff summary, tests/evals) show `_none_` rather than crashing.
    4. Run `voss audit --format json | python -c "import json,sys; json.load(sys.stdin)"` → confirm valid JSON.
    5. Run `voss audit <known_run_id>` twice → confirm identical output (determinism).
    6. Run `voss audit nonexistent_id` → confirm non-zero exit with an "unknown run_id" message.
    7. Confirm calibration rates appear in the rendered audit.
  </how-to-verify>
  <resume-signal>Type "approved" if legibility + forcing-function UX are correct, or describe issues to fix.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI calibration aggregation → render | Calibration reads all-run sidecars; output rendered to operator |
| phase changes → frozen persistence schemas | The closeout must prove no V9 change crossed into the frozen RunRecord/SessionRecord/BudgetScope |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-07-01 | Tampering | accidental frozen-schema drift introduced across waves | mitigate | git diff gate on session.py/recorder.py/voss_runtime + unmodified test_session_redaction.py green; revert any drift |
| T-V9-07-02 | Information Disclosure | calibration/render leaking secrets to stdout/--output | mitigate | Render serializes only already-redacted persisted fields; upstream recorder redaction (test_session_redaction.py) is the control |
| T-V9-07-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies across the entire phase; stdlib + existing project modules only |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/ -x` — full V9 + 37 baseline green.
- `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x` — schema-freeze guard green, file unmodified.
- `git diff <phase-base>..HEAD -- voss/harness/session.py voss/harness/recorder.py voss/harness/voss_runtime` — zero frozen-field changes.
- Human checkpoint: Markdown legibility + sign-off forcing-function UX approved on a real run.
</verification>

<success_criteria>
- audit_cmd renders real calibration rates.
- Full audit suite + redaction guard green; 37 baseline preserved.
- Zero frozen-schema drift proven by git diff.
- ROADMAP V9 plan list complete; O6-superseded confirmed.
- Human verification of legibility + forcing-function UX recorded.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-07-SUMMARY.md` when done.
</output>

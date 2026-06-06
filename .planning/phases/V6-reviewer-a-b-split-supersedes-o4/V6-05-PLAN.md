---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 05
type: execute
wave: 4
depends_on: [V6-02, V6-03, V6-04]
files_modified:
  - .planning/ROADMAP.md
autonomous: false
requirements: [VREV-05]
must_haves:
  truths:
    - "All existing O4 reviewer tests regress green (REV-01..05,07,08 behavior intact)"
    - "A's context excludes EM AC/DoD; B is EM-narrative-blind and sees a context packet distinct from A's"
    - "B retains Residual-2 block authority (blocks when A's verification diverges from the idea)"
    - "git diff shows zero field changes on RunRecord / SessionRecord / BudgetScope"
    - "The full board test suite is green before phase verification"
    - "O4 is marked superseded in ROADMAP (bookkeeping)"
  artifacts:
    - path: ".planning/ROADMAP.md"
      provides: "O4 marked superseded-by-V6; V6 plans listed"
      contains: "superseded"
  key_links:
    - from: ".planning/ROADMAP.md V6 section"
      to: "V6-01..05 plans"
      via: "plan checklist updated to executed"
      pattern: "V6-0"
---

<objective>
Close V6: verify the shipped O4 reviewer behavior still holds under the new two-source wiring (VREV-05 / D-14), prove zero field changes on the frozen records (D-15), confirm the full board suite is green, and record the O4-superseded bookkeeping in ROADMAP. This is a verify-and-regress plan — no reviewer rebuild — plus a single human-verify checkpoint for `voss review` output legibility (the one manual-only verification in V6-VALIDATION).

Purpose: Guarantee the wiring delta did not regress the reviewer intelligence or touch frozen schemas, and finalize phase bookkeeping.
Output: Verified green suite, frozen-diff proof, ROADMAP supersession update.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-SPEC.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-CONTEXT.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-VALIDATION.md

<interfaces>
<!-- Regression + supersession targets (V6-CONTEXT D-14/D-15, V6-RESEARCH Q6). -->

Existing O4 reviewer tests (all must regress green):
  tests/harness/board/test_reviewer_a.py, test_reviewer_b.py, test_reviewer_integration.py,
  test_stub.py, test_stub_full_lifecycle.py, test_critic_loop.py, test_verdict.py
Regression-protected behaviors (D-14):
  - A derives bar from the original idea only (NOT EM AC/DoD)
  - B is EM-narrative-blind (reviewer_b.py structural 2-message isolation unchanged)
  - A and B see different context packets
  - B retains Residual-2 block authority

Frozen records (D-15, zero field changes): RunRecord, SessionRecord, voss_runtime.BudgetScope

ROADMAP V6 section (L1903) + O4 row (L54: "⊘ SUPERSEDED by V6") already marked; V6 plan checklist needs filling.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Full regression + frozen-schema diff gate</name>
  <read_first>
    - tests/harness/board/test_reviewer_a.py, tests/harness/board/test_reviewer_b.py, tests/harness/board/test_reviewer_integration.py (the O4 reviewer behavior tests — confirm A-excludes-EM-AC, B-narrative-blind, distinct context, Residual-2 block)
    - V6-VALIDATION.md Per-Requirement Verification Map + Sampling Rate
    - V6-RESEARCH.md Q6 (regression surface — which tests touch the 6-field shape and the back-compat alias)
  </read_first>
  <action>
    (1) Run the full board suite: `.venv/bin/python -m pytest tests/harness/board/ -q`. It MUST be fully green (the V6-01 pre-existing fix + all V6 features landed). If any O4 reviewer test is red, STOP and record the divergence in the summary — V6 must not silently weaken reviewer behavior.
    (2) Confirm the regression-protected behaviors are still asserted by the existing O4 tests (D-14): A's context excludes EM AC/DoD (`test_reviewer_a.py`), B is EM-narrative-blind with a distinct context packet (`test_reviewer_b.py` / `test_reviewer_integration.py`), B retains Residual-2 block authority. If any of these behaviors lacks an asserting test, note the gap (do not add new reviewer features — this is verify-only).
    (3) Frozen-schema diff gate (D-15): run `git diff --stat` plus targeted `git diff` against the files defining `RunRecord`, `SessionRecord`, and `voss_runtime.BudgetScope`; assert the V6 changeset shows ZERO field additions/removals/renames on those dataclasses. Locate them first via grep (`grep -rn "class RunRecord\|class SessionRecord\|class BudgetScope" voss/`), then diff only those files. Record the result in the summary.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/board/ -q` reports 0 failed (full board suite green)
    - `git diff` on the RunRecord / SessionRecord / BudgetScope definition files shows no field-level change (zero added/removed/renamed fields) — captured verbatim in the summary
    - The summary records that A-excludes-EM-AC, B-narrative-blind+distinct-context, and B-Residual-2-block remain test-asserted (or names any gap)
  </acceptance_criteria>
  <done>Full board suite green; O4 reviewer behavior verified intact; frozen records proven field-unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Mark O4 superseded + record V6 plans in ROADMAP</name>
  <read_first>
    - .planning/ROADMAP.md (O4 row at L54 — already "⊘ SUPERSEDED by V6"; the O4 phase block at L1745-1759; the V6 section at L1903-1911)
    - V6-CONTEXT.md D-14 (mark O4 superseded; O4 artifacts retained as reference)
  </read_first>
  <action>
    In `.planning/ROADMAP.md`:
    (1) Confirm/finalize the O4 supersession marker. The O4 summary row (L54) already says "⊘ SUPERSEDED by V6". In the O4 phase block (≈L1745), add a one-line banner that O4 is superseded by V6 and its artifacts (`voss/harness/board/reviewer_a.py`/`reviewer_b.py`/`verdict.py`) are retained as reference — do NOT delete O4's plan list (retained for lineage).
    (2) In the V6 section (≈L1903), add a `Plans:` checklist listing V6-01..05 with brief objectives, mark them executed `[x]` once this plan's prior waves are done, and set the V6 status from "TBD by SPEC.md" to executed/complete per house style.
    Surgical edits only — do not reflow unrelated ROADMAP content.
  </action>
  <verify>
    <automated>grep -c "V6-0" .planning/ROADMAP.md</automated>
  </verify>
  <acceptance_criteria>
    - The O4 phase block contains a superseded-by-V6 banner and retains its original plan list (lineage preserved)
    - The V6 section lists V6-01..05 plans with objectives
    - `grep -c "V6-0" .planning/ROADMAP.md` ≥ 5 (five plans referenced)
    - No unrelated ROADMAP section reflowed (diff limited to O4 + V6 blocks)
  </acceptance_criteria>
  <done>O4 is marked superseded-by-V6 with artifacts retained; the V6 plan checklist is recorded in ROADMAP.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    The `voss review` CLI now renders persisted per-card review artifacts. All automated gates (full board suite, frozen-schema diff, O4 regression) are green. The only behavior an automated test cannot judge is the human legibility of the `voss review` output layout (V6-VALIDATION manual-only row).
  </what-built>
  <how-to-verify>
    1. From a project dir that has at least one completed board run (a `.voss/sessions/<root_id>/` with `*.review.json` sidecars), run: `voss review`
    2. Confirm it prints, per card and ordered by card: A's verification (test path / rubric + pass/fail result), B's verdict (verdict / conf / tier / domain_inferred / evidence_refs / notes), and the final Done/Blocked outcome.
    3. Run `voss review <known_run_id>` and confirm the same output for that explicit run.
    4. Run `voss review does-not-exist` and confirm a non-zero exit with an `unknown run_id` message on stderr.
    5. Judge: is the per-card A+B+outcome layout legible and unambiguous (matches the `voss board` / `voss sessions` house style)?
  </how-to-verify>
  <resume-signal>Type "approved" if the output is legible, or describe the layout issues to fix.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| V6 changeset → frozen record schemas | The git-diff gate is the boundary check that no frozen dataclass field changed |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V6-05-01 | Tampering | accidental field change to RunRecord/SessionRecord/BudgetScope | mitigate | Explicit `git diff` gate on those definition files (D-15); zero field-level change required and recorded in the summary |
| T-V6-05-02 | Repudiation | O4 lineage lost on supersession | mitigate | O4 plan list retained in ROADMAP (artifacts kept as reference, not deleted) — supersession is a banner, not a removal |
| T-V6-05-03 | Tampering | silent weakening of reviewer behavior (A sees EM AC, B sees narrative) | mitigate | Verify-only task confirms the O4 behavior tests still assert A-excludes-EM-AC / B-narrative-blind / Residual-2; any gap is surfaced, not patched-over |
| T-V6-05-SC | Tampering | npm/pip/cargo installs | mitigate | Zero new dependencies; no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/ -q` — full board suite 0 failed.
- `git diff` on RunRecord/SessionRecord/BudgetScope definition files — zero field changes.
- ROADMAP: O4 superseded banner present (lineage retained); V6-01..05 listed.
- Human sign-off: `voss review` output legible.
</verification>

<success_criteria>
- Existing O4 reviewer tests regress green (VREV-05 / D-14).
- A-excludes-EM-AC, B-narrative-blind+distinct-context, B-Residual-2-block verified intact.
- Zero field changes on RunRecord/SessionRecord/BudgetScope (D-15).
- O4 marked superseded (artifacts retained); V6 plans recorded.
- `voss review` output human-approved.
</success_criteria>

<output>
Create `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-05-SUMMARY.md` when done.
</output>

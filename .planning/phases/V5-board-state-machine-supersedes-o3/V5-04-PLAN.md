---
phase: V5-board-state-machine-supersedes-o3
plan: 04
type: execute
wave: 3
depends_on: [V5-02, V5-03]
files_modified:
  - tests/harness/board/test_session_tree_additive.py
  - .planning/ROADMAP.md
  - .planning/STATE.md
autonomous: true
requirements: [VBOARD-01, VBOARD-02, VBOARD-04, VBOARD-05, VBOARD-06, VBOARD-08, VBOARD-09]
must_haves:
  truths:
    - "The full board suite is green: all V5-new tests pass AND the previously pre-existing stale failure is fixed (zero failures)"
    - "The shipped O3 surface still holds: 6 columns, per-column WIP→BoardWIPError, gate→BoardGateError, Done double-gate, timeout/critic→Blocked, transition persistence, Card↔node 1:1"
    - "git diff shows zero field changes on RunRecord / SessionRecord / BudgetScope / SessionTreeNode (frozen schemas untouched)"
    - "O3 is marked superseded by V5 in ROADMAP.md and STATE.md; V5 is recorded complete"
  artifacts:
    - path: "tests/harness/board/test_session_tree_additive.py"
      provides: "stale test_exit_reasons_is_sorted_superset_of_pre_o3 fixed (equality → subset check)"
      contains: "issubset"
    - path: ".planning/ROADMAP.md"
      provides: "V5 marked complete; O3 supersession confirmed"
      contains: "SUPERSEDED by V5"
    - path: ".planning/STATE.md"
      provides: "V5 row + log entry recording phase completion"
      contains: "VBOARD-03/07/10"
  key_links:
    - from: "tests/harness/board/ full suite"
      to: "zero failures"
      via: "regression run after V5-02 + V5-03 + the stale-test fix"
      pattern: "passed"
---

<objective>
Close Phase V5: prove the shipped O3 board surface (VBOARD-01/02/04/05/06/08/09) still regresses green after the V5-02/V5-03 changes, fix the one known pre-existing stale test so the suite is fully green, assert the frozen schemas are untouched, and record the O3→V5 supersession + V5 completion in ROADMAP.md and STATE.md. This is the phase-closing plan; it runs after V5-02 (machine) and V5-03 (CLI) land.

Purpose: SPEC reqs 4 ("Shipped surface verification") and 5 ("O3 supersession + V4 dependency"). Turn a 1-pre-existing-failure baseline into a fully green board suite and lock the bookkeeping.

Output: the stale-test 1-line fix, a green full board suite, a frozen-schema git-diff assertion, and updated ROADMAP/STATE bookkeeping.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-SPEC.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-RESEARCH.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-PATTERNS.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-VALIDATION.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-02-PLAN.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-03-PLAN.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix the stale exit-reasons test + full board-suite regression (SPEC req 4)</name>
  <files>tests/harness/board/test_session_tree_additive.py</files>
  <read_first>
    - tests/harness/board/test_session_tree_additive.py lines 82-86 (the stale `test_exit_reasons_is_sorted_superset_of_pre_o3`: line 86 asserts `EXIT_REASONS == pre_o3 | {"timeout", "killed"}` but the actual set ALSO contains `"error"`, so the equality still fails — confirmed by running it)
    - V5-PATTERNS.md §"tests/harness/board/test_session_tree_additive.py — 1-line stale assertion fix" (fix = change equality to a subset check; do NOT touch session.py)
    - V5-RESEARCH.md §"Research Focus 4: Verification Surface" (the test→BOARD-## map: which existing files cover VBOARD-01/02/04/05/06/08/09) and Open Question 3 (RESOLVED: fix the stale assertion, do not modify session.py's EXIT_REASONS)
    - V5-VALIDATION.md §"Per-Task Verification Map" rows for `verify` (regression command) and the stale-test fix
  </read_first>
  <action>
    Fix the stale assertion in `test_exit_reasons_is_sorted_superset_of_pre_o3` (line 86): replace the exact-equality `assert EXIT_REASONS == pre_o3 | {"timeout", "killed"}` with a subset check that the test name promises — assert that `(pre_o3 | {"timeout", "killed"}).issubset(EXIT_REASONS)` (those reasons are all present), NOT exact-set equality. This tolerates the additional `"error"` reason added after O3 without modifying `voss/harness/session.py`'s `EXIT_REASONS`. Do NOT touch `session.py`. Then run the FULL board suite to confirm zero failures: the V5-02 + V5-03 changes greened the three new scaffolds, and this fix clears the last pre-existing failure. While running, confirm the shipped-surface tests enumerated in V5-RESEARCH §"Research Focus 4" still pass (6 columns, WIP→BoardWIPError, gate→BoardGateError, Done double-gate, timeout/critic→Blocked, transition persistence, Card↔node 1:1) — these are the VBOARD-01/02/04/05/06/08/09 regression coverage and require no code changes, only verification.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -q --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - The full board suite runs with ZERO failures: `.venv/bin/python -m pytest tests/harness/board/ -q` exits 0 (no `FAILED`, no `ERROR` in the summary).
    - `grep -n "issubset" tests/harness/board/test_session_tree_additive.py` shows the fixed assertion uses a subset check, not `==` on the full set.
    - `git diff --name-only voss/harness/session.py` shows NO change to session.py (the fix is test-only).
    - The shipped-surface regression files all pass: `.venv/bin/python -m pytest tests/harness/board/test_columns_and_unknown.py tests/harness/board/test_wip_cap.py tests/harness/board/test_gate_predicates_basic.py tests/harness/board/test_stub_full_lifecycle.py tests/harness/board/test_card_node_wiring.py tests/harness/board/test_transition_count_invariant.py -q` exits 0.
  </acceptance_criteria>
  <done>The full board suite is green (zero failures); the stale exit-reasons test is fixed as a test-only subset check; session.py is untouched; all enumerated shipped-surface tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Frozen-schema assertion + O3 supersession bookkeeping (SPEC req 5)</name>
  <files>.planning/ROADMAP.md, .planning/STATE.md</files>
  <read_first>
    - V5-RESEARCH.md §"Research Focus 5: Frozen-Schema Guard" (the exact files that must show zero field changes: RunRecord/SessionRecord in voss/harness/session.py, BudgetScope in voss_runtime, SessionTreeNode in voss/harness/session_tree.py) and §"Architectural Responsibility Map" row "O3 supersession bookkeeping"
    - V5-VALIDATION.md §"Manual-Only Verifications" (frozen-schema git-diff assertion + O3-superseded confirmation are the two manual checks)
    - .planning/ROADMAP.md line ~53 (O3 row — already banners "⊘ SUPERSEDED by V5"; confirm/reaffirm) and line ~68 (V5 row — `Success Criteria` cell currently "TBD by SPEC.md" → update to reflect completion)
    - .planning/STATE.md line ~67 (the V5 row stating "planner stalled at 1/N plans" → update to V5 complete) and the dated log section near line ~73 (add a dated V5-complete entry mirroring the existing 2026-06-06 partial-plan entry style)
  </read_first>
  <action>
    First, ASSERT the frozen-schema invariant: run `git diff` on the V5 working tree and confirm ZERO field add/remove/rename on `RunRecord`/`SessionRecord` (voss/harness/session.py), `BudgetScope` (voss_runtime), and `SessionTreeNode` (voss/harness/session_tree.py). The V5 code touched only machine.py, cli.py, cli_view.py (new), and the two test files — none of the frozen-schema modules should appear in `git diff --name-only` for source changes. If any frozen module shows a field change, STOP and flag it (do not paper over). Then update bookkeeping. In `.planning/ROADMAP.md`: confirm the O3 row (~line 53) still banners "⊘ SUPERSEDED by V5" (leave as-is if present), and update the V5 row (~line 68) `Success Criteria` cell from "TBD by SPEC.md" to a completion marker noting the SPEC acceptance criteria met (Card fields idea/role/acceptance_criteria/verification_requirement + self-Done guard + `voss board` CLI + shipped-surface regress green). In `.planning/STATE.md`: update the V5 row (~line 67) from "planner stalled at 1/N plans" to "V5 complete — VBOARD-03/07/10 implemented (Card fields, self-Done guard, `voss board` CLI); shipped surface BOARD-01/02/04/05/06/08/09 regressed green; O3 superseded", and prepend a dated `2026-06-06 — Phase V5 (Board State Machine, supersedes O3) COMPLETE` log entry in the dated log section mirroring the existing partial-plan entry style. Keep edits surgical — only the V5/O3 lines and one new log entry; do not reformat surrounding rows.
  </action>
  <verify>
    <automated>test -z "$(git diff --name-only -- voss/harness/session.py voss/harness/session_tree.py)" && grep -q "SUPERSEDED by V5" .planning/ROADMAP.md && grep -q "VBOARD-03/07/10" .planning/STATE.md && echo BOOKKEEPING-OK</automated>
  </verify>
  <acceptance_criteria>
    - `git diff --name-only -- voss/harness/session.py voss/harness/session_tree.py` returns EMPTY (frozen schemas untouched); BudgetScope source in voss_runtime likewise shows no field change.
    - `.planning/ROADMAP.md` still contains "SUPERSEDED by V5" on the O3 row, and the V5 row `Success Criteria` cell no longer reads "TBD by SPEC.md".
    - `.planning/STATE.md` V5 row no longer says "planner stalled at 1/N plans"; a dated `Phase V5 ... COMPLETE` log entry is present; `grep -q "VBOARD-03/07/10" .planning/STATE.md` succeeds.
    - The verify command prints `BOOKKEEPING-OK`.
    - Edits are surgical: `git diff --stat .planning/ROADMAP.md .planning/STATE.md` shows only the V5/O3 lines + one new log entry changed (no wholesale reformatting).
  </acceptance_criteria>
  <done>Frozen schemas confirmed unchanged via git diff; O3 marked superseded by V5 and V5 recorded complete in ROADMAP.md + STATE.md with a dated log entry; edits are surgical.</done>
</task>

</tasks>

<verification>
- Full board suite green: `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short` → exit 0, zero failures (V5-new tests + shipped-surface regress + the fixed stale test all pass).
- Frozen-schema invariant: `git diff --name-only` over the whole V5 changeset shows source changes ONLY in voss/harness/board/machine.py, voss/harness/board/cli_view.py (new), voss/harness/cli.py, and the two test files — never session.py, session_tree.py, voss_runtime, verdict.py.
- Bookkeeping: ROADMAP.md confirms O3 superseded by V5; STATE.md records V5 complete with the VBOARD-03/07/10 implementation summary.
</verification>

<success_criteria>
- SPEC req 4: shipped board surface (VBOARD-01/02/04/05/06/08/09) regresses green; the full board suite has zero failures (the pre-existing stale test is fixed test-only).
- SPEC req 5: frozen schemas (RunRecord/SessionRecord/BudgetScope/SessionTreeNode) show zero field changes; O3 marked superseded by V5; V5 sits on the V4 session-tree substrate with no V5-owned budget logic.
- ROADMAP.md + STATE.md updated surgically to record completion; session.py untouched.
</success_criteria>

<output>
Create `.planning/phases/V5-board-state-machine-supersedes-o3/V5-04-SUMMARY.md` when done.
</output>

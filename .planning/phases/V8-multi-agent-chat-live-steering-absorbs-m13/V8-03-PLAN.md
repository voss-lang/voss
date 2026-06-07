---
phase: V8-multi-agent-chat-live-steering-absorbs-m13
plan: 03
type: execute
wave: 3
depends_on: ["V8-02"]
files_modified:
  - tests/harness/test_multiagent_fanout.py
  - tests/harness/test_multiagent_recursion.py
  - .planning/ROADMAP.md
  - .planning/STATE.md
autonomous: true
requirements: [VMAG-UNIFY, VMAG-07]
must_haves:
  truths:
    - "MAG-01..09 regress green: non-blocking spawn, immediate handle, status, gather, steer-between-iterations, child budget, quiet-by-default TUI panel + reveal"
    - "Migrated even-split/no-oversell/depth-2 tests pass against the V4-backed path with xfail markers dropped"
    - "test_subagent_recursion.py stays green with zero changes"
    - "Ctrl+C interrupts via _teardown_orphans + finalize"
    - "git diff shows zero field changes on RunRecord/SessionRecord/BudgetScope"
    - "M13 marked absorbed into V8 in ROADMAP and STATE"
  artifacts:
    - path: "tests/harness/test_multiagent_fanout.py"
      provides: "TestEvenSplitRebalance + TestNoOversell migrated to V4-backed path, xfail dropped"
      contains: "node_manager"
    - path: "tests/harness/test_multiagent_recursion.py"
      provides: "TestDepth2 migrated to persisted nested-node path, xfail dropped"
      contains: "SessionTreeManager"
  key_links:
    - from: "tests/harness/test_multiagent_fanout.py"
      to: "voss.harness.session_tree.SessionTreeManager"
      via: "V4-backed allocation assertions replacing M13Allocator"
      pattern: "SessionTreeManager"
---

<objective>
Close V8: migrate the M13Allocator-direct tests onto the V4-backed path (dropping their xfail markers), regression-verify MAG-01..09 + back-compat + frozen schema, and record M13 absorption in ROADMAP/STATE.

Purpose: V8-02 removed `M13Allocator`, so the three test classes that referenced it directly (`TestEvenSplitRebalance`, `TestNoOversell` in fanout; `TestDepth2` in recursion) must migrate to assert the V4-backed behavior. The remaining MAG surface (orphan teardown, steer, back-compat recursion pin, `test_subagent_recursion.py`) regresses green unchanged. Finalize the phase bookkeeping (VMAG-UNIFY closure of the unification + VMAG-07 recursion verification).

Output: Two migrated test files (xfail markers removed); ROADMAP/STATE marked M13-absorbed; full-suite green confirmation including the frozen-schema redaction gate.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-SPEC.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-VALIDATION.md
@.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-PATTERNS.md

<interfaces>
<!-- Post-V8-02 surface the migrated tests assert against. -->
From voss/harness/multiagent.py (post V8-02):
- `M13Allocator` REMOVED. `DEFAULT_VIABLE_FLOOR = 2_000`, `VIABLE_FLOOR` alias present.
- `attach_multiagent_tools(..., node_manager=...)` (renamed from `allocator=`).
From voss/harness/session_tree.py:
- `SessionTreeNode.create_root(*, cwd, limit)`, `SessionTreeManager(root, *, reserve, cwd)`, `.allocate_child(limit, *, scope=None, role=None)`, `.release_child(node_id)`, `BudgetAllocationError`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migrate fanout + recursion tests off M13Allocator to the V4-backed path</name>
  <files>tests/harness/test_multiagent_fanout.py, tests/harness/test_multiagent_recursion.py</files>
  <read_first>
    - `tests/harness/test_multiagent_fanout.py` lines 176-264 (`TestEvenSplitRebalance::test_even_split_then_rebalance` and `TestNoOversell::test_concurrent_allocation_never_oversells` — both currently use `multiagent.M13Allocator` directly + `xfail`) and line 284 (`TestOrphanTeardown` — NOT xfail, leave unchanged).
    - `tests/harness/test_multiagent_recursion.py` lines 51-65 (`TestDepth2::test_nested_budget_is_strictly_bounded`), 67-301 (`TestDepth2::test_three_distinct_panels_then_clean_teardown` — uses the real `attach_multiagent_tools` path), and 304-358 (`TestBackCompatRecursionPinIntact` — leave UNCHANGED, byte-stable).
    - V8-PATTERNS.md sections "Migration: ... TestEvenSplitRebalance + TestNoOversell" (707-773) and "Migration: ... TestDepth2" (777-820) — the exact V4-backed replacements.
    - V8-RESEARCH.md "Research Focus Area 2" (even-split is calculation-only on V4 since limits are immutable — Pitfall 3: migrate the "survivor allotment increased" assertion to "next spawn gets a larger even slice").
  </read_first>
  <action>
    In `test_multiagent_fanout.py`:
    - `TestEvenSplitRebalance::test_even_split_then_rebalance` — drop the `xfail` marker. Replace the `M13Allocator`-direct body with the V4-backed tool-surface form (V8-PATTERNS lines 726-742): create a root via `SessionTreeNode.create_root(cwd=tmp_path, limit=...)`, `SessionTreeManager(root, reserve=0, cwd=tmp_path)`, attach with `node_manager=`, spawn 3 children, parse each `budget=<N>` from the spawn returns, assert each allotment ≈ `root.limit // 3`. Replace the live "survivor allotment increases" assertion with: after gathering one child, a subsequent spawn receives a larger even slice (recomputed from freed budget via `release_child`).
    - `TestNoOversell::test_concurrent_allocation_never_oversells` — drop the `xfail` marker. Replace the body with the V4 `allocate_child` concurrency form (V8-PATTERNS lines 759-771): `SessionTreeManager` + `asyncio.gather` of many `allocate_child(VIABLE_FLOOR)`, assert `sum(granted limits) <= root.limit - reserve`. Replace any `multiagent.M13Allocator.VIABLE_FLOOR` reference with `multiagent.DEFAULT_VIABLE_FLOOR` (or `multiagent.VIABLE_FLOOR`).
    - Leave `TestConcurrentInFlight`, `TestOrphanTeardown`, and any other class unchanged. If `TestConcurrentInFlight` (or others) still carries `xfail(strict=False)` and now XPASSES against the V4 path, drop that marker too so it becomes a hard gate (per V8-PATTERNS "Test Class Non-xfail Convention"); otherwise leave as-is.

    In `test_multiagent_recursion.py`:
    - `TestDepth2::test_nested_budget_is_strictly_bounded` — drop `xfail`. Replace with the V4 per-node form (V8-PATTERNS lines 796-807): root → `root_mgr.allocate_child(...)` → child → `child_mgr = SessionTreeManager(child, reserve=0, cwd=tmp_path)` → `child_mgr.allocate_child(...)` → grandchild; assert `grandchild.envelope["limit"] <= child.envelope["limit"] <= root.envelope["limit"]` AND that the child node persisted (glob under the session dirs).
    - `TestDepth2::test_three_distinct_panels_then_clean_teardown` — drop `xfail`; change the `attach_multiagent_tools(..., allocator=None)` call to `node_manager=<root manager>`; the provider/renderer/assertion structure is otherwise unchanged.
    - `TestBackCompatRecursionPinIntact` — leave UNCHANGED (byte-stable).

    Do NOT touch `tests/harness/test_subagent_recursion.py` (research-confirmed zero changes). Do NOT touch `test_multiagent_steer.py` (it uses the tool surface, which V8-02 preserved — it should pass unchanged; verify in Task 2).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_recursion.py -q 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'M13Allocator' tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_recursion.py` returns 0 for both (all direct references migrated).
    - `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_recursion.py -q` passes with NO xpassed/xfailed entries on the migrated classes (markers dropped → hard pass).
    - `tests/harness/test_multiagent_recursion.py::TestBackCompatRecursionPinIntact` still passes unchanged.
    - `git diff tests/harness/test_subagent_recursion.py` is empty (untouched).
  </acceptance_criteria>
  <done>The three M13Allocator-direct test classes are migrated to the V4-backed path with xfail markers dropped and pass as hard gates; the back-compat recursion pin and test_subagent_recursion.py are untouched and green.</done>
</task>

<task type="auto">
  <name>Task 2: Full-suite regression + frozen-schema gate + MAG-01..09 verification</name>
  <files>(no source edits — verification + evidence capture only)</files>
  <read_first>
    - V8-VALIDATION.md "Per-Task Verification Map" + "Manual-Only Verifications" (the MAG-01..09 regression rows, the Ctrl+C/teardown row, the frozen-schema row, and the two manual-only TUI/doc rows).
    - V8-RESEARCH.md "Research Focus Area 6: Frozen Schema Guard" (the `git diff` zero-field invariant on RunRecord/SessionRecord/BudgetScope) + Open Question 4 (the pre-existing `test_multiagent_chat_e2e` AUTH_STEERED failure is out of scope).
  </read_first>
  <action>
    Run the regression gates and capture results into the SUMMARY (no source changes):
    1. MAG-01..09 + steer regress: `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_recursion.py tests/harness/test_multiagent_steer.py -q`.
    2. New V8 file: `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q`.
    3. Back-compat pin: `.venv/bin/python -m pytest tests/harness/test_subagent_recursion.py -q`.
    4. Ctrl+C / orphan teardown: `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py::TestOrphanTeardown -q`.
    5. Frozen-schema gate: `.venv/bin/python -m pytest tests/harness/test_session_tree.py tests/harness/test_session_redaction.py -q` AND `git diff --stat -- voss/harness/session.py voss_runtime/` to confirm zero field changes on RunRecord/SessionRecord/BudgetScope (V8 touched none of these).
    6. Full harness suite: `.venv/bin/python -m pytest tests/harness/ -q --tb=short`.

    Confirm the ONLY pre-existing failure that may appear is `tests/e2e/test_multiagent_chat_e2e.py::test_multiagent_chat_e2e` (AUTH_STEERED) — flag it as a known pre-existing failure (out of scope per V8-RESEARCH OQ-4); V8 must not have ADDED any new failure. If any OTHER test fails, stop and report — do not paper over it.

    Manual-only (record as checkboxes in SUMMARY for the operator, per V8-VALIDATION "Manual-Only Verifications"): TUI panel quiet-by-default + reveal (launch `voss chat`, spawn agents, confirm panel quiet, trigger reveal key, confirm Ctrl+C interrupts).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/ -q --tb=short 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/ -q` passes with zero failures (the e2e AUTH_STEERED test is under `tests/e2e/`, not `tests/harness/`, so it does not appear in this run).
    - `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -q` passes (frozen RunRecord/SessionRecord).
    - `git diff --stat -- voss/harness/session.py voss_runtime/` shows no field-level changes (V8 did not touch these files).
    - `.venv/bin/python -m pytest tests/harness/test_subagent_recursion.py -q` green.
  </acceptance_criteria>
  <done>The full harness suite is green; MAG-01..09 + steer + orphan-teardown + back-compat regress; frozen schemas show zero field drift; the only known failure (e2e AUTH_STEERED) is pre-existing and flagged.</done>
</task>

<task type="auto">
  <name>Task 3: Bookkeeping — mark M13 absorbed in ROADMAP + STATE</name>
  <files>.planning/ROADMAP.md, .planning/STATE.md</files>
  <read_first>
    - `.planning/ROADMAP.md` line 27 (the M13 row, already marked "⊘ ABSORBED into V8") and lines 640-671 (the "Phase M13" section header + plan list — confirm the absorbed banner is complete) and line 71 (the V8 row).
    - `.planning/STATE.md` line 48 (the M13 phase-status row, already noting "⊘ ABSORBED into V8") and the "Recent Activity" section format.
    - V8-SPEC.md requirement 6 (bookkeeping: ROADMAP/STATE mark M13 absorbed; no ADE-side multiagent panel built in V8 — ADE → V11).
  </read_first>
  <action>
    Update the two planning docs to record V8 completion of the M13 absorption (these rows already carry "ABSORBED into V8" banners from the 2026-06-05 roadmap edit; this task finalizes them to reflect V8 having SHIPPED the unification):
    - `.planning/ROADMAP.md`: in the M13 phase section (around lines 640-655), update the section banner to state M13 is absorbed AND that V8 has now delivered the persisted-unification surface (the M13 in-memory plans are superseded by the V8 V4-backed implementation; M13 artifacts retained as reference). In the V8 row (line 71), note the V8 plan count (3 plans, 3 waves) and that ADE child panels are deferred to V11.
    - `.planning/STATE.md`: update the M13 phase-status row (line 48) to reflect "ABSORBED into V8 — V8 shipped the V4-backed persisted unification (2026-06-06)". Add a "Recent Activity" bullet summarizing V8: VMAG-10 (persist), VMAG-UNIFY (single V4 allocator, M13Allocator removed), VMAG-07 (per-node-manager recursion, no depth constant), VMAG-ROOT (chat root envelope); MAG-01..09 regressed green; frozen schemas unchanged; no ADE panel (→V11).

    Confirm NO ADE-side multiagent panel was built (V8 surface is the existing TUI only). This is a documentation task — make no code or test changes. Keep edits surgical (update existing banners/rows; do not restructure the docs).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -c 'ABSORBED into V8\|absorbed into V8' .planning/ROADMAP.md .planning/STATE.md 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n 'V8' .planning/STATE.md` shows a Recent Activity bullet summarizing the V8 unification (VMAG-10/UNIFY/07/ROOT).
    - `grep -ni 'absorbed into v8' .planning/ROADMAP.md` returns ≥ 1 (M13 absorption banner present).
    - `grep -ni 'V11\|ADE' .planning/ROADMAP.md | grep -i 'v8\|panel'` confirms ADE child panels are noted as deferred to V11 (no ADE panel built in V8).
    - No changes to any file under `voss/` or `tests/` in this task.
  </acceptance_criteria>
  <done>ROADMAP and STATE record M13 as absorbed and V8 as having shipped the V4-backed persisted unification; ADE child panels noted as V11; no code/test changes in this task.</done>
</task>

</tasks>

<verification>
- Full harness suite green: `.venv/bin/python -m pytest tests/harness/ -q --tb=short`.
- Migrated fanout/recursion classes pass with xfail dropped; `M13Allocator` referenced nowhere in tests.
- `test_subagent_recursion.py` and `TestBackCompatRecursionPinIntact` untouched and green.
- Frozen-schema gate (`test_session_redaction.py`) green; `git diff` zero field changes on RunRecord/SessionRecord/BudgetScope.
- Pre-existing `test_multiagent_chat_e2e.py::test_multiagent_chat_e2e` (AUTH_STEERED) is the only known failure — pre-existing, out of scope, not newly introduced.
- ROADMAP/STATE mark M13 absorbed + V8 shipped; ADE → V11.
</verification>

<success_criteria>
- MAG-01..09 + steer + orphan-teardown regress green; the three M13Allocator-direct tests are migrated to the V4-backed path with markers dropped.
- Frozen schemas show zero field drift; `test_subagent_recursion.py` byte-stable green.
- M13 absorption recorded in ROADMAP + STATE; no ADE panel built in V8.
</success_criteria>

<output>
Create `.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-03-SUMMARY.md` when done.
</output>

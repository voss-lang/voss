---
phase: V8-multi-agent-chat-live-steering-absorbs-m13
plan: 03
type: summary
status: complete
requirements: [VMAG-UNIFY, VMAG-07]
files_modified:
  - tests/harness/test_multiagent_fanout.py
  - tests/harness/test_multiagent_recursion.py
  - .planning/ROADMAP.md
  - .planning/STATE.md
---

# V8-03 Summary — Migrate M13Allocator tests to V4, regress, M13-absorbed bookkeeping

## Task 1 — Migrate fanout + recursion tests off M13Allocator

- **TestEvenSplitRebalance** (fanout) — xfail dropped; rewritten to the V4 tool
  surface (root + `SessionTreeManager(reserve=0)` + `node_manager=`, spawn 3
  children, parse `budget=<N>`). Asserts the REAL V8-02 behavior: each slice
  ≥ `VIABLE_FLOOR`, no oversell, and after gather a later spawn gets a LARGER
  slice (freed budget via `release_child`). Note: V8-02's headroom-reserving
  `//(active+2)` split is not exact `limit//N` equality (V4 limits are
  immutable — no M13 rebalance-down), so the migration asserts coexistence +
  rebalance-on-release rather than equal shares.
- **TestNoOversell** (fanout, all 4 methods) — xfail dropped; migrated to V4:
  concurrent `allocate_child` no-oversell (`sum ≤ limit − reserve`); idempotent
  `release_child` (double-release removes one node, not two); per-node depth
  bound (`grandchild ≤ child ≤ root`).
- **TestDepth2** (recursion) — xfail dropped; `test_nested_budget_is_strictly_
  bounded` → V4 per-node (root_mgr → child → child_mgr → grandchild; asserts the
  budget chain AND on-disk persistence); `test_three_distinct_panels_then_clean_
  teardown` → injected `node_manager=<root mgr>` (reserve=`DEFAULT_PARENT_RESERVE`),
  rest unchanged.
- **TestConcurrentInFlight** (fanout, MAG-01) — was xfail-xpassing against the V4
  path; marker dropped → hard gate (per V8-PATTERNS non-xfail convention).
- `TestBackCompatRecursionPinIntact` + `test_subagent_recursion.py` — untouched,
  byte-stable green. `M13Allocator` referenced nowhere in either test file (0).

## Task 2 — Full-suite regression + frozen-schema gate

- V8 surface suites (`test_multiagent_session_tree` 12, `_fanout`, `_recursion`,
  `_steer`, `test_subagent_recursion`, `test_session_tree` 40,
  `test_session_redaction`) — all green.
- **Zero new failures (rigorously checked):** captured `tests/harness/` failure
  set with the V8-03 test edits stashed vs applied — **IDENTICAL (22 = 22, same
  test ids)**. All 22 are pre-existing in subsystems V8 did not touch:
  memory/recall/slash `openai-401` (no API key, environmental), stale
  EXIT_REASONS asserts (red since O3/O5 per STATE), `t1_acceptance` perf,
  `tui/test_no_new_runtime_hooks` (hash baseline on `recorder.py`, which V8 left
  byte-unchanged), `repl_slash` `## Project Index`, `conventions`/`dog07` env.
  (V8 production files are committed, so the relevant proof is that every failure
  is outside multiagent/session_tree/cli, whose suites all pass.)
- Frozen records (`session.py`/`recorder.py`/`voss_runtime`) — zero git drift vs
  the pre-V8 baseline `839aa6c`. Only new dataclass field in the phase:
  `ChildHandle.node` (V8-02).
- Pre-existing `tests/e2e/test_multiagent_chat_e2e::test_multiagent_chat_e2e`
  (AUTH_STEERED, line 399) — unchanged, not regressed (no crash/TypeError).

### Manual-only (operator checklist — per V8-VALIDATION)
- [ ] Launch `voss chat`, spawn agents → panels quiet by default.
- [ ] Trigger the reveal key → child panels show.
- [ ] Ctrl+C mid-fan-out → `_teardown_orphans` cancels + finalizes; no leak.

## Task 3 — Bookkeeping (docs only)

- **ROADMAP.md**: V8 row → `✅ COMPLETE` (3 plans/3 waves; V4-backed unification;
  ADE child panels deferred to V11); M13 summary row + the `## Phase M13` section
  banner updated to `⊘ ABSORBED into V8 — SHIPPED 2026-06-06` (M13 artifacts
  retained as reference; in-memory design superseded).
- **STATE.md**: M13 phase-status row → "ABSORBED into V8 — V8 shipped …"; V8 row →
  `✅ COMPLETE`; dated Recent Activity bullet summarizing VMAG-10/UNIFY/07/ROOT,
  the 3 reconciled plan contradictions, the zero-new-failure proof, and ADE→V11.
- No code/test changes in this task (only the Task-1 test migrations appear under
  `tests/`).

## V8 phase status

VMAG-10 (persist), VMAG-UNIFY (single V4 allocator, `M13Allocator` removed),
VMAG-07 (per-node recursion, no depth constant), VMAG-ROOT (chat root envelope)
all shipped. M13 absorbed; no ADE panel built (→V11). Phase complete.

Resume: V9 (Audit Product, depends V7 ✓) or V10/V11/V12.

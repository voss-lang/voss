---
phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone
plan: 01
subsystem: testing
tags: [session-tree, budget-envelope, dataclass, frozenset, schema-freeze, exit-reasons]

# Dependency graph
requires:
  - phase: O1-session-tree-keystone
    provides: SessionTreeNode, SessionTreeManager.allocate_child, _hydrate_node, finalize_node, EXIT_REASONS frozenset
provides:
  - SessionTreeNode.scope + SessionTreeNode.role nullable fields (populated at spawn when known, null otherwise)
  - allocate_child keyword-only scope/role kwargs that persist atomically with the node file
  - _hydrate_node back-compat for pre-V4 node files (scope/role default to None)
  - EXIT_REASONS now accepts "error" for exception-path subagent finalize
  - TestSchemaExtension test class + extended _NODE_JSON_KEYS schema-lock guard
affects: [V4-02-guard-finalize, V4-03-export-cli, V7-em-dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive nullable dataclass fields (= None defaults, no field(default_factory)) placed before private init=False fields"
    - "_hydrate_node setdefault back-compat per new field (mirrors transitions/retry_notes)"
    - "Additive EXIT_REASONS frozenset member with trailing rationale comment (precedent: timeout/killed)"

key-files:
  created: []
  modified:
    - voss/harness/session_tree.py
    - voss/harness/session.py
    - tests/harness/test_session_tree.py

key-decisions:
  - "Added 'error' to EXIT_REASONS as a distinct exit reason rather than overloading 'interrupt' (resolves RESEARCH Open Question 1 / Assumption A4)"
  - "Extended _NODE_JSON_KEYS (SessionTreeNode schema-lock) intentionally — distinct from the frozen SessionRecord/RunRecord/BudgetScope schemas which were NOT touched"

patterns-established:
  - "Nullable spawn metadata on SessionTreeNode: scope/role default None, persisted via to_dict/asdict automatically"

requirements-completed: [VTREE-01, VTREE-08, VTREE-05, VTREE-06]

# Metrics
duration: 8min
completed: 2026-06-06
---

# Phase V4-01: Session-Tree Schema Foundation Summary

**Additive nullable scope/role fields on SessionTreeNode with spawn-time persistence + back-compat hydrate, plus the "error" EXIT_REASONS member — all under the frozen-record invariant.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- `SessionTreeNode` carries nullable `scope` + `role` fields (default `None`), inserted between `retry_notes` and the private `_budget`/`_finalized` fields. `_NODE_FIELDS` auto-rebuilds; `to_dict()` picks them up via `asdict`.
- `SessionTreeManager.allocate_child` gained keyword-only `scope`/`role` params and passes them into the `SessionTreeNode(...)` constructor inside the existing `async with self._lock:` block (lock scope unchanged).
- `_hydrate_node` appends `setdefault("scope", None)` / `setdefault("role", None)` so pre-V4 node files (lacking the keys) hydrate deterministically with null values.
- `EXIT_REASONS` frozenset gained `"error"` (additive member, not a record field) so the V4-02 exception-path finalize is well-formed.
- `_NODE_JSON_KEYS` schema-lock guard extended with `"scope"`/`"role"`; new `TestSchemaExtension` class (4 tests) proves default-null, spawn-persist, spawn-without-kwargs-null, and pre-V4-hydrate behaviors.

## Files Created/Modified
- `voss/harness/session_tree.py` — scope/role dataclass fields, _hydrate_node setdefaults, allocate_child kwargs + constructor pass-through.
- `voss/harness/session.py` — `"error"` added to EXIT_REASONS frozenset + rationale comment. No dataclass field touched.
- `tests/harness/test_session_tree.py` — `_NODE_JSON_KEYS` extended with scope/role, `_hydrate_node` import added, new `TestSchemaExtension` class.

## Decisions Made

**1. EXIT_REASONS "error" (resolves RESEARCH Open Question 1 / Assumption A4) — INTENTIONAL, NOT A FREEZE VIOLATION.**
Added `"error"` to the `EXIT_REASONS` frozenset rather than overloading `"interrupt"`. `EXIT_REASONS` is a module-level frozenset constant, NOT a field on SessionRecord/RunRecord/BudgetScope — adding a member is purely additive and does not change RunRecord's 24-field count or any key-set. Follows the established additive-member precedent ("timeout" in O3, "killed" in O5, each with a trailing comment). `tests/harness/test_session_redaction.py` passes UNMODIFIED.

**2. `_NODE_JSON_KEYS` extension (added "scope"/"role") — INTENTIONAL, NOT A REDACTION-FREEZE VIOLATION.**
`_NODE_JSON_KEYS` is the SessionTreeNode schema-lock guard, DISTINCT from the frozen SessionRecord/RunRecord/BudgetScope schemas. Extending it is the deliberate signal of an additive SessionTreeNode field change. The `TestSchemaIsolation::test_node_keys_exact` body is unchanged; only the key set grew. Downstream checkers should NOT flag this as a freeze violation.

## Deviations from Plan

None - plan executed exactly as written. The `_hydrate_node` import was added to the existing import block in `test_session_tree.py` (the plan's Task 3 instructed importing it for the back-compat test); no other deviation.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Verification Results
- `test_session_tree.py` — 22 tests, all PASS (includes 4 new TestSchemaExtension tests, TestCapRaiseGuard VTREE-05/06 regression green, TestSchemaIsolation::test_node_keys_exact green).
- `test_session_redaction.py` — 8 tests, all PASS, UNMODIFIED (RunRecord still 24 fields; key set unchanged).
- `git diff -- voss/harness/session.py voss/harness/session_tree.py` — only additive scope/role fields, hydrate setdefaults, allocate_child kwargs, and the EXIT_REASONS "error" member. No field removed/changed/renamed on any frozen record.

## Next Phase Readiness
- Schema foundation ready for V4-02 (guard/finalize): exception-path finalize can use `exit_reason="error"`; spend guard + finalize wiring can populate scope/role at spawn.
- Ready for V4-03 (export/CLI): export must carry the new scope/role keys (already in the on-disk node JSON).

---
*Phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone*
*Completed: 2026-06-06*

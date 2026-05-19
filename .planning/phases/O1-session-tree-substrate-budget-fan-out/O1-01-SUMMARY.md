---
phase: O1-session-tree-substrate-budget-fan-out
plan: 01
status: complete
completed_at: 2026-05-19
commits:
  - a274d2e — test(O1-01): add failing session-tree substrate tests (Task 1)
  - 97d70c5 — feat(O1-01): session-tree substrate — node, allocator, guarded mutator (Task 2)
---

# O1-01 Summary — Session-tree substrate (D-01 + D-02 + D-04)

## Files changed

- `voss/harness/session_tree.py` — **new** (156 lines): `SessionTreeNode`, `SessionTreeManager`, `BudgetAllocationError`, `BudgetCapRaiseError`, `mutate_envelope`, `_write_node_file`, `_hydrate_node`.
- `tests/harness/test_session_tree.py` — **new** (10 tests in 5 classes): tree persistence, fan-out invariant, cap-raise guard, concurrency no-oversell, schema isolation.

## Unchanged (REQ-5)

- `voss/harness/session.py`, `voss/harness/recorder.py`, `voss_runtime/budget.py` — zero field changes.
- `tests/harness/test_session_redaction.py` — unmodified; 7 tests still pass.

## SessionTreeNode persisted schema

Per-node files at `<cwd>/.voss/sessions/<root_id>/<node_id>.json` (mode `0o600`).

JSON keys: `id`, `root_id`, `parent_run_id`, `envelope`, `terminal_state`, `created_at`, `ended_at`, `rejected_raises`.

Runtime-only (never serialized): `_budget` (`BudgetScope`), `_finalized` (for O1-02 D-03 finalize).

## Fan-out invariant (D-02)

`sum(child envelope limits) + reserve <= parent limit`, enforced under `asyncio.Lock` in `allocate_child`. Oversell raises `BudgetAllocationError` with no partial child file or `_children` append.

Concurrency: 10× `allocate_child(100)` on limit 900 / reserve 100 → 8 successes, 2 errors.

## Cap-raise guard (D-04)

`mutate_envelope` is the single funnel: `delta > 0` records audit entry, persists, raises `BudgetCapRaiseError`; `delta <= 0` updates `envelope["spent"]`.

## Deviations from plan

- **`test_no_schema_merge` assertion refined.** Plan asked for full dataclass field-name disjointness from `SessionRecord`/`RunRecord`, but shared names (`id`, `created_at`, `ended_at`) are intentional vocabulary overlap, not a schema merge. Test now asserts tree-only keys (`root_id`, `parent_run_id`, `envelope`, `terminal_state`, `rejected_raises`) are disjoint from session/run fields — the actual redaction invariant.
- **`create_root` writes root node file** on creation (needed for persistence tests; implied by D-01 write-at-open).
- **`to_dict` also strips `_finalized`** so it never reaches disk (not in locked JSON schema).

## Verification

```
python3 -m pytest tests/harness/test_session_tree.py -q          # 10 passed
python3 -m pytest tests/harness/test_session_redaction.py -q     # 7 passed
python3 -m pytest tests/harness/test_subagent_recursion.py -q    # 3 passed
```

Depth-token grep on `session_tree.py`: no `max_depth` / `MAX_DEPTH` / `DEPTH_LIMIT` / `RECURSION_LIMIT`.

## Next

Plan **O1-02** wires D-03 (`run_subagent` finalize boundary) onto this substrate; do not add depth/recursion symbols there either.

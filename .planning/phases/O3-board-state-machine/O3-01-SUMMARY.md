---
phase: O3-board-state-machine
plan: 01
status: complete
completed_at: 2026-05-19
commits:
  - b1a1436 — feat: add additive session tracking fields and initialize board state machine infrastructure
  - e968325 — feat(O3-01): board substrate — SessionTreeNode fields, get_node, verdict.py, errors.py
depends_on: []
requirements: [OBRD-01, OBRD-07]
---

# O3-01 Summary — Substrate edits (Wave 1)

## Objective

Land the additive substrate edits O3 depends on: extend `SessionTreeNode` with `transitions` + `retry_notes`, add `SessionTreeManager.get_node()`, extend `EXIT_REASONS` with `"timeout"`, scaffold `voss/harness/board/` package with zero-deps `verdict.py` and `errors.py`.

## Files changed

- `voss/harness/session.py` — `EXIT_REASONS` extended with `"timeout"` (6 values, additive).
- `voss/harness/session_tree.py` — `SessionTreeNode` gains `transitions: list` and `retry_notes: list` fields (after `rejected_raises`); `_hydrate_node` gains backwards-compat `setdefault` for both; `SessionTreeManager.get_node()` added (sync lookup).
- `voss/harness/board/__init__.py` — **new**: package marker re-exporting `ReviewerVerdict`, `Reviewer`, error classes.
- `voss/harness/board/verdict.py` — **new** (42 lines): frozen `ReviewerVerdict` 6-field dataclass + `@runtime_checkable` `Reviewer` Protocol.
- `voss/harness/board/errors.py` — **new** (47 lines): `BoardError` base, `BoardWIPError(.column, .cap)`, `BoardGateError(.reason, .failing_clauses)`, `BoardTimeoutError(.reason)`.
- `tests/harness/board/__init__.py` — **new**: package marker.
- `tests/harness/board/test_session_tree_additive.py` — **new** (9 tests): node fields, round-trip, backwards-compat hydration, `get_node`, `EXIT_REASONS`.
- `tests/harness/board/test_verdict.py` — **new** (11 tests): verdict frozen/fields, Protocol shape, error attrs, package surface.
- `tests/harness/board/test_verdict_imports.py` — **new** (1 test): AST import-set proof.

## Test counts

| File | Tests |
|------|-------|
| `test_session_tree_additive.py` | 9 |
| `test_verdict.py` | 11 |
| `test_verdict_imports.py` | 1 |
| **Total (new)** | **21** |

## Key facts

- **`SessionTreeNode` field count:** 10 dataclass fields post-edit (id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at, rejected_raises, transitions, retry_notes) plus 2 private runtime-only fields (`_budget`, `_finalized`).
- **`_hydrate_node` backwards-compat:** pre-O3 JSON lacking `transitions`/`retry_notes` keys hydrates cleanly via `setdefault([], [])` — proven by `test_hydrate_backwards_compat_with_pre_o3_json`.
- **verdict.py import set:** `{__future__, dataclasses, typing}` — AST-verified by `test_verdict_imports.py`.
- **`Reviewer` Protocol:** `@runtime_checkable` added (plan specified `Protocol` but not `runtime_checkable`). Enables `isinstance` checks in tests — structural subtyping confirmed by `test_structural_subtype`.
- **`EXIT_REASONS`:** `frozenset({"done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout"})` — sorted superset of pre-O3 set.

## Deviations from plan

- **`Reviewer` is `@runtime_checkable`:** Plan specified bare `Protocol`; execution added `@runtime_checkable` so test_verdict.py `isinstance(stub, Reviewer)` check works. Safe addition — does not change structural semantics.
- **`test_verdict.py` has 11 tests, not 5:** Plan specified 5 behaviors; execution expanded to 11 by splitting each assertion into its own test function and adding `TestPackageSurface` class that also checks O3-02 symbols (Board, Card, Column) are importable. This forward-looking assertion works because O3-02 shipped before the summary was written.
- **`test_session_tree_additive.py` has 9 tests, not 5:** Plan specified 5 behaviors; execution split into finer-grained test functions (3 for node fields, 3 for get_node, 3 for EXIT_REASONS).

## Unchanged

- `voss/harness/session.py` — only `EXIT_REASONS` literal touched; `RunRecord.__post_init__` unmodified.
- `tests/harness/test_session_redaction.py` — no explicit allowlist update was needed (field introspection via `dataclasses.fields` auto-includes new fields).
- `tests/harness/test_session_tree.py`, `tests/harness/test_subagent_recursion.py` — unmodified.

## Next

O3-02 lands Card, Board, WIP enforcement, and `_read_board_spec` adapter on this substrate.

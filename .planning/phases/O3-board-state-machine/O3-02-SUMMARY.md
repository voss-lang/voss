---
phase: O3-board-state-machine
plan: 02
status: complete
completed_at: 2026-05-19
commits:
  - c32f7b2 — feat: implement Kanban board state machine with WIP enforcement and transition management
  - e7c8e81 — test: add comprehensive harness tests for board factory, card-node wiring, and column transition logic
  - 74f66fe — test: add transition invariant and WIP cap enforcement validation tests
  - 2bd6781 — feat(O3-02): board state machine — Card, Board, WIP, transition deltas
depends_on: [O3-01]
requirements: [OBRD-01, OBRD-02, OBRD-03, OBRD-06]
---

# O3-02 Summary — Card, Board, WIP (Wave 2)

## Objective

Land the board state machine bones: `Card` frozen value-object, `Board` class with 6-column model, WIP enforcement, `Board.from_team_config()` factory, `Board.spawn_card()`, `Board.move()`, the `_read_board_spec` adapter, and per-transition delta append onto `SessionTreeNode.transitions`. Gate-predicate evaluation deferred to O3-03.

## Files changed

- `voss/harness/board/machine.py` — **new** (229 lines at wave end): `Card` (frozen 8-field), `_BoardConfig`, `_read_board_spec` adapter, `Board` class with `from_team_config`, `spawn_card`, `move`, `_append_delta`. AST literal helpers `_parse_wip`, `_parse_p_overrides`, `_parse_retry`, `_parse_liveness`, `_lit_str`, `_lit_int`, `_lit_float`.
- `voss/harness/board/__init__.py` — extended: exports `Board`, `Card`, `Column`, `RiskTier`.
- `tests/harness/board/conftest.py` — **new**: `tmp_recorder`, `stub_reviewer` (`_NeverReviewer`), `build_test_team`, `artifact_passing`, `artifact_failing`.
- `tests/harness/board/test_board_factory.py` — **new** (7 tests).
- `tests/harness/board/test_card_node_wiring.py` — **new** (2 tests).
- `tests/harness/board/test_columns_and_unknown.py` — **new** (3 tests).
- `tests/harness/board/test_wip_cap.py` — **new** (3 tests).
- `tests/harness/board/test_transition_count_invariant.py` — **new** (1 test).

## Test counts

| File | Tests |
|------|-------|
| `test_board_factory.py` | 7 |
| `test_card_node_wiring.py` | 2 |
| `test_columns_and_unknown.py` | 3 |
| `test_wip_cap.py` | 3 |
| `test_transition_count_invariant.py` | 1 |
| **Total (new)** | **16** |

## Card fields (frozen 8-field)

`node_id`, `column`, `risk_tier`, `retry_count`, `deadline`, `scope` (Optional), `artifact` (Optional), `eval_threshold` (default 1.0).

## Key facts

- **`_DEFAULT_RISK_THRESHOLDS`** = `{"low": 0.60, "med": 0.80, "high": 0.95}` — single definition in `machine.py` line 57. `gates.py` (O3-03) imports it via lazy import to break circular dependency.
- **`_read_board_spec`** is the single localized consumer of `BoardSpec.raw_items`. Uses `isinstance` dispatch on AST nodes (`IntLit`, `FloatLit`, `StringLit`, `DictLit`). Wrong types fall back to defaults (defensive).
- **`Board.move`** enforces unknown-column (raises `BoardGateError`) and WIP cap (raises `BoardWIPError`) before gate evaluation. The `# TODO(O3-03): wire gate registry` marker was placed where gate predicates land.
- **Transition-delta count invariant:** every `move` attempt (passed or refused) appends exactly one delta to `node.transitions`. Verified by `test_transition_count_invariant.py` across a 20-transition mixed lifecycle.
- **Independent boards:** two `Board.from_team_config` calls with the same `TeamConfig` produce distinct boards with distinct `root_node_id`; mutating one's cards list does not affect the other.

## Deviations from plan

- **`_read_board_spec` imports `DictLit`, `IntLit`, `FloatLit`, `StringLit` from `voss.ast_nodes`:** Plan mentioned `getattr(val, "value", None)` for literal extraction; execution implemented proper `isinstance`-based typed helpers (`_lit_str`, `_lit_int`, `_lit_float`, `_parse_wip`, etc.) for more robust parsing.
- **Test count higher than plan specified:** Plan called for 6 behaviors across 2 tasks; execution expanded to 16 tests by splitting assertions into finer-grained functions.
- **`Board.move` signature uses `to: str` not `to: Column`:** Accepts any string to allow the unknown-column rejection path to fire. Column narrowing happens after the check.

## Unchanged

- `voss/harness/board/verdict.py`, `voss/harness/board/errors.py` — no diff from O3-01.
- `voss/harness/session_tree.py` — no diff; only read via `SessionTreeManager` and `_write_node_file`.

## Next

O3-03 activates the gate-predicate registry and replaces the `# TODO(O3-03)` marker with actual predicate evaluation.

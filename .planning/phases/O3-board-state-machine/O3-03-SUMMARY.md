---
phase: O3-board-state-machine
plan: 03
status: complete
completed_at: 2026-05-19
commits:
  - 48a7620 — feat: implement session persistence and board gate predicates with associated test harnesses
  - 18da40e — test: add full lifecycle board transition tests using DeterministicReviewerStub
  - b071ade — feat(O3-03): gate predicates, dry_run_gate, DeterministicReviewerStub
depends_on: [O3-02]
requirements: [OBRD-04, OBRD-05, OBRD-06, OBRD-07]
---

# O3-03 Summary — Gates, dry_run_gate, stub (Wave 3)

## Objective

Activate the gate-predicate registry. Wire `Board.move` to evaluate predicates in declared order. Add `Board.dry_run_gate` for non-destructive inspection. Land `DeterministicReviewerStub`. Verify artifact-only confidence invariant and risk-tier threshold lookup.

## Files changed

- `voss/harness/board/gates.py` — **new** (173 lines): `Predicate` Protocol, `GateContext` dataclass, 8 predicate classes (7 stable names), `Gates` frozen registry with `build_default()` and `confidence_required()`. `_CODE_DONE_PREDICATES` and `_AI_DONE_PREDICATES` tuples.
- `voss/harness/board/stub.py` — **new** (33 lines): `DeterministicReviewerStub` dataclass with configurable `conf`, `verdict`, `tier`, `source`.
- `voss/harness/board/machine.py` — **edited**: replaced `# TODO(O3-03)` marker with gate-evaluation block in `move()`; added `dry_run_gate()`; added imports from `gates.py`.
- `tests/harness/board/test_gate_predicates_basic.py` — **new** (6 tests).
- `tests/harness/board/test_risk_thresholds.py` — **new** (6 tests).
- `tests/harness/board/test_dry_run_gate.py` — **new** (5 tests).
- `tests/harness/board/test_artifact_only_confidence.py` — **new** (3 tests).
- `tests/harness/board/test_stub.py` — **new** (4 tests).
- `tests/harness/board/test_stub_full_lifecycle.py` — **new** (3 tests).

## Test counts

| File | Tests |
|------|-------|
| `test_gate_predicates_basic.py` | 6 |
| `test_risk_thresholds.py` | 6 |
| `test_dry_run_gate.py` | 5 |
| `test_artifact_only_confidence.py` | 3 |
| `test_stub.py` | 4 |
| `test_stub_full_lifecycle.py` | 3 |
| **Total (new)** | **27** |

## Key facts

- **Predicate names:** `_PREDICATE_NAMES = ("conf", "tests", "eval", "scope", "budget", "retry", "timeout")` — 7 stable names per SPEC L114.
- **8 predicates, 7 names:** `scope_ok` and `scope_clean` both expose `.name = "scope"` (intentional dedup per OQ scope-clean-naming). `failing_clauses` deduplicates via append-if-absent.
- **`conf_meets_p` reviewer cardinality:** calls `reviewer.review(card)` at most once per `move` attempt; result cached on `GateContext.verdict`. No cross-attempt caching.
- **`_DEFAULT_RISK_THRESHOLDS` import:** `gates.py` uses `from .machine import _DEFAULT_RISK_THRESHOLDS` inside `conf_meets_p.evaluate()` (lazy import to break circular dependency between `gates.py` and `machine.py`). Single definition remains in `machine.py`.
- **AI-vs-code Done variant:** `Board.move` introspects `card.artifact` — if `hasattr(artifact, "eval_score") and not hasattr(artifact, "tests_passed")`, swaps in `_AI_DONE_PREDICATES` (`scope_clean`, `conf_meets_p`, `eval_meets_threshold`). Otherwise uses `_CODE_DONE_PREDICATES` (`scope_clean`, `conf_meets_p`, `tests_pass`).
- **`dry_run_gate` non-mutation invariant:** never appends to `node.transitions`, never modifies `board._cards`. Uses the same predicate evaluation as `move` but without side effects.
- **Production-import guard:** `stub.py` is test-only. `test_stub.py` includes a grep gate asserting no production file imports `voss.harness.board.stub`.
- **Artifact-only confidence:** `Backlog->Planned` and `Planned->InProgress` never invoke the reviewer. Proven by `test_artifact_only_confidence.py` using a `RaisingReviewer` that asserts on invocation.

## Deviations from plan

- **`gates.py` uses `TYPE_CHECKING` guard:** Plan showed a direct `from .machine import Card, Column, RiskTier` import. Execution uses `if TYPE_CHECKING: from .machine import Card, Column, RiskTier` to break the circular import, with a lazy import inside `conf_meets_p.evaluate()` for the runtime path.
- **`Gates.build_default()` takes no arguments:** Plan showed `build_default(team_ceiling, team_p_overrides, retry_ceiling, reserve)` in some test descriptions; actual implementation is a classmethod with no parameters (all predicate evaluation context comes from `GateContext` at evaluation time, not at registry construction time).
- **`verdict_snapshot` on passed deltas:** Plan specified `verdict_snapshot` in passed deltas only when reviewer was consulted. Implementation correctly passes `verdict_snapshot` through to the passed-delta `_append_delta` call, so it is `None` for non-artifact transitions and populated for artifact transitions.

## Unchanged

- `voss/harness/board/verdict.py` — no diff (AST import-set invariant preserved).
- `voss/harness/board/errors.py` — no diff.
- `voss/harness/session_tree.py` — no diff.

## Next

O3-04 closes the cage: tick driver, critic loop, `finalize_node` integration, and 100-card stress.

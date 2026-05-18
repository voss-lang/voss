# M11-01 Recorded Data Inspect Core Summary

**Completed:** 2026-05-18T20:22:49Z
**Plan:** `M11-01-recorded-data-inspect-core-PLAN.md`
**Wave:** 1

## Outcome

Completed the pure recorded-data inspection core for M11:

- Added `DecisionView` and `BudgetFrame` view dataclasses.
- Added dictionary/object normalization for JSON-hydrated and dataclass-shaped records.
- Added `decision_sequence()` and `render_decision_sequence()` over `RunRecord.decisions[]`.
- Added `budget_timeline()` and `render_budget_timeline()` over `RunRecord.iterations[]`.
- Added `load_run()` for cwd-scoped session lookup and run selection.

The implementation preserves the M11 D-01 downgrade: probable data is rendered as a confidence-annotated decision sequence, not a propagation DAG; budget data is rendered as an agent-iteration timeline, not per-`ctx(budget:)` frames.

## Files Changed

- `voss/harness/voss_inspect.py`
- `tests/harness/test_voss_inspect.py`
- `.planning/phases/M11-voss-aware-tools-caps-01b/M11-01-SUMMARY.md`

## Verification

- `python3 -m pytest -q tests/harness/test_voss_inspect.py` passed with 6 tests.
- `python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py` passed with 3 tests.
- `python3 -m py_compile voss/harness/voss_inspect.py` passed.
- `git diff --check` passed.
- `git diff -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py` was empty.
- Direct whitespace check on the two new files passed.

## Deviations

- Used generic Codex worker subagents because local GSD agents are not installed for this repo.
- Did not update or rely on the pre-existing dirty `.planning/STATE.md` and `repomix-output.xml` worktree changes.

## Self-Check: PASSED

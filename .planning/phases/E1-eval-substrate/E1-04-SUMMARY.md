---
phase: E1-eval-substrate
plan: 04
subsystem: testing
tags: [eval, golden, checks, hybrid-scoring, EVSUB-03]

requires: [E1-01, E1-03]
provides:
  - All 6 golden tasks carry grounded deterministic [[checks]]
  - test_golden_checks.py coverage for non-empty checks + stub suite execution
affects: [EVSUB-07]

tech-stack:
  added: []
  patterns:
    - "Per-task [[checks]] array-of-tables in golden task.toml"
    - "Stub full-suite run asserts checks list present without requiring gate_pass"

key-files:
  created:
    - tests/eval/test_golden_checks.py
  modified:
    - tests/eval/golden/01-analyze/task.toml
    - tests/eval/golden/02-plan-only/task.toml
    - tests/eval/golden/03-approved-edit/task.toml
    - tests/eval/golden/04-validation/task.toml
    - tests/eval/golden/05-resume/task.toml
    - tests/eval/golden/06-fetch-summarize/task.toml

key-decisions:
  - "05-resume uses cheap fixture-intrinsic gate (test -f notes.txt); resume correctness stays with judge"
  - "Stub suite test asserts checks executed, not gate_pass (stub agents don't edit)"

patterns-established:
  - "Golden tasks are hybrid-scored: rubric + deterministic checks per contract"
  - "load_suite validates [[checks]] via AnyCheck discriminated union"

requirements-completed: [EVSUB-03]

duration: ~10min
completed: 2026-06-10
---

# E1 Plan 04: Golden Checks Retrofit Summary

**All 6 golden task.toml files now carry grounded `[[checks]]` blocks; coverage test proves non-empty checks and stub-mode full-suite execution without error**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2
- **Files modified:** 7 (6 task.toml + 1 new test)

## Accomplishments

- Appended deterministic `[[checks]]` to all 6 golden tasks matching each task's contract
- 01-analyze: `file_exists` on `.voss/architecture.md`
- 02-plan-only: `cmd` gate `git diff --quiet HEAD` (no-writes contract)
- 03-approved-edit: two `file_contains` + cmd gate for removed `def add(`
- 04-validation: `cmd` running `python -m voss.cli check sample.voss`
- 05-resume: `cmd` `test -f notes.txt` (fixture-intrinsic; judge carries resume correctness)
- 06-fetch-summarize: `file_exists` + `file_contains` on `summary.txt`
- Created `test_golden_checks.py` with load_suite assertions and full stub-suite subprocess test

## Files Created/Modified

- `tests/eval/golden/*/task.toml` — additive `[[checks]]` blocks (6 files)
- `tests/eval/test_golden_checks.py` — `test_all_golden_tasks_have_checks` + `test_stub_suite_runs_all_checks_without_error`

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Verification

```
.venv/bin/python -c "load_suite(...)"  → ok (6 tasks, all checks >= 1)
grep -l "[[checks]]" ... | wc -l       → 6
.venv/bin/python -m pytest tests/eval/test_golden_checks.py -x -q  → 2 passed
.venv/bin/python -m pytest tests/eval -q                            → 68 passed
```

## User Setup Required

None.

## Next Phase Readiness

- Golden tasks are hybrid-scored and ready for EVSUB-07 live proof run (≥5/6 gate_pass target)
- Stub suite proves checks execute without crash; gate-pass is a live-agent concern

---
*Phase: E1-eval-substrate*
*Completed: 2026-06-10*

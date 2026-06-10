---
phase: E1-eval-substrate
plan: 01
subsystem: testing
tags: [pydantic, eval, checks, subprocess, task-spec]

requires: []
provides:
  - TaskSpec.checks discriminated union (cmd, file_exists, file_contains)
  - _run_checks pure executor (checks, cwd) -> (gate_pass, results)
affects: [E1-03]

tech-stack:
  added: []
  patterns:
    - "Pydantic Discriminator('type') union for check models"
    - "Pure _run_checks executor — no short-circuit, timeout-safe cmd checks"

key-files:
  created:
    - tests/eval/test_checks.py
  modified:
    - voss/eval/suite.py
    - voss/eval/runner.py
    - tests/eval/test_task_spec.py

key-decisions:
  - "Checks schema only in E1-01; wiring into JSONL rows deferred to E1-03"
  - "cmd checks use shell=True with per-check timeout (default 60s)"

patterns-established:
  - "AnyCheck = Annotated[Union[...], Discriminator('type')] on TaskSpec.checks"
  - "_run_checks returns (gate_pass, results) and always runs every check"

requirements-completed: [EVSUB-01]

duration: ~15min
completed: 2026-06-10
---

# E1 Plan 01: Eval Check Schema + Executor Summary

**TaskSpec accepts optional `checks` (cmd / file_exists / file_contains) with pydantic validation; `_run_checks` runs all checks against a fixture cwd without short-circuiting**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments

- Added `CmdCheck`, `FileExistsCheck`, `FileContainsCheck`, and `AnyCheck` discriminated union to `voss/eval/suite.py`
- Extended `TaskSpec` with `checks: list[AnyCheck] = Field(default_factory=list)` — back-compat preserved (no `checks` key → empty list)
- Implemented `_run_checks` in `voss/eval/runner.py` as a pure function (not yet wired into suite loop)
- Added 7 schema tests and 7 executor unit tests

## Files Created/Modified

- `voss/eval/suite.py` — Check models + `TaskSpec.checks` field
- `voss/eval/runner.py` — `_run_checks` executor after `_file_diff`
- `tests/eval/test_task_spec.py` — 7 new checks validation tests
- `tests/eval/test_checks.py` — Unit tests for all three check types, timeout, no short-circuit

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Verification

```
.venv/bin/python -m pytest tests/eval/test_task_spec.py tests/eval/test_checks.py -q  → 18 passed
.venv/bin/python -m pytest tests/eval/ -q                                           → 59 passed
load_suite(tests/eval/golden)                                                       → 6 tasks
grep -c "def _run_checks" voss/eval/runner.py                                       → 1
```

## User Setup Required

None.

## Next Phase Readiness

- E1-03 can wire `_run_checks` into the suite loop and JSONL row output
- Check schema is ready for `[[checks]]` entries in golden `task.toml` files (future plans)

---
*Phase: E1-eval-substrate*
*Completed: 2026-06-10*

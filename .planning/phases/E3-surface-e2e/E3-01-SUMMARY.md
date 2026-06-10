---
phase: E3-surface-e2e
plan: 01
subsystem: testing
tags: [eval, pydantic, jsonl, surface-routing]

requires:
  - phase: E1-eval-substrate
    provides: run_suite(max_turns), _run_checks, gate_pass/capped/checks row fields (grep gate verified)
provides:
  - TaskSpec.surface (Literal internal|cli:do|cli:chat|cli:edit|serve, default internal) + TaskSpec.target_file
  - _drive_task surface dispatch seam (internal unchanged; 4 surfaces stubbed with crash_reason)
  - Additive "surface" JSONL row field + REQUIRED_FIELDS sentinel updated in-plan
affects: [E3-02 CLI drivers, E3-03 serve driver, E3-04 scenarios]

tech-stack:
  added: []
  patterns: [surface dispatch seam in _drive_task, additive-only JSONL row fields]

key-files:
  created: []
  modified:
    - voss/eval/suite.py
    - voss/eval/runner.py
    - tests/eval/test_task_spec.py
    - tests/eval/test_voss_eval_stub.py
    - tests/eval/conftest.py

key-decisions:
  - "surface row key appended after input_tokens (V18 added input_tokens since the plan was written; additive-only ordering preserved)"
  - "Non-internal dispatch returns early with not-implemented crash_reason; internal path byte-unchanged"

patterns-established:
  - "Surface drivers return (final, crash_reason_or_None, capped); _drive_task wraps into the 4-tuple"

requirements-completed: [EVSRF-01]

duration: 15min
completed: 2026-06-10
---

# Phase E3 Plan 01: Surface Schema + Dispatch Seam Summary

**TaskSpec gains surface/target_file routing fields; _drive_task dispatches by surface (internal unchanged, 4 surfaces stubbed); JSONL row carries additive surface field with sentinel updated in-plan**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `surface` Literal field (default "internal") + `target_file` (default None) on TaskSpec; golden tasks load unchanged (6 tasks, extra=forbid intact)
- `_drive_task` early-returns a clear not-implemented crash_reason for cli:do/cli:chat/cli:edit/serve; internal `05-` resume + run_turn paths untouched
- Row dict gains `"surface": spec.surface` as last key; REQUIRED_FIELDS sentinel updated in the same plan (21 fields: 20 prior incl. V18 input_tokens + surface)
- 5 new TaskSpec field tests (TDD red→green); both `set(row) == REQUIRED_FIELDS` assertions green

## Task Commits

1. **Task 1: surface/target_file fields** - `49d3b36` (test, RED) + `2f4a75b` (feat, GREEN)
2. **Task 2: dispatch skeleton + row field + sentinel** - `b3bd1c7` (absorbed by concurrent auto-committer, bundled with V18 test edits; content verified intact) + conftest fix absorbed into `eb3e738`

## Files Created/Modified
- `voss/eval/suite.py` - surface + target_file TaskSpec fields
- `voss/eval/runner.py` - dispatch seam + additive surface row key
- `tests/eval/test_task_spec.py` - 5 surface/target_file field tests
- `tests/eval/test_voss_eval_stub.py` - REQUIRED_FIELDS + surface
- `tests/eval/conftest.py` - collect_ignore_glob (deviation, below)

## Decisions Made
- Row key placed after `input_tokens` (plan said after `checks`; V18 VOPT-07 added input_tokens in between — additive-only rule respected, no reorder).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] E2-02 matrix fixtures broke repo-level pytest collection**
- **Found during:** Task 2 (full-suite verification)
- **Issue:** `tests/eval/matrix/py-0{1,3,4}-*/fixture/test_calc.py` collected by `pytest tests/eval` from repo root → `from calc import add` ImportError → collection aborted
- **Fix:** `collect_ignore_glob = ["golden/*", "matrix/*"]` in tests/eval/conftest.py — fixture dirs are repos-under-test, exercised only inside the runner's isolated copy
- **Files modified:** tests/eval/conftest.py
- **Verification:** `pytest tests/eval -m 'not live'` collects cleanly
- **Committed in:** eb3e738 (absorbed)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Fix necessary for any full-suite run; no scope creep.

## Issues Encountered
- Full eval suite NOT fully green: 6 failures in test_matrix_{stub,suite,summary}.py — these are E2-01's intended RED tests awaiting E2-05..08 (matrix task.tomls + skip-row summary). The skipif guard auto-activated when E2-02 created the matrix dir, per E2-01 design. Verified pre-existing via stash (fail without E3 changes). 71 passed, 0 E3-caused regressions.
- Concurrent auto-committer absorbed Task 2 commits (b3bd1c7/eb3e738) — known repo behavior; content verified via git show.

## User Setup Required
None.

## Next Phase Readiness
- Dispatch seam fixed interface for E3-02 (cli drivers) and E3-03 (serve driver)
- E2 matrix RED tests outstanding (E2-05..08) — not an E3 blocker

---
*Phase: E3-surface-e2e*
*Completed: 2026-06-10*

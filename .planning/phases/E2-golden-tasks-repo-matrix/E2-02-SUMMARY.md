---
phase: E2-golden-tasks-repo-matrix
plan: 02
subsystem: testing
tags: [pytest, eval-matrix, fixtures, python]

requires:
  - phase: E1-eval-runner
    provides: _prepare_fixture copytree isolation + _run_checks semantics the fixtures rely on
provides:
  - Six tests/eval/matrix/py-*/fixture/ directories (Python column of the repo matrix)
  - Flat 3-file calc repos (pyproject.toml + calc.py + test_calc.py) for py-01/03/04 shape cells
  - Byte-copies of golden fixtures for py-02/05/06 language-agnostic cells
affects: [E2 plan 05 task.toml authoring, eval matrix runner]

tech-stack:
  added: []
  patterns: [flat Python fixture layout (no src/), duplicate-not-symlink fixture isolation]

key-files:
  created:
    - tests/eval/matrix/py-01-analyze/fixture/{pyproject.toml,calc.py,test_calc.py}
    - tests/eval/matrix/py-03-approved-edit/fixture/{pyproject.toml,calc.py,test_calc.py}
    - tests/eval/matrix/py-04-validation/fixture/{pyproject.toml,calc.py,test_calc.py}
    - tests/eval/matrix/py-02-plan-only/fixture/calc.py
    - tests/eval/matrix/py-05-resume/fixture/notes.txt
    - tests/eval/matrix/py-06-fetch-summarize/fixture/README.md
  modified: []

key-decisions:
  - "Shape fixtures byte-identical across py-01/03/04; cell differences live in task.toml (plan 05)"
  - "Flat layout only — pytest resolves `from calc import add` at cwd, no pip install (Pitfall 3)"
  - "Golden fixtures duplicated with cp, not symlinked (RESEARCH Open Q3 — copytree isolation)"

patterns-established:
  - "Python matrix fixture: flat 3-file calc repo with typed add(), pyproject [project] table only"

requirements-completed: [EVGLD-01]

duration: 5min
completed: 2026-06-10
---

# Phase E2 Plan 02: Python Matrix Fixtures Summary

**Six py-* matrix fixture dirs: three identical flat pytest-green calc repos for shape cells, three byte-copies of golden fixtures for language-agnostic cells**

## Performance

- **Duration:** ~5 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 12 created

## Accomplishments
- py-01-analyze / py-03-approved-edit / py-04-validation each hold a byte-identical flat 3-file calc repo (pyproject.toml with `name = "calc"`, typed `add(a: int, b: int)`, test importing `from calc import add`)
- `python3 -m pytest test_calc.py -q` exits 0 in all three shape fixtures from fixture cwd — no src/ layout, no install step
- py-02-plan-only/calc.py, py-05-resume/notes.txt, py-06-fetch-summarize/README.md are byte-for-byte regular-file copies of their golden analogs (diff exits 0, no symlinks)

## Task Commits

1. **Task 1: Build the three Python shape fixtures** - `562a550` (feat)
2. **Task 2: Duplicate the three Python-only golden fixtures** - `07837f0` (feat)

## Files Created/Modified
- `tests/eval/matrix/py-0{1,3,4}-*/fixture/pyproject.toml` - Minimal `[project]` manifest giving analyze a pyproject token
- `tests/eval/matrix/py-0{1,3,4}-*/fixture/calc.py` - Typed editable add() (approved-edit rename target → sum_two)
- `tests/eval/matrix/py-0{1,3,4}-*/fixture/test_calc.py` - pytest target importing calc.add at flat cwd
- `tests/eval/matrix/py-02-plan-only/fixture/calc.py` - Copy of golden 02 fixture (untyped add, plan-mode edit target)
- `tests/eval/matrix/py-05-resume/fixture/notes.txt` - Copy of golden 05 fixture (Project Meridian status report)
- `tests/eval/matrix/py-06-fetch-summarize/fixture/README.md` - Copy of golden 06 fixture

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written. (Verification-only note: pytest acceptance runs left `__pycache__/` in fixture dirs; removed before commit so each fixture stays at its committed file count.)

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Python column of the matrix is ready for plan 05's task.toml authoring (cells point at these fixtures)
- All fixtures ≤ 5 files (D-01), self-contained, zero network/install side effects

---
*Phase: E2-golden-tasks-repo-matrix*
*Completed: 2026-06-10*

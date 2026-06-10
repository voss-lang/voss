---
phase: E2-golden-tasks-repo-matrix
plan: 01
subsystem: testing
tags: [eval, matrix, pytest, nyquist, red-scaffold]

requires: [E1-eval-substrate]
provides:
  - Four matrix test scaffolds mapping EVGLD-01..07 to named pytest selectors
  - skipif/xfail/RED contract for downstream plans 02-09
affects: [E2-02, E2-08, E2-09]

tech-stack:
  added: []
  patterns:
    - "strict xfail for runner tests awaiting E2-08"
    - "skipif on missing tests/eval/matrix for suite/stub tests"

key-files:
  created:
    - tests/eval/test_matrix_suite.py
    - tests/eval/test_matrix_runner.py
    - tests/eval/test_matrix_stub.py
    - tests/eval/test_matrix_summary.py

key-decisions:
  - "Minted EVGLD-01..07 requirement IDs in E2-01-PLAN (no E2-SPEC yet)"
  - "Summary header test asserts - skipped rate: (not bare 'skipped') to avoid tmp_path false-green"

patterns-established:
  - "MATRIX_CELLS / EXPECTED_CELL_IDS frozen 12-cell id list"
  - "Runner toolchain tests xfail(strict=True) until E2-08"

requirements-completed: [EVGLD-01, EVGLD-02, EVGLD-03, EVGLD-04, EVGLD-05, EVGLD-06, EVGLD-07]

duration: ~20min
completed: 2026-06-10
---

# E2 Plan 01: Matrix Test Scaffolds Summary

**Wave-0 Nyquist foundation — four test files with one named selector per EVGLD requirement, RED until feature plans land**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files created:** 4

## Accomplishments

- `test_matrix_suite.py` — EVGLD-01/04 suite-load + cognition-token checks (skipif until matrix dir exists)
- `test_matrix_summary.py` — EVGLD-06 skipped-column contract (true RED until E2-08)
- `test_matrix_runner.py` — EVGLD-02/03/05 toolchain preflight/skip/strict (strict xfail until E2-08)
- `test_matrix_stub.py` — EVGLD-05/07 per-cell + full stub run (skip until matrix fixtures exist)

## Test contract state

| File | State | Count |
|------|-------|------:|
| test_matrix_suite.py | skip (no matrix dir) | 4 |
| test_matrix_summary.py | RED (2 fail) | 2 |
| test_matrix_runner.py | xfail strict | 3 |
| test_matrix_stub.py | skip (13 cells + full run) | 13 |

Prior eval tests: **68 passed**, no regression.

## Deviations from Plan

- Strengthened `test_summary_renders_skipped_header` to assert `- skipped rate:` + `toolchain-absent` (bare `skipped` matched pytest tmp dir name and false-greened)

## Verification

```
.venv/bin/python -m pytest tests/eval/test_matrix_suite.py tests/eval/test_matrix_summary.py --collect-only -q  → 6 collected
.venv/bin/python -m pytest tests/eval/test_matrix_runner.py tests/eval/test_matrix_stub.py --collect-only -q  → 16 collected
.venv/bin/python -m pytest tests/eval/test_matrix_runner.py -q -rx  → 3 xfail
.venv/bin/python -m pytest tests/eval/ -q  → 68 passed, 2 failed (summary RED), 17 skipped, 3 xfailed
```

## Next

- **E2-02+** — build `tests/eval/matrix/` fixtures (activates suite + stub skips)
- **E2-08** — runner toolchain extension + summary skipped column (turns runner xfail + summary RED green)

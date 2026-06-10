---
phase: E1-eval-substrate
plan: 02
subsystem: testing
tags: [eval, config, dev-gate, click, VOSS_DEV]

requires: []
provides:
  - "[eval] config section with max_turns (default 15) and judge_model (default gpt-5.5-mini)"
  - VOSS_DEV=1 gate on voss eval CLI verb
  - --max-turns CLI option (not yet forwarded to run_suite)
  - autouse conftest setting VOSS_DEV=1 for eval test suite
affects: [E1-03]

tech-stack:
  added: []
  patterns:
    - "VOSS_DEV=1 friction gate at eval_cmd entry before run_suite import"
    - "[eval] config reader mirrors [agent] section pattern"

key-files:
  created:
    - tests/eval/conftest.py
    - tests/eval/test_dev_gate.py
  modified:
    - voss/harness/config.py
    - voss/harness/cli.py

key-decisions:
  - "Gate uses generic VOSS_DEV=1, not eval-specific env var"
  - "max_turns accepted by CLI but forwarding to run_suite deferred to E1-03"
  - "programmatic run_suite import intentionally ungated"

patterns-established:
  - "get_eval_max_turns / get_eval_judge_model accessors with warn-on-bad-value fallback"
  - "tests/eval/conftest autouse VOSS_DEV=1 for subprocess tests via os.environ.copy()"

requirements-completed: [EVSUB-05]

duration: ~15min
completed: 2026-06-10
---

# E1 Plan 02: Dev Gate + Eval Config Summary

**`voss eval` requires `VOSS_DEV=1` at verb entry; `[eval]` config supplies `max_turns` (15) and `judge_model` (gpt-5.5-mini) defaults; `--max-turns` flag registered for E1-03 wiring**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- Added `[eval]` section reader to `voss/harness/config.py` with `get_eval_max_turns()` and `get_eval_judge_model()`
- Gated `eval_cmd` in `voss/harness/cli.py` — exits code 1 with one-line message before any provider/fixture work
- Registered `--max-turns` CLI option (parameter accepted, not yet passed to `run_suite`)
- Created autouse `tests/eval/conftest.py` keeping existing eval subprocess tests green
- Added `tests/eval/test_dev_gate.py` proving blocked and allowed paths

## Files Created/Modified

- `voss/harness/config.py` — `_EVAL_BLOCK`, `load_eval_config`, `DEFAULT_MAX_TURNS`, `DEFAULT_JUDGE_MODEL`, getters
- `voss/harness/cli.py` — `VOSS_DEV` guard + `--max-turns` option on `eval_cmd`
- `tests/eval/conftest.py` — autouse `VOSS_DEV=1`
- `tests/eval/test_dev_gate.py` — subprocess gate tests (blocked / proceeds)

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Verification

```
.venv/bin/python -m pytest tests/eval/ -q                    → 61 passed
.venv/bin/python -m pytest tests/harness -k config -q        → 94 passed
VOSS_DEV=1 python -m voss.cli eval --help | grep max-turns   → listed
get_eval_max_turns() / get_eval_judge_model()                → 15 / gpt-5.5-mini
grep -c "VOSS_DEV" voss/harness/cli.py                       → 2
```

## User Setup Required

None. Developers must set `VOSS_DEV=1` to run `voss eval` from the CLI.

## Next Phase Readiness

- E1-03 can wire `max_turns` into `run_suite`, consume `get_eval_max_turns()` / `get_eval_judge_model()`, and integrate `_run_checks` into the eval loop

---
*Phase: E1-eval-substrate*
*Completed: 2026-06-10*

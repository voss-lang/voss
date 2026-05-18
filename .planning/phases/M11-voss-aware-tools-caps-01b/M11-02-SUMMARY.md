# M11-02 Probable and Budget Surfaces Summary

**Completed:** 2026-05-18T20:57:32Z
**Plan:** `M11-02-probable-budget-surfaces-PLAN.md`
**Wave:** 2

## Outcome

Exposed the M11-01 recorded-data inspection core through read-only user and agent surfaces:

- Added agent tools `voss_probable_inspect` and `voss_budget_trace`, both registered as non-mutating.
- Added `voss inspect probable <session>` with optional `--decision N`.
- Added `voss inspect budget <session>`.
- Added `/probable [session] [--decision N]`, defaulting to the current REPL session when omitted.
- Added `/btrace [session]`, defaulting to the current REPL session when omitted.
- Kept `/budget` as the existing T6 USD-budget command.

All surfaces reuse `voss_inspect.load_run()` plus the M11-01 renderers and read only persisted session/run records.

## Files Changed

- `voss/harness/tools.py`
- `voss/harness/cli.py`
- `tests/harness/test_tools.py`
- `tests/harness/test_repl_slash.py`
- `tests/harness/test_voss_inspect.py`
- `.planning/phases/M11-voss-aware-tools-caps-01b/M11-02-SUMMARY.md`

## Verification

- `python3 -m pytest -q tests/harness/test_voss_inspect.py tests/harness/test_tools.py tests/harness/test_repl_slash.py` passed with 50 tests.
- `python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py` passed with 3 tests.
- `python3 -m voss.harness inspect --help` passed.
- `python3 -m voss.harness inspect probable --help` passed.
- `python3 -m voss.harness inspect budget --help` passed.
- `python3 -m voss.cli inspect --help` passed.
- `python3 -m py_compile voss/harness/cli.py voss/harness/tools.py voss/harness/voss_inspect.py` passed.
- `git diff --check` passed.
- `git diff -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py` was empty.

## Deviations

- Generic Codex worker subagents were used because local GSD agents are not installed for this repo.
- One worker committed the tool-registration slice directly as `9e261c6`; remaining CLI/test/summary changes are left in the working tree for integration.

## Self-Check: PASSED

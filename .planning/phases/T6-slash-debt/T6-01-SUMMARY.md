# T6-01 Cost By Tool Approximation Summary

**Completed:** 2026-05-18T01:18:32Z
**Plan:** `T6-01-cost-by-tool-approximation-PLAN.md`
**Wave:** 1

## Outcome

Completed SLASH-07's `/cost --by-tool` behavior:

- Replaced the informational `--by-tool` stub with a derived even-split approximation.
- Aggregates each iteration's `cost_usd / len(tool_results)` per tool name.
- Skips zero-cost iterations and iterations with no tool results.
- Prints an informational no-data line instead of raising or writing stderr.
- Emits a one-time `~approx (turn cost ÷ N tool calls)` caveat before rows.
- Left `/cost --by-model` and default `/cost` behavior unchanged.

## Files Changed

- `voss/harness/cli.py`
- `tests/harness/test_repl_slash.py`
- `.planning/phases/T6-slash-debt/T6-01-SUMMARY.md`

## Required Notes

D-06 reconciliation note: T6 owns `--by-model` and `--by-tool`; T4's D-09 placeholder edit is obsolete; future T4 executor must NOT re-stub `--by-tool`.

Deleting `test_cost_by_tool_is_honest_stub`'s `assert "T4" in out` was an EXPECTED, REQUIRED change per D-01, not a regression.

## Verification

- `python3 -m py_compile voss/harness/cli.py tests/harness/test_repl_slash.py` passed.
- `python3 -m pytest tests/harness/test_repl_slash.py -q` passed with 22 tests.
- `python3 -m pytest tests/harness/test_repl_slash.py -q -k "by_model"` passed.
- `! grep -q "lands with T4" voss/harness/cli.py` passed.
- `grep -n "~approx (turn cost" voss/harness/cli.py` matched the new caveat.
- `grep -n "iterations" voss/harness/cli.py` matched the by-tool iteration walk.
- `grep -nE "len\\(.*tool_results.*\\)|len\\(trs\\)" voss/harness/cli.py` matched the even-split denominator.
- `grep -n 'assert "T4" in out' tests/harness/test_repl_slash.py` returned no match.
- `grep -n "test_cost_by_tool_is_honest_stub" tests/harness/test_repl_slash.py` returned no match.
- `git diff --check -- voss/harness/cli.py tests/harness/test_repl_slash.py` passed.
- No T4 planning or source file was modified.

## Deviations

- Verification used `python3` because this environment uses `python3` for project commands.

## Self-Check: PASSED

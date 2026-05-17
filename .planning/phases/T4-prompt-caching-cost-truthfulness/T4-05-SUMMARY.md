# T4-05 Cost Truth And CLI Summary

**Completed:** 2026-05-17T17:04:35Z
**Plan:** `T4-05-cost-truth-and-cli-PLAN.md`
**Wave:** 4
**Production commit:** `efbbb24`

## Outcome

Implemented the CACHE-03 / CACHE-04 cost-truth verification layer:

- Updated `/cost --by-tool` placeholder text to point at `T6 SLASH-07`.
- Updated the existing `test_cost_by_tool_is_honest_stub` assertion in lockstep.
- Turned `tests/harness/test_cost_slash.py` green for `/cost --by-model` 4-decimal per-model sums and the T6 placeholder citation.
- Turned `tests/harness/test_cost_accounting.py` green by asserting LiteLLM `cost_per_token(...)` charges strictly more when `cache_creation_input_tokens` is non-zero.
- Added no Voss-owned pricing constants or pricing module.

## Files Changed

- `voss/harness/cli.py`
- `tests/harness/test_repl_slash.py`
- `tests/harness/test_cost_slash.py`
- `tests/harness/test_cost_accounting.py`
- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-05-SUMMARY.md`

## Verification

- `python3 -m pytest tests/harness/test_repl_slash.py::TestT6Behaviors -x -q` passed with 10 tests.
- `python3 -m pytest tests/harness/test_cost_slash.py -x -q` passed with 2 tests.
- `python3 -m pytest tests/harness/test_cost_accounting.py -x -q` passed with 1 test.
- `python3 -m pytest tests/harness/test_cost_accounting.py tests/harness/test_cost_slash.py tests/harness/test_repl_slash.py -x -q` passed with 24 tests.
- `grep -F 'T6 SLASH-07' voss/harness/cli.py | wc -l` returned 1.
- `grep -cE '"T4"' voss/harness/cli.py` returned 0.
- `grep -nE '"T4"' tests/harness/test_repl_slash.py || true` returned no matches.
- `grep -rE 'cache_creation_rate|cache_read_rate|cost_multiplier' voss voss_runtime || true` returned no matches.
- `python3 -m py_compile voss/harness/cli.py tests/harness/test_repl_slash.py tests/harness/test_cost_slash.py tests/harness/test_cost_accounting.py` passed.
- `git diff --check` passed.

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed implementation deviations. **Impact:** none.

## Notes

- CACHE-03 uses LiteLLM's own `cost_per_token(...)` as the source of truth and only asserts a strict differential, preserving D-06.
- `/cost --by-model` implementation was not changed; T4-05 only added coverage for the existing 4-decimal aggregation.

## Self-Check: PASSED

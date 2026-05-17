# T5-02 Shell Run Cap Raise Summary

**Completed:** 2026-05-17T17:46:44Z
**Plan:** `T5-02-shell-run-cap-raise-PLAN.md`
**Wave:** 2

## Outcome

Completed SHELL-01:

- Raised `shell_run` output truncation from 4096 bytes to 30720 bytes.
- Raised `_shell_capture` output truncation from 4096 bytes to 30720 bytes.
- Updated the agent-visible `shell_run` tool description from `4KB` to `30KB`.
- Preserved the existing `[exit N]` prefix, `<truncated, total N bytes>` envelope, and `timeout=30.0` behavior.

## Files Changed

- `voss/harness/tools.py`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/T5-shell-ergonomics/T5-02-SUMMARY.md`

## Verification

- `python3 -m pytest tests/harness/test_shell_timeout.py::test_shell_run_30kb_cap_documented tests/harness/test_shell_timeout.py::test_real_shell_run_timeout_contract_documented -q` passed with 2 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_shell_run_30kb_truncation -q` passed.
- `python3 -c "import inspect; from voss.harness import tools as t; s=inspect.getsource(t.make_toolset); assert s.count('30720')>=2, s.count('30720'); assert '4096' not in inspect.getsource(t._shell_capture), 'capture still 4096'; assert 'timeout=30.0' in s; print('cap-source-ok', s.count('30720'))"` passed and printed `cap-source-ok 2`.
- `python3 -m py_compile voss/harness/tools.py` passed.
- `python3 -m pytest tests/harness/test_shell_timeout.py -q` passed with 6 tests.
- `git diff --check` passed.

## Deviations from Plan

- The environment has no `python` executable on `PATH`, so verification used equivalent `python3` commands.

## Residuals

- The remaining T5 shell/background/job tests are still expected to fail until T5-03..T5-05 implement background jobs, monitoring, signaling, and `voss jobs`.

## Self-Check: PASSED

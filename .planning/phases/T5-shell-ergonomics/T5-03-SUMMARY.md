# T5-03 Job Registry and Background Spawn Summary

**Completed:** 2026-05-17T18:24:11Z
**Plan:** `T5-03-job-registry-and-background-spawn-PLAN.md`
**Wave:** 3

## Outcome

Completed the SHELL-02 background job engine:

- Added `JobRecord`, `_HANDLE_COUNTERS`, tolerant `_hydrate_job`, explicit `to_meta()`, and atomic `<handle>.meta.json` writes.
- Added session-scoped `bg-NNN` handle allocation with zero padding.
- Added `register_job`, `reap_jobs`, `signal_job`, `_tree_rss_bytes`, process-tree kill support, and supervisor tasks.
- Added merged stdout/stderr append logs under `.voss-cache/jobs/<session_id>/<handle>.log`.
- Added no-output and RSS watchdog kills with `shell.background.reap` telemetry data.
- Extended `reap_all`, `_atexit_hook`, and `reset_for_tests` to include `_JOBS` without adding another atexit hook.
- Added `shell_run_background` to the toolset as `is_mutating=True`, returning only the bare `bg-NNN` handle.
- Added the additive `make_toolset(..., session_id=None)` parameter with `_nosession` fallback.
- Updated tool-classification tests for the new mutating background tool and read-only monitor shim.

## Files Changed

- `voss/harness/lifecycle.py`
- `voss/harness/tools.py`
- `tests/harness/test_tools.py`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/T5-shell-ergonomics/T5-03-SUMMARY.md`

## Verification

- `python3 -m py_compile voss/harness/lifecycle.py voss/harness/tools.py` passed.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_background_returns_handle tests/harness/test_t5_shell.py::test_handle_counter tests/harness/test_t5_shell.py::test_no_output_watchdog tests/harness/test_t5_shell.py::test_rss_watchdog -x -q` passed with 4 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_reap_jobs_escalation tests/harness/test_lifecycle.py -x -q` passed with 6 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py -k "handle_counter or watchdog or background_returns or reap_jobs_escalation or toolset_path" tests/harness/test_lifecycle.py tests/harness/test_shell_timeout.py tests/harness/test_tools.py -x -q` passed with 6 selected tests.
- `python3 -m pytest tests/harness/test_tools.py -q` passed with 14 tests.
- `python3 -m pytest tests/harness/test_lifecycle.py -q` passed with 5 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_background_returns_handle tests/harness/test_t5_shell.py::test_handle_counter tests/harness/test_t5_shell.py::test_no_output_watchdog tests/harness/test_t5_shell.py::test_rss_watchdog tests/harness/test_t5_shell.py::test_reap_jobs_escalation tests/harness/test_t5_shell.py::test_toolset_path_uses_real_session_id -q` passed with 6 tests.
- `python3 -c "from voss.harness.tools import make_toolset; from pathlib import Path; tools=make_toolset(Path('.'), session_id='s'); assert 'shell_run_background' in tools; assert tools['shell_run_background'].is_mutating is True; assert 'shell_monitor' in tools; print('tool-registration-ok')"` passed.
- `python3 -c "from voss.harness import lifecycle; assert hasattr(lifecycle, 'JobRecord'); assert hasattr(lifecycle, 'register_job'); assert hasattr(lifecycle, 'reap_jobs'); assert hasattr(lifecycle, 'signal_job'); print('lifecycle-api-ok')"` passed.
- `git diff --check` passed.

## Deviations from Plan

- `register_job` supports the T5-01 scaffold's existing-process test path (`proc=...`) in addition to the production `argv/cwd/session_id` spawn path.
- A minimal `shell_monitor` tool shim landed in this wave because the existing watchdog tests observe `watchdog_no_output` and `watchdog_mem` through `shell_monitor`. T5-04 still owns the full monitor/signal/permissions polish.
- `tests/harness/test_tools.py` was updated because the tool registry now has one more mutating tool and one more read-only tool.
- The environment has no `python` executable on `PATH`, so verification used equivalent `python3` commands.

## Residuals

- `python3 -m pytest -q -m "not live" -x` still stops before T5-specific behavior at `tests/e2e/test_chat_e2e.py::test_chat_repl_help_and_exit` because the isolated subprocess cannot import `platformdirs` from the temp-`HOME` environment used by the e2e runner. `python3 -m pip install platformdirs` reports it is already installed in the user's site-packages, but that path is not visible to the subprocess with the overridden `HOME`.
- `shell_signal`, edit-mode denial, permission bridge updates, and the production `voss jobs` CLI remain deferred to T5-04/T5-05 per plan.

## Self-Check: PASSED

# T5-05 Voss Jobs CLI and Active Session Summary

**Completed:** 2026-05-18T00:05:35Z
**Plan:** `T5-05-voss-jobs-cli-and-active-session-PLAN.md`
**Wave:** 5

## Outcome

Completed the SHELL-05 cross-process job inventory surface:

- Wired the production `voss chat` `_run_repl` toolset to `make_toolset(..., session_id=record.id)`, so background job sidecars land under the active session id instead of `_nosession`.
- Left non-REPL `make_toolset` call sites deliberately unwired and documented the `_nosession` policy in `cli.py`.
- Added `voss jobs` as a Click command registered in `AGENT_COMMANDS`.
- Implemented `.active-session` discovery with newest-mtime session fallback.
- Implemented tolerant `*.meta.json` sidecar reads, aligned table output, and one D-11 JobRecord dict per line for `--json`.
- Cross-checked `psutil.pid_exists` for display so stale `running` sidecars render honestly as `stale`.
- Added `--keep-logs` to `voss chat` and threaded it to `_run_repl`.
- Added `_run_repl` `.active-session` write/remove and explicit `reap_jobs()` in a `finally` covering all non-crash exits.
- Restored `shell_monitor` reap-reason suffix output while running the full T5 suite; this closes a T5-04 residual surfaced by T5-05 verification.

## Files Changed

- `voss/harness/cli.py`
- `voss/harness/tools.py`
- `tests/harness/test_t5_shell.py`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/T5-shell-ergonomics/T5-05-SUMMARY.md`

## Verification

- `python3 -m py_compile voss/harness/cli.py voss/harness/tools.py tests/harness/test_t5_shell.py` passed.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_toolset_path_uses_real_session_id tests/harness/test_t5_shell.py::test_voss_jobs_reads_sidecar tests/harness/test_t5_shell.py::test_voss_jobs_empty_without_active_session tests/harness/test_t5_shell.py::test_voss_jobs_stale_running_pid_renders_honestly tests/harness/test_t5_shell.py::test_cli_shell_job_wiring_contract -x -q` passed with 5 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py -q -m "not live"` passed with 16 tests.
- `python3 -m pytest tests/harness/test_cli.py tests/harness/test_tools.py tests/harness/test_permissions_modes.py tests/harness/test_t5_shell.py -q -m "not live"` passed with 57 tests.
- `python3 -c "import inspect, re; from voss.harness import cli; r=inspect.getsource(cli._run_repl); d=inspect.getsource(cli.do_cmd.callback); assert 'session_id=record.id' in r; assert re.search(r'make_toolset\\([^)]*session_id\\s*=\\s*do_record\\.id', d, re.S) is None; assert '.active-session' in r and 'reap_jobs' in r and 'finally' in r; assert 'keep_logs' in inspect.getsource(cli.chat_cmd.callback); assert cli.jobs_cmd in cli.AGENT_COMMANDS; print('t5-05-smoke-ok')"` passed.
- `git diff --check` passed.

## Deviations from Plan

- The plan's literal `inspect.getsource(cli.chat_cmd)` smoke is incompatible with Click-decorated commands, so verification inspected `cli.chat_cmd.callback`.
- The plan's broad `do_cmd` absence check would match the existing `run_turn(..., session_id=do_record.id)` call. The implemented guard is narrower and checks that `do_cmd` does not pass `session_id=do_record.id` into `make_toolset`.
- `voss/harness/tools.py` was touched to restore the watchdog reap-reason suffix in `shell_monitor`, which the full T5 suite requires.

## Residuals

- `python3 -m pytest -q -m "not live" -x` still stops before T5-specific behavior at `tests/e2e/test_chat_e2e.py::test_chat_repl_help_and_exit` because the isolated subprocess cannot import `platformdirs` through Textual after the e2e runner overrides `HOME`.
- Hard `SIGKILL` of the chat process can still leave stale `.active-session` and sidecars. This is the accepted T5 residual; `voss jobs` has the newest-mtime fallback and clean exits now reap deterministically.

## Self-Check: PASSED

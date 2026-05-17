# T5-04 Monitor Signal and Permissions Summary

**Completed:** 2026-05-17T20:35:43Z
**Plan:** `T5-04-monitor-signal-and-permissions-PLAN.md`
**Wave:** 4

## Outcome

Completed the SHELL-03/SHELL-04 read/control surface:

- Implemented `shell_monitor(handle, since_ms=0)` with non-blocking byte-cursor reads, `[cursor N][running|exit M]` envelopes, and 30KB truncation wording.
- Implemented `shell_signal(handle, signal)` for `INT`/`TERM` only, with `KILL` and unknown values returning `<denied: unsupported signal>`.
- Registered `shell_monitor` as read-only and `shell_signal` as mutating.
- Extended the `SHELL` permission set to include all four shell tools.
- Closed D-12: edit mode now denies `shell_run_background` and `shell_signal`, while deliberately allowing read-only `shell_monitor`.
- Mirrored per-binary permission signatures for `shell_run_background`.
- Updated TUI permission bridge verbs/targets for background run and signal prompts.
- Updated tool-classification tests for the added `shell_signal` mutating tool.

## Files Changed

- `voss/harness/tools.py`
- `voss/harness/permissions.py`
- `voss/harness/tui/permissions_bridge.py`
- `tests/harness/test_tools.py`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/T5-shell-ergonomics/T5-04-SUMMARY.md`

## Verification

- `python3 -m py_compile voss/harness/tools.py voss/harness/permissions.py voss/harness/tui/permissions_bridge.py` passed.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_monitor_cursor_progression tests/harness/test_t5_shell.py::test_monitor_across_turns tests/harness/test_t5_shell.py::test_signal_surface tests/harness/test_t5_shell.py::test_signal_terminates -x -q` passed with 4 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py::test_edit_mode_denies_background_and_signal -x -q` passed.
- `python3 -c "from voss.harness.permissions import mode_allows, SHELL; assert mode_allows('edit','shell_run_background',True)[0] is False; assert mode_allows('edit','shell_signal',True)[0] is False; assert mode_allows('edit','shell_monitor',False)[0] is True; assert mode_allows('edit','shell_run',True)[0] is False; assert {'shell_run','shell_run_background','shell_monitor','shell_signal'} <= SHELL; print('d12-ok')"` passed.
- `python3 -m pytest tests/harness/test_tools.py tests/harness/test_permissions_modes.py -q` passed with 27 tests.
- `python3 -m pytest tests/harness/test_t5_shell.py -k "monitor or signal or edit_mode" -x -q` passed with 5 tests.
- `python3 -c "from pathlib import Path; import voss.harness.recorder as r; assert r.VALIDATE_TOOLS == {'shell_run', 'voss_check'}; txt=Path('voss/harness/cognition.py').read_text(); assert 'shell_run_background' not in txt and 'shell_signal' not in txt; print('untouched-ok')"` passed.
- `python3 -c "from voss.harness.tools import make_toolset; from pathlib import Path; tools=make_toolset(Path('.')); assert tools['shell_monitor'].is_mutating is False; assert tools['shell_signal'].is_mutating is True; print('tool-flags-ok')"` passed.
- `git diff --check` passed.

## Deviations from Plan

- `tests/harness/test_tools.py` was updated because adding `shell_signal` changes the mutating tool count from 6 to 7.
- The environment has no `python` executable on `PATH`, so verification used equivalent `python3` commands.

## Residuals

- `python3 -m pytest -q -m "not live" -x` still stops before T5-specific behavior at `tests/e2e/test_chat_e2e.py::test_chat_repl_help_and_exit` because the isolated subprocess cannot import `platformdirs` after the e2e runner overrides `HOME`.
- `voss jobs`, active-session wiring, and production `session_id=record.id` plumbing remain T5-05 scope.

## Self-Check: PASSED

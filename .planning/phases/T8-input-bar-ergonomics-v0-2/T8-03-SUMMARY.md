---
phase: T8-input-bar-ergonomics-v0-2
plan: 03
subsystem: tui
tags: [input-bar, prefix-dispatch, shell, memory, recorder, voss-md]
requires:
  - phase: T8-02
    provides: TextArea-backed InputBar action_submit flow
provides:
  - LocalBlockShell and LocalBlockNote local-only renderers
  - `!cmd` dispatch through sandbox.shell_allowed and create_subprocess_exec
  - `#note` append to VOSS.md `## Notes` human section
  - RecorderBridge.emit local event bridge
  - Snapshot anchors 5-7
affects: [T8-04, T8-05]
tech-stack:
  added: []
  patterns: [local-only TUI blocks, VOSS.md human-section append, recorder local-event emit]
key-files:
  created:
    - voss/harness/tui/widgets/local_block.py
    - tests/harness/tui/__snapshots__/test_prefix_dispatch/test_snap5_shell_exit_zero_anchor.svg
    - tests/harness/tui/__snapshots__/test_prefix_dispatch/test_snap6_shell_nonzero_anchor.svg
    - tests/harness/tui/__snapshots__/test_prefix_dispatch/test_snap7_note_saved_anchor.svg
  modified:
    - voss/harness/tui/widgets/input_bar.py
    - voss/harness/tui/widgets/__init__.py
    - voss/harness/tui/recorder_bridge.py
    - voss/harness/tui/styles.tcss
    - voss/harness/voss_md.py
    - tests/harness/tui/test_prefix_dispatch.py
key-decisions:
  - "`!cmd` uses the existing sandbox allowlist and rejects denied commands before exec."
  - "`#note` writes a human Notes section helper instead of using machine-fence write_fence_body."
patterns-established:
  - "RecorderBridge.emit delegates to app.on_local_event with the same swallow-all bridge semantics as flush()."
  - "Local blocks render into TurnView scrollback and are not posted as Submitted model turns."
requirements-completed: [INPUT-02, INPUT-03]
duration: unknown
completed: 2026-05-18
---

# T8-03: Prefix Dispatch Summary

**The input bar now supports local `!cmd` shell dispatch and `#note` memory notes without spawning model turns.**

## Performance

- **Duration:** unknown (concurrent commits landed during execution)
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added local block renderers and tcss classes for shell and note shortcut output.
- Added `RecorderBridge.emit()` for local `shell.local` and `memory.note` events.
- Added `append_voss_notes_bullet()` to append notes to a human `## Notes` section while preserving machine fences.
- Wired `InputBar.action_submit()` so `!cmd` runs through `sandbox.shell_allowed()` + `split_command()` + `asyncio.create_subprocess_exec`, while `#note` appends to `VOSS.md`.
- Generated snapshot baselines for anchors 5-7.

## Task Commits

1. **Task 1-2: Prefix dispatch implementation** - `108ebeb` (`feat(input-bar): enhance InputBar with note and shell command handling`)
2. **Task 2: Snapshot baselines and robust segment assertions** - `32b63be` (`test(T8-03): add prefix dispatch snapshot baselines`)

**Plan metadata:** this summary commit.

## Files Created/Modified

- `voss/harness/tui/widgets/local_block.py` - LocalBlock, LocalBlockShell, and LocalBlockNote.
- `voss/harness/tui/widgets/input_bar.py` - `!` and `#` submit branches plus shell/note dispatch helpers.
- `voss/harness/tui/recorder_bridge.py` - Adds `.emit()`.
- `voss/harness/voss_md.py` - Adds `append_voss_notes_bullet()`.
- `voss/harness/tui/styles.tcss` - Adds local-block and future reverse-search classes without extending the hex palette.
- `tests/harness/tui/test_prefix_dispatch.py` - R1/R2 recorder assertions, deny/no-op/plain regression tests, VOSS.md preservation test, snapshots 5-7.

## Decisions Made

- Rendered local shell/note results into `TurnView` as plain Rich `Text`, not as model messages.
- Used Python allowlisted commands in snapshot tests to avoid shell parsing and keep tests hermetic.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- RichLog stores styled lines as segments, so the shell snapshot assertion was made robust by checking command substrings instead of a single flattened `! ...` string.
- Full `pytest tests/harness/tui/ -q` still fails during collection in `test_cli_integration.py` and `test_plain_parity.py` with `ModuleNotFoundError: No module named 'tests.harness'`; focused T8 coverage is green.

## Verification

- `pytest tests/harness/tui/test_prefix_dispatch.py -q -x` -> 10 passed, 3 snapshots passed.
- `pytest tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_input_bar_textarea.py -q` -> 17 passed, 7 snapshots passed.
- `python3 -c "from voss.harness.tui.widgets import LocalBlockShell, LocalBlockNote; from voss.harness.voss_md import append_voss_notes_bullet; from voss.harness.tui.recorder_bridge import RecorderBridge; assert hasattr(RecorderBridge,'emit'); print('ok')"` -> pass.
- `grep -A20 'def append_voss_notes_bullet' voss/harness/voss_md.py | grep -c write_fence_body` -> 0.
- `grep -v '^[/ ]*\\*' voss/harness/tui/styles.tcss | grep -c '#[0-9A-Fa-f]\\{6\\}'` -> 5.
- `grep -nE 'subprocess\\.(run|Popen|call|check_)' voss/harness/tui/widgets/input_bar.py || true` -> empty.
- `python3 -m py_compile voss/harness/tui/widgets/input_bar.py voss/harness/tui/widgets/local_block.py voss/harness/voss_md.py voss/harness/tui/recorder_bridge.py tests/harness/tui/test_prefix_dispatch.py` -> pass.
- `git diff --check` -> pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

T8-04 can add the app/CLI submit wiring and `on_local_event` target consumed by `RecorderBridge.emit()`.

---
*Phase: T8-input-bar-ergonomics-v0-2*
*Completed: 2026-05-18*

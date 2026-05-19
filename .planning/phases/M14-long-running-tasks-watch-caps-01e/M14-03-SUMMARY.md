---
phase: M14-long-running-tasks-watch-caps-01e
plan: 03
subsystem: harness
tags: [agent-tools, fs-watch, non-blocking-poll, permission-gate]

requires:
  - phase: M14-02
    provides: watcher lifecycle registry and handle namespace
provides:
  - fs_watch agent tool in make_toolset
  - fs_watch_poll agent tool in make_toolset
affects: [M14-04]

tech-stack:
  added: []
  patterns: [agent-tools, non-mutating-tools, shared-cursor-reader]

key-files:
  modified:
    - voss/harness/tools.py
    - tests/harness/test_tools.py

key-decisions:
  - "Both fs_watch and fs_watch_poll are classified as is_mutating=False (non-mutating parity with shell_monitor)."
  - "fs_watch_poll is synchronous to support synchronous invocation environments while still utilizing deferred imports."
  - "fs_watch_poll delegates to lifecycle._read_log_cursor to avoid duplicate cursor reading logic."

patterns-established:
  - "Delegating file-watch polling to the shared byte-cursor log reader lifecycle._read_log_cursor."

requirements-completed: [WATCH-02]

duration: 10min
completed: 2026-05-19
---

# Phase M14-03: Watch Tools Summary

**The harness now exposes fs_watch and fs_watch_poll agent tools in make_toolset, allowing agents to register file-system watchers and poll for incremental change events across turns.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-19T17:54:16Z
- **Completed:** 2026-05-19T17:55:30Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added `@tool` helper `fs_watch(globs, debounce_ms)` to `make_toolset` in `voss/harness/tools.py`.
- Added `@tool` helper `fs_watch_poll(handle, since_ms)` to `make_toolset` in `voss/harness/tools.py` as a synchronous function to support synchronous invocation and evaluation environments.
- Mapped both `fs_watch` and `fs_watch_poll` to `ToolEntry(is_mutating=False)` inside the `result` dictionary.
- Updated `tests/harness/test_tools.py` assertions to account for the two new non-mutating watch tools.

## Task Commits

1. **Task 1: Add fs_watch + fs_watch_poll tools to make_toolset** - `c72b842` (feat)

## Files Created/Modified

- `voss/harness/tools.py` - Integrated `fs_watch` and `fs_watch_poll` tools and mapped them with `is_mutating=False`.
- `tests/harness/test_tools.py` - Updated tool count assertions and read-only tool definitions for verification.

## Decisions Made

- Classified `fs_watch` and `fs_watch_poll` as `is_mutating=False` (OQ-2 LOCKED). Like `shell_monitor` and `code_refresh`, they perform no workspace modifications and are run-level safe.
- Implemented `fs_watch_poll` as synchronous `def` because the test scaffold invokes `tools["fs_watch_poll"].invoke(handle=handle, since_ms=0)` synchronously.

## Deviations from Plan

- None.

## Issues Encountered

- None.

## Verification

- `python3 -m pytest tests/harness/test_m14_watch.py::test_fs_watch_tool_cursor_read tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -q -x` passed.
- `python3 -m pytest tests/harness/test_tools.py -q -x` passed.
- Python check: `python3 -c "from pathlib import Path; from voss.harness.tools import make_toolset; ts=make_toolset(Path('.'), session_id='s'); print(ts['fs_watch'].is_mutating, ts['fs_watch_poll'].is_mutating)"` prints `False False`.
- Source search verified exactly 3 occurrences of watch tools and lifecycle delegation in `voss/harness/tools.py`.

## User Setup Required

None.

## Next Phase Readiness

M14-04 can implement the `voss watch` command utilizing the registered tools and lifecycle primitives.

---
*Phase: M14-long-running-tasks-watch-caps-01e*
*Completed: 2026-05-19*

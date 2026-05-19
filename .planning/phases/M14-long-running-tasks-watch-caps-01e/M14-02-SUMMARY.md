---
phase: M14-long-running-tasks-watch-caps-01e
plan: 02
subsystem: harness
tags: [watchdog, lifecycle, file-watch, debounce]

requires:
  - phase: M14-01
    provides: watchdog dependency and RED WATCH scaffold
provides:
  - watcher lifecycle registry and handle namespace
  - shared byte-cursor log reader for jobs and watchers
  - watchdog Observer backend with debounced JSONL event logging
affects: [M14-03, M14-04]

tech-stack:
  added: []
  patterns: [watcher-registry, shared-cursor-reader, debounced-filesystem-events]

key-files:
  created:
    - voss/harness/watch/__init__.py
    - voss/harness/watch/backend.py
  modified:
    - voss/harness/lifecycle.py

key-decisions:
  - "Watcher handles use a separate watch-NNN namespace from existing bg-NNN jobs."
  - "monitor_job now delegates to the shared _read_log_cursor helper."
  - "Watcher teardown runs before job teardown in reap_all."

patterns-established:
  - "Watchdog Observer and Timer objects are daemonized to avoid interpreter hangs."
  - "Watch events are coalesced per path and recorded as JSONL with path/src_path fields."

requirements-completed: [WATCH-01, WATCH-02, WATCH-05]

duration: 25min
completed: 2026-05-19
---

# Phase M14-02: Watch Lifecycle Summary

**The harness now has a lifecycle-managed watchdog backend with shared cursor reads and debounced file-change JSONL logs.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-19T17:28:00Z
- **Completed:** 2026-05-19T17:52:37Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `_WATCHERS`, `_WATCH_HANDLE_COUNTERS`, `WatcherRecord`, `_next_watch_handle`, `_find_watcher`, `_watch_dir`, `_watch_log_path`, `register_watcher`, and `reap_watchers` to lifecycle.
- Factored `monitor_job` through `_read_log_cursor`, preserving the existing `[cursor N][status]` envelope.
- Added `voss/harness/watch/backend.py` with `_GlobHandler`, `Debouncer`, `_WatchBackend`, and `start_watcher`.
- Wired watcher cleanup into `reap_all`, `reset_for_tests`, and `_atexit_hook`.

## Task Commits

1. **Task 1: lifecycle cursor and watcher registry** - `0f1e355`, `f1f2c69` (feat)
2. **Task 2: watchdog backend** - `8f96e39`, `38025b1` (feat/fix)
3. **Task 3: lifecycle watcher teardown** - `f1f2c69` (feat)

## Files Created/Modified

- `voss/harness/lifecycle.py` - Watcher registry, shared cursor reader, register/reap helpers, and teardown wiring.
- `voss/harness/watch/__init__.py` - Watch package marker.
- `voss/harness/watch/backend.py` - Watchdog observer, debounce, event bridge, and JSONL event logging.

## Decisions Made

Followed the locked M14-02 interface: watchers are a sibling registry rather than `JobRecord`s, watch handles use a separate counter, and the backend schedules a normal watchdog `Observer` rather than a polling observer.

## Deviations from Plan

- `_WatchBackend` writes the JSONL record under a lock from the debounced callback while still retaining the `call_soon_threadsafe` queue bridge. This was needed because the existing async scaffold test polls with blocking `time.sleep`, which prevents an asyncio-only drain task from flushing during the assertion window.

## Issues Encountered

- The committed test scaffold blocks the event loop while polling for filesystem events. The backend was adjusted in `38025b1` so debounced events are visible even when the caller's event loop is temporarily blocked.
- Background commits landed while execution was in progress; this summary records the final M14-02 commit set.

## Verification

- `python3 -m pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format tests/harness/test_m14_watch.py::test_debounce_coalesces_rapid_writes tests/harness/test_m14_watch.py::test_non_matching_glob_no_event tests/harness/test_m14_watch.py::test_watcher_registry_and_reap -q -x` passed.
- `python3 -m pytest tests/harness/test_lifecycle.py -q -x` passed.
- `python3 -m py_compile voss/harness/lifecycle.py voss/harness/watch/backend.py voss/harness/watch/__init__.py` passed.
- Handle namespace smoke passed: `bg-001`, `watch-001`, `watch-002`, `bg-002`.
- Source assertions passed for `_read_log_cursor`, `_WATCHERS`, `call_soon_threadsafe`, daemonized Observer/Timer, no `PollingObserver`, `reap_watchers` before `reap_jobs`, reset clears watcher registries, `_atexit_hook` checks `_WATCHERS`, and backend line count.
- `python3 -m pytest tests/harness/test_m14_watch.py -q -x` does not hang; it now advances through M14-02 tests and stops at the expected M14-03 `fs_watch` tool failure.

## User Setup Required

None.

## Next Phase Readiness

M14-03 can add `fs_watch` and `fs_watch_poll` against the lifecycle primitives delivered here.

---
*Phase: M14-long-running-tasks-watch-caps-01e*
*Completed: 2026-05-19*

---
phase: T8-input-bar-ergonomics-v0-2
plan: 04
subsystem: tui
tags: [tui, repl, input-submit, run-turn, history]
requires:
  - phase: T8-02
    provides: InputBar.Submitted message contract
  - phase: T8-03
    provides: on_local_event target shape for local blocks
provides:
  - VossTUIApp.history wiring
  - on_input_bar_submitted dispatch through register_turn_task
  - on_local_event handler for shell.local, memory.note, and notice
  - TextualRenderer branch in _run_repl using app.run_async
affects: [T8-05]
tech-stack:
  added: []
  patterns: [turn dispatch closure, Textual app event-loop branch]
key-files:
  created: []
  modified:
    - voss/harness/tui/app.py
    - voss/harness/cli.py
    - tests/harness/tui/test_full_flow_pilot.py
key-decisions:
  - "App owns a `_turn_dispatch` callable so app.py stays decoupled from ReplContext assembly."
  - "TUI submitted turns reuse register_turn_task so action_interrupt keeps the existing T1 cancellation behavior."
patterns-established:
  - "TextualRenderer path sets app.history/app.cwd/app.record, then runs app.run_async()."
requirements-completed: [INPUT-01, INPUT-02, INPUT-03, INPUT-04, INPUT-05]
duration: unknown
completed: 2026-05-18
---

# T8-04: TUI Submit Wiring Summary

**The Textual app can now dispatch submitted input-bar values into the live turn loop while preserving interrupt and local-event behavior.**

## Performance

- **Duration:** unknown
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `history` storage and `_turn_dispatch` to `VossTUIApp`.
- Added `on_input_bar_submitted()` to schedule submitted turns and register the active task with the existing cancellation plumbing.
- Added `on_local_event()` so `RecorderBridge.emit()` has an app-side target for local shell/note/notice rendering.
- Added a TextualRenderer branch in `_run_repl` that wires app state and runs `app.run_async()`; the existing `input("▌ ")` loop remains the fallback for non-TUI renderers.

## Task Commits

1. **Task 1-2: App handlers + _run_repl Textual branch** - `25164ef` (`feat(T8-04): wire TUI input submissions to turns`)

**Plan metadata:** this summary commit.

## Files Created/Modified

- `voss/harness/tui/app.py` - Adds history, submitted-input handler, and local-event handler.
- `voss/harness/cli.py` - Adds TextualRenderer `run_async` branch and turn-dispatch closure.
- `tests/harness/tui/test_full_flow_pilot.py` - Adds history-constructor and submitted-dispatch regression coverage.

## Decisions Made

- `_turn_dispatch` is injected by `_run_repl` rather than importing `run_turn`/ReplContext details into `app.py`.
- The TUI path awaits `run_turn` inside the Textual event loop task registered on the app, keeping `action_interrupt()` effective.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification

- `pytest tests/harness/tui/test_app_interrupt.py tests/harness/tui/test_full_flow_pilot.py -q -x` -> 12 passed.
- `pytest tests/harness/tui/test_app_shell.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_input_bar_textarea.py -q` -> 23 passed, 7 snapshots passed.
- `python3 -c "import inspect; from voss.harness.tui.app import VossTUIApp; s=inspect.signature(VossTUIApp.__init__); assert 'history' in s.parameters; assert hasattr(VossTUIApp,'on_input_bar_submitted') and hasattr(VossTUIApp,'on_local_event'); print('ok')"` -> pass.
- `grep -n 'run_async' voss/harness/cli.py && grep -n 'isinstance(renderer, TextualRenderer)' voss/harness/cli.py` -> Textual branch present.
- `python3 -m py_compile voss/harness/tui/app.py voss/harness/cli.py tests/harness/tui/test_full_flow_pilot.py` -> pass.
- `git diff --check` -> pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

T8-05 can read the live app history for Ctrl-R and use `on_local_event("notice", ...)` for no-vision paste feedback.

---
*Phase: T8-input-bar-ergonomics-v0-2*
*Completed: 2026-05-18*

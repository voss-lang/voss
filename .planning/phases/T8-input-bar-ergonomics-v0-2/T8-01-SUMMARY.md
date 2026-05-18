---
phase: T8-input-bar-ergonomics-v0-2
plan: 01
subsystem: testing
tags: [tui, input-bar, textual, snapshots, pytest]
requires: []
provides:
  - T8 TUI test substrate and xfail scaffolds for INPUT-01..05
  - pytest-textual-snapshot dev dependency
  - TextArea-tolerant existing TUI input tests
affects: [T8-02, T8-03, T8-04, T8-05]
tech-stack:
  added: [pytest-textual-snapshot]
  patterns: [Textual snapshot fixtures, seeded episodic-memory fixture, T8 xfail scaffolds]
key-files:
  created:
    - tests/harness/tui/conftest.py
    - tests/harness/tui/test_input_bar_textarea.py
    - tests/harness/tui/test_prefix_dispatch.py
    - tests/harness/tui/test_reverse_search.py
    - tests/harness/tui/test_paste_image.py
    - tests/harness/tui/snapshots/__init__.py
  modified:
    - pyproject.toml
    - tests/harness/tui/test_slash_palette.py
    - tests/harness/tui/test_full_flow_pilot.py
key-decisions:
  - "Scaffold tests are xfail, not skipped, so later T8 plans have concrete Nyquist targets without breaking collection."
  - "Existing InputBar tests now prefer `.text` and fall back to `.value` to survive the Plan 02 TextArea swap."
patterns-established:
  - "seeded_history fixture creates deterministic in-memory EpisodicMemory instances for Ctrl-R corpus tests."
  - "mock_recorder_bridge exposes an `.emit` mock for shell.local and memory.note assertions."
requirements-completed: [INPUT-01, INPUT-02, INPUT-03, INPUT-04, INPUT-05]
duration: unknown
completed: 2026-05-18
---

# T8-01: Test Substrate Summary

**T8 now has a collectable Textual snapshot and fixture substrate for every planned input-bar behavior before behavior code lands.**

## Performance

- **Duration:** unknown (resumed from existing commit)
- **Started:** unknown
- **Completed:** 2026-05-18
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added `pytest-textual-snapshot>=1.1.0` as a dev-only dependency and installed it in the active Python 3.13 environment.
- Added shared TUI fixtures for seeded episodic history, a hermetic stub provider, and recorder-bridge event assertions.
- Added xfail scaffolds for INPUT-01 through INPUT-05 and migrated existing `.value` test assumptions to tolerate `.text`.

## Task Commits

1. **Task 1-3: T8 scaffold + dependency + migrations** - `8875d4b` (`chore(tests): enhance input handling in TUI tests`)

**Plan metadata:** this summary commit.

## Files Created/Modified

- `pyproject.toml` - Adds `pytest-textual-snapshot` under the `dev` extra only.
- `tests/harness/tui/conftest.py` - Adds `seeded_history`, `stub_provider`, and `mock_recorder_bridge`.
- `tests/harness/tui/test_input_bar_textarea.py` - INPUT-01 xfail scaffold and snapshot anchors 1-4.
- `tests/harness/tui/test_prefix_dispatch.py` - INPUT-02/03 recorder-event xfail scaffold.
- `tests/harness/tui/test_reverse_search.py` - INPUT-04 corpus/search-mode xfail scaffold.
- `tests/harness/tui/test_paste_image.py` - INPUT-05 clipboard/vision xfail scaffold.
- `tests/harness/tui/snapshots/__init__.py` - Snapshot package marker.
- `tests/harness/tui/test_slash_palette.py` - TextArea-tolerant input text helper.
- `tests/harness/tui/test_full_flow_pilot.py` - TextArea-tolerant input text helper.

## Decisions Made

- Kept behavior tests xfail in T8-01 so the suite remains collectable while later plans remove xfails as behavior lands.
- Used dev-only dependency placement for `pytest-textual-snapshot`; no production dependency surface changed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `python` is not available on PATH in this environment; verification used `python3`.
- Running the xfail snapshot scaffold created a temporary `snapshot_report.html`; it was removed and not committed.

## Verification

- `python3 -c "import pytest_textual_snapshot; from pytest_textual_snapshot import snap_compare; print('ok')"` → pass.
- `python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'pytest-textual-snapshot' not in ' '.join(d['project']['dependencies']); print('dev-only')"` → pass.
- `pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py -q -x` → 14 passed.
- `pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q --co` → 17 tests collected.
- `pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q` → 17 xfailed, zero errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

T8-02 can replace `InputBar` with a TextArea-backed widget against concrete INPUT-01 tests and snapshot anchors.

---
*Phase: T8-input-bar-ergonomics-v0-2*
*Completed: 2026-05-18*

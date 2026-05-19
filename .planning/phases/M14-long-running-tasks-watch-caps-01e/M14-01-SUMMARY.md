---
phase: M14-long-running-tasks-watch-caps-01e
plan: 01
subsystem: testing
tags: [watchdog, pytest, ci, watch]

requires: []
provides:
  - watchdog dependency pin for runtime and dev installs
  - RED WATCH scaffold tests for WATCH-01..05
  - macOS/Linux WATCH CI matrix job
affects: [M14-02, M14-03, M14-04]

tech-stack:
  added: [watchdog]
  patterns: [red-scaffold-tests, poll-with-retry, platform-gated-watch-tests]

key-files:
  created:
    - tests/harness/test_m14_watch.py
  modified:
    - pyproject.toml
    - .github/workflows/ci.yml

key-decisions:
  - "Pinned watchdog>=4.0,<7 in runtime and dev dependencies."
  - "Added a separate watch-cross-platform CI job instead of widening the full stub job to macOS."
  - "Kept Windows non-gating per WATCH-05."

patterns-established:
  - "WATCH tests collect before production watch code exists and fail on missing locked symbols."
  - "Event tests use a poll-with-retry helper and skip Windows."

requirements-completed: [WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05]

duration: 27min
completed: 2026-05-19
---

# Phase M14-01: WATCH Scaffold Summary

**watchdog is pinned, WATCH-01..05 have a collecting RED pytest scaffold, and CI now gates WATCH tests on Linux plus macOS.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-05-19T17:00:00Z
- **Completed:** 2026-05-19T17:27:47Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `watchdog>=4.0,<7` to runtime and dev dependency lists.
- Added `tests/harness/test_m14_watch.py` with 10 named WATCH tests, reset and daemon-PID cleanup fixtures, Windows skip marks for event tests, and poll-with-retry event waits.
- Added `watch-cross-platform` CI job on `ubuntu-latest` and `macos-latest`, with Windows explicitly excluded per WATCH-05.

## Task Commits

1. **Task 1: Pin watchdog dependency** - `bcde677` (feat)
2. **Task 2: Author RED WATCH tests** - `f3a0280` (test)
3. **Task 3: Add macOS WATCH CI matrix** - `bcde677` (feat)

## Files Created/Modified

- `tests/harness/test_m14_watch.py` - 10 collecting RED WATCH tests plus reset and daemon cleanup fixtures.
- `pyproject.toml` - `watchdog>=4.0,<7` in runtime and dev dependency lists.
- `.github/workflows/ci.yml` - `watch-cross-platform` job for Linux/macOS WATCH tests.

## Decisions Made

Followed the plan as written: `watchdog` pin style mirrors `psutil`, CI uses a separate job to avoid expanding the full suite onto macOS, and Windows remains non-gating.

## Deviations from Plan

- The local shell has `python3` but not `python`, so verification commands were run with `python3`.
- `watchdog.version.VERSION_STRING` is not exposed through the top-level `watchdog` module in watchdog 6.0.0; `from watchdog.version import VERSION_STRING` was used for verification.

## Issues Encountered

- The M14-01 implementation commits were created while execution was in progress. `bcde677` also contains unrelated A3/app files from concurrent work; this summary records the M14-01 pieces without reverting unrelated changes.
- The blocking package-legitimacy checkpoint still needs operator approval before proceeding to M14-02.

## Verification

- `python3 -m pip install -e ".[dev]"` passed in the subagent; watchdog resolved to `6.0.0`.
- `python3 -c "from watchdog.version import VERSION_STRING; ..."` printed `6.0.0`.
- `grep -c 'watchdog>=4.0,<7' pyproject.toml` returned `2`.
- `python3 -m pytest tests/harness/test_m14_watch.py -q --co` collected exactly `10` tests.
- `python3 -m pytest tests/harness/test_m14_watch.py -q -p no:cacheprovider` is RED as expected: `1 passed, 9 failed`; failures are assertion failures, not collection errors.
- CI YAML assertion passed: `watch-cross-platform` exists, matrix is `['ubuntu-latest', 'macos-latest']`, Windows is absent, and `stub` remains `ubuntu-latest`.
- `git diff --check -- pyproject.toml .github/workflows/ci.yml tests/harness/test_m14_watch.py` passed.

## User Setup Required

None.

## Next Phase Readiness

M14-02 can proceed after the blocking human checkpoint confirms the watchdog PyPI package legitimacy.

---
*Phase: M14-long-running-tasks-watch-caps-01e*
*Completed: 2026-05-19*

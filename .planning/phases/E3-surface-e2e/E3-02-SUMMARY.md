---
phase: E3-surface-e2e
plan: 02
subsystem: testing
tags: [eval, subprocess, cli, stub-provider]

requires:
  - phase: E3-surface-e2e plan 01
    provides: TaskSpec.surface/target_file + _drive_task dispatch seam
provides:
  - _live_env helper (auth inherited, offline guards, no sitecustomize)
  - _drive_cli_do / _drive_cli_chat / _drive_cli_edit subprocess drivers
  - cli:* dispatch wired in _drive_task (serve still stubbed)
  - tests/eval/test_surface_drivers.py (stub-mode CLI driver tests)
affects: [E3-03 serve driver, E3-04 scenarios]

tech-stack:
  added: []
  patterns: [live-vs-stub env split (_live_env vs CliRunner.env), driver returns (final, crash_reason, capped)]

key-files:
  created:
    - tests/eval/test_surface_drivers.py
  modified:
    - voss/eval/runner.py

key-decisions:
  - "Drivers are async def wrapping sync subprocess.run — uniform await in dispatch"
  - "TimeoutExpired → ('', 'timeout', False) row, never an exception"
  - "Tests monkeypatch _live_env to CliRunner stub env (D-10); live code never injects sitecustomize (D-05)"

patterns-established:
  - "CLI surface driver: [sys.executable, -m, voss.cli, VERB, ..., --cwd, cwd, --plain], input piped, stderr[:200] on failure"

requirements-completed: [EVSRF-02]

duration: 15min
completed: 2026-06-10
---

# Phase E3 Plan 02: CLI Subprocess Drivers Summary

**cli:do/cli:chat/cli:edit drive real `python -m voss.cli` subprocesses with live-auth env (no stub injection); dispatch wired; stub-mode tests prove subprocess + EOF-exit + target_file paths offline**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `_live_env`: dict(os.environ) + offline/dev guards; auth keys NOT stripped; no sitecustomize (grep count 0)
- Three driver coroutines: do (input=""), chat (single piped line → EOFError clean exit), edit (requires target_file, clear crash_reason otherwise)
- Dispatch wired for the three cli surfaces; serve branch still not-implemented (E3-03); internal untouched
- 4 stub-mode tests green offline (StubProvider via CliRunner env monkeypatched into _live_env, tests only)

## Task Commits

1. **Task 1: _live_env + three CLI drivers** - `67eed55` (feat)
2. **Task 2: dispatch wiring + stub tests** - `4aff47f` (feat)

## Files Created/Modified
- `voss/eval/runner.py` - _live_env + 3 drivers + wired dispatch
- `tests/eval/test_surface_drivers.py` - 4 CLI stub tests

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Full eval suite: same 6 pre-existing E2 intended-RED failures (matrix task.tomls awaiting E2-05..08); 75 passed, no E3 regressions.

## User Setup Required
None.

## Next Phase Readiness
- _live_env + dispatch ready for E3-03 _drive_serve
- test_surface_drivers.py ready to receive serve/permission tests

---
*Phase: E3-surface-e2e*
*Completed: 2026-06-10*

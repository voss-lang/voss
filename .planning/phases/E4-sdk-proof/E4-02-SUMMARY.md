---
phase: E4-sdk-proof
plan: 02
subsystem: testing
tags: [eval, sdk, surface-dispatch, serve, fake-turn, public-api]

requires:
  - phase: E4-sdk-proof plan 01
    provides: "three buildable consumer subprograms + RED scaffold xfail flip-targets"
  - phase: E3-surface-e2e
    provides: "surface Literal (suite.py), _live_env, _drive_serve lifecycle pattern, FAKE_TURN seam"
provides:
  - "surface Literal extended additively: sdk:python|sdk:ts|sdk:go|sdk:rust (internal default + golden unchanged)"
  - "_drive_sdk_python — in-process driver via voss.harness public __all__ (PlainRenderer/make_toolset commented M7 private exceptions)"
  - "_drive_sdk_client — spawns voss serve (60s handshake, kill-in-finally) + the W0 consumer, parses its JSON stdout, returns final"
  - "sdk:* dispatch branches in _drive_task (after serve, before resume fallthrough)"
affects: [E4-sdk-proof plans 03-07, eval]

tech-stack:
  added: []
  patterns: ["runner-owned serve lifecycle for SDK clients: handshake → consumer env (VOSS_BASE_URL/TOKEN/CWD/PYTHON/PROMPT/MODE) → JSON last-line parse → stdin-EOF teardown"]

key-files:
  created: []
  modified:
    - voss/eval/suite.py
    - voss/eval/runner.py
    - tests/eval/test_sdk.py

key-decisions:
  - "Consumer command paths anchored to Path(__file__).parents[2] repo root, not process cwd — driver tests run from tmp fixture cwds"
  - "Hermetic consumer tests assert 'echo' in final (FAKE_TURN canned text) and share one _drive_consumer_hermetic helper"
  - "Serve-branch grep criterion from the plan was stale (expected E3-03 unexecuted); replaced with git-diff proof that _drive_serve is byte-untouched"

patterns-established:
  - "sdk:* driver returns plain final str; _drive_task wraps as (record, final, None, False) — no new JSONL fields, REQUIRED_FIELDS unchanged"

requirements-completed: [EVSDK-01, EVSDK-02]

duration: 25min
completed: 2026-06-12
---

# Phase E4 Plan 02: Surface Dispatch + SDK Drivers Summary

**sdk:python/ts/go/rust wired end-to-end: additive surface Literal, public-API in-process driver, and a runner-owned serve+consumer subprocess driver — all three W0 consumers complete a hermetic FAKE_TURN round-trip (echo final via real SSE)**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-12T15:50Z
- **Completed:** 2026-06-12T16:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `suite.py` Literal gained the four sdk:* values in place; sdk:bogus → ValidationError; golden still loads 6; full `tests/eval` suite green (113 passed, 1 xfailed, 2 skipped — zero regressions)
- `_drive_sdk_python` (EVSDK-02): run_turn via `from voss.harness import PermissionGate, run_turn` (public __all__); PlainRenderer + make_toolset imported as commented private M7 exceptions; config snapshot/restore in finally
- `_drive_sdk_client` (EVSDK-01): Popen serve → stderr-drain thread → 60s monotonic handshake parse → consumer spawn with the six-var env contract (VOSS_PYTHON pinned absolute for Go interpreterPath) → last-stdout-line JSON parse (TimeoutExpired/JSONDecodeError/IndexError → "") → stdin-EOF + wait(10) + kill teardown
- Hermetic FAKE_TURN driver tests for all THREE consumers pass (plan only required ts; go/rust also green) — each consumer attaches to the pre-spawned server, drains the persistent session queue, sees `final` + `session.idle`, emits the six-key JSON

## Task Commits

1. **Task 1: surface Literal + _drive_sdk_python** - `2d66871` (feat)
2. **Task 2: _drive_sdk_client + sdk:* dispatch** - `aea7fd4` (feat — auto-committed by the concurrent watcher as "feat(EVSDK-05): implement _drive_sdk_client for TS, Go, and Rust consumers"; diff verified = this task's runner.py/test_sdk.py changes, bundled with stale E3-04 `.voss/eval` artifacts)

## Files Created/Modified
- `voss/eval/suite.py` - surface Literal +4 values (only change)
- `voss/eval/runner.py` - `_drive_sdk_client` + `_drive_sdk_python` + two dispatch branches; serve/resume/internal branches byte-unchanged (git-diff verified)
- `tests/eval/test_sdk.py` - 5 xfails flipped to real tests (EVSDK-01..05); shared `_drive_consumer_hermetic` helper; slow+skipif guards

## Decisions Made
- Repo-root-anchored consumer paths (`Path(__file__).resolve().parents[2]`) instead of PATTERNS' cwd-relative paths — the driver is called with tmp fixture cwds.
- Single helper for the three hermetic consumer tests instead of three copies.

## Deviations from Plan

**1. [Rule 3 - Stale premise] E3-03 serve driver already executed**
- **Found during:** Task 2 (read_first)
- **Issue:** Plan asserts "_drive_serve does NOT exist" and gates on grep "surface 'serve' driver not implemented (E3-03)" — but E3-03/04 shipped `_drive_serve` (runner.py:346) on this checkout
- **Fix:** Wrote `_drive_sdk_client`'s own lifecycle as planned (mirroring `_drive_serve`'s proven shape); replaced the stale grep gate with git-diff proof the serve branch is untouched
- **Committed in:** aea7fd4

**2. [Rule 1 - Concurrent auto-commit] Task 2 absorbed by watcher**
- **Found during:** Task 2 commit
- **Issue:** Working tree was already committed as `aea7fd4` by the concurrent process before my commit ran ("nothing to commit")
- **Fix:** Verified `git show aea7fd4` carries exactly the Task 2 runner.py/test_sdk.py diff; recorded the hash
- **Committed in:** aea7fd4

**Total deviations:** 2 (1 stale-premise adjustment, 1 process artifact). **Impact:** none on scope; serve driver preserved byte-identical.

## Issues Encountered
None beyond deviations.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- W2 consumer-hardening plans (03/04/05) can flip remaining details per consumer; hermetic round-trips already proven here
- Remaining xfail: test_sdk_suite_loads (EVSDK-06, W3 plan 06); EVSDK-07/08 live-only skips

---
*Phase: E4-sdk-proof*
*Completed: 2026-06-12*

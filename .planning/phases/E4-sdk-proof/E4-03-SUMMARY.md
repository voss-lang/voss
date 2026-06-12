---
phase: E4-sdk-proof
plan: 03
subsystem: testing
tags: [eval, sdk, typescript, sse, consumer]

requires:
  - phase: E4-sdk-proof plan 02
    provides: "_drive_sdk_client driver + VOSS_* env contract the consumer reads"
  - phase: E4-sdk-proof plan 01
    provides: "W0 TS consumer skeleton + committed node_modules symlink resolution"
provides:
  - "Hardened TS consumer: env-driven permission choice (VOSS_PERMISSION_CHOICE, default a), resilient try/catch event loop, six-key JSON always emitted"
affects: [E4-sdk-proof plans 06-07]

tech-stack:
  added: []
  patterns: ["consumer always emits parseable JSON even on mid-turn error (runner gets a line, not a crash)"]

key-files:
  created: []
  modified:
    - tests/eval/sdk/consumers/ts/consumer.js

key-decisions:
  - "AbortError detection mirrors the SDK's own isAbortError (DOMException name check); other errors logged to stderr, JSON still emitted"

patterns-established: []

requirements-completed: [EVSDK-03]

duration: 6min
completed: 2026-06-12
---

# Phase E4 Plan 03: TS Consumer Hardening Summary

**TS consumer hardened: VOSS_PERMISSION_CHOICE-driven reply branch for the W4 Allow/Deny scenarios, lifecycle try/catch that always emits the six-key JSON, typed SSE union drain to session.idle — hermetic FAKE_TURN round-trip re-verified green**

## Performance

- **Duration:** ~6 min
- **Tasks:** 1
- **Files modified:** 1 (64 lines)

## Accomplishments
- `VOSS_PERMISSION_CHOICE` env read (default `"a"`) feeds `replyPermission` — plan 07 drives Deny through this same file with `=d`
- Lifecycle (createSession → postMessage → for-await subscribeToEvents) wrapped in try/catch: AbortError (from `ac.abort()` on session.idle) swallowed; any other error logged to stderr and the six-key JSON still emitted with whatever was captured
- All grep gates pass: subscribeToEvents/replyPermission present, zero VossLauncher / @vosslang/sdk/node, event.type discrimination (permission.updated/final/session.idle), no per-runtime scoring (no judge/jsonl)
- `node --check` clean; `test_drive_sdk_client_ts_stub` hermetic round-trip green after rewrite

## Task Commits

1. **Task 1: Harden TS consumer event loop + structured emission** - `67f783b` (feat)

## Files Created/Modified
- `tests/eval/sdk/consumers/ts/consumer.js` - hardened event loop, env-driven choice, resilient JSON emission

## Decisions Made
- Field accessors verified against sse.ts/rest.ts/permission.ts: `event.type`/`event.id`/`event.text`, `cost.total_usd` — already correct from W0; no changes needed there.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plans 04 (go) and 05 (rust) are parallel-safe siblings; plan 06 consolidates the end-to-end schema assertions
- TS consumer ready for the live Allow/Deny scenarios (plan 07)

---
*Phase: E4-sdk-proof*
*Completed: 2026-06-12*

---
phase: E3-surface-e2e
plan: 03
subsystem: testing
tags: [eval, sse, httpx, serve, permission-gate]

requires:
  - phase: E3-surface-e2e plan 01
    provides: TaskSpec.surface + dispatch seam
  - phase: E3-surface-e2e plan 02
    provides: _live_env + cli drivers + test_surface_drivers.py
provides:
  - _drive_serve (spawn voss serve, handshake parse, httpx REST+SSE turn, teardown)
  - _consume_sse module-level helper (SSE parse + in-loop permission reply, unit-testable)
  - serve dispatch wired; FAKE_TURN integration test; permission Allow/Deny parser tests; token-leak threat test
affects: [E3-04 scenarios + live permission checkpoint]

tech-stack:
  added: []
  patterns: [SSE-stream-open-before-message-POST, permission reply as in-loop await, stdin-EOF heartbeat teardown]

key-files:
  created: []
  modified:
    - voss/eval/runner.py
    - tests/eval/test_surface_drivers.py

key-decisions:
  - "_consume_sse takes message_body param (not callback) — POST happens inside the stream context; fake client records it in unit tests"
  - "Handshake loop mirrors RESEARCH Pattern 3: per-line 60s monotonic deadline + stdout-EOF → handshake-timeout row"
  - "Token captured in threat test via monkeypatched httpx.AsyncClient.post (driver never exposes it)"

patterns-established:
  - "Serve driver protocol: POST /session → GET /events (server.connected first) → POST /message → permission.updated reply {id,choice} → final → session.idle"

requirements-completed: [EVSRF-03, EVSRF-04]

duration: 20min
completed: 2026-06-10
---

# Phase E3 Plan 03: Serve HTTP/SSE Driver Summary

**_drive_serve spawns `voss serve`, parses the {v,port,token} handshake, and drives a full turn over raw httpx REST+SSE with stream-before-message ordering, in-loop permission replies, and guaranteed subprocess teardown — proven offline via FAKE_TURN integration + parser-level Allow/Deny tests**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `_consume_sse`: module-level importable helper; opens GET /events, POSTs the message INSIDE the stream context (gap events not lost — Pitfall 1), parses SSE frames (ping skip, event/data, `payload.get("type", event_type)`), replies to permission.updated as a normal await in the loop, captures final, breaks on session.idle
- `_drive_serve`: Popen `python -m voss.cli serve` with _live_env+VOSS_DEV, stderr drained in daemon thread (Pitfall 4), 60s monotonic handshake deadline rejecting token-less lines, POST /session → sid, exception → truncated crash_reason row, finally always closes stdin (EOF heartbeat) + wait(10)/kill
- serve dispatch wired in _drive_task (default Allow; E3-04 threads permission_choice)
- 4 new tests green offline: FAKE_TURN integration ("echo: hello" through real spawn/handshake/SSE/idle/teardown), permission Allow + Deny parser tests against _consume_sse with a fake client (deny-no-hang bounded by synthetic stream), token-leak threat test (crash_reason free of "Bearer" and the captured handshake token)

## Task Commits

1. **Task 1: _drive_serve + _consume_sse** - `49382b3` (feat)
2. **Task 2: serve dispatch + FAKE_TURN/permission/token tests** - `91a7886` (feat)

## Files Created/Modified
- `voss/eval/runner.py` - +threading import, _consume_sse, _drive_serve, wired serve branch
- `tests/eval/test_surface_drivers.py` - fake_turn_env fixture, _FakeClient/_FakeStream, 4 serve/permission tests; _consume_sse imported unconditionally at module top (no try/except, no xfail)

## Decisions Made
- message_body param instead of callback for _consume_sse — same unit-testability, simpler seam.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Full eval suite: same 6 pre-existing E2 intended-RED failures (matrix task.tomls/summary awaiting E2-05..08); 79 passed, no E3 regressions. FAKE_TURN does not exercise the permission gate (returns before _install_server_permissions) — live permission proof is the E3-04 D-11 human checkpoint, as planned.

## User Setup Required
None.

## Next Phase Readiness
- All four surface drivers implemented; E3-04 adds scenarios (tests/eval/surfaces/), threads permission_choice through TaskSpec, and runs the live human checkpoint.

---
*Phase: E3-surface-e2e*
*Completed: 2026-06-10*

---
phase: V25-server-native-swarm-runtime
plan: 02
subsystem: api
tags: [swarm, sse, pydantic, discriminated-union, asyncio, server]

# Dependency graph
requires:
  - phase: V17-server-backed-reframe
    provides: AgentEvent discriminated union + _Base event envelope + ServerSession dataclass
provides:
  - 5 swarm SSE event models (SwarmAssign/SwarmWorkerDone/SwarmGate/SwarmNeedsOperator/SwarmComplete) in the AgentEvent union
  - swarm event types surfaced in the EventEnvelope OpenAPI schema
  - ServerSession swarm fields — gate_event + swarm_id/swarm_task_id/swarm_owned_files/swarm_role/swarm_policy
affects: [V25-04, V25-05, V24-swarmReconcile]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Swarm event plane rides the existing SSE AgentEvent union (no new transport, D-03)"
    - "Additive dataclass fields with None/empty defaults preserve ungated session parity"

key-files:
  created:
    - tests/harness/test_swarm_events.py
  modified:
    - voss/harness/server/events.py
    - voss/harness/server/sessions.py

key-decisions:
  - "gate_event field holds the spawn-gate asyncio.Event but does NOT construct it — per Pitfall 2 it must be created inside an async route handler (V25-04)"
  - "swarm_policy typed Any to avoid importing cognition_schemas into sessions.py"
  - "Every swarm event carries swarm_id so V24 swarmReconcile consumes them directly (D-03)"

patterns-established:
  - "New SSE event types: subclass _Base with Literal type discriminator, append to AgentEvent Union members"

requirements-completed: [VSWARM-02, VSWARM-04]

# Metrics
duration: ~8 min
completed: 2026-06-17
---

# Phase V25 Plan 02: Swarm SSE Events + ServerSession Spawn-Gate Fields Summary

**5 swarm event models added to the AgentEvent discriminated union (round-tripping through AgentEventAdapter + surfaced in the OpenAPI envelope) and the gate_event + swarm_* substrate fields added to ServerSession — the data contracts V25-04/05 wire against.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-06-17
- **Tasks:** 2 (both TDD)
- **Files:** 1 created, 2 modified

## Accomplishments
- `SwarmAssign`, `SwarmWorkerDone`, `SwarmGate`, `SwarmNeedsOperator`, `SwarmComplete` subclass `_Base`, appended to the `AgentEvent` union; all round-trip via `AgentEventAdapter.validate_json` and appear as type literals in `EventEnvelope.model_json_schema()` (VSWARM-02).
- `ServerSession` gains `gate_event: asyncio.Event | None` plus `swarm_id`/`swarm_task_id`/`swarm_owned_files`/`swarm_role`/`swarm_policy`, all defaulted — `SessionManager.create`/`adopt` unchanged, ungated parity preserved (VSWARM-04 substrate).

## Task Commits

Not committed by me. Per the operator's git-safety rule (no git write actions without explicit confirmation), work is staged in the working tree only. `git diff --check` clean. Commit when ready.

## Files Created/Modified
- `voss/harness/server/events.py` — +5 swarm event models, +5 union members.
- `voss/harness/server/sessions.py` — +6 swarm fields on ServerSession dataclass.
- `tests/harness/test_swarm_events.py` — 4 tests (union round-trip, schema surface, field defaults, field settability).

## Decisions Made
- `gate_event` field added but Event not constructed here (Pitfall 2 — async-context construction deferred to V25-04 route handler).
- `swarm_policy: Any` to keep `sessions.py` free of a `cognition_schemas` import.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. Regression: `tests/harness/test_server_app.py` 9 passed (pre-existing Starlette/httpx deprecation warning unrelated).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V25-04 can construct `gate_event` in the `/swarm/{id}/task` async handler and emit the 5 swarm events over the SSE bus.
- V25-05 can attach a `PermissionsConfig` to `session.swarm_policy`.
- **Pending git action:** task + summary commits deferred to the operator per git-safety rule.

---
*Phase: V25-server-native-swarm-runtime*
*Completed: 2026-06-17*

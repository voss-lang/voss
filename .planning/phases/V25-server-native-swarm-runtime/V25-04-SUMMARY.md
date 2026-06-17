---
phase: V25-server-native-swarm-runtime
plan: 04
subsystem: api
tags: [fastapi, swarm, sse, asyncio, spawn-gate, routing, permissions, server]

# Dependency graph
requires:
  - phase: V25-01
    provides: SwarmStore (create/add_task/get/validate_no_overlap/register_agent/list_agents_by_swarm), Role, OwnershipOverlapError
  - phase: V25-02
    provides: ServerSession gate_event + swarm fields; 5 swarm SSE event models
provides:
  - /swarm REST surface (POST /swarm, GET /swarm/{id}, POST /swarm/{id}/task, POST /swarm/{id}/message) under bearer auth
  - app-scoped app.state.swarm_store (SwarmStore)
  - per-role session spawn with _resolve_provider + role.model (VSWARM-08)
  - spawn-gate await in _run_turn (gate_event.wait before first turn)
  - swarm.assign unblock (builder gate_event.set in-process) + fan-out emit to all swarm session queues
affects: [V25-05, V25-06, V24-swarmReconcile]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Swarm routes defined INSIDE create_app so _BearerASGI + CORS cover them (Pitfall 5)"
    - "Spawn-gate: await session.gate_event.wait() directly in the coroutine (not to_thread)"
    - "gate_event.set() in-process, independent of the bounded SSE queue (Pitfall 6)"
    - "Fan-out emit iterates list_agents_by_swarm → EventBusRenderer.emit per session queue (Pitfall 3)"

key-files:
  created:
    - tests/harness/server/test_swarm_routes.py
  modified:
    - voss/harness/server/app.py

key-decisions:
  - "asyncio.Event for builders created inside the async POST /swarm handler (Pitfall 2), not in SessionManager.create"
  - "POST /swarm/{id}/message is the generic operator/inter-agent channel: kind ∈ {assign,worker_done,gate,needs_operator,complete} maps to a swarm event; gate/needs_operator are scriptable now, their automatic emit points land in V25-05"
  - "_emit_swarm_event validates the swarm exists before fanning out (T-V25-04-04)"
  - "CreateSwarmBody gains optional roster (RoleSpec list) so per-role distinct models are HTTP-drivable; default_roster used when omitted"
  - "app.state.swarm_store read dynamically in routes so tests can redirect the event-log cwd to tmp_path"

patterns-established:
  - "New resource routes live in create_app alongside /session for middleware coverage"

requirements-completed: [VSWARM-03, VSWARM-04, VSWARM-06, VSWARM-08]

# Metrics
duration: ~22 min
completed: 2026-06-17
---

# Phase V25 Plan 04: /swarm Routes + Spawn-Gate + Per-Role Routing + Fan-Out SSE Summary

**The /swarm REST surface (auth-gated CRUD + task + message), an app-scoped SwarmStore, deterministic spawn-gating in _run_turn, per-role provider/model resolution at spawn, and swarm-event fan-out to all session queues — wiring the Wave-1 store + event models into the running server.**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-06-17
- **Tasks:** 2 (both TDD)
- **Files:** 1 created, 1 modified

## Accomplishments
- 4 `/swarm` routes inside `create_app` (so `_BearerASGI`+CORS cover them): POST /swarm (201, per-role spawn), GET /swarm/{id} (404 if missing), POST /swarm/{id}/task (409 on `OwnershipOverlapError` — VSWARM-06 route layer), POST /swarm/{id}/message. All 401 without a token (VSWARM-03).
- Per-role spawn (VSWARM-08): one `ServerSession` per roster role via `_resolve_provider(role.auth_pref)` + `model=role.model`; builders get an `asyncio.Event` spawn-gate; each registered in the swarm index.
- Spawn-gate (VSWARM-04): `_run_turn` awaits `session.gate_event.wait()` before the first turn; a gated builder runs ZERO turns until `swarm.assign` then EXACTLY one (test asserts with no timing tolerance).
- `swarm.assign` over POST /swarm/{id}/message sets the builder's `gate_event` in-process (Pitfall 6) and fans out the event to every registered swarm session's queue (Pitfall 3); all 5 swarm SSE types delivered with no nudge file / stdin injection (VSWARM-02 transport).

## Task Commits

Not committed by me. Per the operator's git-safety rule (no git write actions without explicit confirmation), work is staged in the working tree only. `git diff --check` clean. Commit when ready.

## Files Created/Modified
- `voss/harness/server/app.py` — imports (SwarmStore/Role/OwnershipOverlapError); RoleSpec/CreateSwarmBody/CreateTaskBody/SwarmMessageBody request models; `app.state.swarm_store`; gate await in `_run_turn`; 4 /swarm routes + `_emit_swarm_event` fan-out helper.
- `tests/harness/server/test_swarm_routes.py` — 5 tests (auth, overlap, per-role routing, spawn-gate, fan-out SSE).

## Decisions Made
- Builder `asyncio.Event` created in the async route (Pitfall 2).
- Message route doubles as the scriptable swarm-event channel; gate/needs_operator automatic triggers deferred to V25-05.
- `CreateSwarmBody.roster` optional override for HTTP-driven per-role models.

## Deviations from Plan

None - plan executed exactly as written.

(Test-authoring fix: the spawn-gate test initially set the counting `run_turn` before `_build_app`, which re-patched it to the default fake → 0 counted turns. Reordered to patch after build. Test-only, no production change.)

## Issues Encountered
None. Regression: `test_server_app.py` + V25-01/02 swarm tests + new routes = 26 passed (only pre-existing Starlette/httpx deprecation warning).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V25-05 (the second app.py plan, serialized after this) wires ownership-policy injection (`build_ownership_policy` → `session.swarm_policy` → `PermissionGate`), scoped recall, and the automatic gate/needs_operator emit points at the denial site.
- **Pending git action:** task + summary commits deferred to the operator per git-safety rule.

---
*Phase: V25-server-native-swarm-runtime*
*Completed: 2026-06-17*

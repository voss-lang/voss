---
phase: V25-server-native-swarm-runtime
plan: 04
type: execute
wave: 2
depends_on: [V25-01, V25-02]
files_modified:
  - voss/harness/server/app.py
  - tests/harness/server/test_swarm_routes.py
autonomous: true
requirements: [VSWARM-03, VSWARM-04, VSWARM-06, VSWARM-08]
must_haves:
  truths:
    - "POST /swarm, GET /swarm/{id}, POST /swarm/{id}/task, POST /swarm/{id}/message work with a valid token and return 401 without one"
    - "POST /swarm/{id}/task returns a 4xx overlap error for two concurrent tasks owning the same file; depends_on-ordered succeeds"
    - "A builder created before its assignment runs zero turns until swarm.assign arrives, then exactly one — no timing tolerance"
    - "A 3-role swarm spawns sessions whose resolved models match the per-role roster spec"
    - "All 5 swarm SSE event types are delivered to a subscriber in a scripted run with no nudge file or stdin injection"
  artifacts:
    - path: "voss/harness/server/app.py"
      provides: "/swarm route table, SwarmStore in app.state, spawn-gate await in _run_turn, per-role provider resolution on spawn, fan-out emit"
      contains: "/swarm"
  key_links:
    - from: "app.state.swarm_store"
      to: "SwarmStore (V25-01)"
      via: "create_app constructs an app-scoped SwarmStore"
      pattern: "swarm_store"
    - from: "_run_turn"
      to: "session.gate_event.wait()"
      via: "builder awaits assign before first turn"
      pattern: "gate_event"
    - from: "POST /swarm/{id}/message (coordinator)"
      to: "builder gate_event.set()"
      via: "swarm.assign unblocks the waiting builder + fans out to its queue"
      pattern: "gate_event.set"
---

<objective>
Add the `/swarm` REST surface to `app.py`, construct an app-scoped `SwarmStore` in `create_app`, wire the spawn-gate await into `_run_turn`, resolve per-role providers/models at spawn, and fan swarm events out to all relevant session queues. This is the FIRST of two `app.py`-touching plans (V25-05 is the second; they are serialized W2→W3 to respect single-file ownership of `app.py`).

Purpose: Delivers the headless HTTP drive surface (VSWARM-03), the deterministic spawn-gate (VSWARM-04), the route-level overlap rejection (VSWARM-06), per-role model routing (VSWARM-08), and the SSE event delivery (VSWARM-02 transport) — all by wiring the Wave-1 SwarmStore + event models into the existing server.

Output: `/swarm` routes + spawn-gate + routing + fan-out emit in `voss/harness/server/app.py`; `tests/harness/server/test_swarm_routes.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md
@.planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md
@.planning/phases/V25-server-native-swarm-runtime/V25-VALIDATION.md

<interfaces>
<!-- From V25-01 (depends_on) -->
SwarmStore (voss/harness/swarm_store.py): create(goal, cwd), add_task(...), get(swarm_id),
validate_no_overlap(new_task, active_tasks) raising OwnershipOverlapError, register_agent(...),
list_agents_by_swarm(swarm_id), default_roster(builders), replay(swarm_id). App-scoped — NOT a module global.

<!-- From V25-02 (depends_on) -->
ServerSession (server/sessions.py): gate_event: asyncio.Event|None, swarm_id, swarm_task_id,
swarm_owned_files, swarm_role, swarm_policy. Swarm event models in server/events.py:
SwarmAssign/SwarmWorkerDone/SwarmGate/SwarmNeedsOperator/SwarmComplete (all carry swarm_id).

<!-- Existing app.py anchors (verified) -->
create_app(token) (app.py:309-562): builds SessionManager mgr, app.state.token/sessions, adds
_BearerASGI then CORS, defines all /session routes INSIDE the closure (so _BearerASGI + CORS cover them).
_resolve_provider(preference) (app.py:85-112): returns (Resolution, provider); honors VOSS_SERVE_FAKE_TURN.
_run_turn(session, text, mode) (app.py:179-272): builds EventBusRenderer, the FAKE_TURN seam at :185-197,
gate construction at :202-207, recall injection at :221-232, the run_turn(...) call at :234-248.
post_message route (app.py:445-454): `s.task = asyncio.create_task(_run_turn(s, text, body.mode))`.
EventBusRenderer.emit(event) is the server-only emit helper (renderer.py).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: /swarm routes + app-scoped SwarmStore + per-role routing + overlap 4xx</name>
  <read_first>
    - voss/harness/server/app.py (create_app :309-562, request models :280-301, session route patterns :356-477, _resolve_provider :85-112)
    - voss/harness/swarm_store.py (SwarmStore API from V25-01)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 2 route insertion, VSWARM-08 per-role routing via _resolve_provider, Pitfall 5 routes MUST be inside create_app for _BearerASGI coverage)
    - tests/harness/server/test_swarm_routes.py is NEW — mirror the TestClient + monkeypatch fixture from tests/harness/test_server_app.py
  </read_first>
  <behavior>
    - Test: POST /swarm (valid token) returns 201 + id; GET /swarm/{id} returns state; POST /swarm/{id}/task adds a task; POST /swarm/{id}/message accepts — and EVERY one returns 401 without a token — `test_swarm_auth`.
    - Test: POST /swarm/{id}/task with owned_files overlapping an active task returns 4xx with an overlap error; the same two tasks ordered by depends_on both succeed — `test_overlap_rejected`.
    - Test: creating a swarm whose roster has 3 distinct role models spawns 3 sessions whose `.model` matches the roster spec — `test_per_role_model_routing`.
  </behavior>
  <action>
    Inside `create_app` (app.py:309-562, alongside the /session routes so _BearerASGI + CORS cover them — Pitfall 5), construct `app.state.swarm_store = SwarmStore(...)` (app-scoped, NOT module-global — RESEARCH Anti-Pattern). Add pydantic request bodies near app.py:280-301: `CreateSwarmBody{goal, cwd}`, `CreateTaskBody{goal, owned_files, depends_on}`, `SwarmMessageBody{from_session, text, kind}`. Add routes per RESEARCH Pattern 2: `POST /swarm` (status 201, create+seed goal, returns `{v:1,id}`), `GET /swarm/{id}` (404 if missing else `{v:1,swarm:...}`), `POST /swarm/{id}/task` (call `SwarmStore.validate_no_overlap`; on `OwnershipOverlapError` raise `HTTPException(409,...)` — the 4xx for VSWARM-06), `POST /swarm/{id}/message` (inter-agent/operator message). For per-role spawn (VSWARM-08), resolve each role via `_resolve_provider(role.auth_pref)` and create its session with `model=role.model` through `SessionManager.create` — exactly mirroring the existing `/session` spawn path (app.py:366-402). Do NOT add a new router/sub-app (Pitfall 5). Reuse the FAKE_TURN seam for tests.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/server/test_swarm_routes.py::test_swarm_auth tests/harness/server/test_swarm_routes.py::test_overlap_rejected tests/harness/server/test_swarm_routes.py::test_per_role_model_routing -x</automated>
  </verify>
  <acceptance_criteria>
    All four /swarm routes work with a valid token and 401 without one (VSWARM-03); overlapping-ownership task creation returns 4xx, depends_on-ordered succeeds (VSWARM-06 route layer); a 3-role swarm spawns sessions with the spec'd models (VSWARM-08). All three pytest node ids PASS.
  </acceptance_criteria>
  <done>/swarm routes live under bearer auth; overlap returns 4xx; per-role routing resolves distinct models.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Spawn-gate wiring in _run_turn + swarm.assign unblock + fan-out emit</name>
  <read_first>
    - voss/harness/server/app.py (_run_turn :179-272 — esp. the renderer build :181-182, FAKE_TURN seam :185-197, before the first run_turn at :234; post_message :445-454)
    - voss/harness/server/sessions.py (gate_event field from V25-02)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 3 spawn-gate: await gate_event.wait() before first turn, coordinator message sets it; Pitfalls 2/3/6: create Event in async context, fan-out to ALL session queues not just coordinator, gate.set() in-process independent of queue state)
  </read_first>
  <behavior>
    - Test: a builder session whose `gate_event` is set (unsignaled) runs ZERO turns; after the coordinator's swarm.assign sets the event, it runs EXACTLY one turn — asserted by counting run_turn invocations with no sleep/timing tolerance — `test_spawn_gate_zero_turns_before_assign`.
    - Test: a subscriber to the swarm receives all 5 swarm SSE event types in a scripted run, and the code path uses NO nudge file / NO stdin injection (assert by absence — the emit goes through EventBusRenderer.emit only) — `test_swarm_sse_event_types`.
  </behavior>
  <action>
    In `_run_turn` (app.py:179-272), immediately after the renderer is built (:182) and BEFORE the first turn work, add: `if session.gate_event is not None: await session.gate_event.wait()` (RESEARCH Pattern 3 — await directly in the coroutine; do NOT use asyncio.to_thread per Pitfall). The asyncio.Event is created inside the async route that spawns the builder (Pitfall 2), not in SessionManager.create. In the `POST /swarm/{id}/message` route (or a dedicated assign helper), when the coordinator emits an assign for a task: call the matching builder session's `gate_event.set()` IN-PROCESS (independent of queue state — Pitfall 6) and add a `SwarmStore.emit_swarm_event(swarm_id, event)` that iterates the swarm's registered sessions and calls `EventBusRenderer.emit(ev)` on EACH session's queue (Pitfall 3 — fan-out to all, not just the coordinator). Emit the 5 swarm event types at their lifecycle points (assign on task assignment, worker_done on builder completion, complete on swarm completion; gate/needs_operator emit points are completed in V25-05). No nudge files, no stdin injection anywhere (SPEC VSWARM-02 acceptance).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/server/test_swarm_routes.py::test_spawn_gate_zero_turns_before_assign tests/harness/server/test_swarm_routes.py::test_swarm_sse_event_types -x</automated>
  </verify>
  <acceptance_criteria>
    A gated builder runs zero turns until swarm.assign then exactly one, with no timing tolerance in the test (VSWARM-04); all 5 swarm event types reach a subscriber via the fan-out emit with zero nudge/stdin usage (VSWARM-02). Both pytest node ids PASS.
  </acceptance_criteria>
  <done>Spawn-gate awaits assign deterministically; swarm events fan out to all session queues; gate.set() is in-process.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP client → /swarm routes | untrusted request bodies (goal, owned_files, depends_on) cross here |
| coordinator session → builder unblock | one session triggers another's first turn |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V25-04-01 | Spoofing | unauthenticated /swarm call | mitigate | Routes defined INSIDE create_app so _BearerASGI (app.py:325) covers them; test_swarm_auth pins 401-without-token (Pitfall 5) |
| T-V25-04-02 | Tampering | malformed request body | mitigate | Pydantic v2 request models (CreateSwarmBody/CreateTaskBody/SwarmMessageBody) validate at the route boundary (V5 input validation) |
| T-V25-04-03 | Denial of service | dropped swarm.assign leaves builder stuck in waiting | mitigate | gate_event.set() is in-process and independent of the bounded queue (Pitfall 6); not routed exclusively through the maxsize-256 queue |
| T-V25-04-04 | Spoofing | cross-swarm event emit | mitigate | emit_swarm_event validates the swarm exists and fans out only to that swarm's registered sessions (RESEARCH Security Domain) |
| T-V25-04-SC | Tampering | npm/pip installs | accept | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/server/test_swarm_routes.py -x` green
- Existing session routes unaffected: `.venv/bin/python -m pytest tests/harness/test_server_app.py -x`
- `git diff --check` clean
</verification>

<success_criteria>
- All four /swarm routes work with a token, 401 without (VSWARM-03)
- Overlap task creation returns 4xx; depends_on-ordered succeeds (VSWARM-06 route layer)
- Gated builder runs zero turns until assign then exactly one (VSWARM-04)
- 3-role swarm spawns spec'd models (VSWARM-08)
- 5 swarm event types delivered to subscriber, no nudge/stdin (VSWARM-02)
</success_criteria>

<output>
Create `.planning/phases/V25-server-native-swarm-runtime/V25-04-SUMMARY.md` when done
</output>

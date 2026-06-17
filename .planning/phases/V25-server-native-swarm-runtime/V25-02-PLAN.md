---
phase: V25-server-native-swarm-runtime
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/server/events.py
  - voss/harness/server/sessions.py
  - tests/harness/test_swarm_events.py
autonomous: true
requirements: [VSWARM-02, VSWARM-04]
must_haves:
  truths:
    - "The 5 swarm event types (swarm.assign, swarm.worker_done, swarm.gate, swarm.needs_operator, swarm.complete) serialize and parse through the existing AgentEvent union"
    - "A ServerSession carries a gate_event plus swarm_id/swarm_task_id/swarm_owned_files/swarm_role/swarm_policy fields; an ungated session (gate_event=None) behaves exactly as before"
  artifacts:
    - path: "voss/harness/server/events.py"
      provides: "SwarmAssign/SwarmWorkerDone/SwarmGate/SwarmNeedsOperator/SwarmComplete models + AgentEvent union members"
      contains: "swarm.assign"
    - path: "voss/harness/server/sessions.py"
      provides: "ServerSession swarm fields + gate_event"
      contains: "gate_event"
  key_links:
    - from: "voss/harness/server/events.py"
      to: "AgentEvent discriminated union"
      via: "5 new members appended with Field(discriminator='type')"
      pattern: "SwarmAssign|swarm\\.assign"
---

<objective>
Add the 5 swarm SSE event models to `server/events.py` (extending the existing `AgentEvent` discriminated union) and the swarm-related fields to the `ServerSession` dataclass in `server/sessions.py` — including the `gate_event: asyncio.Event | None` spawn-gate field. These are the two pure data-shape changes that V25-04 (routes/spawn-gate/routing) and V25-05 (ownership/recall/escalation) wire against; isolating them in Wave 1 means the `app.py`-touching plans receive ready contracts.

Purpose: Swarm coordination must flow over the EXISTING SSE bus (VSWARM-02) with no new transport, and the spawn-gate (VSWARM-04) needs a per-session hold flag. Both are additive: ungated sessions (gate_event=None) are byte-identical to today.

Output: 5 new event models + union members in `server/events.py`; swarm fields + gate_event on `ServerSession`; `tests/harness/test_swarm_events.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md
@.planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md

<interfaces>
<!-- Verified against source. -->

server/events.py: `_Base(BaseModel)` (events.py:24-28) sets `model_config = ConfigDict(extra="ignore")`
and `v: int = PROTOCOL_VERSION`. Every event subclasses `_Base` with a `type: Literal[...]` discriminator.
`AgentEvent` (events.py:191-216) is `Annotated[Union[...21 types...], Field(discriminator="type")]`.
`AgentEventAdapter = TypeAdapter(AgentEvent)` (events.py:218). `EventEnvelope.event: AgentEvent` (events.py:228)
forces the union into OpenAPI components.

server/sessions.py: `ServerSession` is a `@dataclass` (sessions.py:27-47) with fields id, cwd, model,
provider, record, history, queue (asyncio.Queue maxsize 256), task, pending (dict[str,Future]),
title, prior_context. `busy` property at :45-47. `SessionManager.create` at :56-75. Add new fields
with defaults so `create`/`adopt` keep working unchanged.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add 5 swarm event models + extend AgentEvent union</name>
  <read_first>
    - voss/harness/server/events.py (full file: _Base at :24-28, the core-13 + Voss-native models, AgentEvent union at :191-216, AgentEventAdapter at :218, EventEnvelope at :221-228)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 1: exact field shapes for SwarmAssign/SwarmWorkerDone/SwarmGate/SwarmNeedsOperator/SwarmComplete)
    - .planning/phases/V25-server-native-swarm-runtime/V25-CONTEXT.md (D-03: events must satisfy V24 swarmReconcile — carry swarm_id; honest-signal)
  </read_first>
  <behavior>
    - Test: each of `swarm.assign`, `swarm.worker_done`, `swarm.gate`, `swarm.needs_operator`, `swarm.complete` round-trips through `AgentEventAdapter.validate_json(model.model_dump_json())` to the correct subclass — `test_swarm_event_union_roundtrip`.
    - Test: `EventEnvelope.model_json_schema()` includes all 5 swarm event type literals (OpenAPI surface) — `test_swarm_events_in_envelope_schema`.
  </behavior>
  <action>
    In `server/events.py` add 5 models subclassing `_Base`, fields per RESEARCH Pattern 1: `SwarmAssign{type:"swarm.assign", swarm_id, task_id, session_id, owned_files:list[str], role}`; `SwarmWorkerDone{type:"swarm.worker_done", swarm_id, task_id, session_id, summary:str|None=None}`; `SwarmGate{type:"swarm.gate", swarm_id, task_id, gate_type, detail}`; `SwarmNeedsOperator{type:"swarm.needs_operator", swarm_id, task_id, session_id, tool_name, path:str|None=None}`; `SwarmComplete{type:"swarm.complete", swarm_id, task_count:int, summary:str|None=None}`. Append all 5 to the `AgentEvent` Union members list (keep `Field(discriminator="type")`). Each carries `swarm_id` so V24 `swarmReconcile` can consume them (D-03). Do not alter any existing event model.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_swarm_events.py::test_swarm_event_union_roundtrip tests/harness/test_swarm_events.py::test_swarm_events_in_envelope_schema -x</automated>
  </verify>
  <acceptance_criteria>
    All 5 swarm event types parse via `AgentEventAdapter` to their correct subclass and appear in the `EventEnvelope` JSON schema (VSWARM-02 data shapes). Existing event round-trips unaffected. Both pytest node ids PASS.
  </acceptance_criteria>
  <done>5 swarm event models exist in the AgentEvent union and round-trip correctly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add swarm fields + gate_event to ServerSession</name>
  <read_first>
    - voss/harness/server/sessions.py (full file: ServerSession dataclass :27-47, SessionManager.create :56-75, adopt :77-97)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (Pattern 3 spawn-gate mechanics + Pitfall 2: asyncio.Event must be created inside an async context, not at SessionManager.create time)
  </read_first>
  <behavior>
    - Test: a default-constructed ServerSession (via SessionManager.create) has `gate_event is None`, `swarm_id is None`, and empty `swarm_owned_files` — ungated parity — `test_session_swarm_fields_default_none`.
    - Test: setting `session.gate_event = asyncio.Event()` and `swarm_owned_files=["a.py"]` persists on the dataclass and `busy` still reflects task state — `test_session_swarm_fields_settable`.
  </behavior>
  <action>
    In `server/sessions.py` extend the `ServerSession` dataclass with: `gate_event: "asyncio.Event | None" = None` (None = ungated/normal; set = waiting builder per RESEARCH Pattern 3), `swarm_id: str | None = None`, `swarm_task_id: str | None = None`, `swarm_owned_files: list[str] = field(default_factory=list)`, `swarm_role: str | None = None`, and `swarm_policy: Any = None` (a PermissionsConfig attached by V25-05; typed Any here to avoid importing cognition_schemas into sessions.py). All have defaults so `SessionManager.create`/`adopt` (sessions.py:56-97) need NO signature change. Do NOT create the asyncio.Event here — per Pitfall 2 it must be constructed inside an async route handler; this task only adds the field.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_swarm_events.py::test_session_swarm_fields_default_none tests/harness/test_swarm_events.py::test_session_swarm_fields_settable -x</automated>
  </verify>
  <acceptance_criteria>
    ServerSession carries gate_event + swarm_id/swarm_task_id/swarm_owned_files/swarm_role/swarm_policy; a normally-created session has gate_event=None and behaves exactly as before (VSWARM-04 field substrate). Both pytest node ids PASS.
  </acceptance_criteria>
  <done>ServerSession has the swarm fields with safe defaults; create/adopt unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SSE wire → client | swarm event JSON is delivered to subscribers; shape must be discriminator-safe |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V25-02-01 | Spoofing | cross-swarm event injection | mitigate | Every swarm event model carries `swarm_id`; emitting routes (V25-04/05) validate the swarm exists before emit (RESEARCH Security Domain) |
| T-V25-02-02 | Tampering | malformed event breaks the discriminated union parse | mitigate | All 5 subclass `_Base` with a Literal `type`; `AgentEventAdapter` rejects unknown shapes; round-trip test pins this |
| T-V25-02-03 | Information disclosure | swarm fields leak into non-swarm sessions | accept | Fields default to None/empty; ungated sessions serialize identically — no new exposure |
| T-V25-02-SC | Tampering | npm/pip installs | accept | No new packages (RESEARCH audit empty) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_swarm_events.py -x` green
- Existing event tests still pass: `.venv/bin/python -m pytest tests/harness/test_server_app.py -x`
- `git diff --check` clean
</verification>

<success_criteria>
- 5 swarm event types in the AgentEvent union, round-trip + in OpenAPI envelope (VSWARM-02)
- ServerSession carries gate_event + swarm fields; ungated parity preserved (VSWARM-04 substrate)
</success_criteria>

<output>
Create `.planning/phases/V25-server-native-swarm-runtime/V25-02-SUMMARY.md` when done
</output>

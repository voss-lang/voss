---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 05
type: execute
wave: 4
depends_on: [V17-01]
blocked_on: V15
files_modified:
  - voss/harness/server/events.py
  - voss/harness/server/bus.py
  - voss/harness/server/app.py
  - contracts/openapi.json
  - contracts/events.schema.json
  - sdk/go/types.gen.go
  - sdk/typescript/src/generated/types.ts
  - crates/voss-sdk/src/types/events.rs
autonomous: true
requirements: [VBUS-04, VBUS-05]

must_haves:
  truths:
    - "A new additive bus.message event type joins the AgentEvent union; all pre-existing event types stay byte-identical in the schema"
    - "POST /bus/send appends to a durable journal and broadcasts on the dedicated /bus/events SSE stream"
    - "GET /bus/inbox returns messages mentioning the caller since their cursor, then advances the cursor"
    - "bus messages survive server restart: pre-restart unread messages are still returned by inbox"
    - "all /bus/* routes are bearer-authed via the existing _BearerASGI (no unauthenticated route)"
  artifacts:
    - path: "voss/harness/server/bus.py"
      provides: "bus_router + BusState subscriber set + journal/cursors + send/inbox/events handlers"
      contains: "EventSourceResponse"
    - path: "voss/harness/server/events.py"
      provides: "BusMessage class added to the AgentEvent union"
      contains: "bus.message"
    - path: "contracts/events.schema.json"
      provides: "regenerated schema including bus.message, existing types byte-identical"
      contains: "bus.message"
  key_links:
    - from: "POST /bus/send"
      to: ".voss/bus/messages.jsonl + app.state.bus.subscribers"
      via: "journal append then publish to subscriber queues"
      pattern: "messages.jsonl"
    - from: "voss/harness/server/app.py create_app"
      to: "bus_router + BusState"
      via: "app.include_router + app.state.bus"
      pattern: "include_router"
---

<objective>
**V15-GATED — execute only after V15 ships the always-on/sidecar server.** Server-side of the bus: add the additive `bus.message` event type to the union, build the `/bus/*` route module (dedicated SSE broadcast stream, `POST /bus/send`, `GET /bus/inbox`) with a durable journal at `.voss/bus/messages.jsonl` and server-managed `cursors.json`, and regenerate all contract + SDK artifacts. The server is the sole journal writer (D-10).

Purpose: VBUS-05 (event type + durable journal) + the server half of VBUS-04 (the client verbs are V17-06).
Output: `events.py` modified, new `bus.py`, `app.py` registers the router, regenerated contracts + 3 SDKs.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md
@.planning/PROTOCOL.md

<interfaces>
<!-- Analog code (extracted in PATTERNS.md / RESEARCH.md) -->
voss/harness/server/events.py: _Base(BaseModel, v=PROTOCOL_VERSION); AgentEvent = Annotated[Union[...20 types...], Field(discriminator="type")] (lines ~191-218)
voss/harness/server/app.py: _BearerASGI app-wide middleware (lines ~51-76); create_app() (lines ~266-278); SSE handler (lines ~390-419, per-subscriber queue.get loop); POST body pattern (lines ~232-250)
voss/harness/lifecycle.py: atomic os.replace write-temp-rename (lines ~155-160)
contract regen sequence: scripts/export_contract.py -> (cd sdk/go && go generate ./...) -> (cd sdk/typescript && npm run codegen) -> scripts/generate_sdk_events.py
drift gates: tests/harness/server/test_contract_drift.py ; sdk/go/internal/drift/drift_test.go

<!-- New shapes this plan creates -->
BusMessage(_Base): type: Literal["bus.message"]; id: str (ULID); sender: str; body: str; mentions: list[str]=[]; labels: list[str]=[]; ts: float
BusSendBody(BaseModel): body: str; mentions: list[str]=[]; labels: list[str]=[]; sender: str=""
POST /bus/send -> {"v":1,"id": <ulid>} ; GET /bus/inbox?agent=<id> -> {"v":1,"messages":[...]} ; GET /bus/events -> SSE
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add bus.message event type + regenerate contracts/SDKs</name>
  <files>voss/harness/server/events.py, contracts/openapi.json, contracts/events.schema.json, sdk/go/types.gen.go, sdk/typescript/src/generated/types.ts, crates/voss-sdk/src/types/events.rs</files>
  <behavior>
    - AgentEventAdapter can validate/parse a {"type":"bus.message", ...} payload
    - contracts/events.schema.json contains "bus.message" and the new fields
    - every PRE-EXISTING event type in events.schema.json is byte-identical to before (additive-only)
    - test_contract_drift.py passes after regen
  </behavior>
  <read_first>
    - voss/harness/server/events.py (lines ~151-218 — Voss-native additive section + union)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 7 event addition + SDK regen mechanics; Pitfall 4 forgetting SDK regens)
    - .planning/PROTOCOL.md (§6 event taxonomy — migration note requirement)
    - tests/harness/server/test_contract_drift.py (the drift gate that enforces regen)
  </read_first>
  <action>Add `class BusMessage(_Base)` in the `# --- Voss-native (additive) ---` section of `voss/harness/server/events.py` with fields: `type: Literal["bus.message"] = "bus.message"`, `id: str`, `sender: str`, `body: str`, `mentions: list[str] = Field(default_factory=list)`, `labels: list[str] = Field(default_factory=list)`, `ts: float`. Append `BusMessage` to the `AgentEvent` Union (before `Field(discriminator="type")`) — additive only, do not reorder existing entries (byte-identical requirement). Add a migration note to PROTOCOL.md §6 documenting the new `bus.message` type and its `v` version. Then run the full regen chain in order: `.venv/bin/python scripts/export_contract.py`; `cd sdk/go && go generate ./... && cd -`; `cd sdk/typescript && npm run codegen && cd -`; `.venv/bin/python scripts/generate_sdk_events.py`. Commit all regenerated artifacts (contracts/openapi.json, contracts/events.schema.json, sdk/go/types.gen.go, sdk/typescript/src/generated/types.ts, crates/voss-sdk/src/types/events.rs). If go/cargo codegen tooling is unavailable in the env (RESEARCH A2/A3 assumptions), record the failure in the summary and regenerate via the documented fallback rather than hand-editing generated files.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/server/test_contract_drift.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - test_contract_drift.py passes (Python contract files in sync with the live Pydantic union)
    - `grep -c 'bus.message' contracts/events.schema.json` >= 1
    - `cd sdk/go && go test ./internal/drift/...` passes (Go types regenerated) OR documented-unavailable in summary
    - All pre-existing event type entries in events.schema.json are unchanged (diff shows only additions)
    - PROTOCOL.md §6 contains a migration note naming bus.message
  </acceptance_criteria>
  <done>bus.message added additively; all contract + SDK artifacts regenerated and committed; drift gate GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: bus.py route module — SSE broadcast + send + inbox + journal</name>
  <files>voss/harness/server/bus.py, voss/harness/server/app.py</files>
  <behavior>
    - POST /bus/send appends a ULID message to .voss/bus/messages.jsonl and publishes to all /bus/events subscribers
    - GET /bus/events delivers each published bus.message to every connected subscriber (fan-out)
    - GET /bus/inbox?agent=A returns messages mentioning A since A's cursor, then advances cursors.json atomically
    - second GET /bus/inbox?agent=A returns no messages (cursor advanced)
    - after process restart (re-create app), inbox still returns the pre-restart unread message (durable journal + cursors)
    - all /bus/* requests without a valid Bearer token get 401 (via _BearerASGI)
  </behavior>
  <read_first>
    - voss/harness/server/app.py (lines ~51-76 _BearerASGI; ~266-278 create_app + middleware; ~390-419 SSE generator; ~232-250 POST body)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 2 SSE fan-out + asyncio.Lock note A1; Pattern 5 cursors.json; Pattern 8 ULID; bus journal append; read_inbox_since)
    - voss/harness/lifecycle.py (lines ~155-160 atomic os.replace pattern)
    - tests/harness/bus/test_bus_wait.py + test_bus_inbox.py + test_bus_durability.py (RED/xfail tests to turn XPASS)
  </read_first>
  <action>Create `voss/harness/server/bus.py` with: a `BusState` dataclass holding `subscribers: set[asyncio.Queue]` and a `publish(event)` that `put_nowait` to each (drop on QueueFull, do not block — RESEARCH Pattern 2); wrap subscriber set add/discard with an `asyncio.Lock` if needed (RESEARCH A1). Inline stdlib `ulid()` (RESEARCH Pattern 8 — no new deps). A `bus_router = APIRouter(prefix="/bus")`. `POST /bus/send` with `BusSendBody` -> mint ulid, build a `BusMessage`, append to `.voss/bus/messages.jsonl` (server sole writer, D-10), `app.state.bus.publish(msg)`, return `{"v":1,"id":id}`. `GET /bus/events` -> per-subscriber `asyncio.Queue(maxsize=100)`, add to subscribers, `EventSourceResponse` yielding `server.connected` then looping `q.get()` -> ServerSentEvent(event=ev.type, data=ev.model_dump_json()); `finally: subscribers.discard(q)` (no session-task cancel block). `GET /bus/inbox?agent=<id>` -> read messages.jsonl since the agent's cursor (RESEARCH read_inbox_since), filter to messages mentioning the agent, advance cursors.json via atomic os.replace (RESEARCH Pattern 5), return `{"v":1,"messages":[...]}`. In `voss/harness/server/app.py create_app()`, after `app.add_middleware(_BearerASGI, ...)`, add `from .bus import bus_router, BusState; app.state.bus = BusState(); app.include_router(bus_router)`. Do NOT inject bus messages into per-session queues (D-09 anti-pattern). The `.voss/bus/` dir is durable-side (NOT .voss-cache).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/bus/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/bus/ all pass (xfail markers now XPASS): wait-unblocks-within-2s, timeout exit, inbox cursor once-then-empty, durability across restart
    - `grep -c 'messages.jsonl' voss/harness/server/bus.py` >= 1 and journal path is under `.voss/bus/` (not .voss-cache)
    - `grep -c 'include_router' voss/harness/server/app.py` increased by 1 (bus_router registered)
    - A request to /bus/inbox without Bearer returns 401 (asserted via the app fixture in a test)
    - bus.py does NOT reference per-session `s.queue` (D-09) — source assertion in summary
  </acceptance_criteria>
  <done>Bus server live: fan-out SSE, durable journal, atomic cursors, bearer-authed, restart-durable; bus tests XPASS.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI client -> /bus/* HTTP | Loopback REST; bearer-token gated; message bodies untrusted |
| server -> .voss/bus/ filesystem | Server is sole writer of journal + cursors |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-11 | Spoofing | unauthenticated /bus access | mitigate | _BearerASGI applies app-wide; /bus/* inherits 401-on-missing-token with no per-route code |
| T-V17-12 | Tampering | journal/cursor path escape | mitigate | bus_dir resolved under .voss/bus/; agent id used as a dict key in cursors.json, not a path segment; no agent-controlled path joins |
| T-V17-13 | Tampering | message body schema injection | accept | No message-type schema enforcement (SPEC out-of-scope); body stored as opaque string |
| T-V17-14 | DoS | slow subscriber backpressure | mitigate | publish() uses put_nowait + drop-on-QueueFull (maxsize=100) — a slow subscriber cannot block the broadcast |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/bus/ tests/harness/server/test_contract_drift.py -x -q` GREEN.
- `cd sdk/go && go test ./internal/drift/...` GREEN (or documented-unavailable).
- existing event types byte-identical in contracts/events.schema.json (diff review).
</verification>

<success_criteria>
Additive bus.message event type; durable restart-surviving journal; dedicated bearer-authed SSE broadcast + send/inbox endpoints; all SDK artifacts regenerated; drift gates green.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-05-SUMMARY.md` when done.
</output>

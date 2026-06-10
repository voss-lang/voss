---
phase: E4-sdk-proof
plan: 03
type: execute
wave: 3
depends_on: [E4-02]
files_modified:
  - tests/eval/sdk/consumers/ts/consumer.js
autonomous: true
requirements: [EVSDK-03]
must_haves:
  truths:
    - "The TS consumer decodes the typed SSE event union: it discriminates on event.type (permission.updated/final/session.idle) and collects the types seen"
    - "The TS consumer drains to session.idle and aborts the stream (no hang); under FAKE_TURN it reports saw_permission_gate=false (permission gate is live-only)"
    - "The TS consumer has the permission.updated->replyPermission branch (choice from VOSS_PERMISSION_CHOICE, default a) ready for the live Allow/Deny scenarios"
    - "The TS consumer emits one valid JSON line with all six keys {surface,session_id,final,saw_permission_gate,cost_usd,event_types_seen}"
    - "The TS consumer imports ONLY @vosslang/sdk public exports (createVossClient/subscribeToEvents/replyPermission); zero references to VossLauncher or @vosslang/sdk/node (10s timeout pitfall)"
    - "The TS consumer uses only the published client API and adds no per-runtime scoring (no JSONL writes, no judge)"
  artifacts:
    - path: "tests/eval/sdk/consumers/ts/consumer.js"
      provides: "Hardened TS consumer: full SSE event loop, env-driven permission reply, six-key JSON emission"
      contains: "subscribeToEvents"
  key_links:
    - from: "tests/eval/sdk/consumers/ts/consumer.js"
      to: "subscribeToEvents AsyncIterable<AgentEvent>"
      via: "for-await typed event loop; event.type discrimination; replyPermission(choice) on permission.updated"
      pattern: "event\\.type"
    - from: "tests/eval/sdk/consumers/ts/consumer.js"
      to: "process.stdout structured JSON"
      via: "one-line JSON with the six-key schema; runner extracts final + scores via E1"
      pattern: "event_types_seen"
---

<objective>
Wave 2 (EVSDK-03): harden the TS consumer's event-loop logic so it decodes the typed SSE event union correctly, drains to session.idle without hanging, carries the env-driven permission reply branch (used live in W4), and emits the six-key structured JSON. The W0 skeleton already builds + resolves the `@vosslang/sdk` import; this plan makes the runtime behavior correct + robust.

This plan is PARALLEL with E4-04 (go) and E4-05 (rust) — it touches ONLY `tests/eval/sdk/consumers/ts/consumer.js`. Zero file overlap with the go/rust consumer dirs OR with `tests/eval/test_sdk.py` (the consolidated end-to-end schema tests for all three consumers live in plan 06, which owns that file — this keeps the three W2 consumer plans truly parallel).

SCOPE GUARD (D-06, RESEARCH): the consumer uses the PUBLIC client API only — `createVossClient`/`subscribeToEvents`/`replyPermission` from `@vosslang/sdk`. It MUST NOT import `VossLauncher` from `@vosslang/sdk/node` (HANDSHAKE_TIMEOUT_MS=10_000 at dist/node.js:644; cold litellm is 15-45s — the Python runner owns the server). It MUST NOT add per-runtime scoring (no JSONL writes, no judge calls) — it emits structured JSON and the Python runner scores it via the single E1 substrate. Under FAKE_TURN there is NO permission.updated event (app.py:166-178), so `saw_permission_gate` is false in stub mode — that is correct, not a regression.

Purpose: Make the TS external-consumer contract correct + robust (typed SSE decode + env-driven reply + structured emission).
Output: hardened consumer.js (verified by node --check + grep gates; exercised end-to-end in plan 06).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E4-sdk-proof/E4-CONTEXT.md
@.planning/phases/E4-sdk-proof/E4-RESEARCH.md
@.planning/phases/E4-sdk-proof/E4-PATTERNS.md
@.planning/phases/E4-sdk-proof/E4-VALIDATION.md

<interfaces>
<!-- TS public exports (import from @vosslang/sdk — sdk/typescript/src/client/{rest,sse,permission}.ts) -->
createVossClient(baseUrl, token) -> { createSession(cwd?), postMessage(sessionId, text, mode?), getCost(sessionId), getSession(sessionId), deleteSession(sessionId), abort, listSessions }
subscribeToEvents(baseUrl, sessionId, token, signal?) -> AsyncIterable<AgentEvent>
  // AgentEvent is the discriminated union; switch on event.type:
  //   "server.connected" | "permission.updated"(.id) | "final"(.text) | "session.idle" | "tool" | "thinking" | ...
replyPermission(client, sessionId, { id, choice })   // choice "a"=allow, "d"=deny

<!-- env contract from _drive_sdk_client (plan 02): VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD, VOSS_PROMPT, VOSS_MODE -->
<!-- plan 07 forwards VOSS_PERMISSION_CHOICE (default "a") so the same consumer drives Allow + Deny -->
<!-- structured-result schema (last stdout line): {surface, session_id, final, saw_permission_gate, cost_usd, event_types_seen} -->
<!-- FAKE_TURN final text = "echo: <prompt>" (app.py:174); emits server.connected -> final -> session.idle, NO permission.updated -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Harden TS consumer event loop + structured emission</name>
  <files>tests/eval/sdk/consumers/ts/consumer.js</files>
  <read_first>
    - tests/eval/sdk/consumers/ts/consumer.js (the W0 skeleton — current import + lifecycle; harden the event loop here)
    - sdk/typescript/src/client/sse.ts (lines 12-67 — `subscribeToEvents` async iterator; the AgentEvent.type values + how the AbortSignal closes the stream)
    - sdk/typescript/src/client/rest.ts (lines 41-133 — createVossClient methods: createSession/postMessage/getCost shapes; CostInfo.total_usd field name)
    - sdk/typescript/src/client/permission.ts (lines 11-30 — replyPermission(client, sessionId, {id, choice}); valid choice chars a/A/d/y/n)
    - sdk/typescript/tests/helpers/serve-fixture.ts (how the SDK's own tests consume SSE against a server — the reference loop)
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN event sequence: what event.type values arrive in stub mode)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (Pattern 3 TS consumer lines 355-407 — the full structure; the no-VossLauncher note line 353)
  </read_first>
  <action>
    Harden tests/eval/sdk/consumers/ts/consumer.js (built buildable in W0; now make the event loop robust + correct):
      - Keep the env read + the early `process.exit(2)` when VOSS_BASE_URL is missing (the build-resolution probe).
      - Read `const choice = process.env.VOSS_PERMISSION_CHOICE || "a"` (so plan 07's Deny scenario can drive a "d" reply through this same file).
      - createVossClient(baseUrl, token) then `const sessionId = await client.createSession(cwd)`.
      - Initialize finalText="", sawPermissionGate=false, eventTypesSeen=[], `const ac = new AbortController()`.
      - `await client.postMessage(sessionId, prompt, mode)` BEFORE entering the loop (so the turn is in flight when the SSE stream opens).
      - for-await over subscribeToEvents(baseUrl, sessionId, token, ac.signal): push event.type to eventTypesSeen; on "permission.updated" set sawPermissionGate=true and `await replyPermission(client, sessionId, { id: event.id, choice })`; on "final" capture event.text into finalText; on "session.idle" call ac.abort() and break. Verify the exact field accessors (`event.id`, `event.text`) against the AgentEvent union in sse.ts; adjust if the union uses different field names.
      - Wrap the loop in try/catch; on an AbortError (thrown by ac.abort()) swallow it (expected); on any other error still emit the JSON with whatever was captured so the runner gets a parseable line, not a crash.
      - `const cost = await client.getCost(sessionId).catch(() => ({ total_usd: 0 }))`; read cost.total_usd (verify the CostInfo field name in rest.ts).
      - process.stdout.write of JSON.stringify({ surface: "sdk:ts", session_id: sessionId, final: finalText, saw_permission_gate: sawPermissionGate, cost_usd: cost.total_usd ?? 0, event_types_seen: eventTypesSeen }) + "\n".
      - Confirm NO import from "@vosslang/sdk/node" and NO mention of VossLauncher. Keep the file under ~80 lines.
  </action>
  <verify>
    <automated>cd tests/eval/sdk/consumers/ts && node --check consumer.js && test "$(grep -c 'VossLauncher' consumer.js)" = "0"</automated>
  </verify>
  <acceptance_criteria>
    - `node --check tests/eval/sdk/consumers/ts/consumer.js` exits 0 (valid ESM syntax after hardening).
    - `grep -c "subscribeToEvents" tests/eval/sdk/consumers/ts/consumer.js` >= 1 and `grep -c "replyPermission" tests/eval/sdk/consumers/ts/consumer.js` >= 1 (typed SSE + permission branch present).
    - The reply choice is env-driven: `grep -c "VOSS_PERMISSION_CHOICE" tests/eval/sdk/consumers/ts/consumer.js` >= 1.
    - `grep -c "VossLauncher" tests/eval/sdk/consumers/ts/consumer.js` == 0 and `grep -c "@vosslang/sdk/node" tests/eval/sdk/consumers/ts/consumer.js` == 0 (10s timeout pitfall encoded).
    - The event loop discriminates on event.type for permission.updated / final / session.idle: `grep -c "permission.updated\|session.idle\|\"final\"" tests/eval/sdk/consumers/ts/consumer.js` >= 2.
    - The six-key schema is emitted: `grep -c "event_types_seen" tests/eval/sdk/consumers/ts/consumer.js` >= 1 and `grep -c "saw_permission_gate" tests/eval/sdk/consumers/ts/consumer.js` >= 1.
    - No per-runtime scoring: `grep -c "judge\|runs.jsonl\|writeFile.*jsonl" tests/eval/sdk/consumers/ts/consumer.js` == 0.
  </acceptance_criteria>
  <done>TS consumer decodes the typed SSE union, has the env-driven permission.updated->reply branch, drains to idle without hang, and emits the six-key JSON; public API only; no VossLauncher; no per-runtime scoring. End-to-end FAKE_TURN exercise is in plan 06.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| TS consumer -> @vosslang/sdk public API | consumer is committed in-repo; built from the in-repo dist via a file: dep (no registry fetch) |
| node subprocess -> loopback serve | consumer connects to 127.0.0.1:{port} with a bearer token from env; the runner owns the server |
| consumer stdout JSON -> runner parse | last-line JSON parsed under try/except by the runner; malformed -> "" , never a crash |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-09 | Tampering | TS consumer importing VossLauncher (node launcher) | mitigate | Consumer imports only @vosslang/sdk; grep gate asserts 0 references to VossLauncher / @vosslang/sdk/node |
| T-E4-10 | Elevation | TS consumer reaching into private SDK internals | mitigate | Consumer uses only createVossClient/subscribeToEvents/replyPermission public exports; grep asserts no jsonl/judge scoring |
| T-E4-11 | Denial | TS consumer hanging on the SSE stream | mitigate | AbortController aborts on session.idle; the runner runs the consumer with a subprocess timeout and kills serve in finally |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages; the TS file: dep references the already-installed in-repo @vosslang/sdk; no install task |
</threat_model>

<verification>
- `node --check tests/eval/sdk/consumers/ts/consumer.js` valid; zero VossLauncher / @vosslang/sdk/node references
- typed SSE union decoded (permission.updated/final/session.idle); env-driven reply branch; six-key JSON emitted
- no per-runtime scoring in the consumer (single E1 substrate)
- end-to-end FAKE_TURN schema/decode assertion is consolidated in plan 06 (which owns tests/eval/test_sdk.py)
</verification>

<success_criteria>
- EVSDK-03: sdk:ts consumer drives a turn via the public client API + typed SSE, has the env-driven permission reply branch, emits the six-key structured JSON
- TS-no-VossLauncher pitfall encoded (grep-gated); public-API-only; permission gate exercised live (plan 07)
- Parallel-safe: touches only the ts consumer file (no overlap with go/rust plans or test_sdk.py)
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-03-SUMMARY.md` when done
</output>

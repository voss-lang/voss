---
phase: V15-live-plane-integration
plan: 02
type: execute
wave: 2
depends_on: ["V15-01"]
files_modified:
  - apps/voss-app/src/org/live/vossClientBuild.ts
  - apps/voss-app/src/org/live/sseClient.ts
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/org/cockpit/CockpitShell.tsx
  - apps/voss-app/src/org/live/__tests__/clientBuild.test.ts
  - apps/voss-app/src/org/live/__tests__/sseClient.test.ts
autonomous: true
requirements: [VLIVE-02, VLIVE-03]
must_haves:
  truths:
    - "With a live handshake, RunCommandBar's native Start calls the real createSession and returns a real server session id"
    - "The drawer follow-up calls the real postMessage on the bound native session (202)"
    - "Each native session subscribes via the SDK; permission.updated produces an AttentionQueue row; budget.updated changes the overlay"
    - "liveLabel reads 'live' while a stream is connected for the selected run and returns to 'snapshot' after final / session.idle / stream death"
    - "With no sidecar, every native affordance renders the existing disabled-with-reason strings unchanged"
  artifacts:
    - path: "apps/voss-app/src/org/live/vossClientBuild.ts"
      provides: "buildVossClientFromHandshake → {client, runNativeClient, followUpClient, baseUrl, token} with the createSession string→{id} adapter (Pitfall 1)"
      exports: ["buildVossClientFromHandshake"]
    - path: "apps/voss-app/src/org/live/sseClient.ts"
      provides: "onEvent per-pane sink on ConnectLiveStreamArgs + session-keyed live-handle set (multi-session liveLabel fix)"
      contains: "onEvent"
    - path: "apps/voss-app/src/App.tsx"
      provides: "native client construction wired to RunCommandBar.client + CockpitShell followUpClient + per-session connectLiveStream on native start"
      contains: "buildVossClientFromHandshake"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "RunCommandBar.client"
      via: "client prop = runNativeClient from buildVossClientFromHandshake"
      pattern: "client=\\{"
    - from: "apps/voss-app/src/App.tsx"
      to: "connectLiveStream"
      via: "called with {baseUrl, sessionId, token} after createSession on native start"
      pattern: "connectLiveStream"
    - from: "apps/voss-app/src/org/cockpit/CockpitShell.tsx"
      to: "CardDrawer.followUpClient"
      via: "followUpClient prop threaded from App-level state"
      pattern: "followUpClient="
---

<objective>
Construct the V13.1 TS client from the Plan-01 handshake and plug it into all three injectable V14 sockets: RunCommandBar's native `client` (real `createSession`), the drawer's `followUpClient` (real `postMessage`), and a per-session `connectLiveStream` (real SSE driving AttentionQueue + overlay + `liveLabel`). With no sidecar, every affordance must degrade to the existing disabled-with-reason state unchanged.

Purpose: Flip V14's mock/disabled sockets to real, so a native run creates a real server session and its events flow live. The "no sidecar" path stays byte-identical to V14 (existing tests stay green).
Output: A `buildVossClientFromHandshake` factory (with the createSession adapter from Pitfall 1), the `onEvent` extension to sseClient for per-pane sinks, and the App-level wiring that threads the client through RunCommandBar, CockpitShell→CardDrawer, and connectLiveStream.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/V15-live-plane-integration/V15-SPEC.md
@.planning/phases/V15-live-plane-integration/V15-RESEARCH.md
@.planning/phases/V15-live-plane-integration/V15-PATTERNS.md
@apps/voss-app/src/org/live/sidecarClient.ts

<interfaces>
<!-- Contracts the executor needs. Extracted from codebase — no exploration required. -->

From sdk/typescript/src/client/rest.ts:
```typescript
export function createVossClient(baseUrl: string, token: string): VossClient;
export type VossClient = ReturnType<typeof createVossClient>;
// VossClient methods (relevant):
//   createSession(cwd?: string): Promise<string>   ← returns the id STRING, not {id} (Pitfall 1)
//   listSessions(): Promise<SessionInfo[]>
//   postMessage(sessionId: string, text: string, mode?='plan'): Promise<AcceptedResponse>  // 202
//   abort(sessionId: string): Promise<void>
//   client  ← raw openapi-fetch Client (used by replyPermission)
// Auth: createAuthAndErrorMiddleware sets `Authorization: Bearer <token>` on EVERY request incl. SSE.
```

From apps/voss-app/src/org/cockpit/RunCommandBar.tsx (Seam 1 — KEEP the gate, just inject a client):
```typescript
export interface RunNativeClient { createSession(spec: RunSpec): Promise<{ id: string }>; }  // expects {id}
export interface RunCommandBarProps { cwd; cliBinary; client?: RunNativeClient; spawnAgent?; resolvePaneId?; }
// handleStart native branch: `if (!props.client) { setBlockReason('Voss runs need the Voss server — not available in this build.'); return; }`
// On success: `registerNativeCard(response.id, response.id)` then `flashStarted('Run started')`.
// Mounted in App.tsx at lines 1371-1376 with cwd, cliBinary, resolvePaneId, spawnAgent — client is NOT yet passed.
```

From apps/voss-app/src/org/feedbackWritePath.ts (Seam 2):
```typescript
export interface FollowUpClient { postMessage(sessionId: string, text: string): Promise<unknown>; }
export async function dispatchFollowUp(input: { cardId; comment; client: FollowUpClient|undefined; hasNativePath: boolean }): Promise<FollowUpResult>;
// disabled-with-reason when !hasNativePath || !client || !nativeSessionNodeId(cardId).
```

From apps/voss-app/src/org/cockpit/CardDrawer.tsx + CockpitShell.tsx:
```typescript
// CardDrawer already DECLARES the prop (line 114): followUpClient?: FollowUpClient;
//   isFollowUpEnabled = !!props.followUpClient && !!id && !!nativeSessionNodeId(id);
//   dispatchFollowUp({ ..., client: props.followUpClient, hasNativePath: !!props.followUpClient });
// CockpitShell mounts <CardDrawer /> at line 295 with NO props → must thread followUpClient through.
// CockpitShell receives <CockpitSidebar data={runData()} swarm={swarm()} /> at line 156.
```

From apps/voss-app/src/org/live/sseClient.ts (Seam 3 — EXTEND):
```typescript
export interface ConnectLiveStreamArgs { baseUrl; sessionId; token; stream?: AsyncIterable<AgentEvent>; }
export interface LiveStreamHandle { abort(): void; }
export function connectLiveStream(args): LiveStreamHandle;   // sets liveLabel 'live', for-await → ingestEvent + applyOverlay, finally → 'snapshot'
export { liveLabel, liveOverlay };
export function __resetLiveStream(): void;
// IMPORTANT: ingestEvent(ev) is currently called with NO context — permission.updated then has cardId:undefined (Pitfall 3).
```

From apps/voss-app/src/App.tsx (the native client lives at App level — ONE per workspace cwd):
```typescript
// RunCommandBar mounted at 1371-1376. CockpitShell mounted nearby (receives runData/swarm).
// MountedWorkspace (line 167-214) holds per-workspace signals incl. agentConfigByPaneId.
// Native start currently routes through RunCommandBar's own handleStart (Bridge A) — App must
// supply the `client` prop so that path becomes real. Per-session connectLiveStream is called by App
// (or by the pane in Plan 03); this plan wires the client + the App-level connectLiveStream-on-start.
```
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| webview → loopback REST/SSE | every `createSession`/`postMessage`/`subscribeToEvents` call crosses to `127.0.0.1:<port>` carrying the Bearer token |
| handshake token → in-memory client | token lives in an App-level signal; never persisted, never logged |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V15-03 | Spoofing | `buildVossClientFromHandshake` | mitigate | Client is built via `createVossClient(baseUrl, token)` whose middleware sets `Authorization: Bearer` on every request including SSE; never construct a raw `fetch`/`EventSource` that omits the header (SPEC constraint, sse.ts:20). |
| T-V15-04 | Elevation of Privilege | disabled-with-reason bypass | mitigate | The "no sidecar" path keeps the existing gates verbatim: RunCommandBar's `if (!props.client)` gate stays; `dispatchFollowUp`'s `hasNativePath`/`client` checks stay. Injecting a client only satisfies the gate — it never deletes it. Existing tests asserting the disabled strings must stay green. |
| T-V15-10 | Information Disclosure | token in App signal | mitigate | The token is held in a non-exported App-level signal and passed only to `createVossClient`; no `console.log`/serialization of the handshake token. |
</threat_model>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: buildVossClientFromHandshake factory + onEvent sse extension</name>
  <files>apps/voss-app/src/org/live/vossClientBuild.ts, apps/voss-app/src/org/live/sseClient.ts, apps/voss-app/src/org/live/__tests__/clientBuild.test.ts, apps/voss-app/src/org/live/__tests__/sseClient.test.ts</files>
  <behavior>
    - buildVossClientFromHandshake({port, token}) returns { client, runNativeClient, followUpClient, baseUrl, token } where baseUrl === `http://127.0.0.1:${port}`
    - runNativeClient.createSession(spec) calls client.createSession(spec.goal) and wraps the returned STRING as { id } (Pitfall 1)
    - followUpClient.postMessage(sessionId, text) delegates to client.postMessage(sessionId, text)
    - connectLiveStream with an injected stream and an onEvent callback invokes onEvent for every yielded event (in addition to ingestEvent + applyOverlay)
    - connectLiveStream passes ingest context cardId so a permission.updated event yields a queue row with a defined cardId (Pitfall 3)
    - liveLabel is 'live' during an active injected stream and 'snapshot' after the stream completes
  </behavior>
  <read_first>
    - apps/voss-app/src/org/live/sseClient.ts (full — you add `onEvent?` and an optional `cardId?` to ConnectLiveStreamArgs, thread `cardId` into `ingestEvent(ev, { cardId })`, call `args.onEvent?.(ev)` inside the for-await, and add a session-keyed live-handle Set with immutable spread add/delete in connect/finally)
    - sdk/typescript/src/client/rest.ts (lines 41-130 — createVossClient surface, the createSession string return that forces the adapter)
    - apps/voss-app/src/org/cockpit/RunCommandBar.tsx (lines 43-46 — RunNativeClient {id} shape) and apps/voss-app/src/org/feedbackWritePath.ts (lines 13-16 — FollowUpClient shape) so the factory's return types match the seams exactly
    - apps/voss-app/src/org/live/__tests__/sseClient.test.ts + apps/voss-app/src/org/live/__tests__/mockSseStream.ts (the injected-stream test pattern; mockSseStream yields budget.updated + gate.updated with both session_id and sessionID)
    - apps/voss-app/src/org/attention/attentionQueue.ts (lines 146-174 — ingestEvent permission branch reads ctx.cardId; confirm the {cardId} context shape)
  </read_first>
  <action>
    Create `apps/voss-app/src/org/live/vossClientBuild.ts` exporting `buildVossClientFromHandshake(handshake: { port: number; token: string })`. Construct `const baseUrl = \`http://127.0.0.1:${handshake.port}\``; `const client = createVossClient(baseUrl, handshake.token)` (import from `../../../../sdk/typescript/src/client/rest`). Return `{ client, baseUrl, token: handshake.token, runNativeClient, followUpClient }` where `runNativeClient: RunNativeClient = { createSession: async (spec) => ({ id: await client.createSession(spec.goal) }) }` (Pitfall 1 adapter, types imported from RunCommandBar) and `followUpClient: FollowUpClient = { postMessage: (sessionId, text) => client.postMessage(sessionId, text) }` (type imported from feedbackWritePath). No signals here — pure factory.

    Extend `apps/voss-app/src/org/live/sseClient.ts`: add `onEvent?: (ev: AgentEvent) => void;` and `cardId?: string;` to `ConnectLiveStreamArgs`. In the for-await loop, change `ingestEvent(ev)` to `ingestEvent(ev, args.cardId ? { cardId: args.cardId } : {})` (Pitfall 3) and add `args.onEvent?.(ev)` after `applyOverlay(ev)`. Add a module-level `const [liveHandles, setLiveHandles] = createSignal<Set<string>>(new Set())`; on connect do `setLiveHandles((prev) => new Set([...prev, args.sessionId]))`, and in the `finally` do `setLiveHandles((prev) => { const s = new Set(prev); s.delete(args.sessionId); return s; })` plus the existing `setLiveLabel('snapshot')`. Export `liveHandles` and add `setLiveHandles(new Set())` to `__resetLiveStream`. Use immutable Set spreads only — no produce/structuredClone.

    Add tests: create `clientBuild.test.ts` (factory: baseUrl format, createSession string→{id} wrap via a mocked client, followUpClient delegation). Extend `sseClient.test.ts` with: (a) `onEvent` receives every event from an injected stream; (b) a `permission.updated` injected event with a `cardId` produces an AttentionQueue row whose `cardId` is defined; (c) `liveHandles` contains the sessionId during the stream and is empty after completion.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/org/live/__tests__/clientBuild.test.ts src/org/live/__tests__/sseClient.test.ts 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `vossClientBuild.ts` exports `buildVossClientFromHandshake`
    - `clientBuild.test.ts` asserts `baseUrl === 'http://127.0.0.1:<port>'` and that `runNativeClient.createSession({goal:'x'})` resolves `{ id: <string> }` from a mocked `client.createSession` returning a bare string
    - `sseClient.ts` `ConnectLiveStreamArgs` contains `onEvent` and `cardId`; the for-await calls `args.onEvent?.(ev)` and `ingestEvent(ev, { cardId })`
    - `sseClient.test.ts` passes the onEvent, permission-cardId, and liveHandles assertions
    - `npx --no vitest run src/org/live/__tests__/clientBuild.test.ts src/org/live/__tests__/sseClient.test.ts` exits 0
    - No `produce(` / `structuredClone(` introduced in sseClient.ts (grep -c after edit, filtering comments, returns 0)
  </acceptance_criteria>
  <done>The client factory and the per-pane/per-session sse extension exist and are tested; permission events carry a cardId; liveHandles tracks per-session liveness for the multi-session label fix.</done>
</task>

<task type="auto">
  <name>Task 2: Wire the client into RunCommandBar, CardDrawer, and per-session connectLiveStream</name>
  <files>apps/voss-app/src/App.tsx, apps/voss-app/src/org/cockpit/CockpitShell.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (lines 167-214 MountedWorkspace; 280-385 the native/terminal run handlers + runBarResolvePaneId/runBarSpawnAgent; 1360-1420 the RunCommandBar mount and CockpitShell/GridRoot region — you add an App-level vossClient signal, a lazy `ensureClient(cwd)` that calls startVossServe + buildVossClientFromHandshake once per cwd, pass `client={…}` to RunCommandBar, and thread followUpClient into CockpitShell)
    - apps/voss-app/src/org/live/vossClientBuild.ts (Task 1 — the factory you call)
    - apps/voss-app/src/org/live/sidecarClient.ts (Plan 01 — startVossServe)
    - apps/voss-app/src/org/live/sseClient.ts (connectLiveStream — call on native start with the new session's id, baseUrl, token, cardId)
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (lines around 148-156 RunCommandBar/CockpitSidebar region and 295 <CardDrawer /> — add a `followUpClient?: FollowUpClient` prop to CockpitShell's props and forward it to CardDrawer)
    - apps/voss-app/src/org/cockpit/RunCommandBar.tsx (handleStart native branch — confirm the client.createSession(spec) call and registerNativeCard so App's connectLiveStream uses the same id)
  </read_first>
  <action>
    In `App.tsx`, add an App-level `const [vossClient, setVossClient] = createSignal<ReturnType<typeof buildVossClientFromHandshake> | null>(null)` and an async `ensureVossClient(cwd: string)` that returns the existing client if present, else `startVossServe(cwd)` → `buildVossClientFromHandshake(handshake)` → `setVossClient(built)` → returns it. Build a `runNativeClient` view that lazily ensures the client: pass `client={{ createSession: async (spec) => { const built = await ensureVossClient(workspacePath() ?? ''); const r = await built.runNativeClient.createSession(spec); /* native start side-effects */ return r; } }}` to `<RunCommandBar>` (keep existing cwd/cliBinary/resolvePaneId/spawnAgent props). After a native session id is known, call `connectLiveStream({ baseUrl: built.baseUrl, sessionId: r.id, token: built.token, cardId: r.id })` (the sessionId IS the cardId — Bridge A) and retain the returned handle for teardown. Keep this plan's connectLiveStream wiring at App level; the per-pane transcript sink (`onEvent` → ProtocolPane) lands in Plan 03 — here it is sufficient that the stream feeds AttentionQueue + overlay + liveLabel.

    Thread the follow-up client: give `CockpitShell` a new `followUpClient?: FollowUpClient` prop (import the type from `../feedbackWritePath`), forward it to `<CardDrawer followUpClient={props.followUpClient} />` at line 295. In `App.tsx`, pass `followUpClient={vossClient()?.followUpClient}` to `<CockpitShell>` (the drawer's `hasNativePath` becomes true automatically because the prop is now defined — feedbackWritePath gates on `!!props.followUpClient`).

    Do NOT remove the disabled-with-reason gates (T-V15-04). When `vossClient()` is null (no sidecar yet), RunCommandBar's own `if (!props.client)` path is bypassed because we always pass a client object — but that client lazily spawns; if `startVossServe` throws, surface the error through the existing block-reason path (the createSession adapter rejects, RunCommandBar's await throws — wrap so the bar shows a reason rather than an unhandled rejection). Keep CardDrawer's disabled-with-reason intact for snapshot cards (no native session node).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx --no vitest run src/org/cockpit/__tests__/runCommandBar.test.tsx src/org/feedbackWritePath.test.ts 2>&1 | tail -15 && npx --no tsc --noEmit 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `App.tsx` imports and calls `buildVossClientFromHandshake` and `startVossServe`
    - `App.tsx` passes a `client=` prop to `<RunCommandBar>` and a `followUpClient=` prop to `<CockpitShell>`
    - `App.tsx` calls `connectLiveStream(` with `{ baseUrl, sessionId, token, cardId }` after a native session id is known
    - `CockpitShell.tsx` declares `followUpClient?` in its props and forwards it to `<CardDrawer followUpClient={...} />`
    - `runCommandBar.test.tsx` stays green (the disabled-with-reason string assertion still passes when no client is injected in the test harness — T-V15-04)
    - `feedbackWritePath.test.ts` stays green (disabled path for snapshot cards unchanged)
    - `tsc --noEmit` reports no new errors vs. baseline
  </acceptance_criteria>
  <done>A native run constructs the client lazily, creates a real session, subscribes live (queue + overlay + label flip), and the drawer follow-up posts to the bound session; the no-sidecar disabled-with-reason behavior is preserved.</done>
</task>

</tasks>

<verification>
- `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/clientBuild.test.ts src/org/live/__tests__/sseClient.test.ts src/org/cockpit/__tests__/runCommandBar.test.tsx src/org/feedbackWritePath.test.ts` exits 0
- `npx --no tsc --noEmit` reports no new errors vs. the pre-V15 baseline
- grep confirms `client=` on RunCommandBar and `followUpClient=` on CockpitShell→CardDrawer in App.tsx/CockpitShell.tsx
</verification>

<success_criteria>
- Native Start → real `createSession` → real server session id (VLIVE-02)
- Drawer follow-up → real `postMessage` → 202 on a native session (VLIVE-02)
- Per-session `connectLiveStream` drives AttentionQueue + overlay + `liveLabel` flip (VLIVE-03)
- No-sidecar path renders the V14 disabled-with-reason strings unchanged; existing suites green (T-V15-04)
- Bearer token set on every request incl. SSE; never logged (T-V15-03 / T-V15-10)
</success_criteria>

<output>
Create `.planning/phases/V15-live-plane-integration/V15-02-SUMMARY.md` when done
</output>

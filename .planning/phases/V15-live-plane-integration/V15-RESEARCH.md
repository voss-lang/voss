# Phase V15: Live Plane Integration — Research

**Researched:** 2026-06-09
**Domain:** Tauri managed state · V13.1 TS SDK wiring · Solid reactive pane rendering · PROTOCOL §6 event rendering
**Confidence:** HIGH (all findings from direct codebase inspection; no training-data assumptions for seams)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Native run submit (RunCommandBar, either mode) auto-opens a structured pane in the Live Work grid immediately; if the app is in Run Review, it flips to Live Work focused on the new pane.
**D-02:** New structured panes land via the same grid-insertion path as the sidebar quick-launch agent spawn (new cell + `balanceRatios` equalize). One insertion behavior everywhere; zero new layout logic.
**D-03:** One pane per native run, no cap. Honest 1:1 run↔pane mapping; grid proven at 9 panes.
**D-04:** Attach-to-existing lives in a cockpit sidebar "Server sessions" section: `GET /session` list (id/title/age, recent-first) with an Attach action. Attached panes land via the D-02 grid path.
**D-05:** Session list shows everything `GET /session` returns, newest first. No source filtering.
**D-06:** Attaching registers the session as a native cockpit card via the existing native-card bridge — attached ≡ started; board/drawer see one consistent model.
**D-07:** Tool lines render as collapsed one-liners by default; click expands full args/result/excerpt. Overrides mockup's inline fs_edit excerpts.
**D-08:** Transcript DOM is capped, trim-oldest (~few hundred events). EM task header and pending permission rows are pinned — never trimmed.
**D-09:** `stream.delta` appends to a growing live block with V14 honest streaming pulse; `stream.finalize` settles it into plain prose. Sticky-bottom auto-scroll unless the user scrolled up.
**D-10:** Cold start renders an in-pane boot placeholder ("starting Voss…" + elapsed) until handshake lands.
**D-11:** Server death mid-run: transcript appends ended banner row, pane chrome dims, statusbar flips to snapshot, follow-up goes disabled-with-reason. Reuse ExitBanner visual language.
**D-12:** Sidecar spawn failure: boot placeholder becomes in-pane error state — message + stderr tail + Retry button.

### Claude's Discretion

- Exact transcript cap value (D-08) — a few hundred events, planner picks.
- Internal architecture of the structured pane component (new component vs PaneComponent mode branch), event→DOM renderer structure, EM-header data sourcing from the event stream, stub-provider test mechanics.

### Deferred Ideas (OUT OF SCOPE)

- Queue↔pane focus linking (clicking an AttentionQueue row focuses the owning pane)
- Attach-while-turn-busy semantics (409 handling nuance beyond honest error)
- Session list management (delete/rename from sidebar)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VLIVE-01 | Tauri command `start_voss_serve(cwd)` + managed per-workspace sidecar state | `sidecar.rs` complete; needs `lib.rs` wrapper + managed state map + `generate_handler!` registration |
| VLIVE-02 | V13.1 client fills V14 sockets (RunCommandBar `client`, drawer `followUpClient`, `sseClient`) | All three seams verified; injection point is App-level mount per V14 D-03 pattern |
| VLIVE-03 | Live SSE drives queue, overlay, and label | `connectLiveStream` + `ingestEvent` already wired; needs real `baseUrl`/`token` from handshake |
| VLIVE-04 | Structured pane mode for native runs | `PaneComponent.doSpawn` branch point identified; new `ProtocolPane` component approach confirmed |
| VLIVE-05 | Inline permission gate sharing the queue's reply loop | `ingestEvent` already routes `permission.updated`; need `replyPermission` call + dual-surface clear |
| VLIVE-06 | Attach structured pane to existing session | `listSessions()` in SDK; D-04 sidebar section new; attach = respawn sidecar if needed + `connectLiveStream` |
| VLIVE-07 | Lifecycle honesty (cold start, spawn failure, server death) | Boot placeholder, error state, ExitBanner reuse all designed in UI-SPEC |
| VLIVE-08 | Hermetic verification + human checkpoint | Vitest jsdom for TS; gated cargo test pattern from spike for Rust; stub-provider pattern from `mockSseStream` |
</phase_requirements>

---

## Summary

V15 is an integration phase, not a greenfield phase. Every major technical component already exists; the work is wiring them together in the correct order with lifecycle honesty. The risk surface collapsed after the sidecar spike (commit `de93b4d`) and V14's socket preparation. Research here is codebase mapping, not library discovery.

**Sidecar (VLIVE-01):** `crates/voss-app-core/src/sidecar.rs` is the complete, proven implementation — `spawn_voss_serve(python, cwd)` returns `VossServe` holding the `ServeHandshake`. What remains is a thin `#[tauri::command] async fn start_voss_serve(cwd: String, state: tauri::State<'_, Mutex<HashMap<String, VossServe>>>) -> Result<ServeHandshakePayload, String>` in `lib.rs`, `.manage(Mutex::new(HashMap::<String, VossServe>::new()))` at builder time, and registration in `generate_handler!`. The per-workspace map uses the `cwd` string as the key; `reuse-if-alive` checks that `map.get(cwd).pid()` is still alive before spawning.

**Frontend wiring (VLIVE-02/03):** The V13.1 SDK exports `createVossClient(baseUrl, token)` → `VossClient` with `createSession`, `postMessage`, `listSessions`, and `replyPermission` (via separate `permission.ts`). The SSE subscription is `subscribeToEvents(baseUrl, sessionId, token, signal?)` returning `AsyncIterable<AgentEvent>`. `sseClient.ts:connectLiveStream()` already consumes this verbatim; `RunCommandBar` already accepts `client?: RunNativeClient`; `feedbackWritePath.ts:dispatchFollowUp` already accepts `client: FollowUpClient | undefined`. The planner's injection point is a single App-level `createEffect` or `onMount` that calls `invoke('start_voss_serve', {cwd})` → constructs the SDK client → passes it to `RunCommandBar`, the drawer, and a global `connectLiveStream` call.

**Structured pane (VLIVE-04):** `PaneComponent.tsx` contains a `doSpawn` branch that today goes `managed → spawnManagedAgent` vs `plain → spawn`. A third branch `protocol → no PTY, render ProtocolPane` fits naturally here. The `ProtocolPane` component is entirely new — it owns a `createSignal<AgentEvent[]>` transcript store, a `connectLiveStream`-derived stream, and renders the UI-SPEC event rows. It lives inside `.pane-body` (the existing chrome is untouched). The pane-kind discriminator is whether the pane was started by the native `createSession` path.

**Permission gate (VLIVE-05):** `ingestEvent` already handles `permission.updated` and pushes an `AttentionItem`. The gate in the pane just needs to call `replyPermission(client, sessionId, {id, choice})` from `sdk/typescript/src/client/permission.ts`, then remove the item from both the pane transcript (mark as resolved) and the attention queue. The attention queue has no removal API today — a `resolveItem(id)` function needs to be added.

**21-member event union (VLIVE-04):** Confirmed from `contracts/events.schema.json`. The discriminator field is `type`. 8 members get dedicated DOM (per UI-SPEC Event Coverage Table); 13 get generic fallback rows. `ToolEvent` has `name`, `state`, `summary`, `args` fields — `state` is `"pending"` | `"ok"` | `"error"`. `PermissionUpdated` has `id`, `tool_name`, `args`, `dimension` — no `session_id` (important: context-supplied cardId required for bridge lookup).

**Primary recommendation:** Build the Tauri command first (VLIVE-01) because every other piece gates on having a real `{port, token}` in the webview. Then wire the three V14 sockets (VLIVE-02/03). Then build `ProtocolPane` from the UI-SPEC. Permission gate and attach surface can land in the same wave as the pane.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Spawn `voss serve`, own lifecycle, expose handshake | Backend / Tauri | — | `voss serve` is a child process; webview cannot spawn node:child_process |
| Managed-state reuse-if-alive + reap on exit | Backend / Tauri | — | Process tracking requires OS-level handle held in Tauri managed state |
| Construct TS SDK client from handshake | Frontend (webview) | — | Bearer-authed REST/SSE client runs entirely in webview; SDK is TS |
| SSE subscription per session | Frontend (webview) | — | `subscribeToEvents` uses `fetch` + `Authorization: Bearer`; webview-native |
| Structured pane DOM rendering | Frontend / Browser | — | DOM manipulation is browser-tier; no server knows about pane layout |
| Permission reply `POST /session/:id/permission` | Frontend (webview) | — | `replyPermission` in SDK; HTTP from webview through authenticated client |
| Inline permission gate + AttentionQueue dual-surface | Frontend / Browser | — | Both surfaces are webview DOM signals |
| Session list (`GET /session`) | Frontend (webview) | — | `listSessions()` from SDK; data fetched into reactive signal |
| Pane insertion into grid (D-02) | Frontend / Browser | — | `gridController.splitFocused('H')` + `balanceRatios` — pure JS tree |
| Cold-start / spawn-failure error surface | Frontend / Browser | Backend (stderr) | Stderr tail comes from Tauri command error string; UI renders it |

---

## Standard Stack

### Core (already in repo — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sdk/typescript` (internal) | — | `createVossClient`, `subscribeToEvents`, `replyPermission` | Frozen V13.1 SDK; authoritative client surface |
| `solid-js` | repo version | Reactive signals, `createSignal`, `For`, `Show` | Project-standard UI framework; all V14 components use it |
| `@tauri-apps/api/core` | repo version | `invoke('start_voss_serve', ...)` IPC call | Established pattern in RunCommandBar, PtyTransport |
| `eventsource-parser/stream` | already in sdk/typescript | SSE parsing in `subscribeToEvents` | Already vendored; `subscribeToEvents` handles this internally |
| `voss-app-core` (crate) | workspace path dep | `spawn_voss_serve`, `VossServe`, `ServeHandshake` | Spike already proven; production home |

### Supporting (already in repo — no new installs)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tokio` | workspace | Async runtime for Tauri commands | Already used in `spawn_voss_serve`; no new dep |
| `serde` / `serde_json` | workspace | Serialization of `ServeHandshake` for IPC | Already used; `ServeHandshake` is `#[derive(Serialize)]` |
| `anyhow` | workspace | Error type in `spawn_voss_serve` | Already imported in sidecar.rs |

**No new npm or cargo dependencies are expected.** SPEC constraint confirmed.

### Installation

No installation needed — all dependencies already in the workspace.

---

## Package Legitimacy Audit

> Not applicable — this phase installs zero new packages (SPEC constraint: "No new npm/cargo dependencies expected").

---

## Architecture Patterns

### System Architecture Diagram

```
[RunCommandBar: native start]
        |
        | invoke('start_voss_serve', {cwd})
        v
[Tauri lib.rs: start_voss_serve command]
        |
        | calls spawn_voss_serve(&python, &cwd)
        v
[voss-app-core/src/sidecar.rs]
        |  already proven: spawn → handshake parse → reap
        |
        v
[VossServe {handshake: {port, token}}]
        |
        | ServeHandshake returned to webview
        v
[App.tsx: receives {port, token}]
        |
        | createVossClient("http://127.0.0.1:{port}", token)
        v
[VossClient + subscribeToEvents fn]
        |
        |--- inject client --> RunCommandBar.props.client
        |--- inject client --> drawer followUpClient
        |--- invoke on session start --> connectLiveStream(baseUrl, sessionId, token)
                        |
                        v
              [sseClient.ts: for-await AgentEvent]
                        |
                        |--- ingestEvent(ev) --> [attentionQueue]
                        |--- applyOverlay(ev) --> [liveOverlay signal]
                        |--- emit to ProtocolPane transcript signal
                        v
              [ProtocolPane: event[] → DOM rows]
                        |
                        |-- permission.updated --> [InlinePermissionGate]
                        |                               |
                        |                               v
                        |                    replyPermission(client, sid, {id, choice})
                        |                    clears pane gate + attentionQueue row
                        |-- tool/plan/stream/final/thinking --> [dedicated row components]
                        |-- all others --> [GenericFallbackRow]
```

### Recommended Project Structure

```
apps/voss-app/src/
├── pane/
│   ├── ProtocolPane.tsx          # NEW: structured protocol pane body
│   ├── ProtocolPane.css          # NEW: .protocol-pane, .proto-* classes from UI-SPEC
│   └── PaneComponent.tsx         # EDIT: add 3rd doSpawn branch for protocol panes
├── org/
│   ├── cockpit/
│   │   ├── CockpitSidebar.tsx    # EDIT: add "Server sessions" section (D-04)
│   │   └── serverSessions.ts     # NEW (optional): GET /session list signal + attach handler
│   └── live/
│       └── sseClient.ts          # EDIT: add per-session dispatch to ProtocolPane
└── App.tsx                       # EDIT: invoke start_voss_serve, construct client, inject sockets

crates/voss-app-core/src/
└── sidecar.rs                    # NO CHANGE: spike is production home

apps/voss-app/src-tauri/src/
└── lib.rs                        # EDIT: add start_voss_serve command + VossServeState + generate_handler!
```

### Pattern 1: Tauri Command with Managed HashMap State

The existing Tauri command pattern uses type-aliased `tauri::State` guards. The sidecar map follows `PtyRegistry` / `Mutex<GridState>` precedent exactly.

```rust
// Source: apps/voss-app/src-tauri/src/lib.rs (existing pattern)
// PtyRegistry (Arc<PtyRegistry>) and GridState (Mutex<GridState>) show the pattern.

use std::sync::Mutex;
use std::collections::HashMap;
use voss_app_core::sidecar::{VossServe, spawn_voss_serve, python_path, ServeHandshake};

// Managed state type (add to lib.rs):
type VossServeMap<'a> = tauri::State<'a, Mutex<HashMap<String, VossServe>>>;

// New command (add to lib.rs):
#[tauri::command]
async fn start_voss_serve(
    cwd: String,
    state: VossServeMap<'_>,
) -> Result<ServeHandshake, String> {
    // Reuse-if-alive: check if cwd already has a live server
    {
        let map = state.lock().map_err(|_| "lock poisoned".to_string())?;
        if let Some(serve) = map.get(&cwd) {
            if serve.pid().is_some() {  // pid() returns None after kill
                return Ok(serve.handshake.clone());
            }
        }
    }
    // Spawn new
    let python = python_path();
    let serve = spawn_voss_serve(&python, std::path::Path::new(&cwd))
        .await
        .map_err(|e| e.to_string())?;
    let handshake = serve.handshake.clone();
    state.lock().map_err(|_| "lock poisoned".to_string())?
        .insert(cwd, serve);
    Ok(handshake)
}

// In run() builder:
// .manage(Mutex::new(HashMap::<String, VossServe>::new()))
// In generate_handler!: start_voss_serve
```

**Critical notes for implementation:**
- `VossServe` is NOT `Sync` or `Clone` by default (contains `Child`). The `Mutex<HashMap<String, VossServe>>` wraps it; `kill_on_drop` reaps on map entry removal or app exit.
- `pid()` returns `Option<u32>`; `None` after the child has been reaped means the entry is stale — re-spawn.
- The `ServeHandshake` is `#[derive(Serialize, Deserialize, Clone)]` already — safe for IPC return.
- Tauri IPC serde: all field names in `ServeHandshake` are already lowercase single words (`port`, `token`) — no camelCase/snake_case surprise (V14 `AgentEntry` lesson does not apply here).

### Pattern 2: App-Level Client Construction (V13.1 SDK)

```typescript
// Source: sdk/typescript/src/client/rest.ts — createVossClient signature

// In App.tsx onMount or createEffect watching the workspace cwd:
import { createVossClient } from '../../sdk/typescript/src/client/rest';
import { connectLiveStream } from './org/live/sseClient';

// After invoke('start_voss_serve', {cwd}) resolves:
const { port, token } = handshake; // ServeHandshake fields (lowercase)
const baseUrl = `http://127.0.0.1:${port}`;
const vossClient = createVossClient(baseUrl, token);

// Inject into RunCommandBar (matches RunNativeClient interface):
// RunNativeClient.createSession(spec) ≡ vossClient.createSession(spec.goal)
// Note: RunCommandBar expects createSession(spec: RunSpec) → {id: string}
// But SDK's createSession(cwd?: string) → string (just the id, no wrapper object)
// SEAM MISMATCH: RunCommandBar expects {id: string}; SDK returns string directly.
// Adapter needed: wrap SDK's string return in {id: string} at injection point.

const runNativeClient: RunNativeClient = {
  createSession: async (spec) => {
    const id = await vossClient.createSession(spec.goal); // note: SDK returns string
    return { id };
  }
};

// Inject into feedbackWritePath (matches FollowUpClient interface):
const followUpClient: FollowUpClient = {
  postMessage: (sessionId, text) => vossClient.postMessage(sessionId, text)
};
```

**Important seam difference:** `RunCommandBar`'s `RunNativeClient.createSession` expects `(spec: RunSpec) => Promise<{id: string}>` but `sdk/typescript/src/client/rest.ts` `createVossClient` returns `createSession(cwd?: string): Promise<string>` (returns the ID string directly, not wrapped). A thin adapter at the injection point wraps the string return. [VERIFIED: codebase inspection]

### Pattern 3: ProtocolPane Component Structure (Solid reactive)

```typescript
// Source: apps/voss-app/src/pane/PaneComponent.tsx (existing pattern)
// Mirror the module-level signal pattern from budgetRegistry.ts / sseClient.ts

import { createSignal, For, Show } from 'solid-js';
import type { AgentEvent } from '../../../../sdk/typescript/src/client/sse';

// NOTE: Solid render-layer discipline — module-level createSignal, immutable spreads.
// Never produce() or structuredClone() for tree utils called from render.

interface ProtocolPaneProps {
  sessionId: string;
  baseUrl: string;
  token: string;
  onEnded?: () => void;
}

// Transcript state is local (per-pane), not module-level.
// Use createSignal<AgentEvent[]> inside the component (not module-level)
// because each pane needs independent transcript state.

export default function ProtocolPane(props: ProtocolPaneProps) {
  const [events, setEvents] = createSignal<AgentEvent[]>([]);
  const [bootState, setBootState] = createSignal<'booting'|'live'|'ended'|'error'>('booting');
  // ...
}
```

**D-08 transcript cap implementation:** The planner should pick N ≈ 300 events. On each new event push, if `events().length >= CAP`, trim from index 0 — but skip any item that is a `permission.updated` (pending) or the first `user` event (task header pin). Use `setEvents(prev => trimOldest([...prev, newEvent], CAP))` where `trimOldest` is a pure function.

### Pattern 4: Permission Reply + Dual-Surface Clear

```typescript
// Source: sdk/typescript/src/client/permission.ts
import { replyPermission, type PermissionChoice } from '../../../../sdk/typescript/src/client/permission';
import { __resetAttentionQueue } from '../attention/attentionQueue'; // test only

// The attention queue has no resolveItem today — needs addition:
// export function resolveAttentionItem(id: string): void {
//   setAttentionQueue(prev => prev.filter(item => item.id !== id));
// }

const handlePermissionReply = async (
  ev: PermissionUpdated,
  choice: PermissionChoice,
  client: VossClient,
  sessionId: string,
) => {
  // Disable buttons immediately
  await replyPermission(client, sessionId, { id: ev.id, choice });
  // Clear both surfaces:
  resolveAttentionItem(`permission:${ev.id}`);  // queue row
  // pane gate: mark the event row as resolved (local state update)
};
```

### Anti-Patterns to Avoid

- **`new EventSource(url)`:** Cannot set `Authorization: Bearer` header. Always use `subscribeToEvents` from `sdk/typescript/src/client/sse.ts`. The comment at `sse.ts:20` (line 19 in the actual file) documents this.
- **`produce()` or `structuredClone()` in pane render:** DATA_CLONE_ERR on Proxy objects (Solid Proxy pitfall). Use immutable spread `{ ...prev, [key]: newVal }` for signal updates.
- **Module-level signal for per-pane transcript:** Module-level signals are global; each pane needs local `createSignal` inside the component function.
- **Hardcoding the 21-member event union:** Always derive from `contracts/events.schema.json` via the generated TypeScript types (`AgentEvent` discriminated union). Never add a new `case` that's not in the union.
- **Calling `invoke('start_voss_serve')` from inside `PaneComponent`:** The command should be called at app-level or workspace-level, not per-pane. One server per workspace, shared across panes.
- **Assuming `VossServe.pid()` is non-None after map lookup:** After `shutdown()` or crash, `pid()` returns `None`. Always check before reusing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE with auth header | Custom EventSource wrapper | `subscribeToEvents` from `sdk/typescript/src/client/sse` | Raw EventSource cannot set Authorization header; SDK handles reconnect, abort, parse |
| Permission reply HTTP | Custom `fetch` POST | `replyPermission` from `sdk/typescript/src/client/permission` | Handles body shape, error parsing, VossApiError |
| Server list | Direct `fetch` to `/session` | `vossClient.listSessions()` from `sdk/typescript/src/client/rest` | Handles auth, type safety, error handling |
| Session create | Direct `fetch` to `/session` | `vossClient.createSession(cwd)` from rest.ts | Same |
| Process spawn / heartbeat | Any new Rust | `spawn_voss_serve` in `voss-app-core/src/sidecar.rs` | Already proven, stdin heartbeat, stderr drain, 60s timeout, env vars |
| Pane insertion | New layout logic | `gridController.splitFocused('H')` + `balanceRatios` (D-02) | Existing path, tested, equalize proven at 9 panes |
| Auth middleware | Custom headers | `createVossClient(baseUrl, token)` — middleware is inside `createAuthAndErrorMiddleware` in rest.ts | Sets Bearer on every request including SSE |

**Key insight:** The SDK is the complete client layer; the sidecar.rs is the complete spawn layer. V15's only new custom logic is the DOM renderer (ProtocolPane) and the per-workspace Tauri command wrapper.

---

## Common Pitfalls

### Pitfall 1: `RunNativeClient.createSession` vs SDK `createSession` return type mismatch

**What goes wrong:** `RunCommandBar` expects `client.createSession(spec) → Promise<{id: string}>`. The SDK's `createVossClient().createSession(cwd?)` returns `Promise<string>` (the session ID directly). Passing the SDK client object directly as `RunNativeClient` will fail at runtime: `response.id` will be `undefined`.

**Why it happens:** `RunNativeClient` was designed as a mock interface before the real SDK existed. The shapes diverged.

**How to avoid:** At the injection site in `App.tsx`, wrap with an adapter:
```typescript
const runNativeClient: RunNativeClient = {
  createSession: async (spec) => ({ id: await vossClient.createSession(spec.goal) })
};
```

**Warning signs:** `registerNativeCard(response.id, response.id)` stores `undefined` as both cardId and sessionNodeId; `cardToSessionNode()` has no entries after a native run.

### Pitfall 2: `VossServe` not Sync — cannot use `Arc<VossServe>` directly in Tauri state

**What goes wrong:** `VossServe` contains `tokio::process::Child` which is not `Sync`. Attempting `Arc<VossServe>` as managed state will fail compilation.

**Why it happens:** `tokio::process::Child` is explicitly not `Sync`.

**How to avoid:** Use `Mutex<HashMap<String, VossServe>>` as the managed state type. The Mutex provides the Sync wrapper. Obtain a lock before accessing the map.

**Warning signs:** Compile error `the trait Sync is not implemented for Child`.

### Pitfall 3: `permission.updated` has no `session_id` field

**What goes wrong:** The `ingestEvent` function in `attentionQueue.ts` handles `permission.updated` using `ctx.cardId` from context (not from the event). The event schema confirms: `PermissionUpdated` has no `session_id` field. Code that tries `ev.session_id` on a `permission.updated` event will get `undefined`.

**Why it happens:** Permission events are session-scoped by delivery (per-session SSE stream) but the event payload itself carries only `{id, tool_name, args, dimension}`.

**How to avoid:** When routing a `permission.updated` event from `connectLiveStream` into `ingestEvent`, pass `ctx: { cardId: <the session's bound cardId> }`. The `cardId` is known at `connectLiveStream` call time (the caller knows which native card started this session).

**Warning signs:** `attentionQueue` items for permissions have `cardId: undefined` and `deepLink: {}`.

### Pitfall 4: `connectLiveStream` is module-level — shared across all sessions

**What goes wrong:** `sseClient.ts` exports a single `liveLabel` and `liveOverlay` module-level signal. Today one live session at a time is implied. V15 allows multiple simultaneous native runs (D-03). Calling `connectLiveStream` twice with different session IDs would clobber the `liveLabel` on the first call when the second starts, and the overlay is keyed by session_id so multiple sessions work — but the single `liveLabel` means "is any session live" not "is this pane's session live".

**Why it happens:** V14 was designed for one session at a time.

**How to avoid:** Per-session live state should live in `ProtocolPane` local signals. The module-level `liveLabel` is for the statusbar (selected pane). The planner should decide whether to pass a per-session `isLive` signal to the pane or extend `sseClient.ts` with a session-keyed label map. The simplest approach: each `ProtocolPane` tracks its own `isLive` boolean signal; the module-level `liveLabel` reflects only the selected/focused pane's liveness.

**Warning signs:** Statusbar shows 'live' even when the focused pane's session has ended; or all panes show 'snapshot' the moment any one ends.

### Pitfall 5: Reuse-if-alive check: `VossServe.pid()` returns None after `kill_on_drop`

**What goes wrong:** After a server crashes or `shutdown()` is called, `VossServe.pid()` returns `None` (the `Child`'s PID slot is consumed). The Tauri command must handle this — a stale map entry with `pid() == None` means the server is dead and needs respawning.

**Why it happens:** `tokio::process::Child::id()` returns `None` after the process has been waited on.

**How to avoid:** After map lookup, call `serve.pid()`. If `None`, remove the stale entry and spawn fresh. Document this explicitly in the command implementation.

**Warning signs:** `start_voss_serve` returns the old `{port, token}` but the port is no longer listening; SDK calls return connection refused.

### Pitfall 6: Attach in cold-start — sidecar may not be alive post-restart

**What goes wrong:** After app restart, `GET /session` is called to list sessions (VLIVE-06), but no sidecar is running. `listSessions()` needs a `baseUrl`/`token` — but there's no handshake yet because nobody has called `start_voss_serve`.

**Why it happens:** The server session list is server-side state; the app needs to respawn the sidecar before it can query the list.

**How to avoid:** The "Server sessions" sidebar section (D-04) should trigger a `start_voss_serve(cwd)` call first (getting the boot placeholder for the new pane), then `listSessions()`. Or: the sidebar always shows the local `.voss/sessions/` directory (Tauri reads it) for listing, but attach goes through the live server. Check what data `SessionInfo` from `GET /session` provides vs local directory listing.

**Warning signs:** "Server sessions" shows no entries even when `.voss/sessions/` has runs; or attach triggers the boot placeholder unexpectedly.

### Pitfall 7: `ServeHandshake` IPC camelCase — no surprise here

Unlike `AgentEntry` in V14 (which had a snake_case→undefined crash), `ServeHandshake` fields are lowercase single words (`port: u16`, `token: String`). These serialize identically in snake_case and camelCase. No serde rename attribute needed. [VERIFIED: codebase inspection of sidecar.rs]

---

## Code Examples

### V13.1 SDK: Full Client Construction

```typescript
// Source: sdk/typescript/src/client/rest.ts
import { createVossClient } from '../../../../sdk/typescript/src/client/rest';

// createVossClient(baseUrl: string, token: string) returns VossClient with:
//   .createSession(cwd?: string): Promise<string>   — returns session ID (not wrapped)
//   .listSessions(): Promise<SessionInfo[]>
//   .postMessage(sessionId, text, mode?): Promise<AcceptedResponse>
//   .abort(sessionId): Promise<void>
//   .getCost(sessionId): Promise<CostInfo>
//   .client  — the raw openapi-fetch Client for custom calls
```

### V13.1 SDK: SSE Subscription

```typescript
// Source: sdk/typescript/src/client/sse.ts
// subscribeToEvents(baseUrl, sessionId, token, signal?) → AsyncIterable<AgentEvent>
// AgentEvent is the discriminated union from contracts/events.schema.json

// Used verbatim in connectLiveStream (sseClient.ts):
const stream = subscribeToEvents(args.baseUrl, args.sessionId, args.token, ac.signal);
for await (const ev of stream) {
  // ev.type narrows the discriminated union
}
```

### V13.1 SDK: Permission Reply

```typescript
// Source: sdk/typescript/src/client/permission.ts
import { replyPermission, type PermissionChoice } from '../../../../sdk/typescript/src/client/permission';
// replyPermission(client: VossClient, sessionId: string, {id, choice}: PermissionReplyArgs) → Promise<void>
// PermissionChoice = "a" | "A" | "d" | "y" | "n"
// UI-SPEC §3 choices: "d"=Deny, "a"=Allow once, "A"=Allow for scope

await replyPermission(vossClient, sessionId, { id: permissionEvent.id, choice: 'd' });
```

### Tauri Command Registration Pattern (from lib.rs)

```rust
// Source: apps/voss-app/src-tauri/src/lib.rs lines 1299-1373
// Pattern: .manage(type), #[tauri::command] fn, register in generate_handler!

// At builder (in run()):
.manage(Mutex::new(HashMap::<String, VossServe>::new()))

// New command following spawn_agent pattern:
#[tauri::command]
async fn start_voss_serve(
    cwd: String,
    state: tauri::State<'_, Mutex<HashMap<String, VossServe>>>,
) -> Result<ServeHandshake, String> { ... }

// In generate_handler![..., start_voss_serve]
```

### Grid Insertion (D-02 path in App.tsx)

```typescript
// Source: apps/voss-app/src/App.tsx lines 362-385 (runBarResolvePaneId / runBarSpawnAgent)
// The D-02 insertion path is splitFocused('H') on the gridController:

const before = ctrl.snapshot().focusedId;
ctrl.splitFocused('H');
const newId = ctrl.snapshot().focusedId;
if (newId === before) return; // GRD-05 floor violation — grid too small

// For native panes: instead of setting agentConfig (PTY-specific),
// store a "nativeSessionId" for the new pane ID so ProtocolPane can pick it up.
// Pattern: a new map ws.nativeSessionByPaneId similar to agentConfigByPaneId.
```

### ExitBanner Reuse (D-11)

```typescript
// Source: apps/voss-app/src/pane/ExitBanner.tsx
// ExitBanner({ exitCode: number, onRestart: () => void }) — simple component
// For protocol pane ended state (D-11): exitCode=1, onRestart=no-op
// UI-SPEC says render inline in transcript flow (not position:absolute)

<ExitBanner exitCode={1} onRestart={() => {}} />
// Note: ExitBanner has a Restart button that calls onRestart() — the no-op
// means the button renders but does nothing. UI-SPEC says "no Restart button
// for server-death case". Planner may choose to hide the button via props
// or wrap ExitBanner in a container that hides .eb-restart.
```

---

## V14 Socket Seams — Exact Injection Points

### Seam 1: `RunCommandBar.client?`

**File:** `apps/voss-app/src/org/cockpit/RunCommandBar.tsx`
**Interface:** `RunNativeClient { createSession(spec: RunSpec): Promise<{id: string}> }`
**Current behavior:** When `client` is undefined, `handleStart()` returns early with `setBlockReason('Voss runs need the Voss server — not available in this build.')` — the disabled-with-reason no-op.
**Injection:** Pass `runNativeClient` (wrapped adapter) as `client` prop on the `<RunCommandBar>` in `App.tsx`.
**Gate to remove:** None — the gate is `if (!props.client) { setBlockReason(...); return; }`. Keep the gate; just inject a real client so it's no longer triggered.

### Seam 2: `feedbackWritePath.dispatchFollowUp` FollowUpClient

**File:** `apps/voss-app/src/org/feedbackWritePath.ts`
**Interface:** `FollowUpClient { postMessage(sessionId: string, text: string): Promise<unknown> }`
**Current behavior:** `dispatchFollowUp` returns `{ disabled: true, reason: FOLLOWUP_DISABLED_REASON }` when `client` is undefined OR when `sessionNodeId` is not registered.
**Injection:** The drawer calls `dispatchFollowUp({ cardId, comment, client: followUpClient, hasNativePath: true })`. The `followUpClient` is constructed from the SDK. The planner needs to find where `CardDrawer` receives the `followUpClient` and inject it from App-level state.
**Note:** `hasNativePath` is currently `false` in V14 (gated). Set to `true` with a live client. [VERIFIED: codebase inspection of feedbackWritePath.ts line 53]

### Seam 3: `sseClient.connectLiveStream` stream source

**File:** `apps/voss-app/src/org/live/sseClient.ts`
**Current behavior:** `connectLiveStream` is never called with a real source. `liveLabel` permanently 'snapshot'.
**Injection:** After `createSession` returns a `sessionId`, call `connectLiveStream({ baseUrl, sessionId, token })`. Return the `LiveStreamHandle` for `abort()` on pane close/session end.
**Multi-session consideration:** Each native session gets its own `connectLiveStream` call. The module-level `liveLabel` needs to reflect the *selected* pane's session; per-pane `isLive` state is simpler and decoupled.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| raw EventSource for SSE | `subscribeToEvents` via fetch + EventSourceParserStream | V13.1 SDK | Never raw EventSource — cannot set Bearer header |
| Mock/disabled native client in RunCommandBar | Injected `RunNativeClient` from App mount | V15 (this phase) | Enables real session creation |
| PTY-only pane body | PTY + protocol pane mode (new in V15) | V15 (this phase) | Structured event rendering for native sessions |
| Snapshot-only `liveLabel` | Live SSE-backed label | V15 (this phase) | `connectLiveStream` now has a real stream source |

**Deprecated / changed:**
- `sseClient.ts: connectLiveStream` was never called in production before V15 (only in tests via mockSseStream). V15 makes it the real live path.

---

## Assumptions Log

> All findings in this research were verified by direct codebase inspection. The only non-verified claim is noted below.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SessionInfo` from `GET /session` carries enough data (id, title/task, age) for the sidebar list | VLIVE-06 / D-04 seam | Session list may have less data than expected; title field may need to be derived from the first `user` event or session file |
| A2 | `VossServe` is not `Sync` due to `tokio::process::Child` | Pitfall 2 | If `Child` is `Sync` in the Tauri runtime version, `Arc<VossServe>` would work — but `Mutex<HashMap>` is safer and should be used regardless |

**If this table is near-empty:** All critical claims were verified from codebase files read in this session.

---

## Open Questions (RESOLVED)

> All three questions are resolved by plan design (checker Dimension 11):
> A1 RESOLVED — Plan 05 T1 Wave-0 step inspects the live `GET /session` shape (read `voss/api/routes/session.py`); row accessors handle missing optional fields.
> A2 RESOLVED — Plan 02 T2 reads `CardDrawer.tsx` and threads `followUpClient` App → CockpitShell → CardDrawer.
> A3 RESOLVED — Plan 02 T2 sets `hasNativePath` from the native-card registration at the `dispatchFollowUp` call site.

1. **`SessionInfo` shape from `GET /session`**
   - What we know: `rest.ts` `listSessions()` returns `SessionInfo[]` typed as `JsonObject` (opaque). The spike's `http_get(port, "/session", Some(&token))` returned 200 but the body shape was not inspected.
   - What's unclear: Which fields `SessionInfo` carries — at minimum `id`, but `title`, `created_at`, `task` (from the first user event?) are needed for the sidebar.
   - Recommendation: The planner should add a VLIVE-06 Wave 0 task to inspect the live `GET /session` response shape (run `VOSS_SIDECAR_SPIKE=1 cargo test spike_spawn_handshake_authed_request_and_reap` and print the body, or read `voss/api/routes/session.py`). Design the sidebar to handle missing optional fields gracefully.

2. **CardDrawer `followUpClient` injection path**
   - What we know: `dispatchFollowUp` in `feedbackWritePath.ts` takes `client: FollowUpClient | undefined`. The drawer calls this function.
   - What's unclear: Where in `App.tsx` / `CockpitShell.tsx` the `followUpClient` prop is threaded to `CardDrawer`. This requires reading `CardDrawer.tsx` props to find the exact injection site.
   - Recommendation: The planner should read `CardDrawer.tsx` props before writing the App.tsx injection task. (Not blocking — the seam interface is clear; it's a prop-threading task.)

3. **`hasNativePath` flag in `dispatchFollowUp`**
   - What we know: `dispatchFollowUp` checks both `client` and `hasNativePath`. Currently hardcoded `false` somewhere upstream.
   - What's unclear: Whether `hasNativePath` is derived from the card's registration type or from a global flag.
   - Recommendation: Check where `dispatchFollowUp` is called in `CardDrawer.tsx` — the caller controls `hasNativePath`. With a live sidecar, native panes should pass `true`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `.venv/bin/python` with `voss` installed | VLIVE-01 sidecar spawn | ✓ (spike proven) | dev venv | `VOSS_PYTHON` override |
| `voss serve --port 0` capability | VLIVE-01 handshake | ✓ (spike proven, commit de93b4d) | v13.x | — |
| Vitest (jsdom) | VLIVE-08 TS tests | ✓ | 4.1.6 | — |
| `cargo test` with `VOSS_SIDECAR_SPIKE=1` | VLIVE-01/08 integration | ✓ | workspace | — |
| `tauri::State` + `Mutex` + `HashMap` | VLIVE-01 managed state | ✓ (already used for PtyRegistry, GridState) | workspace | — |

**Missing dependencies with no fallback:** None.

**Notes:** The test suite currently shows 77 failing / 387 passing tests (pre-V15). The failures are concentrated in `chords.test.ts` and `windowEffects.test.ts` — pre-existing failures unrelated to V15 scope. The V15 plan should not be blocked by these.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.6 + jsdom |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/ src/org/attention/__tests__/ src/org/cockpit/__tests__/` |
| Full suite command | `cd apps/voss-app && npx --no vitest run` |
| Rust integration test | `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core spike_spawn` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VLIVE-01 | Same-cwd double invoke reuses one server | integration (cargo) | `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core spike_spawn` | ✅ sidecar.rs |
| VLIVE-01 | Tauri command returns `ServeHandshake` | unit (vitest mock) | `npx --no vitest run src/.../__tests__/sidecar.test.ts` | ❌ Wave 0 |
| VLIVE-02 | RunCommandBar native path calls real createSession | unit (vitest) | `npx --no vitest run src/org/cockpit/__tests__/runCommandBar.test.tsx` | ✅ extends existing |
| VLIVE-03 | `permission.updated` → AttentionQueue row; `budget.updated` → overlay | unit (vitest) | `npx --no vitest run src/org/live/__tests__/sseClient.test.ts` | ✅ extends existing |
| VLIVE-03 | `liveLabel` = 'live' during stream, 'snapshot' after final | unit (vitest) | same | ✅ |
| VLIVE-04 | ProtocolPane renders header/tool/plan/stream/final per UI-SPEC | unit (vitest) | `npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx` | ❌ Wave 0 |
| VLIVE-04 | Out-of-set union member renders as generic row | unit (vitest) | same | ❌ Wave 0 |
| VLIVE-04 | PTY pane suite passes unmodified | regression (vitest) | `npx --no vitest run src/pane/__tests__/` | ✅ existing suite |
| VLIVE-05 | Permission gate renders + one reply clears both surfaces | unit (vitest) | `npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx` | ❌ Wave 0 |
| VLIVE-06 | Attach renders forward events; follow-up returns 202 | integration (stub-provider) | AC suite (new) | ❌ Wave 0 |
| VLIVE-07 | SIGKILL mid-run → label flip + ended state | integration (stub-provider) | AC suite (new) | ❌ Wave 0 |
| VLIVE-08 | AC suite passes with no provider credentials | integration (stub-provider) | AC suite (new) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `npx --no vitest run src/org/live/__tests__/ src/pane/__tests__/` (affected modules)
- **Per wave merge:** `npx --no vitest run` (full Vitest suite)
- **Phase gate:** Full Vitest green + cargo tests + AC suite before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx` — covers VLIVE-04, VLIVE-05
- [ ] `apps/voss-app/src/__tests__/sidecar.test.ts` (or extend existing) — VLIVE-01 Tauri command unit
- [ ] AC suite (integration) — covers VLIVE-06, VLIVE-07, VLIVE-08 with real `voss serve` + stub provider

---

## Security Domain

> `security_enforcement` not explicitly disabled in config.json (absent = enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (Bearer token) | `Authorization: Bearer {token}` — SDK middleware in `createAuthAndErrorMiddleware`; never stripped |
| V3 Session Management | partial | Token is ephemeral per sidecar spawn; no rotation mechanism needed (local loopback only) |
| V4 Access Control | partial | Auth enforced server-side (401 on missing Bearer — spike proven); no RBAC needed (single-user local) |
| V5 Input Validation | yes | `cwd` path passed to Tauri command: existing `is_safe_run_id` pattern; apply path validation to cwd |
| V6 Cryptography | no | loopback only, no TLS; token is random string generated by server |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `cwd` path traversal in Tauri command | Tampering | Canonicalize + check stays within allowed workspace roots; mirror `load_run` `is_safe_run_id` pattern |
| SSE stream injection (token theft) | Spoofing | Token is loopback-only; webview only connects to `127.0.0.1:{port}` — no cross-origin |
| Orphan server process after crash | Denial of service | `kill_on_drop` + `kill -0` reuse check covers crash paths |
| Permission gate bypass | Elevation of privilege | `replyPermission` POST requires valid Bearer; server enforces (spike confirmed 401 without token) |

---

## Sources

### Primary (HIGH confidence — direct codebase inspection)

- `crates/voss-app-core/src/sidecar.rs` — complete spawn/handshake/reap implementation
- `apps/voss-app/src-tauri/src/lib.rs` — all Tauri command patterns (managed state, generate_handler, async command structure)
- `sdk/typescript/src/client/rest.ts` — `createVossClient`, method signatures, `SessionInfo` type
- `sdk/typescript/src/client/sse.ts` — `subscribeToEvents` signature, Bearer header set via fetch not EventSource
- `sdk/typescript/src/client/permission.ts` — `replyPermission`, `PermissionChoice` type, body shape
- `apps/voss-app/src/org/cockpit/RunCommandBar.tsx` — `RunNativeClient` interface, injection seam, disabled-with-reason gate
- `apps/voss-app/src/org/feedbackWritePath.ts` — `FollowUpClient` interface, `dispatchFollowUp` signature
- `apps/voss-app/src/org/live/sseClient.ts` — `connectLiveStream`, `LiveStreamHandle`, `liveLabel`, `applyOverlay`
- `apps/voss-app/src/org/attention/attentionQueue.ts` — `ingestEvent`, `AttentionItem` type, dedup pattern
- `apps/voss-app/src/pane/PaneComponent.tsx` — `doSpawn` branch structure, `ExitBanner` integration
- `apps/voss-app/src/pane/ExitBanner.tsx` — `ExitBannerProps`, `Tier` type, visual language
- `apps/voss-app/src/org/model/bridge.ts` — `registerNativeCard`, `cardToSessionNode`, Bridge A/B patterns
- `apps/voss-app/src/App.tsx` (lines 290-385) — `handleLaunchAgent`, `splitFocused('H')`, `runBarResolvePaneId`
- `contracts/events.schema.json` — authoritative 21-member event union with field shapes
- `.planning/phases/V15-live-plane-integration/V15-SPIKE-sidecar.md` — proven measurements and env vars
- `.planning/phases/V15-live-plane-integration/V15-UI-SPEC.md` — complete visual contract, event coverage table
- `.planning/phases/V15-live-plane-integration/V15-CONTEXT.md` — locked decisions D-01..D-12
- `.planning/phases/V15-live-plane-integration/V15-SPEC.md` — 8 locked requirements with acceptance criteria

### Secondary (HIGH confidence — tests as specification)

- `apps/voss-app/src/org/live/__tests__/sseClient.test.ts` — mock stream pattern, test structure for extension
- `apps/voss-app/src/org/live/__tests__/mockSseStream.ts` — `MockAgentEvent` type, dual correlation key pattern
- `apps/voss-app/src/org/cockpit/__tests__/runCommandBar.test.tsx` — `RunNativeClient` mock injection pattern

---

## Metadata

**Confidence breakdown:**
- Sidecar API (VLIVE-01): HIGH — complete source read, spike proven
- SDK surface (VLIVE-02/03/05): HIGH — complete source read
- V14 socket seams: HIGH — complete source read including injection seam signatures
- Event union (VLIVE-04): HIGH — contracts/events.schema.json authoritative
- Grid insertion path (D-02): HIGH — App.tsx lines 362-385 exact code read
- Test infrastructure: HIGH — vitest.config.ts + existing test patterns verified
- SessionInfo shape (VLIVE-06): LOW — `listSessions()` returns opaque `JsonObject`

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (stable stack; protocol/SDK frozen; 30 days conservative)

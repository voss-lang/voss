# Phase V15: Live Plane Integration - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `apps/voss-app/src-tauri/src/lib.rs` | config/command | request-response | self (extend: `spawn_agent` command) | exact |
| `crates/voss-app-core/src/sidecar.rs` | service | request-response | self (no change) | frozen |
| `apps/voss-app/src/App.tsx` | provider | request-response | self (extend: `handleLaunchAgent` pattern) | exact |
| `apps/voss-app/src/pane/ProtocolPane.tsx` | component | event-driven | `apps/voss-app/src/pane/PaneComponent.tsx` | role-match |
| `apps/voss-app/src/pane/ProtocolPane.css` | config | — | `apps/voss-app/src/pane/pane.css` | role-match |
| `apps/voss-app/src/pane/PaneComponent.tsx` | component | event-driven | self (extend: `doSpawn` branch) | exact |
| `apps/voss-app/src/org/cockpit/CockpitSidebar.tsx` | component | CRUD | self (extend: add Server sessions section) | exact |
| `apps/voss-app/src/org/cockpit/serverSessions.ts` | service | CRUD | `apps/voss-app/src/org/live/sseClient.ts` | role-match |
| `apps/voss-app/src/org/live/sseClient.ts` | service | event-driven | self (extend: per-session dispatch) | exact |
| `apps/voss-app/src/org/attention/attentionQueue.ts` | service | event-driven | self (extend: `resolveAttentionItem`) | exact |

---

## Pattern Assignments

### `apps/voss-app/src-tauri/src/lib.rs` — EDIT: add `start_voss_serve` command

**Analog:** same file, `spawn_agent` command (line 183) and the `run()` builder (lines 1297–1373)

**Imports pattern** (lines 1–31, existing; add these to the use block):
```rust
use std::collections::HashMap;
// std::sync::Mutex already imported (line 5)
use voss_app_core::sidecar::{spawn_voss_serve, python_path, ServeHandshake, VossServe};
```

**Managed-state type alias pattern** (copy from existing `AgentDb`/`Reg` aliases, ~line 130):
```rust
// Existing aliases for reference — add analogous VossServeMap:
type AgentDb<'a> = tauri::State<'a, Mutex<Option<Connection>>>;
type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;

// NEW — add before run():
type VossServeMap<'a> = tauri::State<'a, Mutex<HashMap<String, VossServe>>>;
```

**Core command pattern** (analog: `spawn_agent` lines 183–222):
```rust
// spawn_agent shows the exact async #[tauri::command] structure to copy:
#[tauri::command]
#[allow(clippy::too_many_arguments)]
async fn spawn_agent(
    on_data: tauri::ipc::Channel<PtyEvent>,
    ...
    pty_state: Reg<'_>,
) -> Result<String, String> {
    // ...lock, operate, return Ok(value) or Err(e.to_string())
}

// NEW command following this EXACT structure:
#[tauri::command]
async fn start_voss_serve(
    cwd: String,
    state: VossServeMap<'_>,
) -> Result<ServeHandshake, String> {
    // reuse-if-alive check (Pitfall 5: pid() returns None after child reaped)
    {
        let map = state.lock().map_err(|_| "lock poisoned".to_string())?;
        if let Some(serve) = map.get(&cwd) {
            if serve.pid().is_some() {
                return Ok(serve.handshake.clone());
            }
        }
    }
    // stale entry removed, fresh spawn
    let python = python_path();
    let serve = spawn_voss_serve(&python, std::path::Path::new(&cwd))
        .await
        .map_err(|e| e.to_string())?;
    let handshake = serve.handshake.clone();
    state.lock().map_err(|_| "lock poisoned".to_string())?
        .insert(cwd, serve);
    Ok(handshake)
}
```

**`.manage()` registration pattern** (lines 1302–1305, existing):
```rust
// Existing .manage() calls show the pattern:
.manage(Arc::new(PtyRegistry::default()))
.manage(Mutex::new(GridState::default()))
.manage(Mutex::new(None::<Connection>))
.manage(SwarmWatchState::default())

// NEW — add one more .manage() before .invoke_handler():
.manage(Mutex::new(HashMap::<String, VossServe>::new()))
```

**`generate_handler!` registration pattern** (lines 1307–1370):
```rust
// The handler list shows the pattern — add start_voss_serve to the end:
tauri::generate_handler![
    get_theme_overrides,
    spawn_pty,
    // ... existing 40+ handlers ...
    run_decision,
    start_voss_serve,  // NEW — add here
]
```

**Error handling pattern** (consistent across all commands):
```rust
// All commands use .map_err(|e| e.to_string()) — never custom error types.
// Lock poison: .map_err(|_| "lock poisoned".to_string())
// Spawn error: .await.map_err(|e| e.to_string())?
```

---

### `crates/voss-app-core/src/sidecar.rs` — NO CHANGE

**Status:** Frozen — spike is the production home. The Tauri command in `lib.rs` wraps it.

**Key APIs the Tauri command calls** (lines 54–130):
```rust
// python_path() — resolves VOSS_PYTHON > .venv/bin/python > python3
pub fn python_path() -> String { ... }

// spawn_voss_serve(python, cwd) — spawns, drains stderr, parses handshake (60s)
pub async fn spawn_voss_serve(python: &str, cwd: &std::path::Path) -> anyhow::Result<VossServe>

// VossServe.pid() — returns None after child reaped (critical for reuse-if-alive check)
pub fn pid(&self) -> Option<u32> { self.child.id() }

// ServeHandshake — {port: u16, token: String}, #[derive(Clone, Serialize, Deserialize)]
// Fields are lowercase single words — no camelCase/snake_case IPC surprise (Pitfall 7)
```

---

### `apps/voss-app/src/App.tsx` — EDIT: sidecar invoke + client construction + socket injection

**Analog:** same file — `handleLaunchAgent` + `runBarResolvePaneId` + `runBarSpawnAgent` (lines 296–385)

**Imports to add** (copy the invoke + signal pattern from lines 1–12):
```typescript
// Already imported: invoke, createEffect, createSignal, onMount, batch
// Add imports:
import { createVossClient, type VossClient } from '../../../sdk/typescript/src/client/rest';
import { connectLiveStream } from './org/live/sseClient';
import type { RunNativeClient } from './org/cockpit/RunCommandBar';
import type { FollowUpClient } from './org/feedbackWritePath';
import type { ServeHandshake } from './types'; // or inline: {port: number; token: string}
```

**Workspace-level sidecar signal pattern** (mirror the per-workspace `agentConfigByPaneId` map in WorkspaceRecord, ~line 358):
```typescript
// Existing per-workspace state pattern (WorkspaceRecord stores maps):
ws.setAgentConfigByPaneId({ ...ws.agentConfigByPaneId(), [newId]: cfg });

// NEW — analogous per-workspace sidecar client signal (add to workspace store or App-level):
// NOTE: one client per workspace cwd — reuse across panes (RESEARCH recommendation)
const [vossClient, setVossClient] = createSignal<VossClient | null>(null);
const [serveHandshake, setServeHandshake] = createSignal<{port: number; token: string} | null>(null);
```

**Core invoke + client construction pattern** (analog: `runBarResolvePaneId` + invoke at lines 365–385):
```typescript
// Existing invoke pattern for reference:
// invoke('spawn_agent', { cliBinary: ..., cliArgs: ..., ... })

// NEW — after native run intent, before pane insertion:
const handshake = await invoke<{port: number; token: string}>('start_voss_serve', { cwd });
const baseUrl = `http://127.0.0.1:${handshake.port}`;
const client = createVossClient(baseUrl, handshake.token);
setVossClient(client);
setServeHandshake(handshake);

// Adapter (Pitfall 1 — SDK returns string, RunNativeClient expects {id: string}):
const runNativeClient: RunNativeClient = {
  createSession: async (spec) => ({ id: await client.createSession(spec.goal) }),
};

// followUpClient (matches FollowUpClient interface from feedbackWritePath.ts):
const followUpClient: FollowUpClient = {
  postMessage: (sessionId, text) => client.postMessage(sessionId, text),
};
```

**Grid insertion pattern for native panes** (lines 318–358 — `handleLaunchAgent`):
```typescript
// Exact D-02 path to copy for native run pane insertion:
const before = ctrl.snapshot().focusedId;
ctrl.splitFocused('H');
const newId = ctrl.snapshot().focusedId;
if (newId === before) return; // GRD-05 floor — split rejected

// For native panes: store sessionId in a new per-pane map (analog to agentConfigByPaneId):
ws.setNativeSessionByPaneId({ ...ws.nativeSessionByPaneId(), [newId]: sessionId });
// Then call connectLiveStream for the new session (VLIVE-03):
const handle = connectLiveStream({ baseUrl, sessionId, token: handshake.token });
```

**CardDrawer followUpClient injection** (CockpitShell.tsx line 295 — `<CardDrawer />`):
```typescript
// Currently: <CardDrawer />
// V15 change: pass followUpClient prop (CardDrawer.tsx line 114 shows the prop exists):
//   followUpClient?: FollowUpClient  — already declared, just needs a value
// Thread it from App-level vossClient signal:
<CardDrawer followUpClient={followUpClient()} />
// CockpitShell needs a followUpClient prop threaded from App.tsx
```

---

### `apps/voss-app/src/pane/ProtocolPane.tsx` — NEW component

**Analog:** `apps/voss-app/src/pane/PaneComponent.tsx` (role: component; data flow: event-driven)
**Secondary analog:** `apps/voss-app/src/org/live/sseClient.ts` (for-await pattern)

**Imports pattern** (copy from PaneComponent.tsx lines 1–44, adapt):
```typescript
import { createSignal, For, Show, onCleanup } from 'solid-js';
import type { AgentEvent } from '../../../../sdk/typescript/src/client/sse';
import { connectLiveStream, type LiveStreamHandle } from '../org/live/sseClient';
import { ingestEvent } from '../org/attention/attentionQueue';
import { replyPermission, type PermissionChoice } from '../../../../sdk/typescript/src/client/permission';
import type { VossClient } from '../../../../sdk/typescript/src/client/rest';
import ExitBanner from './ExitBanner';
import './ProtocolPane.css';
```

**Props interface pattern** (copy from PaneComponent.tsx `PaneProps` at lines 45–62):
```typescript
// PaneComponent uses a flat PaneProps interface — copy the pattern:
export interface PaneProps { id?: string; cwd?: string; ... }

// NEW ProtocolPane props:
export interface ProtocolPaneProps {
  sessionId: string;
  baseUrl: string;
  token: string;
  client: VossClient;
  onEnded?: () => void;
}
```

**Local signal pattern** (copy sseClient.ts lines 41–55 BUT make signals LOCAL, not module-level):
```typescript
// CRITICAL: sseClient.ts uses module-level signals (line 41-55) — that's for
// GLOBAL state. ProtocolPane needs LOCAL per-pane signals (one per instance):
export default function ProtocolPane(props: ProtocolPaneProps) {
  // Local signals — NEVER module-level for per-pane transcript (RESEARCH Pitfall 4)
  const [events, setEvents] = createSignal<AgentEvent[]>([]);
  const [bootState, setBootState] = createSignal<'booting' | 'live' | 'ended' | 'error'>('booting');
  const [isLive, setIsLive] = createSignal(false);

  // D-08: CAP = 300 events; trim-oldest but pin permission.updated (pending) + first user event
  const CAP = 300;
  const appendEvent = (ev: AgentEvent) => {
    setEvents((prev) => {
      const next = [...prev, ev];
      if (next.length <= CAP) return next;
      // Trim oldest, skipping pinned rows (pending permission + first user)
      const pinned = (e: AgentEvent) =>
        (e.type === 'permission.updated') ||
        (e.type === 'user' && prev.indexOf(e) === 0);
      const trimIdx = next.findIndex((e) => !pinned(e));
      return trimIdx === -1 ? next : [...next.slice(0, 0), ...next.slice(trimIdx + 1)];
    });
  };
```

**SSE for-await pattern** (copy sseClient.ts `connectLiveStream` lines 136–164):
```typescript
// sseClient.ts connectLiveStream shows the exact for-await + abort pattern:
const ac = new AbortController();
void (async () => {
  try {
    for await (const ev of stream) {
      if (ac.signal.aborted) break;
      ingestEvent(ev, { cardId: props.sessionId }); // pass cardId context (Pitfall 3)
      applyOverlay(ev);
      appendEvent(ev);
      // Handle specific lifecycle events:
      if (ev.type === 'session.idle' || ev.type === 'final') {
        setBootState('ended'); setIsLive(false);
      }
    }
  } catch { /* stream ended / aborted — degrade, never throw */ }
  finally { setBootState('ended'); setIsLive(false); }
})();
// onCleanup: ac.abort()
```

**ExitBanner reuse pattern** (D-11, from ExitBanner.tsx lines 1–31):
```typescript
// ExitBanner props: { exitCode: number, onRestart: () => void }
// D-11: server death → ended state in transcript flow (not position:absolute)
// Planner note: ExitBanner shows a "Restart" button via onRestart().
// For server-death case, onRestart should re-invoke start_voss_serve.
// UI-SPEC says no Restart button for server-death — either pass no-op or
// add a showRestart prop to ExitBanner (one-line change).
<Show when={bootState() === 'ended'}>
  <ExitBanner exitCode={1} onRestart={() => {}} />
</Show>
```

**Error handling pattern** (copy from PaneComponent.tsx signal guard):
```typescript
// PaneComponent uses Show guards + signal-driven rendering — copy this:
<Show when={bootState() === 'error'}>
  <div class="proto-error">
    <p>{errorMsg()}</p>
    <button type="button" onClick={retry}>Retry</button>
  </div>
</Show>
```

**Immutable signal update rule** (sseClient.ts lines 46–51):
```typescript
// NEVER produce() or structuredClone() — copy mergeOverlay's immutable spread:
setLiveOverlay((prev) => ({ ...prev, [key]: { ...prev[key], ...patch } }));
// For ProtocolPane event list — use spread, not mutation:
setEvents((prev) => [...prev, ev]);
```

---

### `apps/voss-app/src/pane/PaneComponent.tsx` — EDIT: add 3rd `doSpawn` branch

**Analog:** self — `doSpawn` function at lines 284–313

**Existing `doSpawn` branch pattern** (lines 284–313 — copy structure, add 3rd branch):
```typescript
const doSpawn = async (t: Terminal) => {
  if (props.agentConfig) {
    if (props.agentConfig.managed) {
      // Branch 1: managed PTY agent
      await transport!.spawnManagedAgent({ ... });
    } else {
      // Branch 2: unmanaged PTY agent
      await transport!.spawnAgent({ ... });
    }
  } else {
    // Branch 3 (existing): plain shell
    await transport!.spawn({ rows: t.rows, cols: t.cols, cwd: props.cwd });
  }
  setDot('running');
};

// NEW Branch pattern — add BEFORE the else clause (protocol panes skip PTY entirely):
// The discriminator: props.nativeSessionId is set for protocol panes (no agentConfig)
if (props.nativeSessionId) {
  // No PTY spawn — ProtocolPane handles its own stream via connectLiveStream.
  // doSpawn is a no-op for protocol panes; the pane body switches to ProtocolPane.
  setDot('running');
  return;
}
```

**Props extension pattern** (copy from `PaneProps` at lines 45–62):
```typescript
// Add one discriminator prop to PaneProps (minimal extension):
export interface PaneProps {
  // ... existing props ...
  /**
   * When set, this pane renders ProtocolPane instead of xterm PTY.
   * Value is the server session id for the native run.
   */
  nativeSessionId?: string;
  /** Client needed by ProtocolPane for permission replies and follow-up. */
  nativeClient?: VossClient;
  /** Handshake fields for ProtocolPane's connectLiveStream call. */
  nativeBaseUrl?: string;
  nativeToken?: string;
}
```

**Show guard pattern for conditional body** (copy from lines 584–668):
```typescript
// PaneComponent uses <Show when={props.agentConfig}> for conditional chrome sections.
// Apply same pattern to switch body between PTY and protocol:
<Show when={props.nativeSessionId} fallback={<div ref={bodyRef} class="pane-body">...</div>}>
  <ProtocolPane
    sessionId={props.nativeSessionId!}
    baseUrl={props.nativeBaseUrl!}
    token={props.nativeToken!}
    client={props.nativeClient!}
    onEnded={() => setExitCode(1)}
  />
</Show>
```

---

### `apps/voss-app/src/org/cockpit/CockpitSidebar.tsx` — EDIT: add Server sessions section

**Analog:** self — existing three sections at lines 1–200 (exact-match extension)

**Section structure pattern** (lines 62–100 — `sessionsOpen` collapsible):
```typescript
// CockpitSidebar already has a collapsible "Sessions / Run Lineage" section
// using createSignal(false) + a toggle button. Copy this exact pattern:
const [sessionsOpen, setSessionsOpen] = createSignal(false);
// ...
<button class="cs-section__toggle" onClick={() => setSessionsOpen((v) => !v)}>
  SESSIONS · RUN LINEAGE <span class="cs-caret">{sessionsOpen() ? '▾' : '▸'}</span>
</button>
<Show when={sessionsOpen()}>
  <SessionTreePanel ... />
</Show>

// NEW "Server sessions" section uses the SAME pattern:
const [serverSessionsOpen, setServerSessionsOpen] = createSignal(false);
// Expose as a fourth section after existing three.
```

**Props extension pattern** (lines 62–65 — props interface):
```typescript
// Current props: { data: RunData | null; swarm: SwarmReconcileResult }
// Add V15 client for session listing and attach:
export default function CockpitSidebar(props: {
  data: RunData | null;
  swarm: SwarmReconcileResult;
  vossClient?: ReturnType<typeof createVossClient>; // optional — no client = section hidden
  onAttach?: (sessionId: string) => void;           // callback to App.tsx to open a pane
})
```

**List rendering pattern** (lines 80–115 — external agents list):
```typescript
// Existing external agents list uses For + createMemo for reactive data.
// Copy this for session list:
const externalRows = createMemo<ExternalRow[]>(() => { ... });
// <For each={externalRows()}>{(row) => <div class="cs-arow">...</div>}</For>

// NEW session list follows identical pattern:
// sessions() is loaded via createResource or createSignal fed by listSessions().
```

---

### `apps/voss-app/src/org/cockpit/serverSessions.ts` — NEW (optional extraction)

**Analog:** `apps/voss-app/src/org/live/sseClient.ts` (module-level signal + exported function)

**Module pattern** (copy from sseClient.ts lines 21–55):
```typescript
// sseClient.ts is the closest analog: module-level signal + exported functions.
// serverSessions.ts follows the SAME structure:
import { createSignal } from 'solid-js';
import type { VossClient, SessionInfo } from '../../../../sdk/typescript/src/client/rest';

const [serverSessions, setServerSessions] = createSignal<SessionInfo[]>([]);
const [loading, setLoading] = createSignal(false);

export async function refreshSessions(client: VossClient): Promise<void> {
  setLoading(true);
  try {
    const list = await client.listSessions();
    setServerSessions(list);
  } catch { /* degrade silently — no sessions shown */ }
  finally { setLoading(false); }
}

export { serverSessions, loading };
```

**Test-reset pattern** (copy from sseClient.ts lines 173–176):
```typescript
// Every module-level signal needs a test-only reset (mirrors __resetLiveStream):
export function __resetServerSessions(): void {
  setServerSessions([]);
  setLoading(false);
}
```

---

### `apps/voss-app/src/org/live/sseClient.ts` — EDIT: per-session ProtocolPane dispatch

**Analog:** self (extend the `connectLiveStream` call to also push to per-pane transcript signals)

**Current `connectLiveStream` core loop** (lines 136–164):
```typescript
// connectLiveStream already calls ingestEvent + applyOverlay.
// V15 adds a third sink: per-session event dispatch for ProtocolPane.
// The simplest approach: add an optional onEvent callback to ConnectLiveStreamArgs:
export interface ConnectLiveStreamArgs {
  baseUrl: string;
  sessionId: string;
  token: string;
  stream?: AsyncIterable<AgentEvent>;
  /** Optional per-pane sink for ProtocolPane transcript (VLIVE-04). */
  onEvent?: (ev: AgentEvent) => void;
}

// In the for-await loop (line 146-149), add:
if (args.onEvent) args.onEvent(ev);
```

**liveLabel multi-session pattern** (lines 55 + 142 — module-level `setLiveLabel`):
```typescript
// Current: module-level liveLabel reflects LAST connected session (Pitfall 4).
// V15 fix: module-level liveLabel reflects SELECTED pane's session liveness.
// ProtocolPane tracks its own isLive signal internally.
// The module-level liveLabel should only be set from connectLiveStream when
// that session belongs to the focused/selected pane.
// Simplest: keep module-level liveLabel as-is for statusbar; add a session-keyed
// map of live handles so App.tsx can query isLive(sessionId):
const [liveHandles, setLiveHandles] = createSignal<Set<string>>(new Set());
// Insert sessionId on connect; delete on finally (immutable Set spread):
setLiveHandles((prev) => new Set([...prev, args.sessionId]));
// In finally: setLiveHandles((prev) => { const s = new Set(prev); s.delete(args.sessionId); return s; });
```

---

### `apps/voss-app/src/org/attention/attentionQueue.ts` — EDIT: add `resolveAttentionItem`

**Analog:** self — `pushItem` at lines 83–88 (exact mirror)

**`pushItem` pattern to copy** (lines 83–88):
```typescript
// pushItem uses immutable spread + dedup check — resolveItem is the inverse:
function pushItem(item: AttentionItem): void {
  setAttentionQueue((prev) => {
    if (prev.some((existing) => existing.id === item.id)) return prev;
    return [...prev, item];
  });
}

// NEW resolveAttentionItem (mirror pushItem — filter instead of append):
export function resolveAttentionItem(id: string): void {
  setAttentionQueue((prev) => prev.filter((item) => item.id !== id));
}
```

**Permission event id format** (lines 159–173 — `ingestEvent` permission branch):
```typescript
// The id stored for permission items is: `permission:${ev.id}` (line 159)
// resolveAttentionItem must be called with the SAME format:
resolveAttentionItem(`permission:${permissionEvent.id}`);
// NOT just ev.id — the prefix is load-bearing for dedup.
```

---

## Shared Patterns

### Tauri IPC: `invoke` call site
**Source:** `apps/voss-app/src/App.tsx` line 1; `RunCommandBar.tsx` line 7
**Apply to:** `App.tsx` new sidecar invoke
```typescript
import { invoke } from '@tauri-apps/api/core';
// Usage: const result = await invoke<ReturnType>('command_name', { camelCaseArgs });
// All Tauri command args are camelCase in TS; lib.rs receives them as snake_case.
// ServeHandshake fields (port, token) are single lowercase words — no rename needed.
```

### Solid signal immutability (no `produce`, no `structuredClone`)
**Source:** `apps/voss-app/src/org/live/sseClient.ts` lines 46–51; `bridge.ts` lines 74–78
**Apply to:** all new signal-backed state in ProtocolPane, serverSessions.ts, attentionQueue edit
```typescript
// ALWAYS use spread for signal updates — never mutation:
setFoo((prev) => ({ ...prev, [key]: newVal }));      // Record update
setBar((prev) => [...prev, newItem]);                 // Array append
setBar((prev) => prev.filter((x) => x.id !== id));  // Array remove
// NEVER: prev[key] = newVal; setFoo(prev);
// NEVER: produce((draft) => { draft[key] = newVal; });
// NEVER: structuredClone(prev);
```

### Module-level signal + test-reset pattern
**Source:** `attentionQueue.ts` lines 76 + 348–350; `sseClient.ts` lines 41 + 173–176; `bridge.ts` lines 63 + 104–107
**Apply to:** `serverSessions.ts` (new); any new module-level signals
```typescript
// Pattern: module-level signal, exported accessor, test-only reset function
const [foo, setFoo] = createSignal<T>(initialValue);
export { foo };
export function __resetFoo(): void { setFoo(initialValue); }
// Tests: afterEach(() => { __resetFoo(); });
```

### Disabled-with-reason discipline
**Source:** `RunCommandBar.tsx` lines 137–180 (`handleStart` native path); `feedbackWritePath.ts` lines 46–58
**Apply to:** `ProtocolPane` permission gate (disabled while request in-flight), `serverSessions` attach button
```typescript
// Pattern: if condition not met, set blockReason (never silent no-op):
if (!props.client) {
  setBlockReason('Voss runs need the Voss server — not available in this build.');
  return;
}
// Render blockReason inline (never hide the affordance — show WHY it is disabled):
<Show when={blockReason()}>
  <span class="rcb-block-reason" role="alert">{blockReason()}</span>
</Show>
```

### `ingestEvent` context (cardId for permission.updated)
**Source:** `attentionQueue.ts` lines 127–136; RESEARCH Pitfall 3
**Apply to:** every `connectLiveStream` call that may emit `permission.updated`
```typescript
// CRITICAL: permission.updated has no session_id — must pass cardId via context:
ingestEvent(ev, { cardId: boundCardId });
// Without context: deepLink has no paneId, AttentionQueue row has no focus target.
// boundCardId = the sessionId returned by createSession (Bridge A: cardId === sessionNodeId)
```

### `registerNativeCard` Bridge A pattern
**Source:** `bridge.ts` lines 80–88; `RunCommandBar.tsx` native start path
**Apply to:** App.tsx after `createSession` returns a session id
```typescript
// Bridge A: store create-response id directly — it IS the session node id (A1 finding):
registerNativeCard(sessionId, sessionId);
// Both args are the same id (not a mistake).
// This makes the card visible to: cardToSessionNode, resolveCard, nativeSessionNodeId, ingestEvent lookup
```

---

## No Analog Found

No files in V15 are fully without analog. All new files have a close role-match or exact-match in the codebase.

---

## Metadata

**Analog search scope:** `apps/voss-app/src/`, `apps/voss-app/src-tauri/src/`, `crates/voss-app-core/src/`, `sdk/typescript/src/`
**Files read:** 20 source files
**Pattern extraction date:** 2026-06-09

**Critical seams verified from source:**
- `doSpawn` branch structure: `PaneComponent.tsx` lines 284–313 (two-branch today; third slot confirmed open)
- `CardDrawer.followUpClient` prop: `CardDrawer.tsx` line 114 (prop declared, not yet wired from shell)
- `CockpitShell` passes `<CardDrawer />` with no props: `CockpitShell.tsx` line 295 (injection point)
- `connectLiveStream` args: `sseClient.ts` lines 111–121 (onEvent not yet in args — must be added)
- `attentionQueue` has no `resolveItem`: confirmed by full read — only `pushItem` exists
- `ServeHandshake` IPC shape: `sidecar.rs` lines 22–26 (fields `port`, `token` — no camelCase surprise)
- `createSession` return type mismatch: `rest.ts` lines 49–61 returns `string`; `RunNativeClient.createSession` expects `Promise<{id: string}>` — adapter required at injection point

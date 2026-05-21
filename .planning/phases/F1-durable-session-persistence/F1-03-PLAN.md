---
phase: F1-durable-session-persistence
plan: 03
type: execute
wave: 2
depends_on: [F1-01, F1-02]
files_modified:
  - apps/voss-app/src/workspaces/workspaceSessionPersist.ts
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/pane/pty-ipc.ts
autonomous: false
requirements: [FPRS-04, FPRS-05]

must_haves:
  truths:
    - "On boot, active registry entries are queried and passed as agentConfig to GridRoot"
    - "Agent panes spawn via spawn_agent instead of spawn_pty on restore"
    - "On quit, close-requested handler updates last_seen on all active registry rows"
    - "PTY exit event triggers mark_agent_stopped IPC call"
    - "Orphan sweep runs after boot restore and marks unmatched active rows as stopped"
    - "Shell panes (no agentConfig) spawn as plain shells on restore"
  artifacts:
    - path: "apps/voss-app/src/workspaces/workspaceSessionPersist.ts"
      provides: "Registry last_seen update in close-requested handler (D-09)"
      contains: "update_agents_last_seen"
    - path: "apps/voss-app/src/App.tsx"
      provides: "Boot restore registry query + agentConfigByPaneId prop injection + orphan sweep (D-04, D-11)"
      contains: "get_active_agents"
    - path: "apps/voss-app/src/pane/pty-ipc.ts"
      provides: "Agent exit callback invokes mark_agent_stopped (D-10)"
      contains: "mark_agent_stopped"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/grid/GridRoot.tsx"
      via: "agentConfigByPaneId prop"
      pattern: "agentConfigByPaneId"
    - from: "apps/voss-app/src/workspaces/workspaceSessionPersist.ts"
      to: "Rust update_agents_last_seen"
      via: "invoke IPC"
      pattern: "update_agents_last_seen"
    - from: "apps/voss-app/src/pane/pty-ipc.ts"
      to: "Rust mark_agent_stopped"
      via: "invoke IPC on exit event"
      pattern: "mark_agent_stopped"
---

<objective>
Wire the boot restore orchestration, quit lifecycle, and PTY exit hooks that make agent session persistence end-to-end: on boot, query the registry and pass agent configs to panes; on quit, mark last_seen; on agent exit, mark stopped; after restore, sweep orphans.

Purpose: This is the integration plan that makes F1 functional. Plans 01 and 02 built the components; this plan connects them into the full restart lifecycle described in SPEC FPRS-04 and FPRS-05.

Output: Full agent restart loop working: quit with agent panes -> relaunch -> agents auto-restart with correct session IDs and cwd. Shell panes unaffected.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F1-durable-session-persistence/F1-SPEC.md
@.planning/phases/F1-durable-session-persistence/F1-CONTEXT.md
@.planning/phases/F1-durable-session-persistence/F1-RESEARCH.md
@.planning/phases/F1-durable-session-persistence/F1-PATTERNS.md
@.planning/phases/F1-durable-session-persistence/F1-01-SUMMARY.md
@.planning/phases/F1-durable-session-persistence/F1-02-SUMMARY.md

<interfaces>
<!-- Key types and contracts the executor needs — from Plan 01 and Plan 02 outputs. -->

From apps/voss-app/src/pane/pty-ipc.ts (Plan 02):
```typescript
export interface AgentConfig {
  cliBinary: string;
  cliArgs: string[];
  sessionId: string;
}

export class PtyTransport {
  async spawnAgent(o: {
    rows: number; cols: number; cwd?: string;
    paneId: string; workspacePath?: string;
  } & AgentConfig): Promise<string>;
  // onExit callback already exists via PtyTransportOpts
}
```

From apps/voss-app/src/grid/GridRoot.tsx (Plan 02):
```typescript
export default function GridRoot(props: {
  // ... existing props ...
  agentConfigByPaneId?: Record<string, AgentConfig>;
  workspacePath?: string;
})
```

From Rust (Plan 01 — Tauri commands available via invoke):
- `invoke('get_active_agents', { workspacePath })` -> `AgentEntry[]`
- `invoke('mark_agent_stopped', { paneId, workspacePath })` -> void
- `invoke('update_agents_last_seen', { workspacePath })` -> void
- `invoke('sweep_orphan_agents', { validPaneIds, workspacePath })` -> number

AgentEntry shape (from Rust serde camelCase):
```typescript
interface AgentEntry {
  paneId: string;
  sessionId: string;
  cliBinary: string;
  cliArgs: string; // JSON text
  cwd: string;
  status: string;
  lastSeen: number;
}
```

From apps/voss-app/src/workspaces/workspaceSessionPersist.ts:
```typescript
export async function installAllWorkspacesCloseSave(
  getContexts: () => WorkspaceSessionContext[],
  getIndex: () => WorkspacesIndex,
  saveIndex: (index: WorkspacesIndex) => Promise<void>,
): Promise<() => void>
// Close handler flow: preventDefault -> scrollback -> save sessions -> save index -> close
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: PTY exit hook + close-requested lifecycle + boot restore orchestration</name>
  <files>
    apps/voss-app/src/pane/pty-ipc.ts
    apps/voss-app/src/workspaces/workspaceSessionPersist.ts
    apps/voss-app/src/App.tsx
  </files>
  <read_first>
    apps/voss-app/src/pane/pty-ipc.ts
    apps/voss-app/src/pane/PaneComponent.tsx
    apps/voss-app/src/workspaces/workspaceSessionPersist.ts
    apps/voss-app/src/App.tsx
    apps/voss-app/src/grid/GridRoot.tsx
    apps/voss-app/src/grid/SplitNode.tsx
    apps/voss-app/src/grid/tree.ts
  </read_first>
  <action>
    Three integration wiring changes, one per file:

    **1. pty-ipc.ts — Agent exit callback (per D-10):**

    Add an optional `agentPaneId?: string` property to `PtyTransportOpts` interface. When a PtyTransport is created for an agent pane, the caller (PaneComponent) passes the pane ID.

    Add an optional `workspacePath?: string` property to `PtyTransportOpts`.

    In the `handle` method's `'exit'` case, AFTER calling `this.opts.onExit?.(ev.code)`, add: if `this.opts.agentPaneId` is defined, fire `invoke('mark_agent_stopped', { paneId: this.opts.agentPaneId, workspacePath: this.opts.workspacePath ?? null }).catch((e) => console.error('[voss-app] agent registry exit update failed:', e))`. This is best-effort (per Pitfall 5 pattern — never block on registry failure).

    Update PaneComponent.tsx where the PtyTransport constructor is called: if `props.agentConfig` is defined, pass `agentPaneId: props.id, workspacePath: props.workspacePath` in the PtyTransportOpts. If no agentConfig, omit these (existing behavior unchanged).

    **2. workspaceSessionPersist.ts — Close-requested registry update (per D-09, FPRS-05):**

    Import `invoke` from `@tauri-apps/api/core`.

    Add a 4th parameter to `installAllWorkspacesCloseSave`: `getWorkspacePath?: () => string | null`. This is optional to avoid breaking existing call sites.

    In the close-requested handler, AFTER `await saveIndex(getIndex())` and BEFORE `isClosingAfterSave = true`, add:

    ```
    // F1 D-09: update agent registry last_seen timestamps (best-effort)
    await invoke('update_agents_last_seen', {
      workspacePath: getWorkspacePath?.() ?? null,
    }).catch((e) => console.error('[voss-app] agent registry quit update failed:', e));
    ```

    This must be inside the existing try block, AFTER `await saveIndex(getIndex())`. It is best-effort: `.catch()` logs but does not prevent window close (per Pitfall 5, RESEARCH).

    **3. App.tsx — Boot restore registry query + orphan sweep (per D-04, D-05, D-11):**

    Import `invoke` from `@tauri-apps/api/core`. Import `AgentConfig` from `./pane/pty-ipc`.

    Find the workspace restore path where `initialSession` is resolved before GridRoot mounts. The exact location depends on how A8 structured the workspace mounting — look for where `loadSession` or `loadProjectLessSession` result is passed to GridRoot as `initialSession`.

    Add a helper function `fetchAgentConfigs(workspacePath: string | null): Promise<Record<string, AgentConfig>>`:
    - Call `invoke<AgentEntry[]>('get_active_agents', { workspacePath })` with `.catch(() => [])` fallback
    - Convert the result into a `Record<string, AgentConfig>` keyed by `paneId`: for each entry, `{ cliBinary: entry.cliBinary, cliArgs: JSON.parse(entry.cliArgs), sessionId: entry.sessionId }`
    - Return the record

    In the workspace restore flow, AFTER session load completes but BEFORE GridRoot mounts:
    - Call `fetchAgentConfigs(projectPath)` (where projectPath is the current workspace's project path or null)
    - Store the result in a signal or variable
    - Pass it to GridRoot as `agentConfigByPaneId={agentConfigs}` and `workspacePath={projectPath ?? undefined}`

    After GridRoot mounts (in an onMount or after the render), run the orphan sweep (per D-11):
    - Collect all leaf pane IDs from the restored tree (use `collectLeaves` from `./grid/tree` on the initial session root)
    - Call `invoke('sweep_orphan_agents', { validPaneIds: leafIds, workspacePath: projectPath ?? null }).catch(...)` (best-effort)

    Also pass `getWorkspacePath` to `installAllWorkspacesCloseSave` so the close handler knows the workspace path for the registry update.

    **IMPORTANT — Do NOT modify PaneLeaf or GridState or session.json schema.** The registry is the sole source of truth for agent metadata (per Pitfall 6, RESEARCH). The `agentConfigByPaneId` prop is populated from the registry query, not from the serialized tree.

    **IMPORTANT — Ordering matters (per Pitfall 4):** The orphan sweep MUST run AFTER boot restore + agent spawn. The sequence is: load session -> query registry -> mount GridRoot (agents spawn on mount) -> sweep orphans.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -10 && npx vitest --run 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `pty-ipc.ts` PtyTransportOpts has optional `agentPaneId?: string` and `workspacePath?: string`
    - `pty-ipc.ts` handle() exit case calls `invoke('mark_agent_stopped', ...)` when agentPaneId is set
    - `workspaceSessionPersist.ts` close-requested handler calls `invoke('update_agents_last_seen', ...)` AFTER saveIndex, BEFORE isClosingAfterSave
    - The registry update call uses `.catch()` (best-effort, never blocks close)
    - `App.tsx` calls `invoke('get_active_agents', ...)` during workspace restore
    - `App.tsx` passes `agentConfigByPaneId` to GridRoot
    - `App.tsx` calls `invoke('sweep_orphan_agents', ...)` after mount with leaf pane IDs
    - `tsc --noEmit` passes with 0 errors
    - Existing vitest suite passes (no regressions)
  </acceptance_criteria>
  <done>
    Agent exit updates registry to stopped; quit handler updates last_seen; boot restore queries registry and passes agent configs to panes; orphan sweep cleans stale entries; TypeScript compiles clean
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: End-to-end agent restart verification</name>
  <what-built>
    The full F1 agent restart lifecycle:
    1. Rust SQLite agent_registry.rs with CRUD operations
    2. spawn_command_session for arbitrary CLI binary spawning
    3. 5 Tauri command wrappers (spawn_agent, get_active_agents, mark_agent_stopped, update_agents_last_seen, sweep_orphan_agents)
    4. Frontend PtyTransport.spawnAgent + PaneComponent agentConfig branching
    5. Component tree threading (GridRoot -> SplitNode -> PaneComponent)
    6. Boot restore orchestration (registry query -> agentConfig prop injection)
    7. Close-requested lifecycle (last_seen update)
    8. PTY exit hook (mark_stopped on agent exit)
    9. Orphan sweep (stale active rows -> stopped)
    10. Command palette "Start Agent" entry
    11. .gitignore for agent-registry.sqlite
  </what-built>
  <how-to-verify>
    **Pre-test: build and launch the app**
    ```bash
    cd apps/voss-app && pnpm tauri dev
    ```

    **Test 1: Agent spawn via command palette (FPRS-03)**
    1. Open command palette (Cmd+Shift+P)
    2. Type "Start Agent" — verify the command appears
    3. Note: the startAgent handler is not wired to App.tsx yet (D-07 minimal UX), so it will be a no-op. This is expected — full palette wiring is a future phase concern.

    **Test 2: Verify build is clean**
    ```bash
    cargo test -p voss-app-core -- agent_registry -x
    cargo build -p voss-app
    cd apps/voss-app && npx tsc --noEmit
    cd apps/voss-app && npx vitest --run
    ```
    All should pass.

    **Test 3: Registry file creation**
    After launching the app and spawning any pane, check:
    - No `.voss/agent-registry.sqlite` should exist yet (registry opens lazily on first spawn_agent call)
    - The `.gitignore` contains `.voss/agent-registry.sqlite`

    **Test 4: Verify no regressions**
    - Open the app, split panes, resize, close panes — grid works as before
    - Quit and relaunch — session restore works as before (A6 pane geometry + scrollback)
    - Shell panes open as plain shells (no agent behavior unless agentConfig is explicitly provided)

    **Expected result:** All builds green, no visual regressions, "Start Agent" command visible in palette, registry file gitignored. The full agent restart loop cannot be tested end-to-end without a real spawn_agent call from the UI (which requires the startAgent AppContext wiring), but the infrastructure is in place and verified via unit tests + build + type checking.
  </how-to-verify>
  <resume-signal>Type "approved" if builds pass and no regressions, or describe issues</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Registry query -> frontend state | Active agent entries from SQLite populate component props |
| PTY exit event -> registry update | Exit callback crosses from Rust reader thread to frontend to Rust registry |
| Close-requested -> registry update | Quit handler must not block on registry failure |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F1-07 | Denial of Service | close-requested handler | mitigate | Registry update is best-effort with .catch(); existing QUIT_SAVE_TIMEOUT_MS (5000ms) wraps the entire try block including the registry call |
| T-F1-08 | Tampering | boot restore agentConfig injection | accept | AgentEntry comes from local SQLite file; same trust as session.json |
| T-F1-09 | Information Disclosure | agent exit mark_stopped timing | accept | Registry status update is local-only; no network exposure |
| T-F1-SC | Tampering | npm installs | mitigate | No new npm packages in this plan |
</threat_model>

<verification>
```bash
cargo test -p voss-app-core -- agent_registry -x
cargo build -p voss-app
cd apps/voss-app && npx tsc --noEmit
cd apps/voss-app && npx vitest --run
```
</verification>

<success_criteria>
- Boot restore queries registry and passes agent configs to GridRoot
- Close-requested handler updates last_seen (best-effort)
- PTY exit marks agent as stopped in registry
- Orphan sweep runs after boot restore
- No regressions in existing shell pane behavior
- All builds and tests pass
</success_criteria>

<output>
Create `.planning/phases/F1-durable-session-persistence/F1-03-SUMMARY.md` when done
</output>

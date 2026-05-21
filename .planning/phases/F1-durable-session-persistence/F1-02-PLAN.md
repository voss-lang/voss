---
phase: F1-durable-session-persistence
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/pane/pty-ipc.ts
  - apps/voss-app/src/pane/PaneComponent.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/command-palette/registry.ts
  - .gitignore
autonomous: true
requirements: [FPRS-03, FPRS-04]

must_haves:
  truths:
    - "PaneComponent accepts an optional agentConfig prop"
    - "PtyTransport has a spawnAgent method that invokes the spawn_agent Tauri command"
    - "SplitNode passes agentConfig through to PaneComponent"
    - "GridRoot accepts and propagates agentConfigByPaneId"
    - "Command palette has a Start Agent command"
    - ".voss/agent-registry.sqlite is gitignored"
  artifacts:
    - path: "apps/voss-app/src/pane/pty-ipc.ts"
      provides: "spawnAgent IPC method"
      contains: "spawnAgent"
    - path: "apps/voss-app/src/pane/PaneComponent.tsx"
      provides: "agentConfig prop + branching spawn"
      contains: "agentConfig"
    - path: "apps/voss-app/src/grid/SplitNode.tsx"
      provides: "agentConfig prop passthrough"
      contains: "agentConfigByPaneId"
    - path: "apps/voss-app/src/grid/GridRoot.tsx"
      provides: "agentConfigByPaneId prop"
      contains: "agentConfigByPaneId"
    - path: "apps/voss-app/src/command-palette/registry.ts"
      provides: "Start Agent command definition + startAgent AppContext method"
      contains: "startAgent"
  key_links:
    - from: "apps/voss-app/src/pane/PaneComponent.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "transport.spawnAgent call"
      pattern: "spawnAgent"
    - from: "apps/voss-app/src/grid/SplitNode.tsx"
      to: "apps/voss-app/src/pane/PaneComponent.tsx"
      via: "agentConfig prop"
      pattern: "agentConfig.*asLeaf"
    - from: "apps/voss-app/src/grid/GridRoot.tsx"
      to: "apps/voss-app/src/grid/SplitNode.tsx"
      via: "agentConfigByPaneId prop"
      pattern: "agentConfigByPaneId"
---

<objective>
Add frontend plumbing for agent-aware pane spawning: PtyTransport.spawnAgent method, PaneComponent agentConfig prop with branching spawn logic, SplitNode/GridRoot prop threading, command palette "Start Agent" entry, and gitignore for the registry file.

Purpose: This plan makes the frontend capable of spawning agent panes (via props or command palette) and propagating agent config through the component tree. Plan 03 wires the boot restore orchestration that populates these props.

Output: All frontend components accept agent config, spawnAgent IPC method exists, "Start Agent" palette command registered, `.voss/agent-registry.sqlite` gitignored.
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

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From apps/voss-app/src/pane/pty-ipc.ts (PtyTransport class):
```typescript
export class PtyTransport {
  private channel = new Channel<PtyEvent>();
  private sessionId: string | null = null;

  async spawn(o: { rows: number; cols: number; cwd?: string }): Promise<string> {
    this.sessionId = await invoke<string>('spawn_pty', {
      onData: this.channel,
      rows: o.rows, cols: o.cols, cwd: o.cwd,
    });
    return this.sessionId;
  }
}
```

From apps/voss-app/src/pane/PaneComponent.tsx (PaneProps):
```typescript
export interface PaneProps {
  id?: string;
  cwd?: string;
  shell?: string;
  index?: number;
  restoredScrollback?: string[];
  onFirstInput?: () => void;
}

const doSpawn = async (t: Terminal) => {
  await transport!.spawn({ rows: t.rows, cols: t.cols, cwd: props.cwd });
  setDot('running');
};
```

From apps/voss-app/src/grid/SplitNode.tsx (SplitNodeView props):
```typescript
export default function SplitNodeView(props: {
  node: TreeNode;
  store: Store<GridStore>;
  setStore: SetStoreFunction<GridStore>;
  path: string;
  dims: () => Dims;
  closeUI?: CloseUI;
  restoredScrollbackByPaneId?: Record<string, string[]>;
  onPaneFirstInput?: (paneId: string) => void;
  prefixActive?: boolean;
  prefixReserved?: boolean;
})
```

From apps/voss-app/src/grid/GridRoot.tsx (GridRoot props):
```typescript
export default function GridRoot(props: {
  onCloseRequest?: (store: GridStore) => void;
  closeUI?: CloseUI;
  activeLayout?: () => ActiveLayout;
  onLayoutChange?: (next: ActiveLayout) => void;
  controllerRef?: (ctrl: GridController) => void;
  projectCwd?: string;
  initialSession?: SessionFile;
  externalKeymap?: boolean;
  prefixActive?: boolean;
  prefixReserved?: boolean;
  active?: () => boolean;
})
```

From apps/voss-app/src/command-palette/registry.ts (AppContext + CommandDefinition):
```typescript
export interface AppContext {
  splitFocused: (orientation: 'H' | 'V') => void;
  closeFocused: () => void;
  // ... 20+ methods ...
  newWorkspace?: () => void;
  switchTheme?: () => void;
}

export interface CommandDefinition {
  id: string;
  label: string;
  category: CommandCategory;
  keybinding?: string;
  aliases?: string[];
  handler: (ctx: AppContext) => void;
}
```

From apps/voss-app/src/grid/tree.ts (PaneLeaf — NOT modified, registry is sole source of truth per Pitfall 6):
```typescript
export type PaneLeaf = {
  kind: 'pane';
  id: string;
  cwd: string;
  shell: string;
  index: number;
};
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: PtyTransport.spawnAgent + PaneComponent agentConfig prop</name>
  <files>
    apps/voss-app/src/pane/pty-ipc.ts
    apps/voss-app/src/pane/PaneComponent.tsx
  </files>
  <read_first>
    apps/voss-app/src/pane/pty-ipc.ts
    apps/voss-app/src/pane/PaneComponent.tsx
  </read_first>
  <action>
    **pty-ipc.ts** (per D-06):

    Add an `AgentConfig` type export: `export interface AgentConfig { cliBinary: string; cliArgs: string[]; sessionId: string; }` near the top of the file alongside other types.

    Add a `spawnAgent` method to `PtyTransport` alongside the existing `spawn` method. Signature: `async spawnAgent(o: { rows: number; cols: number; cwd?: string; paneId: string; workspacePath?: string } & AgentConfig): Promise<string>`. Body: invoke `'spawn_agent'` with params `{ onData: this.channel, rows: o.rows, cols: o.cols, cwd: o.cwd, cliBinary: o.cliBinary, cliArgs: o.cliArgs, sessionId: o.sessionId, paneId: o.paneId, workspacePath: o.workspacePath }`. Set `this.sessionId` from the result. Return it. Same pattern as existing `spawn` method.

    **PaneComponent.tsx** (per D-06):

    Add `agentConfig?: AgentConfig` to `PaneProps` interface. Import `AgentConfig` from `./pty-ipc`.

    Also add `workspacePath?: string` to PaneProps (needed for registry path resolution in the spawn_agent IPC call).

    Modify `doSpawn`: if `props.agentConfig` is defined, call `transport.spawnAgent({ rows: t.rows, cols: t.cols, cwd: props.cwd, paneId: props.id ?? '', workspacePath: props.workspacePath, ...props.agentConfig })` instead of `transport.spawn(...)`. The `setDot('running')` call stays the same in both branches.

    Do NOT touch the `restart` function, keyHandler, or any other part of PaneComponent. The agent pane restart behavior is the same as shell restart (re-invokes doSpawn which now branches on agentConfig).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `pty-ipc.ts` exports `AgentConfig` interface with fields cliBinary, cliArgs, sessionId
    - `PtyTransport` class has `async spawnAgent(...)` method that invokes `'spawn_agent'`
    - `PaneProps` interface includes `agentConfig?: AgentConfig` and `workspacePath?: string`
    - `doSpawn` branches: agentConfig present -> spawnAgent, absent -> spawn (existing)
    - `tsc --noEmit` passes with 0 errors
  </acceptance_criteria>
  <done>
    PtyTransport.spawnAgent method invokes spawn_agent Tauri command; PaneComponent branches spawn on agentConfig prop; TypeScript compiles clean
  </done>
</task>

<task type="auto">
  <name>Task 2: SplitNode + GridRoot prop threading + command palette + gitignore</name>
  <files>
    apps/voss-app/src/grid/SplitNode.tsx
    apps/voss-app/src/grid/GridRoot.tsx
    apps/voss-app/src/command-palette/registry.ts
    .gitignore
  </files>
  <read_first>
    apps/voss-app/src/grid/SplitNode.tsx
    apps/voss-app/src/grid/GridRoot.tsx
    apps/voss-app/src/command-palette/registry.ts
    .gitignore
    apps/voss-app/src/pane/pty-ipc.ts
  </read_first>
  <action>
    **SplitNode.tsx** (per D-06, Pitfall 6 — registry is sole source of truth, NOT PaneLeaf):

    Import `AgentConfig` from `../pane/pty-ipc`.

    Add two optional props to the SplitNodeView props type:
    - `agentConfigByPaneId?: Record<string, AgentConfig>` (keyed by pane id)
    - `workspacePath?: string`

    In the leaf rendering Match branch (around line 125 where `<PaneComponent>` is rendered), add:
    - `agentConfig={props.agentConfigByPaneId?.[asLeaf().id]}` prop
    - `workspacePath={props.workspacePath}` prop

    In the split rendering Match branch (around line 137+ where recursive SplitNodeView children are rendered), pass through `agentConfigByPaneId={props.agentConfigByPaneId}` and `workspacePath={props.workspacePath}` to both left and right child SplitNodeView instances.

    **GridRoot.tsx** (per D-04):

    Import `AgentConfig` from `../pane/pty-ipc`.

    Add to GridRoot props:
    - `agentConfigByPaneId?: Record<string, AgentConfig>` — populated by caller before mount (per D-04, the registry query completes before GridRoot renders)
    - `workspacePath?: string`

    Pass both through to the root SplitNodeView render:
    - `agentConfigByPaneId={props.agentConfigByPaneId}`
    - `workspacePath={props.workspacePath}`

    **registry.ts** (per D-07):

    Add `startAgent?: () => void` to the `AppContext` interface (optional, matching the established pattern for incrementally-added features like newWorkspace, switchTheme, etc.).

    Add a new exported function `agentCommands(): CommandDefinition[]` returning an array with one command:
    ```
    {
      id: 'agent.start',
      label: 'Start Agent',
      category: 'Pane',
      handler: (ctx) => ctx.startAgent?.(),
    }
    ```

    Category is `'Pane'` (existing category, no need to extend CommandCategory union). The handler calls the optional `startAgent` on AppContext. When App.tsx wires this (Plan 03 or future phase), it will prompt for task description and call spawn_agent. For now the handler is a no-op if `startAgent` is undefined.

    **.gitignore** (per SPEC acceptance criteria — `.voss/agent-registry.sqlite` is gitignored):

    Add under the existing `.voss-cache/` entry:
    ```
    .voss/agent-registry.sqlite
    ```

    This ensures the SQLite registry file is never committed to any project repo.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && npx tsc --noEmit 2>&1 | tail -10 && cd /Users/benjaminmarks/Projects/Voss && grep -c 'agent-registry.sqlite' .gitignore</automated>
  </verify>
  <acceptance_criteria>
    - SplitNodeView props include `agentConfigByPaneId?: Record<string, AgentConfig>` and `workspacePath?: string`
    - SplitNodeView leaf branch passes `agentConfig={props.agentConfigByPaneId?.[asLeaf().id]}` to PaneComponent
    - SplitNodeView split branch passes `agentConfigByPaneId` and `workspacePath` to recursive children
    - GridRoot props include `agentConfigByPaneId?: Record<string, AgentConfig>` and `workspacePath?: string`
    - GridRoot passes both through to root SplitNodeView
    - `AppContext` interface includes `startAgent?: () => void`
    - `agentCommands()` function exported with one `agent.start` command definition
    - `.gitignore` contains `.voss/agent-registry.sqlite`
    - `tsc --noEmit` passes with 0 errors
  </acceptance_criteria>
  <done>
    Component tree threads agentConfig from GridRoot through SplitNode to PaneComponent; command palette has Start Agent entry; registry SQLite file is gitignored; TypeScript compiles clean
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User input -> command palette | Task description crosses from user to spawn_agent args |
| Frontend prop -> Tauri IPC | agentConfig values are passed to Rust spawn_agent command |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-F1-05 | Elevation of Privilege | PtyTransport.spawnAgent | accept | Same trust boundary as user typing in a shell; cli_binary is user-chosen |
| T-F1-06 | Tampering | agentConfig prop injection | accept | Props come from the app's own state (registry query result); no external injection vector |
| T-F1-SC | Tampering | npm installs | mitigate | No new npm packages in this plan; all imports are existing workspace dependencies |
</threat_model>

<verification>
```bash
cd apps/voss-app && npx tsc --noEmit
grep -c 'agent-registry.sqlite' .gitignore
```
</verification>

<success_criteria>
- PaneComponent spawns agents when agentConfig is provided
- PtyTransport.spawnAgent invokes spawn_agent Tauri command
- Component tree fully threads agentConfig from GridRoot to PaneComponent
- Start Agent command registered in palette
- .voss/agent-registry.sqlite gitignored
- tsc --noEmit passes, no regressions in existing vitest suite
</success_criteria>

<output>
Create `.planning/phases/F1-durable-session-persistence/F1-02-SUMMARY.md` when done
</output>

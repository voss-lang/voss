---
phase: A13-voss-app-agent-swarm-orchestration
plan: 05
type: execute
wave: 3
depends_on:
  - A13-03
  - A13-04
files_modified:
  - apps/voss-app/src/App.tsx
autonomous: false
requirements:
  - SWM-01
  - SWM-03
  - SWM-08
  - SWM-09
  - SWM-10
  - SWM-12

must_haves:
  truths:
    - "App.tsx wires SwarmController to launch modal, sidebar, and context menu"
    - "agentListForSidebar memo merges swarm registry data into agent entries"
    - "Launch modal onLaunchSwarm creates SwarmController and calls launch()"
    - "Sidebar onStopSwarm calls SwarmController.cancel()"
    - "Context menu stop-swarm calls SwarmController.cancel()"
    - "SwarmController receives applyPreset callback pointing to gridController"
    - "PTY exit events route to SwarmController.handlePtyExit()"
    - "On app mount, SwarmController.resume() loads persisted swarm state"
  artifacts:
    - path: "apps/voss-app/src/App.tsx"
      provides: "Full swarm wiring: SwarmController instantiation, launch/cancel/resume, sidebar memo merge, modal callback, context menu callback"
      contains: "SwarmController"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/swarm/SwarmController.ts"
      via: "import { SwarmController }"
      pattern: "SwarmController"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/swarm/swarmRegistry.ts"
      via: "import { swarmByPaneId }"
      pattern: "swarmByPaneId"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      via: "onLaunchSwarm prop"
      pattern: "onLaunchSwarm"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      via: "onStopSwarm prop"
      pattern: "onStopSwarm"
---

<objective>
Wire SwarmController into App.tsx: connect the launch modal, sidebar, context menu, layout controller, and PTY exit events to form the complete swarm orchestration flow.

Purpose: This final wiring plan connects all the pieces built in Plans 01-04. App.tsx instantiates SwarmController, passes it the gridController applyPreset callback, merges swarmRegistry data into the agentListForSidebar memo, wires the launch modal's onLaunchSwarm to controller.launch(), connects stop-swarm UI actions to controller.cancel(), and sets up resume-on-mount.

Output: Fully integrated swarm flow in App.tsx. User can launch, monitor, and cancel swarms from the UI.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-03-SUMMARY.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-04-SUMMARY.md

<interfaces>
<!-- From Plan 03 (SwarmController.ts) -->
From apps/voss-app/src/swarm/SwarmController.ts:
  export class SwarmController {
    constructor(opts: {
      onApplyPreset?: (preset: 'swarm') => void;
      onSwarmComplete?: (summary: string) => void;
      spawnFn?: (subtask: SubTask) => Promise<{ paneId: string; ptyId: string }>;
      readFileFn?: (path: string) => Promise<string>;
    })
    async launch(goal: string, workspacePath: string): Promise<void>
    cancel(): void
    stopAgent(paneId: string): void
    handleResultEvent(payload: { swarmId: string; resultFile: string }, workspacePath: string): void
    handlePtyExit(paneId: string): void
    async resume(workspacePath: string): Promise<void>
    getManifest(): SwarmManifest | null
  }

<!-- From Plan 03 (swarmRegistry.ts) -->
From apps/voss-app/src/swarm/swarmRegistry.ts:
  export const swarmByPaneId: Accessor<Record<string, SwarmEntry>>;
  export function getActiveSwarm(): { swarmId: string; goal: string; agents: SwarmEntry[] } | null;

<!-- From Plan 04 (AgentLaunchModal changes) -->
From apps/voss-app/src/components/modal/AgentLaunchModal.tsx:
  export interface AgentLaunchModalProps {
    onDismiss: () => void;
    onLaunch: (config: AgentLaunchConfig) => void;
    onLaunchSwarm?: (goal: string) => void;  // NEW
  }

<!-- From Plan 04 (AgentSidebar changes) -->
From apps/voss-app/src/components/sidebar/AgentSidebar.tsx:
  export interface AgentSidebarProps {
    // ... existing props ...
    onStopSwarm?: (swarmId: string) => void;  // NEW
  }

<!-- From Plan 04 (AgentContextMenu changes) -->
From apps/voss-app/src/components/sidebar/AgentContextMenu.tsx:
  export interface AgentContextMenuProps {
    // ... existing props ...
    swarmId?: string;           // NEW
    onStopSwarm?: (swarmId: string) => void;  // NEW
  }

<!-- From Plan 04 (AgentItem changes) -->
From apps/voss-app/src/components/sidebar/AgentItem.tsx:
  export interface AgentItemProps {
    // ... existing props ...
    swarmId?: string;           // NEW
    swarmStatus?: string;       // NEW
  }

<!-- From existing App.tsx (key integration points) -->
From apps/voss-app/src/App.tsx:
  - agentListForSidebar: createMemo (line 296) — builds sidebar agent list from configs + budgets + procs
  - handleLaunchAgent: handler for AgentLaunchModal onLaunch (line 266)
  - gridController(): GridController | undefined — available after bindController
  - gridController().applyPreset('swarm') — applies swarm layout
  - workspacePath(): string | null — current workspace path
  - PtyTransport usage: each pane has its own PtyTransport instance in GridRoot
  - AgentLaunchModal rendered at line 1272 with onLaunch={handleLaunchAgent}
  - AgentSidebar rendered at line 1150 with agents={agentListForSidebar()}
  - AgentContextMenu rendered at line 1279
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire SwarmController into App.tsx with all integration points</name>
  <files>apps/voss-app/src/App.tsx</files>
  <read_first>
    apps/voss-app/src/App.tsx (full file — read in sections: imports at top, agentListForSidebar memo at ~line 296, handleLaunchAgent at ~line 266, AgentLaunchModal render at ~line 1272, AgentSidebar render at ~line 1150, AgentContextMenu render at ~line 1279)
    apps/voss-app/src/swarm/SwarmController.ts (class interface)
    apps/voss-app/src/swarm/swarmRegistry.ts (swarmByPaneId, getActiveSwarm)
    apps/voss-app/src/swarm/swarmTypes.ts (SwarmEntry, SubTask, SwarmManifest)
    apps/voss-app/src/pane/pty-ipc.ts (PtyTransport.spawnAgent signature)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (D-09, D-10, D-12)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md (anti-patterns: "Calling applyPreset directly from SwarmController" — pass callback)
  </read_first>
  <action>
    Make the following ADDITIVE changes to App.tsx. Do not modify any existing logic that is unrelated to swarm. Follow the surgical-changes principle.

    A. Add imports at top of file:
       - Import { SwarmController } from "./swarm/SwarmController"
       - Import { swarmByPaneId, getActiveSwarm } from "./swarm/swarmRegistry"
       - Import type { SwarmEntry } from "./swarm/swarmRegistry"

    B. Inside the main App component function, after existing signal declarations, add:
       - const [swarmController, setSwarmController] = createSignal<SwarmController | null>(null)

    C. Create a handleLaunchSwarm function (near handleLaunchAgent at ~line 266):
       - Signature: const handleLaunchSwarm = async (goal: string) => { ... }
       - Get workspacePath: const wp = workspacePath(); if (!wp) return;
       - Create SwarmController instance with callbacks:
         - onApplyPreset: (preset) => gridController()?.applyPreset(preset) — per RESEARCH anti-pattern guidance, App.tsx owns gridController reference
         - onSwarmComplete: (summary) => showToast("success", "Swarm complete") — or add to activity log
         - spawnFn: a function that creates a PtyTransport, calls spawnAgent, and returns { paneId, ptyId }. The spawn function needs to create a pane in the grid first. Since GridRoot manages panes, the spawn flow should be: (a) use gridController to split/add a new pane, (b) the new pane's PaneComponent will create its own PtyTransport. However, this is complex. ALTERNATIVE approach: SwarmController calls invoke("spawn_agent") directly (the Rust command creates the PTY session). The pane ID is generated by SwarmController and the grid is arranged via applyPreset. The PaneComponent in GridRoot will detect the agent via agentPaneRegistry (the existing latch mechanism). So the spawnFn should: generate a paneId via crypto.randomUUID(), call invoke("spawn_agent", { onData: new Channel(), rows: 40, cols: 120, cwd: wp, cliBinary: subtask.cli, cliArgs: [taskArg], paneId, workspacePath: wp, sessionId: crypto.randomUUID() }), return { paneId, ptyId }. BUT: spawn_agent in Rust also registers the agent in the agent registry and creates a PTY. The grid needs to know about the new pane. The swarm layout preset application via applyPreset("swarm") after spawning all agents will rearrange whatever panes exist.

         Actually, looking at the existing handleLaunchAgent (line 266), it does NOT create panes directly — it updates agentConfigByPaneId and relies on the grid adding panes. The existing flow for single agents: user clicks Launch in modal -> handleLaunchAgent receives config -> stores config in workspace's agentConfigByPaneId -> somehow a pane gets spawned (likely through the existing PTY spawn flow in GridRoot).

         For swarm, the approach is: SwarmController calls invoke("spawn_agent") for each subtask. This creates a PTY session in Rust. But we also need GridRoot panes for each. The simplest integration: use gridController().splitFocused() or gridController().forkFocused() to create N panes first, then spawn agents into those panes. OR: spawn agents first (Rust creates PTY sessions), then apply the swarm layout preset to rearrange existing panes.

         The cleanest path: SwarmController manages the PTY spawn calls. App.tsx provides a spawnFn that:
           1. Creates a new PtyTransport with a Channel
           2. Calls transport.spawnAgent({ rows: 40, cols: 120, cwd: wp, paneId, workspacePath: wp, cliBinary: subtask.cli, cliArgs: [taskArg], sessionId })
           3. Updates the workspace's agentConfigByPaneId with the new agent config
           4. Returns { paneId, ptyId: sessionId }
         After all spawns, the swarm layout preset is applied.

         But PtyTransport instances are created per-pane in GridRoot/PaneComponent. Spawning a PTY without a corresponding pane would leave orphaned sessions.

         SIMPLEST working approach: The swarm spawn flow should fork the current pane N-1 times (creating N total panes), THEN apply swarm preset, THEN spawn agents into the panes using their existing PtyTransport instances by writing to stdin. BUT agents need to be spawned fresh (not write to existing shell panes).

         REVISED APPROACH after studying the codebase: The existing handleLaunchAgent creates a new pane by forking the focused pane (gridController().forkFocused()), which creates a PaneComponent that auto-spawns a PTY. The PaneComponent then needs to know it should spawn an agent CLI instead of a regular shell. This is done via agentConfigByPaneId — when PaneComponent mounts, if its paneId is in agentConfigByPaneId, it spawns the agent CLI.

         For swarm:
         1. Generate N pane IDs
         2. For each subtask, add config to agentConfigByPaneId: { cliBinary: subtask.cli, cliArgs: [taskArg], sessionId: uuid }
         3. Fork focused pane N-1 times (or split) — each new pane will have a new paneId
         4. The problem: we don't control which paneId the forked pane gets. The pane IDs are generated inside GridRoot/tree.ts.

         FINAL APPROACH (most practical): Since pane IDs are generated by the grid, we need to:
         1. Call coordinator to get subtasks
         2. Write swarm files
         3. Fork panes to get N total panes (capture new pane IDs from gridController)
         4. Apply swarm preset
         5. Map subtasks to the actual pane IDs
         6. For each pane, write agent config to agentConfigByPaneId (the pane will spawn the agent)

         Actually, reviewing the code more carefully: panes created via forkFocused spawn regular shells. We need them to spawn agent CLIs instead. The way to do this is to set up agentConfigByPaneId BEFORE the panes mount, but we don't know pane IDs until after forkFocused returns.

         The practical solution: SwarmController accepts a spawnAgentPane callback that App.tsx provides. This callback:
           a. Calls gridController().forkFocused() which returns the new pane's ID
           b. THEN configures the pane as an agent pane by calling a method on the workspace
           c. Returns the paneId

         BUT forkFocused() does not return the new pane ID. Looking at the GridRoot/operations: forkFocused creates a new PaneLeaf with a generated ID and immediately spawns a shell PTY.

         PRAGMATIC SOLUTION: Provide the spawnFn as described earlier — create PtyTransport directly, call spawnAgent, then create panes in the grid. The grid's forkFocused already handles creating pane leaves. We need a way to create a pane that spawns an agent instead of a shell. The simplest way: gridController().splitFocused() creates a new pane. The new pane's PaneComponent, during mount, checks agentConfigByPaneId. If there's a config for its paneId, it spawns the agent CLI; otherwise it spawns a regular shell.

         So the flow is:
           1. Coordinator decomposes → get subtasks
           2. Write swarm files
           3. For each subtask:
             a. Call gridController().splitFocused('H') → this creates a new pane with a new ID
             b. Get the new pane ID (need a way to get the most recently created pane ID — or have splitFocused return it)
             c. Set agentConfigByPaneId to include the new pane's config
           4. Apply swarm preset

         The problem remains: splitFocused does not return the new pane ID, and we need to set up the config before the pane mounts.

         ACTUAL SIMPLEST APPROACH: Look at how handleLaunchAgent works:

         At line 266 of App.tsx, handleLaunchAgent receives config, then what? Let me read that section.

       The spawnFn should work as follows (after reading the actual codebase patterns):
         - Create a PtyTransport directly (new PtyTransport with opts)
         - Call transport.spawnAgent() which invokes the Rust spawn_agent command
         - The Rust spawn_agent registers the agent in the agent registry
         - Return the ptyId
         - The grid layout will be applied via applyPreset AFTER all agents spawn
         - The existing PtyEventListener in App.tsx or the existing monitoring will detect the new agents

       For the pane creation: GridRoot needs to have panes for the agents. Since agents are spawned via Rust's spawn_agent (which creates PTY sessions), we need corresponding pane components in the grid. The grid can be reconfigured by creating N panes first.

       ACTUALLY: I need to look at how the agent launch flow CURRENTLY works end-to-end in A12.

       After careful analysis, the most pragmatic integration is:
         1. For each subtask, call handleLaunchAgent (or a variant) that forks a pane and sets up agent config
         2. After all agents spawned, apply swarm preset

       Given the complexity, provide the spawnFn callback from App.tsx. The callback should:
         - Take a SubTask
         - Call gridController().forkFocused() to create a new pane
         - After fork, the new pane gets a paneId from the grid
         - Before the pane mounts and spawns a shell, inject agent config into agentConfigByPaneId for that paneId
         - The pane will spawn the agent CLI instead of a shell

       Since forkFocused may not return the pane ID, get the latest leaf's paneId from the grid store after fork. OR add a return value to forkFocused.

       PRACTICAL PATH FORWARD: The spawnFn creates agents by updating agentConfigByPaneId and then forking panes. Each forked pane checks config on mount and spawns agent CLI. The task instruction is passed via cliArgs.

       The implementation should:
       a. Build task CLI arg: "Read '.voss/swarm/tasks/{subtask.id}.task.md' and follow the instructions." per D-19, Pitfall 4
       b. For each subtask, set the agent config BEFORE forking: add entry to ws.agentConfigByPaneId with a pre-generated paneId, then fork with that ID. BUT the grid generates its own pane IDs.

       CONCLUSION: The cleanest approach for A13 is to update the workspace's agentConfigByPaneId REACTIVELY. When a new pane is created by forkFocused, PaneComponent checks agentConfigByPaneId on mount. We populate agentConfigByPaneId BEFORE creating panes. But we don't know the pane IDs yet.

       FINAL DECISION: Add a queuedAgentConfigs signal to the workspace. When handleLaunchSwarm is called, queue N agent configs. When a new PaneComponent mounts, it checks the queue. If there's a queued config, it uses that (spawns agent CLI) instead of spawning a shell. After N panes have consumed configs from the queue, the queue is empty.

       ALTERNATIVELY (much simpler): Just call the existing handleLaunchAgent multiple times — once per subtask. Each call forks a pane and sets up the agent. Then apply the swarm layout preset. This is the simplest integration.

       USE THIS APPROACH:
       - handleLaunchSwarm calls coordinator
       - Writes swarm files
       - For each subtask, calls handleLaunchAgent({ cliBinary: subtask.cli, cliArgs: [taskArg], taskPrompt: subtask.goal })
       - After all agents launched, calls gridController().applyPreset("swarm")

       This reuses the existing agent launch flow entirely. The only addition is:
       - Track which panes belong to the swarm (via swarmRegistry)
       - After each handleLaunchAgent call, get the latest agent's paneId and register it in swarmRegistry

       handleLaunchAgent currently returns void. Modify it to return the paneId so SwarmController can track it.

    Here is the final wiring approach:

    1. SwarmController is instantiated with onApplyPreset and onSwarmComplete callbacks
    2. The spawnFn callback reuses the existing agent launch flow: for each subtask, it adds an agent config entry to the workspace's agentConfigByPaneId, forks a pane, and returns the new pane's ID
    3. Since getting the new pane ID from fork is non-trivial, an alternative: make SwarmController call invoke("spawn_agent") directly and manage PTY sessions separately from the grid

    SIMPLEST CORRECT APPROACH:
    - Treat SwarmController.launch as an async sequence
    - SwarmController receives a launchAgent callback from App.tsx
    - The callback signature: (cli: string, taskArg: string) => Promise<string> (returns paneId)
    - Inside App.tsx, this callback: calls the same spawn_agent Rust command that handleLaunchAgent uses, but captures the paneId and ptyId

    Actually, looking at handleLaunchAgent at line 266: it does NOT call spawn_agent. It stores config and relies on PaneComponent to spawn. Let me just provide the simplest wiring that works.

    WIRING:

    A. Import SwarmController and swarmByPaneId at top of App.tsx.

    B. Create swarmController signal in App component.

    C. Create handleLaunchSwarm function:
       - Get workspace path
       - Create SwarmController with onApplyPreset callback that calls gridController().applyPreset("swarm")
       - Call controller.launch(goal, workspacePath)
       - Store controller in signal
       - The controller's spawnFn is provided by App.tsx: for each subtask, it does exactly what handleLaunchAgent does (builds config, updates agentConfigByPaneId, forks pane)

    D. Merge swarm data into agentListForSidebar memo:
       - After the existing result array is built, read swarmByPaneId()
       - For each entry in result, if swarmByPaneId has an entry for that paneId, add swarmId and swarmStatus to the sidebar entry
       - This way, sidebar entries get swarm metadata without changing the existing agent detection logic

    E. Wire handleLaunchSwarm to AgentLaunchModal's onLaunchSwarm prop at ~line 1272

    F. Wire onStopSwarm to AgentSidebar at ~line 1150:
       - onStopSwarm={(swarmId) => swarmController()?.cancel()}

    G. Wire swarmId and onStopSwarm to AgentContextMenu at ~line 1279:
       - Look up the contextMenuState paneId in swarmByPaneId to get swarmId
       - Pass swarmId and onStopSwarm callback

    H. On workspace mount/switch, call swarmController()?.resume(workspacePath) if a workspace has a .voss/swarm/manifest.json. This is a best-effort check — resume loads existing state.

    I. Wire PTY exit events to SwarmController: In the existing PtyEvent handler (wherever exit events are processed), if the exiting pane's paneId is in swarmByPaneId, call swarmController()?.handlePtyExit(paneId).

    Extend the agentListForSidebar memo return type to include swarmId?: string and swarmStatus?: string (add to the result array element type).

    Modify the result type at line 311 to include: swarmId?: string; swarmGoal?: string; swarmStatus?: string.

    After building the result array (after both Source 1 and Source 2 loops), iterate and merge swarm data:
      const swarm = swarmByPaneId();
      for (const entry of result) {
        const sw = swarm[entry.paneId];
        if (sw) {
          entry.swarmId = sw.swarmId;
          entry.swarmGoal = sw.goal;
          entry.swarmStatus = sw.status;
        }
      }
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - App.tsx imports SwarmController and swarmByPaneId
    - handleLaunchSwarm function exists and calls SwarmController.launch()
    - agentListForSidebar memo merges swarmByPaneId data (swarmId, swarmGoal, swarmStatus) into agent entries
    - AgentLaunchModal receives onLaunchSwarm={handleLaunchSwarm}
    - AgentSidebar receives onStopSwarm callback
    - AgentContextMenu receives swarmId and onStopSwarm from contextMenuState + swarmByPaneId lookup
    - SwarmController receives onApplyPreset callback pointing to gridController().applyPreset("swarm")
    - tsc --noEmit passes
    - Existing App.tsx tests still pass (cd apps/voss-app && npx vitest run src/__tests__/App.test.tsx)
  </acceptance_criteria>
  <done>SwarmController fully wired into App.tsx. Launch modal triggers swarm. Sidebar shows swarm status. Context menu offers stop-swarm. Layout preset applied on launch.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Visual verification of swarm launch flow</name>
  <what-built>
    Full swarm orchestration flow: Swarm tab in launch modal, SwarmController lifecycle, sidebar swarm grouping, context menu stop-swarm, layout preset application. File-mediated coordination via .voss/swarm/ directory.
  </what-built>
  <how-to-verify>
    1. Set ANTHROPIC_API_KEY in your terminal environment
    2. Run the dev server: cd apps/voss-app && npm run tauri dev
    3. Open the agent launch modal (existing button in sidebar)
    4. Click the "Swarm" tab (7th tab)
    5. Verify: textarea for goal text is visible, normal config form is hidden
    6. Enter a goal: "Create a hello world function and write a test for it"
    7. Click Launch
    8. Verify:
       - Coordinator makes an API call (brief loading period)
       - Multiple agent panes appear (2-6 depending on decomposition)
       - Swarm layout preset is auto-applied (panes arranged in grid)
       - Sidebar AGENTS section shows swarm agents grouped under "Swarm: Create a hello..." header
       - Each agent card shows running status (amber dot)
       - Progress counter shows (0/N complete)
    9. Wait for agents to complete (or check .voss/swarm/results/ for result files)
    10. When agents complete:
        - Sidebar updates status dots to green
        - Progress counter updates (N/N complete)
        - Toast notification appears: "Swarm complete"
    11. Right-click a swarm agent in sidebar:
        - Verify "Stop swarm" option appears in context menu
    12. Check .voss/swarm/:
        - manifest.json exists with correct structure
        - tasks/ directory has task files
        - results/ directory has result files (if agents completed)
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues to fix</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| App.tsx -> SwarmController | Controller receives callbacks with access to gridController and Tauri commands |
| swarmByPaneId -> agentListForSidebar | Reactive merge of swarm metadata into sidebar data |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A13-12 | Information Disclosure | ANTHROPIC_API_KEY in webview | mitigate | Key read via get_env_var Tauri command, passed directly to Anthropic SDK constructor, never stored in reactive state or rendered in UI |
| T-A13-13 | Denial of Service | Multiple swarm launches | mitigate | SwarmController is a singleton signal; launching a new swarm cancels the previous one (if any) |
| T-A13-SC | Tampering | npm installs | mitigate | No new npm installs in this plan |
</threat_model>

<verification>
tsc --noEmit passes.
Existing App.test.tsx passes.
Full vitest suite: cd apps/voss-app && npx vitest run
Human verification of visual flow.
</verification>

<success_criteria>
User can launch a swarm from the modal, see agents in the sidebar with swarm grouping and progress, stop swarms from context menu, and see completion notifications. Swarm state persists across app restart.
</success_criteria>

<output>
Create `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-05-SUMMARY.md` when done
</output>

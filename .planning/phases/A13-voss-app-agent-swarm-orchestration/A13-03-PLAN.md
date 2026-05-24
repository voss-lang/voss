---
phase: A13-voss-app-agent-swarm-orchestration
plan: 03
type: execute
wave: 2
depends_on:
  - A13-01
  - A13-02
files_modified:
  - apps/voss-app/src/swarm/SwarmController.ts
  - apps/voss-app/src/swarm/swarmRegistry.ts
  - apps/voss-app/src/swarm/__tests__/SwarmController.test.ts
autonomous: true
requirements:
  - SWM-03
  - SWM-04
  - SWM-05
  - SWM-06
  - SWM-10
  - SWM-11
  - SWM-12

must_haves:
  truths:
    - "SwarmController can execute a full swarm lifecycle: decompose -> write files -> spawn agents -> watch results -> synthesize"
    - "Each subtask spawns a dedicated agent pane via existing spawn_agent Tauri command"
    - "Agents are instructed via CLI positional arg to read their task file"
    - "Result file creation triggers status updates in the swarm registry"
    - "PTY exit events serve as fallback completion detection"
    - "Swarm manifest is persisted to .voss/swarm/manifest.json"
    - "SwarmRegistry provides reactive signal store for per-agent swarm status"
    - "Swarm layout preset is auto-applied on launch"
  artifacts:
    - path: "apps/voss-app/src/swarm/SwarmController.ts"
      provides: "SwarmController class with launch, cancel, resume, handleResultEvent, handlePtyExit methods"
      exports: ["SwarmController"]
    - path: "apps/voss-app/src/swarm/swarmRegistry.ts"
      provides: "Reactive SolidJS signal store for swarm agent entries"
      exports: ["swarmByPaneId", "registerSwarmAgent", "updateSwarmAgentStatus", "unregisterSwarmAgents", "getActiveSwarm"]
    - path: "apps/voss-app/src/swarm/__tests__/SwarmController.test.ts"
      provides: "Unit tests covering launch, result handling, PTY exit fallback, timeout, cancel, manifest persistence, resume"
  key_links:
    - from: "apps/voss-app/src/swarm/SwarmController.ts"
      to: "apps/voss-app/src/swarm/coordinator.ts"
      via: "import { coordinatorDecompose, synthesizeResults, buildTaskFileContent }"
      pattern: "coordinatorDecompose|synthesizeResults|buildTaskFileContent"
    - from: "apps/voss-app/src/swarm/SwarmController.ts"
      to: "apps/voss-app/src/swarm/swarmRegistry.ts"
      via: "import { registerSwarmAgent, updateSwarmAgentStatus, unregisterSwarmAgents }"
      pattern: "registerSwarmAgent|updateSwarmAgentStatus"
    - from: "apps/voss-app/src/swarm/SwarmController.ts"
      to: "@tauri-apps/api"
      via: "invoke('write_swarm_files'), invoke('watch_swarm_results'), invoke('stop_swarm_watcher'), invoke('get_env_var'), invoke('spawn_agent')"
      pattern: "invoke.*swarm|invoke.*spawn_agent"
---

<objective>
Build the SwarmController orchestration engine and reactive swarm registry that manages the full swarm lifecycle.

Purpose: This is the core business logic for agent swarm orchestration. SwarmController orchestrates: coordinator LLM call -> write task files -> spawn agent panes -> watch for results -> update status -> synthesize. The swarmRegistry provides a SolidJS reactive signal store (following the budgetRegistry pattern) that the sidebar reads to display swarm state.

Output: SwarmController.ts (lifecycle orchestrator), swarmRegistry.ts (reactive signal store), comprehensive unit tests.
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
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-01-SUMMARY.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-02-SUMMARY.md

<interfaces>
<!-- From Plan 01 (swarmTypes.ts) -->
From apps/voss-app/src/swarm/swarmTypes.ts:
  export type SwarmAgentStatus = 'pending' | 'running' | 'complete' | 'stuck' | 'error';
  export type SubTask = { id: string; cli: string; goal: string; fileScope: string[]; excludeScope: string[]; };
  export type SwarmAgent = { id: string; paneId: string; ptyId: string; cli: string; status: SwarmAgentStatus; taskSummary: string; };
  export type SwarmManifest = { id: string; goal: string; status: 'running' | 'complete' | 'cancelled'; created: number; agents: SwarmAgent[]; };
  export type ResultFileParsed = { agentId: string; status: 'complete' | 'error'; filesModified: string[]; durationSecs: number | null; summary: string; };
  export const SWARM_DIR = '.voss/swarm';
  export const MAX_CONCURRENT_AGENTS = 6;
  export const SWARM_RESULT_EVENT = 'voss://swarm-result-added';
  export const SWARM_POLL_MS = 500;

<!-- From Plan 02 (coordinator.ts, resultParser.ts) -->
From apps/voss-app/src/swarm/coordinator.ts:
  export async function coordinatorDecompose(goal, repoTree, claudeMd, apiKey): Promise<SubTask[]>;
  export function synthesizeResults(goal, results): string;
  export function buildTaskFileContent(swarmId, agentId, cli, goal, fileScope, excludeScope): string;

From apps/voss-app/src/swarm/resultParser.ts:
  export function parseResultFile(raw: string): ResultFileParsed;

<!-- From existing codebase -->
From apps/voss-app/src/pane/pty-ipc.ts (lines 167-186):
  class PtyTransport {
    async spawnAgent(o: { rows, cols, cwd?, paneId, workspacePath? } & AgentConfig): Promise<string>
    // returns ptyId (session ID)
  }
  interface AgentConfig { cliBinary: string; cliArgs: string[]; sessionId?: string; }

From apps/voss-app/src/pane/budgetRegistry.ts (signal store pattern):
  const [budgetByPaneId, setBudgetByPaneId] = createSignal<Record<string, BudgetEntry>>({});
  export function registerPaneBudget(paneId, data): void { ... }
  export function unregisterPaneBudget(paneId): void { ... }
  export { budgetByPaneId };

From apps/voss-app/src/grid/layoutPresets.ts:
  export type LayoutPreset = 'fanout' | 'pipeline' | 'swarm' | 'watchers';
  export function applyPreset(root: TreeNode, preset: LayoutPreset): TreeNode;

From apps/voss-app/src/command-palette/toast.tsx:
  export function showToast(severity: 'info' | 'success' | 'warning' | 'error', message: string): void;

From @tauri-apps/api/event:
  import { listen } from '@tauri-apps/api/event';
  const unlisten = await listen<T>(eventName, (event) => { event.payload });

From @tauri-apps/api/core:
  import { invoke } from '@tauri-apps/api/core';
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create swarmRegistry reactive signal store</name>
  <files>apps/voss-app/src/swarm/swarmRegistry.ts</files>
  <read_first>
    apps/voss-app/src/pane/budgetRegistry.ts (signal store pattern to mirror exactly)
    apps/voss-app/src/swarm/swarmTypes.ts (SwarmAgentStatus, SwarmAgent types)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md (Pattern 5: SwarmRegistry)
  </read_first>
  <action>
    Create apps/voss-app/src/swarm/swarmRegistry.ts following the budgetRegistry.ts pattern exactly.

    Import createSignal from "solid-js". Import SwarmAgentStatus from "./swarmTypes".

    Define and export SwarmEntry type: swarmId (string), goal (string), agentPaneId (string), agentId (string), cli (string), status (SwarmAgentStatus).

    Create module-level signal: const [swarmByPaneId, setSwarmByPaneId] = createSignal of Record<string, SwarmEntry>, initial value empty object.

    Export function registerSwarmAgent(paneId: string, entry: SwarmEntry): void
      - setSwarmByPaneId spreading prev with new entry keyed by paneId
      - Same identity-check optimization as budgetRegistry: if existing entry has same status, return prev unchanged

    Export function updateSwarmAgentStatus(paneId: string, status: SwarmAgentStatus): void
      - setSwarmByPaneId: look up entry by paneId, if not found or same status return prev, else spread with new status

    Export function unregisterSwarmAgents(swarmId: string): void
      - setSwarmByPaneId: clone prev, delete all entries where entry.swarmId === swarmId, return next

    Export function getActiveSwarm(): { swarmId: string; goal: string; agents: SwarmEntry[] } | null
      - Read swarmByPaneId(), collect all entries
      - If no entries, return null
      - Group by swarmId, return the first group as { swarmId, goal (from first entry), agents (array of entries) }

    Export { swarmByPaneId } for reactive reads.

    No @tauri-apps imports. This is a pure SolidJS reactive module.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -10</automated>
  </verify>
  <acceptance_criteria>
    - File exists at apps/voss-app/src/swarm/swarmRegistry.ts
    - Exports: swarmByPaneId, registerSwarmAgent, updateSwarmAgentStatus, unregisterSwarmAgents, getActiveSwarm, SwarmEntry
    - Uses createSignal from solid-js (not createStore)
    - Identity-check optimization prevents unnecessary re-renders on duplicate status updates
    - tsc --noEmit passes
  </acceptance_criteria>
  <done>swarmRegistry signal store created matching budgetRegistry pattern, all exports present, tsc clean</done>
</task>

<task type="auto">
  <name>Task 2: Create SwarmController lifecycle orchestrator with tests</name>
  <files>apps/voss-app/src/swarm/SwarmController.ts, apps/voss-app/src/swarm/__tests__/SwarmController.test.ts</files>
  <read_first>
    apps/voss-app/src/swarm/swarmTypes.ts (all types)
    apps/voss-app/src/swarm/coordinator.ts (coordinatorDecompose, synthesizeResults, buildTaskFileContent)
    apps/voss-app/src/swarm/resultParser.ts (parseResultFile)
    apps/voss-app/src/swarm/swarmRegistry.ts (registerSwarmAgent, updateSwarmAgentStatus, unregisterSwarmAgents)
    apps/voss-app/src/pane/pty-ipc.ts (PtyTransport.spawnAgent signature at lines 167-186)
    apps/voss-app/src/command-palette/toast.tsx (showToast)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (D-09, D-10, D-12, D-13, D-19, D-21, D-22)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md (Pattern 4: Agent Spawn, Pitfall 3: race, Pitfall 4: quoting, Pitfall 5: backfill, anti-patterns)
  </read_first>
  <action>
    Create apps/voss-app/src/swarm/SwarmController.ts.

    Import types from ./swarmTypes (SwarmManifest, SwarmAgent, SubTask, SWARM_DIR, MAX_CONCURRENT_AGENTS, SWARM_RESULT_EVENT). Import coordinatorDecompose, synthesizeResults, buildTaskFileContent from ./coordinator. Import parseResultFile from ./resultParser. Import registerSwarmAgent, updateSwarmAgentStatus, unregisterSwarmAgents from ./swarmRegistry. Import invoke from "@tauri-apps/api/core". Import listen from "@tauri-apps/api/event". Import showToast from "../command-palette/toast".

    Export class SwarmController:

    Private fields:
      - manifest: SwarmManifest | null
      - unlistenResult: (() => void) | null (cleanup for Tauri event listener)
      - timeoutIds: Map<string, ReturnType<typeof setTimeout>> (per-agent timeout timers)
      - onApplyPreset: ((preset: "swarm") => void) | null (callback for layout, per RESEARCH anti-pattern: controller does not own gridController)
      - onSwarmComplete: ((summary: string) => void) | null (callback for completion notification)

    Constructor(opts: { onApplyPreset?: (preset: "swarm") => void; onSwarmComplete?: (summary: string) => void }):
      - Store callbacks

    async launch(goal: string, workspacePath: string): Promise<void>:
      1. Get API key: invoke("get_env_var", { name: "ANTHROPIC_API_KEY" }). If it rejects or returns empty, showToast("error", "ANTHROPIC_API_KEY not set...") and return early.
      2. Read repo tree: invoke("list_dir", { path: workspacePath }) — this existing command returns file listing. If fails, use empty string.
      3. Read CLAUDE.md: invoke("fs_read_text" or similar) for {workspacePath}/CLAUDE.md. If not found, use empty string. Per D-11.
      4. Call coordinatorDecompose(goal, repoTree, claudeMd, apiKey). If throws, showToast("error", "Swarm coordinator failed: " + error message) and return.
      5. Enforce MAX_CONCURRENT_AGENTS: slice subtasks to first 6 if longer. Per D-12.
      6. Build manifest: { id: "swarm-" + Date.now(), goal, status: "running", created: Date.now(), agents: subtasks mapped to SwarmAgent with status "pending", paneId/ptyId empty strings initially }
      7. Build task file content for each subtask via buildTaskFileContent.
      8. Build shared context: CLAUDE.md content (or excerpt) per D-11.
      9. Call invoke("write_swarm_files", { workspacePath, manifestJson: JSON.stringify(manifest), tasks: array of [filename, content] tuples, sharedContext }). Wait for completion. Per Pitfall 3, watcher starts AFTER this succeeds.
      10. Apply swarm layout preset: call this.onApplyPreset?.("swarm"). Per D-10, SWM-10.
      11. Spawn each agent: for each subtask, create a new PtyTransport is NOT the controller's concern — instead, invoke("spawn_agent", { onData: channel, rows: 40, cols: 120, cwd: workspacePath, cliBinary: subtask.cli, cliArgs: ["Read '.voss/swarm/tasks/{subtask.id}.task.md' and follow the instructions."], paneId: generatedPaneId, workspacePath, sessionId: crypto.randomUUID() }). Actually, since spawn_agent requires a Channel, and PtyTransport wraps that, the controller should accept a spawnFn callback: (subtask: SubTask) => Promise<{ paneId: string; ptyId: string }>. The App.tsx integration layer will provide this. Store returned paneId and ptyId on the SwarmAgent in manifest.
      12. After each spawn, register the agent in swarmRegistry: registerSwarmAgent(paneId, { swarmId: manifest.id, goal, agentPaneId: paneId, agentId: subtask.id, cli: subtask.cli, status: "running" })
      13. Update manifest agents with real paneId/ptyId values and status "running".
      14. Persist updated manifest: invoke("write_swarm_files", { workspacePath, manifestJson: JSON.stringify(manifest), tasks: [], sharedContext: "" }) — empty tasks/shared to avoid overwrite (or add a separate write_swarm_manifest command). Actually, reuse write_swarm_files with empty tasks array (it only writes task files for non-empty list).
      15. Start result watcher: invoke("watch_swarm_results", { swarmId: manifest.id, resultsDir: workspacePath + "/" + SWARM_DIR + "/results" })
      16. Listen for result events: this.unlistenResult = await listen(SWARM_RESULT_EVENT, (event) => this.handleResultEvent(event.payload, workspacePath))
      17. Start timeout timer for each agent: per D-22, 10 minutes (configurable). On timeout, call updateSwarmAgentStatus(paneId, "stuck") and showToast("warning", "Agent {id} appears stuck").

    handleResultEvent(payload: { swarmId: string; resultFile: string }, workspacePath: string): void:
      - If payload.swarmId !== this.manifest?.id, ignore
      - Extract agentId from resultFile (e.g. "agent-1.result.md" -> "agent-1")
      - Read the result file content: invoke a Rust command to read the file, or use a simple Tauri invoke. Since we need file content, add a read_file Tauri command OR use an existing one. Check if there is an existing fs_read command. If not, the result summary can be read later at synthesis time. For now, mark the agent as "complete" in the registry and cancel its timeout.
      - updateSwarmAgentStatus(paneId, "complete") — look up paneId from manifest by agentId
      - Clear timeout for this agent
      - Check if all agents are complete: if so, call finishSwarm(workspacePath)

    handlePtyExit(paneId: string): void:
      - Per D-21 fallback: if an agent's PTY exits and we haven't received a result file, mark it as "complete" (agent may have finished without writing result, or crashed)
      - Update status to "complete" in swarmRegistry
      - Clear timeout
      - Check if all agents complete

    async finishSwarm(workspacePath: string): Promise<void>:
      - Stop watcher: invoke("stop_swarm_watcher", { swarmId: manifest.id })
      - Unlisten result events
      - Read all result files from .voss/swarm/results/ (one Tauri invoke per file or a batch read)
      - Parse each with parseResultFile
      - Build synthesis: synthesizeResults(manifest.goal, parsed results mapped to { agentId, summary })
      - Update manifest status to "complete"
      - Persist manifest
      - Call this.onSwarmComplete?.(synthesis)
      - showToast("success", "Swarm complete: " + manifest.goal.slice(0, 50))

    cancel(): void:
      - Per D-09: stop all agents
      - For each agent in manifest with status !== "complete": invoke("pty_kill", { sessionId: agent.ptyId })
      - Stop watcher
      - Unlisten events
      - Clear all timeouts
      - Update manifest status to "cancelled", persist
      - unregisterSwarmAgents(manifest.id)
      - showToast("info", "Swarm cancelled")

    stopAgent(paneId: string): void:
      - Per D-09: stop individual agent
      - Find agent by paneId in manifest
      - invoke("pty_kill", { sessionId: agent.ptyId })
      - updateSwarmAgentStatus(paneId, "error")
      - Clear timeout for this agent
      - Check if all done

    async resume(workspacePath: string): Promise<void>:
      - Per SWM-12: read manifest.json from .voss/swarm/
      - If manifest.status !== "running", return (already finished)
      - Re-register agents in swarmRegistry with their persisted status
      - Restart result watcher for agents still in "running" or "pending" status
      - Restart timeouts for non-complete agents
      - Do NOT re-spawn agents (they may still be running in existing PTYs)

    getManifest(): SwarmManifest | null:
      - Return current manifest

    For reading CLAUDE.md and result files, use a new Tauri command or reuse an existing one. Check if there is a read_file or fs_read_text command. If not, the controller should accept a readFile callback in its constructor opts, which App.tsx can wire to read via Tauri invoke.

    Create apps/voss-app/src/swarm/__tests__/SwarmController.test.ts:
      - Mock @tauri-apps/api/core invoke and @tauri-apps/api/event listen
      - Mock coordinator.ts (coordinatorDecompose, synthesizeResults, buildTaskFileContent)
      - Mock resultParser.ts (parseResultFile)
      - Mock swarmRegistry.ts (registerSwarmAgent, updateSwarmAgentStatus, unregisterSwarmAgents)
      - Mock showToast

      Tests:
      - "launch: calls coordinator, writes files, spawns agents, starts watcher": Verify invoke sequence and swarmRegistry calls. Verify layout preset callback called.
      - "launch: fails gracefully when API key missing": Verify showToast error, no coordinator call.
      - "launch: fails gracefully when coordinator throws": Verify showToast error, no file writes.
      - "handleResultEvent: marks agent complete, checks all-done": Verify updateSwarmAgentStatus called with "complete".
      - "handleResultEvent: triggers finishSwarm when all agents complete": Verify synthesis called, manifest updated.
      - "handlePtyExit: fallback completion detection": Verify agent marked complete on PTY exit.
      - "cancel: stops all agents, cleans up watcher and timeouts": Verify pty_kill called for each running agent, stop_swarm_watcher called.
      - "stopAgent: stops individual agent": Verify single pty_kill call.
      - "timeout: marks agent stuck after 10 minutes": Use vi.useFakeTimers, advance 10 minutes, verify "stuck" status.
      - "resume: re-registers agents from manifest": Provide mock manifest, verify swarmRegistry calls.
      - "manifest persistence: writes updated manifest after spawn": Verify write_swarm_files called with updated manifest.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/swarm/__tests__/SwarmController.test.ts --reporter=verbose 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - SwarmController.ts exports SwarmController class
    - swarmRegistry.ts exports swarmByPaneId, registerSwarmAgent, updateSwarmAgentStatus, unregisterSwarmAgents, getActiveSwarm
    - SwarmController.launch() calls coordinatorDecompose, invoke("write_swarm_files"), spawns agents, invoke("watch_swarm_results"), listen(SWARM_RESULT_EVENT)
    - SwarmController.cancel() calls pty_kill for all running agents and stop_swarm_watcher
    - SwarmController.handleResultEvent() updates swarmRegistry and checks all-done
    - SwarmController.handlePtyExit() provides D-21 fallback completion
    - Timeout marks agents as "stuck" per D-22
    - Resume reads manifest and re-registers agents without re-spawning
    - Layout preset callback called during launch per D-10
    - All unit tests pass
    - tsc --noEmit passes
  </acceptance_criteria>
  <done>SwarmController orchestrates full lifecycle (launch/cancel/resume/result-handling/timeout), swarmRegistry provides reactive state, all tests pass</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SwarmController -> Tauri commands | invoke calls to write_swarm_files, spawn_agent, pty_kill, watch/stop watcher |
| SwarmController -> Anthropic API (via coordinator) | LLM call with user goal text |
| Agent CLI -> filesystem | Agents write result files (soft trust per D-20) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A13-07 | Tampering | SwarmController.launch goal text | mitigate | Goal is passed to coordinator prompt as-is; coordinator prompt wraps it in a structured template that separates instruction from user input |
| T-A13-08 | Denial of Service | MAX_CONCURRENT_AGENTS | mitigate | Hard cap at 6 agents (D-12); coordinator output sliced if longer; prevents resource exhaustion |
| T-A13-09 | Tampering | Agent writes to unexpected files | accept | Soft scope enforcement per D-20; agents are instruction-following CLIs; accepted design trade-off |
| T-A13-SC | Tampering | npm installs | mitigate | No new npm installs in this plan; deps from Plan 02 already verified |
</threat_model>

<verification>
All SwarmController tests pass.
tsc --noEmit passes.
swarmRegistry signal store is reactive and follows budgetRegistry pattern.
</verification>

<success_criteria>
SwarmController can orchestrate a full swarm lifecycle with mocked Tauri commands. swarmRegistry provides reactive state for sidebar consumption. All edge cases (missing API key, coordinator failure, timeout, cancel, resume) handled.
</success_criteria>

<output>
Create `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-03-SUMMARY.md` when done
</output>

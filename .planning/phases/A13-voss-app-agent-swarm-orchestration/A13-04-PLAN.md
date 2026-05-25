---
phase: A13-voss-app-agent-swarm-orchestration
plan: 04
type: execute
wave: 2
depends_on:
  - A13-01
files_modified:
  - apps/voss-app/src/components/sidebar/AgentSidebar.tsx
  - apps/voss-app/src/components/sidebar/AgentItem.tsx
  - apps/voss-app/src/components/sidebar/AgentContextMenu.tsx
  - apps/voss-app/src/components/modal/AgentLaunchModal.tsx
  - apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx
  - apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx
autonomous: true
requirements:
  - SWM-01
  - SWM-08
  - SWM-09

must_haves:
  truths:
    - "User can launch a swarm from a Swarm tab in the launch modal by entering a natural language goal"
    - "Sidebar AGENTS section displays swarm agents grouped under a swarm header with progress"
    - "Swarm group header shows goal text and completion count (e.g. 2/4 complete)"
    - "Context menu shows 'Stop swarm' option when right-clicking a swarm agent"
    - "Context menu 'Stop swarm' action is available and calls the onStopSwarm callback"
  artifacts:
    - path: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      provides: "Swarm tab in launch modal with goal text input"
      contains: "swarm"
    - path: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      provides: "Swarm group display with header and per-agent cards"
      contains: "swarmId"
    - path: "apps/voss-app/src/components/sidebar/AgentContextMenu.tsx"
      provides: "Stop swarm menu item"
      contains: "Stop swarm"
    - path: "apps/voss-app/src/components/sidebar/AgentItem.tsx"
      provides: "Swarm badge on agent items"
      contains: "swarmStatus"
  key_links:
    - from: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      to: "apps/voss-app/src/App.tsx"
      via: "onLaunchSwarm callback prop"
      pattern: "onLaunchSwarm"
    - from: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      to: "apps/voss-app/src/swarm/swarmRegistry.ts"
      via: "agents prop includes swarmId/swarmStatus fields from App.tsx memo"
      pattern: "swarmId"
---

<objective>
Add swarm-specific UI: the Swarm tab in the launch modal and swarm grouping/controls in the sidebar.

Purpose: Per D-15/SWM-01, the user launches a swarm via a Swarm tab in the existing AgentLaunchModal. Per D-08/SWM-08, swarm agents appear in the sidebar with a swarm group header showing progress. Per D-09/SWM-09, the context menu provides "Stop swarm" to cancel the entire swarm.

Output: Modified AgentLaunchModal with Swarm tab, modified AgentSidebar with swarm grouping, modified AgentContextMenu with stop-swarm action, extended AgentItem with swarm badge. Tests for all UI changes.
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

<interfaces>
<!-- From existing codebase -->

From apps/voss-app/src/components/modal/AgentLaunchModal.tsx:
```typescript
type CliTab = 'claude' | 'codex' | 'antigravity' | 'opencode' | 'voss' | 'custom';
const CLI_TABS: { id: CliTab; label: string }[] = [
  { id: 'claude', label: 'Claude' },
  { id: 'codex', label: 'Codex' },
  { id: 'antigravity', label: 'Antigravity' },
  { id: 'opencode', label: 'OpenCode' },
  { id: 'voss', label: 'Voss' },
  { id: 'custom', label: 'Custom' },
];
export interface AgentLaunchConfig {
  // existing fields for single agent launch
}
export interface AgentLaunchModalProps {
  onDismiss: () => void;
  onLaunch: (config: AgentLaunchConfig) => void;
}
```

From apps/voss-app/src/components/sidebar/AgentSidebar.tsx:
```typescript
type AgentEntry = Omit<AgentItemProps, 'onClick' | 'onContextMenu' | 'isActive'>;
export interface AgentSidebarProps {
  // ...
  agents: AgentEntry[];
  // ...
}
```

From apps/voss-app/src/components/sidebar/AgentItem.tsx:
```typescript
export interface AgentItemProps {
  paneId: string;
  cliBinary: string;
  model: string;
  role: string;
  costUsd: number;
  isStreaming: boolean;
  isActive: boolean;
  taskPrompt?: string;
  tokensUsed?: number;
  tokenLimit?: number | null;
  onContextMenu?: (e: MouseEvent) => void;
  onClick?: () => void;
}
```

From apps/voss-app/src/components/sidebar/AgentContextMenu.tsx:
```typescript
export interface AgentContextMenuProps {
  anchor: HTMLElement;
  paneId: string;
  costUsd: number;
  onClose: () => void;
  onFocusPane: (paneId: string) => void;
  onStopAgent: (paneId: string) => void;
  onRestartAgent: (paneId: string) => void;
  onDetachAgent: (paneId: string) => void;
}
```

From apps/voss-app/src/swarm/swarmTypes.ts (Plan 01):
  export type SwarmAgentStatus = 'pending' | 'running' | 'complete' | 'stuck' | 'error';
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Swarm tab to AgentLaunchModal</name>
  <files>apps/voss-app/src/components/modal/AgentLaunchModal.tsx, apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx</files>
  <read_first>
    apps/voss-app/src/components/modal/AgentLaunchModal.tsx (full file)
    apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx (existing tests)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (D-15: sidebar button + launch modal Swarm tab)
  </read_first>
  <action>
    Modify AgentLaunchModal.tsx:

    A. Extend the CliTab union type: add "swarm" to the union. It becomes: type CliTab = "claude" | "codex" | "antigravity" | "opencode" | "voss" | "custom" | "swarm"

    B. Add swarm tab entry to CLI_TABS array: { id: "swarm", label: "Swarm" } — append as the 7th entry per D-15.

    C. Add a swarmGoal signal: const [swarmGoal, setSwarmGoal] = createSignal("")

    D. Add onLaunchSwarm prop to AgentLaunchModalProps: onLaunchSwarm?: (goal: string) => void. This is optional to maintain backward compat.

    E. When activeTab() === "swarm", render a different body section instead of the normal agent config form. The swarm body contains:
       - A heading: "Launch Agent Swarm"
       - A description paragraph: "Enter a goal. The coordinator will decompose it into parallel subtasks and assign agents automatically." (per D-16)
       - A textarea for the goal text, bound to swarmGoal signal. Placeholder: "e.g., Refactor the auth module and add comprehensive tests"
       - The existing "Launch" button at the bottom. When clicked with swarm tab active:
         - If swarmGoal is empty, do nothing
         - Call props.onLaunchSwarm?.(swarmGoal())
         - Call props.onDismiss()

    F. The normal agent config form (model selector, effort level, task prompt, etc.) should be wrapped in a Show when={activeTab() !== "swarm"} guard so it does not render on the swarm tab.

    G. Style the swarm tab body to match existing modal aesthetic: same padding, font, colors using CSS variables (--fg-1, --bg-2, etc.). Textarea should be full-width, min-height 100px, styled with bg-bg-2 border border-bright rounded.

    Extend AgentLaunchModal.test.tsx:
    - Test that the Swarm tab renders when clicking the "Swarm" tab button
    - Test that the swarm body shows a textarea when swarm tab is active
    - Test that clicking Launch with swarm tab calls onLaunchSwarm with the entered goal
    - Test that the normal config form is hidden when swarm tab is active
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/components/modal/__tests__/AgentLaunchModal.test.tsx --reporter=verbose 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - CliTab type includes "swarm"
    - CLI_TABS array has 7 entries, last is { id: "swarm", label: "Swarm" }
    - AgentLaunchModalProps has onLaunchSwarm?: (goal: string) => void
    - Swarm tab renders textarea for goal input
    - Launch button calls onLaunchSwarm when swarm tab active
    - Normal config form hidden on swarm tab
    - All existing AgentLaunchModal tests still pass
    - New swarm-specific tests pass
  </acceptance_criteria>
  <done>Swarm tab added to launch modal with goal text entry, Launch button wired to onLaunchSwarm callback, all tests pass</done>
</task>

<task type="auto">
  <name>Task 2: Add swarm grouping to AgentSidebar and stop-swarm action to AgentContextMenu</name>
  <files>apps/voss-app/src/components/sidebar/AgentSidebar.tsx, apps/voss-app/src/components/sidebar/AgentItem.tsx, apps/voss-app/src/components/sidebar/AgentContextMenu.tsx, apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx</files>
  <read_first>
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx (full file)
    apps/voss-app/src/components/sidebar/AgentItem.tsx (full file)
    apps/voss-app/src/components/sidebar/AgentContextMenu.tsx (full file)
    apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx (existing tests)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (D-08: swarm group indicator, D-09: stop swarm)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md (Pattern 6: Sidebar Swarm Group Display)
  </read_first>
  <action>
    A. Extend AgentItemProps in AgentItem.tsx:
       - Add optional swarmId?: string
       - Add optional swarmStatus?: string (SwarmAgentStatus values)
       - When swarmStatus is present, render a small badge next to the agent name showing the status. Use a colored dot: green for "complete", amber for "running", gray for "pending", red for "stuck"/"error". Display as a 6px circle with appropriate CSS var colors (--accent for running, --fg-dim for pending, --success or green for complete, --error for stuck/error).

    B. Modify AgentSidebar.tsx to group swarm agents:
       - The agents prop already receives entries from App.tsx's agentListForSidebar memo. After Plan 05 wires it, entries will include swarmId and swarmStatus fields. For now, add the optional fields to the AgentEntry type (Omit<AgentItemProps, ...> already picks up the new AgentItemProps fields).
       - In the AGENTS section rendering, split agents into two groups:
         1. Non-swarm agents (no swarmId): render as before
         2. Swarm agents (have swarmId): group by swarmId. For each group:
            - Render a swarm group header div: "Swarm: {goal}" (truncated to 40 chars) + " ({N}/{M} complete)" where N = agents with status "complete", M = total in group
            - Style: 11px font, fg-dim color, padding 4px 12px, border-bottom border-bright
            - Below the header, render each agent in the group using the existing AgentItem component (passing through all props + the new swarmId/swarmStatus)
       - The swarm group header should also show a "Cancel" button (small, text-only, fg-dim, hover fg-error) that calls a new onStopSwarm prop.

    C. Add onStopSwarm prop to AgentSidebarProps:
       - onStopSwarm?: (swarmId: string) => void
       - The swarm group header Cancel button calls this with the swarmId

    D. Extend AgentContextMenu.tsx:
       - Add optional swarmId?: string prop to AgentContextMenuProps
       - Add optional onStopSwarm?: (swarmId: string) => void prop
       - When swarmId is present, add a "Stop swarm" menu item after the separator (before or after existing items). Style matches existing items. On click, call onStopSwarm?.(swarmId) then onClose().
       - The "Stop swarm" item uses a red-ish color (--error) to indicate destructive action.

    E. Extend AgentSidebar.test.tsx:
       - Test that agents without swarmId render normally (existing behavior preserved)
       - Test that agents with swarmId are grouped under a swarm header
       - Test that swarm header shows correct completion count (e.g. "1/3 complete")
       - Test that swarm header Cancel button calls onStopSwarm
       - Test that context menu shows "Stop swarm" when swarmId is present
       - Test that context menu does NOT show "Stop swarm" when swarmId is absent
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/components/sidebar/__tests__/AgentSidebar.test.tsx --reporter=verbose 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - AgentItemProps has swarmId? and swarmStatus? optional fields
    - AgentItem renders a status badge dot when swarmStatus is present
    - AgentSidebar groups agents by swarmId with a header showing "Swarm: {goal} (N/M complete)"
    - AgentSidebarProps has onStopSwarm?: (swarmId: string) => void
    - AgentContextMenuProps has swarmId? and onStopSwarm? optional fields
    - "Stop swarm" menu item appears only when swarmId is present
    - All existing sidebar and context menu tests still pass
    - All new swarm-specific tests pass
    - tsc --noEmit passes
  </acceptance_criteria>
  <done>Sidebar shows swarm groups with progress headers, context menu offers stop-swarm, all tests pass</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User input -> goal text | User-provided goal enters the system via textarea |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A13-10 | Tampering | Goal text from modal textarea | accept | Goal text is passed to coordinator as user intent; it will be interpolated into an LLM prompt (handled by coordinator.ts sanitization, not a UI concern) |
| T-A13-11 | Denial of Service | Swarm group rendering | accept | MAX_CONCURRENT_AGENTS caps at 6 agents per swarm; sidebar renders at most 6 items per group |
| T-A13-SC | Tampering | npm installs | mitigate | No new npm installs in this plan |
</threat_model>

<verification>
All sidebar and modal tests pass.
tsc --noEmit passes.
Existing tests do not regress.
</verification>

<success_criteria>
Launch modal has a Swarm tab with goal text entry. Sidebar groups swarm agents with progress header. Context menu offers stop-swarm action. All UI changes are tested and backward compatible with non-swarm agent display.
</success_criteria>

<output>
Create `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-04-SUMMARY.md` when done
</output>

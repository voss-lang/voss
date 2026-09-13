---
phase: A12-voss-app-ade-visual-redesign
plan: 03
type: execute
wave: 2
depends_on:
  - A12-01
  - A12-02
files_modified:
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/grid/GridRoot.tsx
  - apps/voss-app/src/grid/operations.ts
  - apps/voss-app/src/command-palette/registry.ts
  - apps/voss-app/src/pane/PaneComponent.tsx
autonomous: true
requirements:
  - ADE-03

must_haves:
  truths:
    - "Sidebar is visible by default on app launch"
    - "Cmd+Shift+B toggles sidebar open and closed"
    - "Sidebar collapsed state persists in localStorage across app restarts"
    - "Grid resizes smoothly via ResizeObserver when sidebar toggles"
    - "Clicking an agent in sidebar focuses its pane in grid (bidirectional sync)"
    - "Focusing a pane in grid highlights its agent in sidebar"
    - "ContextPanel coexists with sidebar (both can be open simultaneously)"
  artifacts:
    - path: "apps/voss-app/src/App.tsx"
      provides: "Sidebar state signals, layout integration, bidirectional focus sync"
      contains: "sidebarCollapsed"
    - path: "apps/voss-app/src/grid/GridRoot.tsx"
      provides: "focusPaneById method on GridController"
      contains: "focusPaneById"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      via: "JSX render with props"
      pattern: "<AgentSidebar"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/grid/GridRoot.tsx"
      via: "gridController().focusPaneById(paneId)"
      pattern: "focusPaneById"
    - from: "apps/voss-app/src/App.tsx"
      to: "apps/voss-app/src/pane/budgetRegistry.ts"
      via: "budgetByPaneId() for agent list derivation"
      pattern: "budgetByPaneId"
---

<objective>
Wire AgentSidebar into App.tsx layout. Add sidebar state signals (collapsed, localStorage persistence), Cmd+Shift+B keybinding, bidirectional focus sync between sidebar and grid. Add focusPaneById to GridController. Wire budgetRegistry into PaneComponent.

Purpose: This is the critical integration plan that connects P1 (theme) and P2 (sidebar shell) into a working sidebar experience.
Output: Sidebar visible in app layout, toggle keybinding, focus sync, budget data flowing.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-CONTEXT.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-01-SUMMARY.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-02-SUMMARY.md

<interfaces>
<!-- From P2 (AgentSidebar) -->
AgentSidebarProps: { collapsed, onToggle, agents, focusedPaneId, onAgentClick, onAgentContextMenu, onLaunchAgent, sessions, projectPath, workspacePath }

<!-- From P2 (budgetRegistry) -->
budgetByPaneId(): Record<string, BudgetEntry>
registerPaneBudget(paneId, data): void
unregisterPaneBudget(paneId): void

<!-- From existing App.tsx -->
contextPanelOpen / toggleContextPanel pattern (localStorage, createSignal)
focusedPaneId signal (already exists line 229)
agentConfigByPaneId on MountedWorkspace (already exists line 148)

<!-- From existing GridRoot.tsx -->
GridController type (line 95-112): does NOT have focusPaneById yet
collectLeaves(root): PaneLeaf[] (from tree.ts, already imported in App.tsx)
onFocusChange prop (already exists on GridRoot)

<!-- From existing registry.ts -->
AppContext interface: has startAgent callback (line 70)
CommandCategory: 'Window' | 'Workspace' | 'Pane' | 'Layout' | 'Project' | 'Settings' | 'Help'
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add focusPaneById to GridController and wire budgetRegistry into PaneComponent</name>
  <files>
    apps/voss-app/src/grid/GridRoot.tsx,
    apps/voss-app/src/pane/PaneComponent.tsx
  </files>
  <read_first>
    apps/voss-app/src/grid/GridRoot.tsx,
    apps/voss-app/src/grid/tree.ts (collectLeaves function),
    apps/voss-app/src/pane/PaneComponent.tsx,
    apps/voss-app/src/pane/budgetRegistry.ts,
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 2: focusPaneById, Finding 3: budgetRegistry wiring)
  </read_first>
  <action>
    1. In GridRoot.tsx:
       - Add focusPaneById(paneId: string) => void to the GridController type (after focusDirection)
       - Implement in the controller object returned via controllerRef callback:
         Use collectLeaves(store.root) to find the leaf with matching id.
         If found, call setStore(produce((s) => { s.focusedId = paneId; })) then props.onFocusChange?.(paneId)
         If not found, return silently (no error)
       - collectLeaves is already imported from ./tree

    2. In PaneComponent.tsx:
       - Import registerPaneBudget and unregisterPaneBudget from ../pane/budgetRegistry
       - In the onBudgetUpdate callback (where BudgetState is received from the PTY event handler), call registerPaneBudget(paneId, budgetData) alongside the existing local signal update
       - In onCleanup, call unregisterPaneBudget(paneId)
       - This wires cost data into the shared registry so the sidebar and status bar can read it reactively
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - GridController type includes focusPaneById: (paneId: string) => void
    - Controller implementation walks tree via collectLeaves and sets store.focusedId
    - PaneComponent calls registerPaneBudget on budget_update events and unregisterPaneBudget on cleanup
    - TypeScript compiles with no errors
  </acceptance_criteria>
  <done>focusPaneById added to GridController. Budget data flows from PaneComponent to shared registry.</done>
</task>

<task type="auto">
  <name>Task 2: Wire sidebar into App.tsx layout with state, keybinding, and focus sync</name>
  <files>
    apps/voss-app/src/App.tsx,
    apps/voss-app/src/command-palette/registry.ts
  </files>
  <read_first>
    apps/voss-app/src/App.tsx,
    apps/voss-app/src/command-palette/registry.ts,
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    apps/voss-app/src/pane/budgetRegistry.ts,
    apps/voss-app/src/pane/agentDetect.ts
  </read_first>
  <action>
    1. In App.tsx, add sidebar state signals following the contextPanelOpen pattern:
       - createSignal for sidebarCollapsed, initialized from localStorage.getItem('voss:sidebarCollapsed') === 'true'
       - Per D-03: visible by default, so falsy default is correct (collapsed=false by default)
       - toggleSidebar function: flips collapsed, persists to localStorage 'voss:sidebarCollapsed'

    2. Add agent list derivation memo in App.tsx (inside App component, after activeMounted):
       - Import budgetByPaneId from ../pane/budgetRegistry
       - Import isKnownAgentCli from ../pane/agentDetect
       - createMemo agentListForSidebar that derives from activeMounted().agentConfigByPaneId() and budgetByPaneId()
       - Filter entries by isKnownAgentCli(cfg.cliBinary) per D-08
       - Map each entry to { paneId, cliBinary, model (parsed from cliArgs --model=X), costUsd, isStreaming (Date.now() - lastSeenMs < 3000), role (derive from cliBinary: claude->planner, codex->executor, gemini->reviewer, etc.) }

    3. In App.tsx onAppKey handler, add Cmd+Shift+B handling BEFORE the chord-based registry dispatch:
       - Check: e.metaKey && e.shiftKey && e.key === 'b' (or e.key === 'B')
       - Call toggleSidebar()
       - e.preventDefault(); e.stopImmediatePropagation(); return;

    4. Also add toggleSidebar to AppContext (add toggleSidebar?: () => void to the AppContext interface in registry.ts, and set appCtx.toggleSidebar = toggleSidebar in App.tsx)

    5. In registry.ts v0Commands, add a new command definition:
       - id: 'sidebar.toggle', label: 'Toggle Sidebar', category: 'Window', keybinding: 'Cmd+Shift+B', handler: (ctx) => ctx.toggleSidebar?.()

    6. Modify the App.tsx JSX layout. The current structure at line ~938 has:
       Titlebar -> WorkspaceTabBar -> flex-column div -> (Show grid | SetupWindow) -> StatusBar
       Inside the Show(when=showGrid) block, the content area is a flex-column div containing For(workspaceIds) and ContextPanel.
       Change the inner content div from flex-direction: column to flex-direction: row.
       Place AgentSidebar BEFORE the workspaces For loop:
         <AgentSidebar
           collapsed={sidebarCollapsed()}
           onToggle={toggleSidebar}
           agents={agentListForSidebar()}
           focusedPaneId={focusedPaneId()}
           onAgentClick={(paneId) => gridController()?.focusPaneById(paneId)}
           onAgentContextMenu={(paneId, e) => { /* wired in P4 */ }}
           onLaunchAgent={() => { /* wired in P4 */ }}
           sessions={[]}
           projectPath={activeMounted()?.project()?.path ?? null}
           workspacePath={workspacePath() ?? null}
         />
       Wrap the For loop + ContextPanel in a new flex-column div with flex: 1, min-width: 0, position: relative.
       The ContextPanel remains position: absolute overlay within the grid area (D-07: coexists, not flex child).

    7. Import AgentSidebar from './components/sidebar/AgentSidebar' at top of App.tsx.
       Import budgetByPaneId from './pane/budgetRegistry'.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20 && npx vitest run 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Sidebar renders inside the grid content area, left of the workspace grid
    - sidebarCollapsed state persisted in localStorage key 'voss:sidebarCollapsed'
    - Cmd+Shift+B toggles sidebar (handled in onAppKey before registry dispatch)
    - 'sidebar.toggle' command registered in v0Commands with keybinding 'Cmd+Shift+B'
    - Clicking agent in sidebar calls gridController().focusPaneById(paneId)
    - Agent list derived from agentConfigByPaneId filtered by isKnownAgentCli
    - ContextPanel coexists with sidebar (position absolute, not flex child)
    - All existing tests pass
  </acceptance_criteria>
  <done>Sidebar wired into App.tsx. Toggle via Cmd+Shift+B. Bidirectional focus sync. Agent list derives from existing signals. ContextPanel coexists.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sidebar click -> grid focus | User click in sidebar triggers grid focus change |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-03 | Tampering | localStorage sidebar state | accept | UI preference only; no security impact |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test — all tests green.
npx tsc --noEmit — zero type errors.
Manual: pnpm dev, sidebar visible by default, Cmd+Shift+B collapses/expands.
</verification>

<success_criteria>
1. Sidebar visible by default per D-03.
2. Cmd+Shift+B toggles per D-03.
3. Collapsed state persists via localStorage.
4. Grid resizes when sidebar toggles (ResizeObserver handles reflow).
5. Click agent -> focuses pane (D-22 sidebar->grid direction).
6. Focus pane -> highlights agent in sidebar (D-22 grid->sidebar direction via focusedPaneId prop).
7. ContextPanel coexists per D-07.
8. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-03-SUMMARY.md` when done
</output>

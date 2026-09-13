---
phase: A12-voss-app-ade-visual-redesign
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/components/sidebar/AgentSidebar.tsx
  - apps/voss-app/src/components/sidebar/AgentItem.tsx
  - apps/voss-app/src/components/sidebar/SessionsSection.tsx
  - apps/voss-app/src/components/sidebar/sidebar.css
  - apps/voss-app/src/pane/budgetRegistry.ts
  - apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx
autonomous: true
requirements:
  - ADE-02

must_haves:
  truths:
    - "AgentSidebar component renders with 4 sections in order: AGENTS, SESSIONS, FILES, GIT"
    - "Sidebar is 280px wide with 2px orange left accent bar"
    - "Sidebar header has Voss logo, Agents label, + Agent button, and collapse chevron"
    - "Agent items show status dot, name, model, role pill, and cost"
    - "Budget registry shares pane cost data reactively across consumers"
    - "Sidebar accepts collapsed boolean and animates width to 0"
  artifacts:
    - path: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      provides: "Main sidebar component with 4 sections"
      exports: ["AgentSidebar", "AgentSidebarProps"]
    - path: "apps/voss-app/src/components/sidebar/AgentItem.tsx"
      provides: "Individual agent row component"
      exports: ["AgentItem", "AgentItemProps"]
    - path: "apps/voss-app/src/pane/budgetRegistry.ts"
      provides: "Shared reactive budget/cost registry mirroring procRegistry pattern"
      exports: ["budgetByPaneId", "registerPaneBudget", "unregisterPaneBudget"]
  key_links:
    - from: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      to: "apps/voss-app/src/components/sidebar/AgentItem.tsx"
      via: "For each agent import"
      pattern: "import.*AgentItem"
    - from: "apps/voss-app/src/pane/budgetRegistry.ts"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "BudgetState type import"
      pattern: "import.*BudgetState"
---

<objective>
Create the AgentSidebar component shell with all 4 sections (Agents/Sessions/Files/Git) and the supporting budgetRegistry module. This is the pure component — no App.tsx wiring yet (that is P3).

Purpose: Sidebar component is the largest new UI surface in A12. Building it in isolation enables parallel development with P1 (theme).
Output: AgentSidebar.tsx, AgentItem.tsx, SessionsSection.tsx, sidebar.css, budgetRegistry.ts, tests.
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

<interfaces>
<!-- Existing types the sidebar consumes -->

From apps/voss-app/src/pane/pty-ipc.ts:
- BudgetState = { tokens_used: number; token_limit: number | null; cost_usd: number; iteration: number; model: string }
- AgentConfig = { cliBinary: string; cliArgs: string[]; sessionId: string }

From apps/voss-app/src/pane/agentDetect.ts:
- isKnownAgentCli(proc: string): boolean
- KNOWN_AGENT_CLIS: Set<string> — claude, codex, gemini, opencode, aider, cursor

From apps/voss-app/src/pane/procRegistry.ts (pattern to mirror):
- procByPaneId signal, registerPaneProc(paneId, proc), unregisterPaneProc(paneId)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create budgetRegistry and AgentSidebar component tree</name>
  <files>
    apps/voss-app/src/pane/budgetRegistry.ts,
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    apps/voss-app/src/components/sidebar/AgentItem.tsx,
    apps/voss-app/src/components/sidebar/SessionsSection.tsx,
    apps/voss-app/src/components/sidebar/sidebar.css
  </files>
  <read_first>
    apps/voss-app/src/pane/procRegistry.ts,
    apps/voss-app/src/pane/pty-ipc.ts,
    apps/voss-app/src/pane/agentDetect.ts,
    apps/voss-app/src/components/ContextPanel.tsx,
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md (Component Contracts: AgentSidebar),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 3: budgetRegistry, Finding 7: drag pattern, Finding 11: streaming detection)
  </read_first>
  <action>
    1. Create apps/voss-app/src/pane/budgetRegistry.ts mirroring procRegistry.ts pattern exactly:
       - Module-level createSignal for budgetByPaneId (Record of string to BudgetEntry)
       - BudgetEntry type extends BudgetState with lastSeenMs: number field (for streaming detection per RESEARCH Finding 11)
       - Export registerPaneBudget(paneId: string, data: BudgetState): void — spreads prev, sets entry with Date.now() as lastSeenMs
       - Export unregisterPaneBudget(paneId: string): void — removes entry
       - Export the budgetByPaneId accessor
       - Same no-op-if-unchanged guard as procRegistry (skip update if identical)

    2. Create apps/voss-app/src/components/sidebar/sidebar.css:
       - .sidebar class: width var(--sidebar-w), flex-shrink 0, overflow hidden, background var(--bg-1), border-right 1px solid var(--border), transition width 200ms cubic-bezier(0.4,0,0.2,1), position relative
       - .sidebar--collapsed class: width 0
       - .sidebar::before pseudo: 2px wide left accent bar, full height, background var(--focus), absolute positioned
       - .sidebar-header class: 44px height, display flex, align-items center, padding 0 8px, gap 4px, border-bottom 1px solid var(--border)
       - .sidebar-section-label class: Poppins 600 11px uppercase, letter-spacing 0.08em, color var(--fg-3), padding 8px 12px 4px
       - .sidebar-section-body class: overflow-y auto
       - .sidebar-expand class: position absolute, left 0, top 50%, transform translateY(-50%), width 16px, height 48px, background var(--bg-2), border 1px solid var(--border), border-left none, border-radius 0 3px 3px 0 (use inline style for radius per global reset), z-index 10, cursor pointer, color var(--fg-2)
       - .agent-item class: 32px height, display flex, align-items center, padding 0 8px, gap 6px, cursor pointer, transition background 80ms ease
       - .agent-item:hover: background var(--bg-2)
       - .agent-item--active: 2px var(--focus) left border via box-shadow or ::before, background var(--focus-soft)
       - .agent-dot: 7px width/height, border-radius 9999px (inline style), flex-shrink 0
       - .agent-dot--streaming: animation voss-pulse 0.8s ease-in-out infinite alternate
       - @keyframes voss-pulse: from opacity 1, to opacity 0.3
       All border-radius values on interactive elements must use inline styles to override global border-radius: 0 reset (per RESEARCH Finding 10).

    3. Create apps/voss-app/src/components/sidebar/AgentItem.tsx:
       Props interface AgentItemProps: paneId string, cliBinary string, model string, role string (planner/executor/reviewer/watcher/user), costUsd number, isStreaming boolean, isActive boolean, onContextMenu callback, onClick callback
       - Render: status dot (role color from --role-{role} var + box-shadow glow), agent name (Inter 12px --fg-0), model (JetBrains Mono 11px --fg-3), role pill (Poppins 600 11px uppercase, 6px inline radius, role color at 20% opacity bg), cost (JetBrains Mono 11px, --fg-2 normally, --focus when > 1.00)
       - Streaming dot uses .agent-dot--streaming class
       - Active state uses .agent-item--active class
       - onContextMenu on the row fires the callback with the event
       - Drag support: draggable attribute, onDragStart sets text/plain data to paneId (HTML5 pattern from WorkspaceTabBar)

    4. Create apps/voss-app/src/components/sidebar/SessionsSection.tsx:
       Props: sessions array of { id: string, description: string, startedAt: number, stoppedAt: number | null }
       - Render each session as a row: relative timestamp (JetBrains Mono 11px --fg-3) + description (Inter 12px --fg-1)
       - Use Intl.RelativeTimeFormat for relative timestamps (per RESEARCH Don't Hand-Roll)
       - Empty state: "No sessions yet" in Inter 12px --fg-3, centered

    5. Create apps/voss-app/src/components/sidebar/AgentSidebar.tsx:
       Props interface AgentSidebarProps: collapsed boolean, onToggle callback, agents array (AgentItemProps data without callbacks), focusedPaneId string | undefined, onAgentClick callback(paneId), onAgentContextMenu callback(paneId, event), onLaunchAgent callback, sessions array, projectPath string | null, workspacePath string | null
       - Sidebar header (44px): Voss logo SVG inline (18px, --focus fill, same 2-path SVG from site/public/logo.svg), "Agents" label (Poppins 500 12px --fg-1), flex spacer, "+ Agent" button (24x24, 3px inline radius, transparent bg, --fg-2 color, hover --focus bg per D-02 and D-14), collapse chevron "◀" button (aria-label "Collapse sidebar")
       - 4 sections per D-01: AGENTS, SESSIONS, FILES, GIT — each with .sidebar-section-label heading
       - AGENTS section: For loop over agents array rendering AgentItem, with isActive derived from props.focusedPaneId === agent.paneId. Empty state: "No agents running" (Inter 12px --fg-3)
       - SESSIONS section: render SessionsSection component. Pass sessions from props.
       - FILES section: placeholder div with "FILES" heading and empty state "No project open" (implementation in P7)
       - GIT section: placeholder div with "GIT" heading and empty state "Not a git repository" (implementation in P8)
       - Collapsed state: entire sidebar div gets .sidebar--collapsed class. When collapsed, render expand handle button outside the sidebar at left edge of parent with class .sidebar-expand, glyph "▸", aria-label "Expand sidebar", onClick fires onToggle
       - Drag-to-reorder: accept onDragOver/onDrop on the agent list area, reorder agents in a local createSignal of paneId order (visual only per D-25)
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - budgetRegistry.ts exports budgetByPaneId, registerPaneBudget, unregisterPaneBudget
    - BudgetEntry type includes lastSeenMs field
    - AgentSidebar.tsx renders 4 section headings: AGENTS, SESSIONS, FILES, GIT in that order
    - sidebar.css defines .sidebar (280px), .sidebar--collapsed (0px), .sidebar::before (2px accent), .sidebar-expand
    - AgentItem.tsx renders dot + name + model + role pill + cost with correct CSS var references
    - SessionsSection.tsx renders rows with relative timestamps or empty state
    - All TypeScript compiles with no errors
  </acceptance_criteria>
  <done>AgentSidebar component tree compiles and renders 4 sections with agent items, sessions, file/git placeholders.</done>
</task>

<task type="auto">
  <name>Task 2: Unit tests for AgentSidebar and budgetRegistry</name>
  <files>
    apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx,
    apps/voss-app/src/pane/__tests__/budgetRegistry.test.ts
  </files>
  <read_first>
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    apps/voss-app/src/pane/budgetRegistry.ts,
    apps/voss-app/src/grid/__tests__/GridRoot.test.tsx (for SolidJS test patterns)
  </read_first>
  <action>
    1. Create apps/voss-app/src/pane/__tests__/budgetRegistry.test.ts:
       - Test: "registerPaneBudget adds entry" — register, read budgetByPaneId(), assert paneId key exists with correct cost_usd and lastSeenMs > 0
       - Test: "unregisterPaneBudget removes entry" — register then unregister, assert key absent
       - Test: "registerPaneBudget updates existing entry" — register twice with different cost_usd, assert latest value

    2. Create apps/voss-app/src/components/sidebar/__tests__/AgentSidebar.test.tsx:
       - Import render from solid-js/web (or existing test utility pattern from GridRoot.test.tsx)
       - Test: "renders 4 section headings" — render AgentSidebar with collapsed=false and empty agents, query for text content AGENTS, SESSIONS, FILES, GIT
       - Test: "collapsed renders with width 0 class" — render with collapsed=true, assert sidebar element has sidebar--collapsed class
       - Test: "renders expand handle when collapsed" — render with collapsed=true, assert element with aria-label "Expand sidebar" exists
       - Test: "renders agent items" — pass 2 mock agents, assert 2 agent items rendered with correct names
       - Test: "empty agents shows placeholder" — pass empty agents array, assert "No agents running" text present
       - Test: "calls onToggle when chevron clicked" — render, click chevron button, assert onToggle callback called
       - Test: "calls onLaunchAgent when + Agent clicked" — render, click + Agent button, assert callback called
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "AgentSidebar|budgetRegistry" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - budgetRegistry tests pass: register, unregister, update
    - AgentSidebar tests pass: 4 sections rendered, collapsed class applied, expand handle visible, agent items render, empty state shown, callbacks fire
    - pnpm --filter voss-app test passes with no regressions
  </acceptance_criteria>
  <done>AgentSidebar and budgetRegistry have passing unit tests. Full suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| N/A | This plan creates UI components with no external input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-02 | Information Disclosure | budgetRegistry cost data | accept | Cost data is display-only within the same browser context; no cross-origin exposure |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test — all tests green.
npx tsc --noEmit — zero type errors.
</verification>

<success_criteria>
1. AgentSidebar renders with 4 sections (AGENTS, SESSIONS, FILES, GIT) per D-01.
2. Sidebar is 280px with 2px orange accent bar and 44px header per D-04.
3. Agent items show dot, name, model, role pill, cost per UI-SPEC.
4. budgetRegistry mirrors procRegistry pattern with lastSeenMs for streaming detection.
5. Collapsed state shows expand handle per UI-SPEC.
6. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-02-SUMMARY.md` when done
</output>

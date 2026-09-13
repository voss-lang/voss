---
phase: A12-voss-app-ade-visual-redesign
plan: 05
type: execute
wave: 2
depends_on:
  - A12-01
files_modified:
  - apps/voss-app/src/components/titlebar/Titlebar.tsx
  - apps/voss-app/src/components/StatusBar.tsx
  - apps/voss-app/src/components/titlebar/__tests__/Titlebar.test.tsx
  - apps/voss-app/src/App.tsx
autonomous: true
requirements:
  - ADE-05

must_haves:
  truths:
    - "Voss logo mark (18-20px SVG, orange fill) is visible left of project name in titlebar"
    - "Project name renders in Poppins 500 (not monospace)"
    - "Status bar shows orange agent badge pill with count and total cost"
    - "Agent badge is hidden when 0 agents active"
    - "Clicking agent badge toggles sidebar"
  artifacts:
    - path: "apps/voss-app/src/components/titlebar/Titlebar.tsx"
      provides: "Titlebar with Voss logo mark and Poppins project name"
      contains: "logo"
    - path: "apps/voss-app/src/components/StatusBar.tsx"
      provides: "Status bar with orange agent badge pill"
      contains: "agent-badge"
  key_links:
    - from: "apps/voss-app/src/components/StatusBar.tsx"
      to: "apps/voss-app/src/pane/budgetRegistry.ts"
      via: "budgetByPaneId() for total cost calculation"
      pattern: "budgetByPaneId"
    - from: "apps/voss-app/src/components/StatusBar.tsx"
      to: "apps/voss-app/src/App.tsx"
      via: "onToggleSidebar callback"
      pattern: "onToggleSidebar"
---

<objective>
Add Voss branding to the titlebar (logo SVG + Poppins project name) and add the agent count badge pill to the status bar. Badge shows live agent count + total cost from budget registry.

Purpose: Titlebar branding and status bar badge are the persistent visual indicators that this is an Agent Development Environment, not just a terminal.
Output: Modified Titlebar.tsx, modified StatusBar.tsx, extended Titlebar tests.
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
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-01-SUMMARY.md

<interfaces>
<!-- Titlebar.tsx current props (line 17-22) -->
TitlebarProps = { activeLayout?, layoutDisabled?, onLayoutSelect?, projectName? }
- titleText() returns projectName or 'Voss ADE' fallback
- Layout: WindowControls | drag spacer | title text | drag spacer | PresetSwitcher

<!-- StatusBar.tsx current props (line 6-12) -->
StatusBarProps = { workspaceName, paneCount, focusedPaneId, gitBranch, contextPanelOpen, onToggleContextPanel }

<!-- Logo SVG from site/public/logo.svg -->
<svg viewBox="0 0 2048 2048" fill="none">
  <path d="M332 471h278l566 908-136 226L332 471Z" fill="#ff5b1f"/>
  <path d="M1432 470h308l-503 724-144-197 339-527Z" fill="#ff5b1f"/>
</svg>

<!-- budgetRegistry (from P2) -->
budgetByPaneId(): Record<string, BudgetEntry>
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Voss logo and Poppins project name to Titlebar</name>
  <files>
    apps/voss-app/src/components/titlebar/Titlebar.tsx,
    apps/voss-app/src/components/titlebar/__tests__/Titlebar.test.tsx
  </files>
  <read_first>
    apps/voss-app/src/components/titlebar/Titlebar.tsx,
    apps/voss-app/src/components/titlebar/__tests__/Titlebar.test.tsx,
    site/public/logo.svg
  </read_first>
  <action>
    1. In Titlebar.tsx, modify the center title area (lines 54-68):
       - Replace the single title text div with a group containing logo + title
       - The group div keeps data-tauri-drag-region and align-self: stretch
       - Add inline SVG for the Voss logo mark: an svg element with viewBox="0 0 2048 2048", width 18, height 18, fill="none", containing the two path elements from site/public/logo.svg. The fill on each path uses "var(--focus)" instead of hardcoded #ff5b1f (so it follows the theme). Add margin-right: 6px per D-28.
       - Change project name text styles from font-family var(--font-mono), font-size 11px, font-weight 400 to font-family var(--font-display), font-size 13px, font-weight 500 per D-29 (Poppins 500)
       - Layout order per D-28: traffic lights -> gap -> logo -> project name -> gap -> preset switcher

    2. The TitlebarProps type does not need changes — projectName prop already exists.

    3. Extend apps/voss-app/src/components/titlebar/__tests__/Titlebar.test.tsx:
       - Add test: "renders Voss logo SVG" — render Titlebar, query for svg element, assert it exists
       - Add test: "renders project name with Poppins font" — render Titlebar with projectName="test-project", assert text "test-project" is visible, assert containing element has font-family including "Poppins" (or var(--font-display))
       - Ensure existing tests still pass (they reference 'Voss ADE' fallback text which should still work)
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "Titlebar" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - Titlebar renders inline SVG logo with 2 paths and viewBox="0 0 2048 2048"
    - Logo fill uses var(--focus) (theme-aware)
    - Project name uses font-family var(--font-display) (Poppins) at 13px weight 500
    - Logo positioned left of project name per D-28
    - data-tauri-drag-region preserved on title group
    - Existing Titlebar tests pass
    - New logo and font tests pass
  </acceptance_criteria>
  <done>Titlebar displays Voss logo mark and Poppins project name per D-28/D-29.</done>
</task>

<task type="auto">
  <name>Task 2: Add agent badge pill to StatusBar</name>
  <files>
    apps/voss-app/src/components/StatusBar.tsx,
    apps/voss-app/src/App.tsx
  </files>
  <read_first>
    apps/voss-app/src/components/StatusBar.tsx,
    apps/voss-app/src/App.tsx (StatusBar props wiring, lines 1045-1054),
    apps/voss-app/src/pane/budgetRegistry.ts,
    apps/voss-app/src/pane/agentDetect.ts
  </read_first>
  <action>
    1. Extend StatusBarProps in StatusBar.tsx:
       - Add agentCount: number
       - Add totalCost: number
       - Add onToggleSidebar: () => void

    2. In StatusBar component, add agent badge pill to the right side div, BEFORE the Ctx toggle button:
       - Wrapped in Show(when=props.agentCount > 0) — hidden when 0 agents per D-26
       - Badge content: "● {N} agent{s} · ${X.XX}" where N = agentCount, X.XX = totalCost.toFixed(2)
       - Singular/plural: "agent" when N === 1, "agents" otherwise
       - Styles: background rgba(255,91,31,0.15), border 1px solid var(--focus), color var(--focus), border-radius 9999px via inline style, padding 0 8px, height 16px, display inline-flex, align-items center, font-size 11px, cursor pointer, white-space nowrap
       - onClick: props.onToggleSidebar() per D-27

    3. In App.tsx, update the StatusBar render (around line 1045):
       - Compute agentCount and totalCost from budgetByPaneId and agentConfigByPaneId:
         agentCount = number of entries in agentListForSidebar() (already computed)
         totalCost = Object.values(budgetByPaneId()).reduce((sum, b) => sum + b.cost_usd, 0)
       - Pass agentCount={agentListForSidebar().length}
       - Pass totalCost={totalCost computed value}
       - Pass onToggleSidebar={toggleSidebar}
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -10 && npx vitest run 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - StatusBar shows orange pill badge when agentCount > 0
    - Badge text format: "● N agent(s) · $X.XX"
    - Badge hidden when agentCount === 0
    - Badge click calls onToggleSidebar per D-27
    - Badge uses 9999px border-radius (inline style), --focus color, semi-transparent --focus background
    - All tests pass
  </acceptance_criteria>
  <done>StatusBar displays live agent badge pill with count and cost. Click toggles sidebar per D-27.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| N/A | Display-only changes to titlebar and status bar |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test — all tests green.
npx tsc --noEmit — zero type errors.
</verification>

<success_criteria>
1. Voss logo mark visible in titlebar per D-28.
2. Project name in Poppins 500 per D-29.
3. Agent badge pill shows "● N agents · $X.XX" per D-26.
4. Badge hidden when 0 agents.
5. Badge click toggles sidebar per D-27.
6. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-05-SUMMARY.md` when done
</output>

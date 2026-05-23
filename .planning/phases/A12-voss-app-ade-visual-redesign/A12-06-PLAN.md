---
phase: A12-voss-app-ade-visual-redesign
plan: 06
type: execute
wave: 2
depends_on:
  - A12-01
files_modified:
  - apps/voss-app/src/grid/PaneHeader.tsx
  - apps/voss-app/src/grid/SplitNode.tsx
  - apps/voss-app/src/index.css
  - apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx
autonomous: true
requirements:
  - ADE-06

must_haves:
  truths:
    - "Agent panes have a 3px colored left accent bar in the header"
    - "Accent bar color matches the agent's role (planner=orange, executor=cyan, reviewer=amber)"
    - "Focused agent pane has --focus-soft background tint and --focus left bar"
    - "Streaming agents show a pulsing orange dot animation"
    - "Non-agent panes have no accent bar (or optional dim hairline)"
    - "Pane header height is 28px (increased from 22px)"
    - "isAgent, roleColor, isStreaming, costUsd props threaded from data sources through SplitNode to PaneHeader"
  artifacts:
    - path: "apps/voss-app/src/grid/PaneHeader.tsx"
      provides: "PaneHeader with role-colored accent bar and streaming pulse"
      contains: "roleColor"
    - path: "apps/voss-app/src/grid/SplitNode.tsx"
      provides: "Prop threading from agentConfigByPaneId and budgetByPaneId to PaneHeader"
      contains: "isAgent"
    - path: "apps/voss-app/src/index.css"
      provides: "Updated .grid-pane-leaf--focused with focus-soft bg and pane header height vars"
  key_links:
    - from: "apps/voss-app/src/grid/SplitNode.tsx"
      to: "apps/voss-app/src/grid/PaneHeader.tsx"
      via: "isAgent, roleColor, isStreaming, costUsd props"
      pattern: "isAgent.*roleColor.*isStreaming.*costUsd"
    - from: "apps/voss-app/src/grid/SplitNode.tsx"
      to: "apps/voss-app/src/pane/budgetRegistry.ts"
      via: "budgetByPaneId import for streaming detection and cost"
      pattern: "budgetByPaneId"
    - from: "apps/voss-app/src/grid/PaneHeader.tsx"
      to: "apps/voss-app/src/pane/budgetRegistry.ts"
      via: "streaming detection from lastSeenMs"
      pattern: "isStreaming"
---

<objective>
Enhance PaneHeader with role-colored accent bars for agent panes, focus-soft background on focused agent pane, and streaming pulse dot animation. Thread isAgent/roleColor/isStreaming/costUsd props from data sources through SplitNode to PaneHeader. Increase pane header height from 22px to 28px to accommodate accent bar spacing.

Purpose: Pane chrome warmth is what makes each terminal pane feel agent-aware. Role colors at a glance tell the user which agent is doing what.
Output: Modified PaneHeader.tsx, modified SplitNode.tsx (prop threading), updated index.css grid-pane-leaf styles, extended PaneChrome tests.
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
<!-- Current PaneHeader props (from PaneHeader.tsx lines 13-27) -->
PaneHeaderProps = {
  index: number, focused: boolean, cwd: string, shell: string,
  dotState?: 'running' | 'exited', process?: string,
  prefixActive?: boolean, prefixReserved?: boolean,
  onToggleMenu: () => void
}

<!-- Current styles -->
- Height: 22px (inline style)
- Focused: bg-bg-2 (Tailwind class), unfocused: bg-bg-1
- Status dot: 8px, green (running) or red (exited)

<!-- CSS in index.css (lines 88-103) -->
.grid-pane-leaf--focused: box-shadow inset 0 0 0 1px var(--focus)

<!-- SplitNode.tsx props (lines 36-52) -->
SplitNodeView(props: {
  node: TreeNode, store: Store<GridStore>, setStore: SetStoreFunction<GridStore>,
  path: string, dims: () => Dims, closeUI?: CloseUI,
  restoredScrollbackByPaneId?: Record<string, string[]>,
  onPaneFirstInput?: (paneId: string) => void,
  prefixActive?: boolean, prefixReserved?: boolean,
  agentConfigByPaneId?: Record<string, AgentConfig>,
  workspacePath?: string,
})
- agentConfigByPaneId is already passed from GridRoot -> SplitNode
- PaneHeader is rendered at SplitNode line 97 but does NOT currently receive agent-related props

<!-- budgetByPaneId (from pane/budgetRegistry.ts, created in A12-03) -->
budgetByPaneId(): Record<string, BudgetEntry>
- BudgetEntry has cost_usd: number, lastSeenMs: number

<!-- agentDetect.ts role mapping -->
isKnownAgentCli(binary: string): boolean
- claude -> planner role, codex -> executor, gemini -> reviewer, etc.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add role accent bar, streaming pulse, and prop threading to PaneHeader</name>
  <files>
    apps/voss-app/src/grid/PaneHeader.tsx,
    apps/voss-app/src/grid/SplitNode.tsx,
    apps/voss-app/src/index.css
  </files>
  <read_first>
    apps/voss-app/src/grid/PaneHeader.tsx,
    apps/voss-app/src/grid/SplitNode.tsx (lines 36-110, props and PaneHeader render),
    apps/voss-app/src/pane/budgetRegistry.ts,
    apps/voss-app/src/pane/agentDetect.ts (isKnownAgentCli, role mapping),
    apps/voss-app/src/index.css (lines 87-130, grid-pane-leaf styles),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md (PaneHeader contract, Agent Role Colors)
  </read_first>
  <action>
    1. Extend PaneHeaderProps interface:
       - Add isAgent?: boolean -- whether this pane has an agent CLI
       - Add roleColor?: string -- CSS variable name like '--role-planner' (passed from parent)
       - Add isStreaming?: boolean -- whether the agent is currently streaming
       - Add costUsd?: number -- optional cost display for agent panes

    2. In SplitNode.tsx, thread the new props from data sources to PaneHeader:
       - Import budgetByPaneId from '../pane/budgetRegistry'
       - Import isKnownAgentCli from '../pane/agentDetect' (or use a role-mapping helper)
       - In the PaneHeader JSX render (line ~97), derive and pass the new props:
         * isAgent: derive from props.agentConfigByPaneId -- check if asLeaf().id exists in agentConfigByPaneId AND isKnownAgentCli(agentConfigByPaneId[asLeaf().id]?.cliBinary)
         * roleColor: map cliBinary to role color CSS variable: claude->'--role-planner', codex->'--role-executor', gemini/antigravity->'--role-reviewer', opencode->'--role-watcher', voss->'--role-planner'. Default '--role-user' for unknown agents.
         * isStreaming: derive from budgetByPaneId() -- check if budgetByPaneId()[asLeaf().id] exists and Date.now() - budgetByPaneId()[asLeaf().id].lastSeenMs < 3000
         * costUsd: derive from budgetByPaneId()[asLeaf().id]?.cost_usd ?? 0
       - The PaneHeader render call becomes:
         <PaneHeader
           index={asLeaf().index}
           focused={isFocused()}
           cwd={asLeaf().cwd}
           shell={asLeaf().shell}
           prefixActive={isFocused() && props.prefixActive}
           prefixReserved={props.prefixReserved}
           onToggleMenu={() => setMenuOpen((v) => !v)}
           isAgent={!!props.agentConfigByPaneId?.[asLeaf().id] && isKnownAgentCli(props.agentConfigByPaneId[asLeaf().id].cliBinary)}
           roleColor={mapCliToRoleColor(props.agentConfigByPaneId?.[asLeaf().id]?.cliBinary)}
           isStreaming={budgetByPaneId()[asLeaf().id] ? Date.now() - (budgetByPaneId()[asLeaf().id].lastSeenMs ?? 0) < 3000 : false}
           costUsd={budgetByPaneId()[asLeaf().id]?.cost_usd}
         />

    3. Increase pane header height from 22px to 28px:
       - Change height inline style from '22px' to 'var(--pane-header-height, 22px)'
       - Change min-height similarly
       - The Voss Ignite theme sets --pane-header-height: 28px in cssVars, so under Ignite it will be 28px; under Variant B it falls back to 22px
       - Update padding from '0 10px' to '0 8px 0 16px' per UI-SPEC (extra left for accent bar, 16px left accommodates 3px bar giving 13px visual padding)

    4. Add accent bar via ::before pseudo-element styling:
       - When isAgent is true, render a left accent bar using an additional span or inline style:
         Since CSS pseudo-elements cannot be conditionally applied inline in SolidJS, use a span:
         Render a span as first child, position absolute, left 0, top 0, bottom 0, width 3px, background set to var(roleColor) if roleColor provided, otherwise transparent
       - When focused AND isAgent: background uses var(--focus) regardless of role color; header background uses var(--focus-soft)
       - When not isAgent: no accent bar span rendered (or transparent)

    5. Modify the status dot rendering:
       - When isStreaming is true: apply a CSS class for pulsing animation (add the class directly in the span's classList)
       - The pulsing animation keyframes (voss-pulse) are already defined in sidebar.css from P2; add them to index.css as well (or move to index.css so PaneHeader can use them):
         @keyframes voss-pulse { from { opacity: 1; } to { opacity: 0.3; } }
       - Streaming dot color: var(--focus) (orange pulse)
       - Non-streaming agent dot: use role color with box-shadow glow per UI-SPEC
       - Non-agent dot: keep existing green/red behavior unchanged

    6. Add cost display for agent panes:
       - When isAgent and costUsd is defined, render cost after the flex spacer, before the menu button
       - Cost text: JetBrains Mono 11px, color var(--fg-2) normally, var(--focus) when costUsd > 1.00
       - Format: "$" + costUsd.toFixed(2)

    7. Update .grid-pane-leaf--focused in index.css:
       - Add background: var(--focus-soft) (in addition to existing box-shadow)
       - This provides the subtle orange tint on focused agent pane headers
       - NOTE: this applies to ALL focused panes (not just agents). Agent-specific focused styling is the accent bar color change (step 4 above).

    8. Add the voss-pulse keyframes to index.css (after the existing grid pane chrome section around line 130):
       @keyframes voss-pulse { from { opacity: 1; } to { opacity: 0.3; } }
       .pane-dot--streaming { animation: voss-pulse 0.8s ease-in-out infinite alternate; }
       (prefers-reduced-motion kill switch in index.css already handles disabling)
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -10</automated>
  </verify>
  <acceptance_criteria>
    - PaneHeader accepts isAgent, roleColor, isStreaming, costUsd props
    - SplitNode derives isAgent from agentConfigByPaneId[paneId] and isKnownAgentCli
    - SplitNode derives roleColor by mapping cliBinary to role color CSS variable
    - SplitNode derives isStreaming from budgetByPaneId activity (lastSeenMs < 3000)
    - SplitNode derives costUsd from budgetByPaneId cost_usd
    - All four props passed from SplitNode to PaneHeader
    - Height uses var(--pane-header-height, 22px) -- 28px under Ignite, 22px under Variant B
    - Padding is 0 8px 0 16px per UI-SPEC
    - Agent panes render 3px left accent bar in role color
    - Focused agent panes use --focus color for accent bar and --focus-soft for background
    - Streaming dot pulses with voss-pulse animation
    - Cost displayed as $X.XX, turns --focus when > $1.00
    - Non-agent panes unchanged (no bar, existing dot behavior)
    - TypeScript compiles
  </acceptance_criteria>
  <done>PaneHeader renders role-colored accent bars, streaming pulse, and cost for agent panes. Props threaded from data sources through SplitNode.</done>
</task>

<task type="auto">
  <name>Task 2: Extend PaneChrome tests for accent bar and streaming</name>
  <files>
    apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx
  </files>
  <read_first>
    apps/voss-app/src/grid/__tests__/PaneChrome.test.tsx,
    apps/voss-app/src/grid/PaneHeader.tsx
  </read_first>
  <action>
    1. Add tests to the existing PaneChrome.test.tsx file:
       - Test: "renders accent bar when isAgent=true" -- render PaneHeader with isAgent=true, roleColor="--role-planner", assert accent bar span exists with width 3px
       - Test: "no accent bar when isAgent=false" -- render PaneHeader with isAgent=false or undefined, assert no accent bar span
       - Test: "focused agent uses --focus-soft background" -- render with focused=true, isAgent=true, assert header element has background style referencing focus-soft
       - Test: "streaming dot has pulsing class" -- render with isStreaming=true, assert dot element has pane-dot--streaming class
       - Test: "cost displays with correct format" -- render with costUsd=0.42, assert text "$0.42" visible
       - Test: "cost turns orange above $1.00" -- render with costUsd=1.50, assert cost element color references --focus

    2. Verify existing PaneChrome tests still pass without modification (the new props are optional, so existing tests should not break).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "PaneChrome|PaneHeader" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - New accent bar tests pass
    - Streaming pulse test passes
    - Cost display tests pass
    - Existing PaneChrome tests pass without modification
    - Full suite green
  </acceptance_criteria>
  <done>PaneChrome tests extended for accent bar, streaming pulse, and cost display. All tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| N/A | Display-only changes to pane headers |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test -- all tests green.
npx tsc --noEmit -- zero type errors.
</verification>

<success_criteria>
1. Agent panes show 3px role-colored accent bar.
2. Props (isAgent, roleColor, isStreaming, costUsd) threaded from agentConfigByPaneId and budgetByPaneId through SplitNode to PaneHeader.
3. Focused agent pane has --focus accent bar and --focus-soft background.
4. Streaming dot pulses per D-30.
5. Cost display in header per UI-SPEC.
6. Non-agent panes unaffected.
7. Pane header height 28px under Ignite, 22px under Variant B.
8. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-06-SUMMARY.md` when done
</output>

---
phase: V24-ade-product-revamp-swarm-observability
plan: 05
type: execute
wave: 2
depends_on: ["V24-02"]
files_modified:
  - apps/voss-app/src/surfaces/overview/OverviewSurface.tsx
  - apps/voss-app/src/surfaces/tasks/TasksSurface.tsx
  - apps/voss-app/src/surfaces/agents/AgentsSurface.tsx
  - apps/voss-app/src/surfaces/surfaces.css
  - apps/voss-app/src/portal/PortalShell.tsx
  - apps/voss-app/src/surfaces/tasks/__tests__/TasksSurface.test.tsx
  - apps/voss-app/src/__tests__/portalDeepLink.test.tsx
autonomous: true
requirements: [VADE2-05]
must_haves:
  truths:
    - "Overview/Tasks/Agents surfaces present managed work grouped by status: active, blocked, reviewing, done, adopted, terminal-agent"
    - "Fixture runs spanning each status appear under the correct status grouping"
    - "An attention action on a blocked item is actionable (inline action row, not a new modal)"
    - "Clicking a row deep-links to the corresponding pane/drawer via org/selection"
  artifacts:
    - path: "apps/voss-app/src/surfaces/tasks/TasksSurface.tsx"
      provides: "Status-grouped Task list from cardsFromRunData + deriveColumn; attention badges; deep-link rows"
      contains: "cardsFromRunData"
    - path: "apps/voss-app/src/surfaces/agents/AgentsSurface.tsx"
      provides: "Agent roster grouped by role with status dot, model, cost, elapsed"
      contains: "AgentsSurface"
    - path: "apps/voss-app/src/surfaces/tasks/__tests__/TasksSurface.test.tsx"
      provides: "Fixture-run status-grouping assertions across each status"
      contains: "TasksSurface"
    - path: "apps/voss-app/src/__tests__/portalDeepLink.test.tsx"
      provides: "Row click → openInGridRequest/openInReviewRequest deep-link assertion"
      contains: "portalDeepLink"
  key_links:
    - from: "apps/voss-app/src/surfaces/tasks/TasksSurface.tsx"
      to: "apps/voss-app/src/org/boardDerive.ts"
      via: "cardsFromRunData(runData()) + deriveColumn grouping"
      pattern: "cardsFromRunData"
    - from: "apps/voss-app/src/surfaces/tasks/TasksSurface.tsx"
      to: "apps/voss-app/src/org/selection.ts"
      via: "requestOpenInGrid / requestOpenInReview row deep link"
      pattern: "requestOpenIn(Grid|Review)"
    - from: "apps/voss-app/src/portal/PortalShell.tsx"
      to: "surfaces/{overview,tasks,agents}"
      via: "Switch mounts the new surfaces for overview/tasks/agents activeView"
      pattern: "TasksSurface|OverviewSurface|AgentsSurface"
---

<objective>
Build the mission-control surfaces (VADE2-05): Overview, Tasks, and Agents.
Managed agent work reads like a status system (Linear-like), not a toolbar.
Work is grouped by status (active/blocked/reviewing/done/adopted/terminal-agent),
each row carries attention actions for blocked items, and clicking a row
deep-links to the corresponding pane/drawer using the existing `org/selection`
signals. The surfaces reuse `cardsFromRunData` + `deriveColumn` (no re-derivation)
and the existing `.org-spinner`/`.org-error-state` loading patterns.

Purpose: Replaces the cockpit-panel/attention-queue presentation with the
product-coherent Overview/Tasks/Agents surfaces the portal navigates to.

Output: `OverviewSurface.tsx`, `TasksSurface.tsx`, `AgentsSurface.tsx`,
`surfaces.css`, PortalShell wiring of the three surfaces, and the two Wave-0
tests (status grouping + deep link).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-RESEARCH.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md
@apps/voss-app/PRODUCT.md

<interfaces>
<!-- Verified from codebase 2026-06-14. -->
From apps/voss-app/src/org/orgStore.ts:
  export const [runData] = createSignal<RunData | null>(null);
  export const [runEntries] = createSignal<RunEntry[]>([]);
  export const [loading] = createSignal(false);
  export const [loadError] = createSignal<string | null>(null);
  export function enumerateRuns(cwd: string): Promise<RunEntry[]>;

From apps/voss-app/src/org/boardDerive.ts:
  export interface BoardCard { ...; column: string; ... }
  export function deriveColumn(node: SessionTreeNode): string;  // 'InProgress'|'Blocked'|'InReview'|'Done'|...
  export function cardsFromRunData(data: RunData | null): BoardCard[];  // null-tolerant → []

From apps/voss-app/src/org/attention/attentionQueue.ts:
  export const attentionQueue: () => AttentionItem[];  // items with kind 'permission'|'budget'|'blocked', deepLink {paneId?, sessionNodeId?}

From apps/voss-app/src/org/selection.ts:
  export function requestOpenInGrid(paneId: string): void;
  export function requestOpenInReview(cardId: string): void;

From apps/voss-app/src/components/sidebar/AgentItem.tsx:
  roleColor = () => `var(--role-${props.role})`;  // roles: planner|reviewer|watcher|user|executor
  status-dot streaming pattern at L48-55.

From apps/voss-app/src/portal/PortalShell.tsx (V24-02): the <Switch> currently mounts placeholder divs for overview/tasks/agents — replace those three Match arms.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Author status-grouping + deep-link tests (Wave 0 gaps)</name>
  <files>apps/voss-app/src/surfaces/tasks/__tests__/TasksSurface.test.tsx, apps/voss-app/src/__tests__/portalDeepLink.test.tsx</files>
  <read_first>
    - apps/voss-app/src/org/__tests__/swarmReconcile.test.ts (pure fixture-test discipline analog)
    - apps/voss-app/src/org/cockpit/__tests__/cockpit.test.tsx (tauri invoke mock for data-loading components)
    - apps/voss-app/src/org/boardDerive.ts (deriveColumn / cardsFromRunData — column keys to assert)
    - apps/voss-app/src/org/selection.ts (openInGridRequest/openInReviewRequest signals to observe)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§TasksSurface.test.tsx, §Vitest Test Harness Setup)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-VALIDATION.md (VADE2-05 rows)
  </read_first>
  <behavior>
    - TasksSurface test 1: a fixture run with an InProgress node yields a card in the ACTIVE group.
    - TasksSurface test 2: a Blocked node yields a card in the BLOCKED group; a Done node → DONE; an InReview node → REVIEWING.
    - TasksSurface test 3: empty/null runData → no cards, no crash (null-tolerant); surface shows empty state.
    - portalDeepLink test: clicking a Task row with a paneId calls requestOpenInGrid(paneId) (openInGridRequest signal becomes that paneId); a row without paneId calls requestOpenInReview(cardId).
  </behavior>
  <action>
    Write `TasksSurface.test.tsx` mirroring `swarmReconcile.test.ts` discipline plus the cockpit tauri-mock.
    Build fixture RunData spanning statuses (InProgress/Blocked/InReview/Done) and assert
    `cardsFromRunData(fixture).filter(c => c.column === '<col>')` is non-empty for each, then assert the
    rendered surface groups them under the correct UI-SPEC group headers (ACTIVE/BLOCKED/REVIEWING/DONE).
    Write `portalDeepLink.test.tsx` using the standard mount harness: render a Task row (or the surface with a
    one-card fixture), simulate a click, and assert the appropriate `org/selection` signal updated —
    `openInGridRequest()` equals the paneId when present, else `openInReviewRequest()` equals the card id.
    Reset the selection signals in `afterEach`. Both RED until Task 2.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- TasksSurface 2>&1 | tail -15; npm test -- portalDeepLink 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `TasksSurface.test.tsx` builds fixtures for InProgress/Blocked/InReview/Done and asserts correct grouping plus a null-tolerant empty case.
    - `portalDeepLink.test.tsx` asserts row click drives `requestOpenInGrid` (paneId path) and `requestOpenInReview` (cardId path) via the real selection signals.
    - Both test files use the standard tauri-mock harness and compile/run.
    - No fabricated APIs — tests import real `cardsFromRunData`, `deriveColumn`, and `org/selection`.
  </acceptance_criteria>
  <done>Status-grouping and deep-link contract tests exist (RED), pinning VADE2-05 behavior.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build Overview/Tasks/Agents surfaces and wire into PortalShell</name>
  <files>apps/voss-app/src/surfaces/overview/OverviewSurface.tsx, apps/voss-app/src/surfaces/tasks/TasksSurface.tsx, apps/voss-app/src/surfaces/agents/AgentsSurface.tsx, apps/voss-app/src/surfaces/surfaces.css, apps/voss-app/src/portal/PortalShell.tsx</files>
  <read_first>
    - apps/voss-app/src/org/panels/BoardPanel.tsx (COLUMNS + cardsFromRunData grouping analog)
    - apps/voss-app/src/org/orgStore.ts (runData/loading/loadError/enumerateRuns data source)
    - apps/voss-app/src/org/boardDerive.ts (deriveColumn / cardsFromRunData)
    - apps/voss-app/src/org/attention/attentionQueue.ts (attention items + deepLink for blocked rows)
    - apps/voss-app/src/components/sidebar/AgentItem.tsx + AgentSidebar.tsx (agent row analog for AgentsSurface)
    - apps/voss-app/src/org/orgStyles.css (.org-spinner / .org-error-state classes to reuse)
    - apps/voss-app/src/org/cockpit/cockpitStyles.css (.cockpit-sect section-heading token pattern)
    - apps/voss-app/src/portal/PortalShell.tsx (the three placeholder Match arms to replace)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§OverviewSurface/TasksSurface, §AgentsSurface, §Deep-Link, §Loading/Error, §Section Heading)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 4 + §Interaction Contracts Attention Actions + §Copywriting group labels)
  </read_first>
  <behavior>
    - Task 1 tests pass (GREEN): correct status grouping; row deep links fire the right selection signal.
    - Blocked rows render an attention badge; clicking it opens an inline action row (not a modal).
    - Surfaces use existing loading/error markup classes; empty state shows the locked copy ("No active Tasks" / "Use ⌘K…").
  </behavior>
  <action>
    Build `TasksSurface.tsx`: derive `cards = () => cardsFromRunData(runData())`, group by `c.column` into
    UI-SPEC groups — InProgress→ACTIVE, Blocked→BLOCKED, InReview→REVIEWING, Done→DONE, plus ADOPTED and
    TERMINAL AGENT groups (display-layer rename only; code keys unchanged, per D-09). Render group headers with
    the `.cockpit-sect` / `.sidebar-section-label` Poppins ALL-CAPS pattern; hide zero-item groups; render the
    full-surface empty state with locked copy when no cards. Each Task row is a `<button aria-label={`Open Task:
    ${name}`}>` with a status dot, the Task name (focal point, `--fg-0` 13px weight 500), agent + elapsed
    metadata, and — for Blocked rows — an attention badge sourced from `attentionQueue()`. Clicking the row
    calls `requestOpenInGrid(card.paneId)` when a paneId exists else `requestOpenInReview(card.id)`. Clicking the
    attention badge expands an inline action row (44px, `color-mix(in srgb, var(--accent-red) 8%, transparent)`)
    with the blocker description + a primary action button — no new modal.
    Build `OverviewSurface.tsx`: a condensed roll-up reusing the same grouping helper (summary counts per group +
    the active/blocked groups expanded). Build `AgentsSurface.tsx`: reuse the AgentItem row shape grouped by
    agent role (Voss main / reviewer / tester / terminal-agent), showing name (focal), status dot via
    `var(--role-*)`, model, cost (`--font-mono` tabular-nums), elapsed; empty state "No agents running".
    Write `surfaces.css` (40px surface header, 28px group header, 32px row, hover `var(--bg-2)`, attention badge
    tint) using tokens only. Replace the three placeholder Match arms in `PortalShell.tsx` to mount
    `<OverviewSurface/>`, `<TasksSurface/>`, `<AgentsSurface/>` for activeView 'overview'/'tasks'/'agents'.
    All copy MUST use PRODUCT.md vocabulary ("Tasks", "steps"/"cards" for board items, never "tasks" inside a Task).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -iE "surfaces/|PortalShell" | head; npm test -- TasksSurface 2>&1 | tail -10; npm test -- portalDeepLink 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `TasksSurface.tsx` groups cards via `cardsFromRunData`+`deriveColumn` into ACTIVE/BLOCKED/REVIEWING/DONE/ADOPTED/TERMINAL AGENT; zero-item groups hidden; empty state uses locked copy.
    - Rows are `<button>` with `aria-label="Open Task: …"`; deep links call `requestOpenInGrid`/`requestOpenInReview`.
    - Blocked rows render an attention badge that expands an inline action row (no new modal).
    - `AgentsSurface.tsx` groups by role and shows status dot/model/cost/elapsed; `OverviewSurface.tsx` shows status roll-up.
    - `PortalShell.tsx` mounts the three real surfaces (placeholder divs gone for overview/tasks/agents).
    - `npm test -- TasksSurface` and `npm test -- portalDeepLink` pass GREEN; `npx tsc --noEmit` clean for surfaces/* and PortalShell.
    - `surfaces.css` and inline styles use `var(--*)` tokens only (no raw hex); copy uses "Tasks"/"steps"/"cards", never "Runs".
  </acceptance_criteria>
  <done>Overview/Tasks/Agents surfaces present status-grouped managed work with working attention actions and deep links.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| RunData/registry → surface render | Run/board/agent data (from harness via Tauri) rendered as node labels/row text — treated as untrusted display input. |
| attention action → harness | Blocked-item action button triggers a permission/approval action against the harness. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-05-I1 | Injection | Task/agent/step labels in rows | mitigate | All labels rendered as Solid text children (auto-escaped), never innerHTML — a malicious run/agent label cannot inject DOM/markup into the surface. |
| T-V24-05-I2 | Information Disclosure | row metadata | mitigate | Rows show Task name + safety-relevant status only; raw `runId` is not surfaced as user-facing copy (D-09). Cost/budget shown are already user-owned local values. |
| T-V24-05-E | Elevation of Privilege | attention action button | mitigate | The inline action button dispatches the existing attentionQueue/permission action path (cage-governed); the surface does NOT bypass safety-mode or grant edit capability directly. Reuses governed path, adds no new privilege. |
| T-V24-05-T | Tampering | npm/pip/cargo installs | mitigate | No new packages; reuses boardDerive/attentionQueue/selection. Zero install surface. |

No HIGH-severity threats. Injection rows are the load-bearing concern — mitigated by Solid auto-escaping (no innerHTML).
</threat_model>

<verification>
- `npm test -- TasksSurface` and `npm test -- portalDeepLink` GREEN.
- `npx tsc --noEmit` clean for surfaces/* and PortalShell.tsx.
- Full suite green at wave merge.
</verification>

<success_criteria>
For fixture runs spanning each status, each appears under the correct grouping; a blocked-item attention
action is actionable; a row deep link opens the corresponding pane/drawer (VADE2-05 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-05-SUMMARY.md` when done.
</output>

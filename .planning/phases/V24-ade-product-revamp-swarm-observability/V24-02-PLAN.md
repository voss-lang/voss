---
phase: V24-ade-product-revamp-swarm-observability
plan: 02
type: execute
wave: 1
depends_on: ["V24-01"]
files_modified:
  - apps/voss-app/src/portal/portalTypes.ts
  - apps/voss-app/src/portal/PortalShell.tsx
  - apps/voss-app/src/portal/PortalRail.tsx
  - apps/voss-app/src/portal/portal.css
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/__tests__/swarmPortal.test.tsx
autonomous: true
requirements: [VADE2-02]
must_haves:
  truths:
    - "A left portal rail exposes all 8 items: Overview, Tasks, Agents, Swarm Map, Review, Context, Memory, Settings"
    - "Selecting a surface uses canvas-swap: GridRoot stays mounted (display toggles), and pane/session identity survives a portal round-trip"
    - "Fresh/project-less workspaces boot to the terminal grid (activeView defaults to 'grid')"
    - "Deep-link requests (openInGridRequest) flip activeView back to 'grid' and focus the pane"
  artifacts:
    - path: "apps/voss-app/src/portal/portalTypes.ts"
      provides: "PortalView union type + PORTAL_ITEMS contract consumed by PortalRail, PortalShell, App, and downstream surfaces"
      contains: "PortalView"
    - path: "apps/voss-app/src/portal/PortalShell.tsx"
      provides: "Canvas-swap host: grid via display:none keepalive + position:absolute portal surface Switch"
      contains: "PortalShell"
    - path: "apps/voss-app/src/portal/PortalRail.tsx"
      provides: "48px nav rail, role=tablist, 8 items + ask trigger; receives activeView/onNavTo as props"
      contains: "role=\"tablist\""
    - path: "apps/voss-app/src/__tests__/swarmPortal.test.tsx"
      provides: "Canvas-swap round-trip test: grid host same element ref, display flips, pane registry identity survives"
      contains: "swarmPortal"
  key_links:
    - from: "apps/voss-app/src/App.tsx"
      to: "activeView signal"
      via: "createSignal<PortalView>('grid') replaces orgViewOpen boolean"
      pattern: "activeView"
    - from: "apps/voss-app/src/App.tsx"
      to: "GridRoot container"
      via: "display: activeView()==='grid' ? 'flex' : 'none' (NOT <Show>)"
      pattern: "display.*grid.*flex.*none"
---

<objective>
Build the left-portal navigation shell and the canvas-swap spatial model
(VADE2-02). Replace the binary `orgViewOpen` toggle in App.tsx with an
8-way `activeView: PortalView` signal. The terminal grid stays mounted and
alive behind the portal surface via `display:none` keepalive (NOT `<Show>`),
so PTY sessions and pane state survive a portal round-trip. Fresh/project-less
workspaces boot to the grid.

Purpose: This is the structural keystone of V24. Every downstream surface
(V24-03 chrome, V24-05 mission control, V24-06 Swarm Map) navigates through this
portal and relies on the canvas-swap contract being correct (no PTY teardown).

Output: `portalTypes.ts` (the PortalView contract — Wave 0 interface), `PortalShell.tsx`,
`PortalRail.tsx`, `portal.css`, modified `App.tsx`, and the canvas-swap round-trip test.
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
<!-- Verified from codebase 2026-06-14. Executor uses these directly — no exploration needed. -->

From apps/voss-app/src/App.tsx (the canvas-swap block to convert):
- L289:  const [orgViewOpen, setOrgViewOpen] = createSignal(false);  // → replace with activeView
- L515:  createEffect watching openInGridRequest() → currently setOrgViewOpen(false); ctrl.focusPaneById(paneId)
- L1495: <div style={{ ..., display: orgViewOpen() ? 'none' : 'flex', ... }}><GridRoot .../></div>
- L1581: <Show when={orgViewOpen()}><OrgViewShell .../></Show>
- L184 comment: "Once true, GridRoot stays mounted when switching away (D-01)."

From apps/voss-app/src/org/selection.ts:
  export const [openInGridRequest, setOpenInGridRequest] = createSignal<string | null>(null);
  export function requestOpenInGrid(paneId: string): void;
  export const [openInReviewRequest, setOpenInReviewRequest] = createSignal<string | null>(null);

From apps/voss-app/src/grid/GridRoot.tsx:438 — documented display:none / keepalive contract
  (onCleanup tears down PTY ONLY on true unmount, not on display toggle).

PortalView contract this plan AUTHORS (Wave 0 interface for downstream plans):
  export type PortalView = 'grid' | 'overview' | 'tasks' | 'agents'
    | 'swarm-map' | 'review' | 'context' | 'memory' | 'settings';
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Author PortalView contract + canvas-swap round-trip test (Wave 0)</name>
  <files>apps/voss-app/src/portal/portalTypes.ts, apps/voss-app/src/__tests__/swarmPortal.test.tsx</files>
  <read_first>
    - apps/voss-app/src/__tests__/liveReviewToggle.test.tsx (EXACT harness + canvas-swap assertion analog — copy structure)
    - apps/voss-app/src/grid/GridRoot.tsx (lines ~430-445: display:none keepalive contract comment)
    - apps/voss-app/src/pane/paneSessionRegistry.ts (module-level pane→session map; identity-survival assertion target)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§swarmPortal.test.tsx + §Vitest Test Harness Setup)
  </read_first>
  <behavior>
    - Test 1: grid host element ref is identical before and after a portal round-trip (grid→tasks→grid); only inline `display` flips ('flex' → 'none' → 'flex').
    - Test 2: switching activeView to a portal surface sets the grid container `display:none` (grid NOT unmounted).
    - Test 3: pane/session identity survives — the paneSessionRegistry keys present before the swap are still present after the round-trip (module-level state, not tied to component lifecycle).
  </behavior>
  <action>
    First author `apps/voss-app/src/portal/portalTypes.ts` exporting the `PortalView` union
    (`'grid' | 'overview' | 'tasks' | 'agents' | 'swarm-map' | 'review' | 'context' | 'memory' | 'settings'`)
    and a `PORTAL_ITEMS` array of `{ id: PortalView; label: string; glyph: string }` for the 8
    navigable items in UI-SPEC §1 order (Overview/Tasks/Agents/Swarm Map/Review/Context/Memory/Settings,
    glyphs `⊞ ✓ ⬡ ◈ ※ ≡ ◉ ⚙`). Labels use locked vocabulary from PRODUCT.md ("Tasks" not "Runs", "Swarm Map").
    `'grid'` is the canvas default and is NOT a PORTAL_ITEMS entry (it is the underlying canvas, not a nav item).
    Then write `swarmPortal.test.tsx` mirroring `liveReviewToggle.test.tsx` exactly: standard mount/dispose
    harness, `vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }))`. Implement the three behavior tests.
    For the canvas-swap test, render a minimal grid-host div driven by a local `createSignal<PortalView>('grid')`
    with `style={{ display: activeView()==='grid' ? 'flex' : 'none' }}` and assert element-ref identity +
    display flip across `setActiveView('tasks')` → `setActiveView('grid')`. For the pane-identity test, seed
    the paneSessionRegistry with a fake entry before swap and assert the key remains after the round-trip.
    These tests are RED until Task 2 wires PortalShell/App; they MUST compile and run.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -v node_modules | grep -i "portalTypes\|swarmPortal" || true; npm test -- swarmPortal 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `portalTypes.ts` exports `PortalView` (9-member union incl. 'grid') and `PORTAL_ITEMS` (8 entries, no 'grid').
    - `PORTAL_ITEMS` labels match PRODUCT.md vocabulary: "Tasks" present, "Runs" absent; "Swarm Map" present.
    - `swarmPortal.test.tsx` compiles and runs (file uses the liveReviewToggle harness shape with `vi.mock` of tauri core).
    - The three behavior tests exist and assert: same grid host element ref across round-trip; display flips flex→none→flex; paneSessionRegistry key survives.
    - Test references no fenced fabricated API — uses real `paneSessionRegistry` and `PortalView`.
  </acceptance_criteria>
  <done>PortalView contract authored; canvas-swap round-trip + pane-identity tests exist and run (RED until Task 2 GREEN).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build PortalRail + PortalShell and wire activeView into App.tsx</name>
  <files>apps/voss-app/src/portal/PortalRail.tsx, apps/voss-app/src/portal/PortalShell.tsx, apps/voss-app/src/portal/portal.css, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/App.tsx (lines ~289, ~515, ~1495, ~1581: orgViewOpen signal, deep-link effect, canvas-swap div, OrgViewShell Show)
    - apps/voss-app/src/components/sidebar/AgentSidebar.tsx + AgentItem.tsx (rail + active-item analog)
    - apps/voss-app/src/components/sidebar/sidebar.css (rail layout + .agent-item--active inset-border pattern)
    - apps/voss-app/src/org/OrgViewShell.tsx (the component that becomes the "review" surface)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§PortalShell.tsx, §PortalRail.tsx, §portal.css, §App.tsx modified)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 1 + §Spatial Model + §Interaction Contracts)
  </read_first>
  <behavior>
    - After wiring, the Task 1 canvas-swap test passes (GREEN): grid host element identity + display flip + pane identity all hold.
    - PortalRail renders 8 buttons with role="tab" and aria-selected reflecting activeView.
    - Deep-link via openInGridRequest() sets activeView to 'grid' and focuses the pane.
  </behavior>
  <action>
    Build `PortalRail.tsx`: a `<nav aria-label="Voss portal">` containing a `role="tablist"
    aria-orientation="vertical"` of 8 `<button role="tab" aria-selected aria-label>` items from
    `PORTAL_ITEMS`, plus an "Ask Voss to…" trigger button (`❯`) at the rail bottom. Props:
    `{ activeView: PortalView; onNavTo: (v: PortalView) => void; onOpenComposer?: () => void }` —
    PortalRail does NOT own the signal (Pitfall 5). Active item uses `box-shadow: inset 2px 0 0 var(--focus)`.
    Build `PortalShell.tsx`: receives `{ activeView; onNavTo }` (signal lives in App). It renders the
    portal-surface layer ONLY: `<Show when={props.activeView !== 'grid'}>` wrapping a
    `position:absolute; inset:0; z-index:10; background:var(--bg-0)` container with a `<Switch>` over
    activeView → for now mount existing shells: 'review' → `<OrgViewShell .../>`; 'context'/'memory'/'settings'
    → their existing panel shells if available else a labeled stub placeholder div; the four new surfaces
    (overview/tasks/agents/swarm-map) render labeled placeholder divs (`data-surface={id}`) — they are filled
    by V24-05/V24-06. CRITICAL: PortalShell MUST NOT render GridRoot and MUST NOT wrap the grid in `<Show>`.
    Write `portal.css`: 48px rail (`var(--bg-1)`, right border `var(--border)`), 48px items, hover
    `var(--bg-2)` with `transition: background 80ms ease`, active inset-border accent, focus-visible
    `outline: 1px solid var(--focus); outline-offset: -1px`, tooltip pattern per UI-SPEC. No raw hex.
    Modify `App.tsx`: replace `const [orgViewOpen, setOrgViewOpen] = createSignal(false)` with
    `const [activeView, setActiveView] = createSignal<PortalView>('grid')`. Convert the grid container
    (L1495) to `display: activeView() === 'grid' ? 'flex' : 'none'` (keep it OUT of any `<Show>`). Replace the
    OrgViewShell `<Show>` (L1581) with `<PortalShell activeView={activeView()} onNavTo={setActiveView} />`,
    and mount `<PortalRail activeView={activeView()} onNavTo={setActiveView} onOpenComposer={...} />` in the
    left rail position. In the deep-link createEffect (~L515) replace `setOrgViewOpen(false)` with
    `setActiveView('grid')`. Replace remaining `setOrgViewOpen(true)`/toggle call sites: legacy "open org view"
    becomes `setActiveView('review')`. Default remains 'grid' so fresh/project-less workspaces boot to the grid (D-02).
    Wire `⌘⌥1`–`⌘⌥8` to the 8 portal items (UI-SPEC §Canvas-Swap keyboard) without clobbering `⌘1`–`⌘9` pane focus.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -iE "portal|App.tsx" | head; npm test -- swarmPortal 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `App.tsx` no longer declares `orgViewOpen`; it declares `activeView`/`setActiveView` of type `PortalView`.
    - The grid container uses `display: activeView() === 'grid' ? 'flex' : 'none'` and is NOT wrapped in `<Show>` (grep: grid host div present, no `<Show when={activeView() === 'grid'}>`).
    - `PortalRail.tsx` renders `role="tablist"` with 8 `role="tab"` buttons whose `aria-selected` reflects activeView, plus an ask trigger.
    - `PortalShell.tsx` renders the portal surface via `position:absolute; inset:0` and does NOT render GridRoot.
    - The deep-link effect sets `activeView` to 'grid' (not `setOrgViewOpen`).
    - `npm test -- swarmPortal` passes GREEN (canvas-swap + pane identity).
    - `npx tsc --noEmit` reports no new errors in portal/* or App.tsx.
    - `portal.css` contains no raw hex (uses `var(--*)` tokens only).
  </acceptance_criteria>
  <done>Left portal + canvas-swap live; grid stays mounted across round-trips; fresh workspace boots to grid; deep links return to grid.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user → portal nav (Solid signal) | User clicks portal items; pure UI state, no backend crossing. |
| GridRoot ↔ PTY (Tauri/Rust) | Pane sessions owned by Rust proc registry; the canvas-swap contract must NOT trigger teardown. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-02-D | Denial of Service | GridRoot PTY sessions | mitigate | Canvas-swap uses display:none keepalive, never `<Show>` unmount — prevents accidental PTY teardown (lost terminals = self-inflicted DoS). Guarded by the swarmPortal pane-identity test. |
| T-V24-02-T1 | Tampering | App state boundary | mitigate | Solid owns UI state only; portal nav does not write to `.voss/` or invoke filesystem mutations on project open (CONTEXT constraint: no hidden writes). Portal switching invokes no Tauri filesystem command. |
| T-V24-02-T2 | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH: @solidjs/router explicitly rejected — use createSignal). Zero install surface. |
| T-V24-02-R | Repudiation | n/a | accept | Pure local UI navigation; no audit-relevant action. Low value. |

No HIGH-severity threats. The DoS row is the load-bearing one — mitigated by the canvas-swap contract test.
</threat_model>

<verification>
- `npm test -- swarmPortal` GREEN (canvas-swap round-trip + pane identity).
- `npx tsc --noEmit` clean for portal/* and App.tsx.
- Full suite remains green: `cd apps/voss-app && npm test` (run at wave merge).
</verification>

<success_criteria>
The left portal exposes all 8 items; selecting a surface preserves grid/pane state via canvas-swap;
fresh workspace boots to the grid; deep links return to the grid (VADE2-02 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-02-SUMMARY.md` when done.
</output>

# Phase V24: ADE Product Revamp + Swarm Observability — Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 22 (13 new, 9 modified/test)
**Analogs found:** 22 / 22

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `src/portal/PortalShell.tsx` | component (canvas-swap host) | event-driven | `src/App.tsx:1495` + `src/__tests__/liveReviewToggle.test.tsx` | exact |
| `src/portal/PortalRail.tsx` | component (nav rail) | event-driven | `src/components/sidebar/AgentSidebar.tsx` + `AgentItem.tsx` | role-match |
| `src/portal/portal.css` | config (styles) | — | `src/components/sidebar/sidebar.css` | role-match |
| `src/surfaces/overview/OverviewSurface.tsx` | component (mission-control list) | CRUD | `src/org/panels/BoardPanel.tsx` + `src/org/cockpit/CockpitShell.tsx` | role-match |
| `src/surfaces/tasks/TasksSurface.tsx` | component (mission-control list) | CRUD | `src/org/panels/BoardPanel.tsx` | role-match |
| `src/surfaces/agents/AgentsSurface.tsx` | component (roster list) | CRUD | `src/components/sidebar/AgentSidebar.tsx` + `AgentItem.tsx` | role-match |
| `src/surfaces/swarm-map/SwarmMap.tsx` | component (SVG canvas) | event-driven | `src/org/cockpit/CockpitShell.tsx` (composite shell pattern) | partial-match |
| `src/surfaces/swarm-map/swarmMapDerive.ts` | utility (pure derive fn) | transform | `src/org/boardDerive.ts` + `src/org/swarmReconcile.ts` | exact |
| `src/surfaces/swarm-map/SwarmMapLegend.tsx` | component (detail panel) | event-driven | `src/org/cockpit/CardDrawer.tsx` + cockpit kv-grid pattern | role-match |
| `src/surfaces/swarm-map/ReplayScrubber.tsx` | component (scrubber) | event-driven | `src/org/panels/ReplayPanel.tsx` | role-match |
| `src/surfaces/swarm-map/EventTraceList.tsx` | component (trace list) | event-driven | `src/org/attention/AttentionPanel.tsx` pattern | role-match |
| `src/surfaces/swarm-map/swarmMap.css` | config (styles + keyframes) | — | `src/org/cockpit/cockpitStyles.css` (reduced-motion section) | role-match |
| `src/composer/VossComposer.tsx` | component (modal dialog) | request-response | `src/org/cockpit/RunCommandBar` + `src/org/cockpit/runIntake.ts` | role-match |
| `src/composer/composer.css` | config (styles) | — | `src/org/cockpit/cockpitStyles.css` | role-match |
| `src/components/titlebar/TopChrome.tsx` | component (chrome) | event-driven | `src/components/titlebar/Titlebar.tsx` | exact |
| `src/App.tsx` (modified) | component (root, signal wiring) | event-driven | `src/App.tsx:1495` (existing canvas-swap) | self-analog |
| `src/__tests__/swarmPortal.test.tsx` | test (canvas-swap round-trip) | — | `src/__tests__/liveReviewToggle.test.tsx` | exact |
| `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` | test (pure fn guard) | — | `src/org/__tests__/swarmReconcile.test.ts` | exact |
| `src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx` | test (render smoke) | — | `src/org/cockpit/__tests__/cockpit.test.tsx` | role-match |
| `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` | test (SSE → edge) | — | `src/org/__tests__/swarmReconcile.test.ts` + sseClient pattern | role-match |
| `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` | test (CSS assertion) | — | `src/org/cockpit/__tests__/a11y.test.tsx` | exact |
| `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` | test (scrubber drive) | — | `src/__tests__/liveReviewToggle.test.tsx` + ReplayPanel pattern | role-match |
| `src/composer/__tests__/VossComposer.test.tsx` | test (dialog state) | — | `src/org/cockpit/__tests__/cockpit.test.tsx` | role-match |
| `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` | test (fixture grouping) | — | `src/org/__tests__/swarmReconcile.test.ts` | role-match |

---

## Pattern Assignments

---

### `src/App.tsx` (modified — signal wiring)

**Analog:** `src/App.tsx:1480–1540` (existing canvas-swap block)

**What changes:** Replace `orgViewOpen: () => boolean` with `activeView: () => PortalView` signal. Replace `setOrgViewOpen(false)` in deep-link effects with `setActiveView('grid')`.

**Existing canvas-swap signal pattern** (App.tsx:1495):
```tsx
// KEEP THIS STRUCTURE — just widen the condition from binary to 8-way
<div style={{
  flex: '1', 'min-height': '0', 'min-width': '0',
  display: orgViewOpen() ? 'none' : 'flex',   // → activeView() === 'grid' ? 'flex' : 'none'
  'flex-direction': 'column', position: 'relative'
}}>
  <GridRoot ... />
</div>
<Show when={orgViewOpen()}>                    // → activeView() !== 'grid'
  <OrgViewShell ... />
</Show>
```

**Deep-link effect pattern** (App.tsx, replicable from liveReviewToggle.test.tsx:169–176):
```tsx
// Replicates App.tsx:317-323 verbatim — extend for V24:
createEffect(() => {
  const paneId = openInGridRequest();
  if (!paneId) return;
  setActiveView('grid');        // was: setOrgViewOpen(false)
  ctrl.focusPaneById(paneId);
  setOpenInGridRequest(null);
});
```

**Type declaration for new signal:**
```typescript
type PortalView =
  | 'grid' | 'overview' | 'tasks' | 'agents'
  | 'swarm-map' | 'review' | 'context' | 'memory' | 'settings';
const [activeView, setActiveView] = createSignal<PortalView>('grid');
```

---

### `src/portal/PortalShell.tsx` (new — canvas-swap host + surface Switch)

**Analog:** `src/App.tsx:1495` (canvas-swap) + `src/__tests__/liveReviewToggle.test.tsx` (verification contract)

**Core canvas-swap + Switch pattern:**
```tsx
// Portal surface container — position:absolute, z-index above the grid div
<Show when={props.activeView !== 'grid'}>
  <div style={{ position: 'absolute', inset: '0', 'z-index': '10', background: 'var(--bg-0)' }}>
    <Switch>
      <Match when={props.activeView === 'overview'}><OverviewSurface /></Match>
      <Match when={props.activeView === 'tasks'}><TasksSurface /></Match>
      <Match when={props.activeView === 'agents'}><AgentsSurface /></Match>
      <Match when={props.activeView === 'swarm-map'}><SwarmMap /></Match>
      <Match when={props.activeView === 'review'}><OrgViewShell ... /></Match>
      {/* context / memory / settings → existing panel shells */}
    </Switch>
  </div>
</Show>
```

**Critical: the grid container must NEVER be inside a `<Show>`** (Pitfall 1 — see RESEARCH). The grid div uses `display: props.activeView === 'grid' ? 'flex' : 'none'` in its `style` prop. The PortalShell receives `activeView` and `onNavTo` as props; it does NOT own the signal (signal lives in App.tsx).

---

### `src/portal/PortalRail.tsx` (new — 48px nav rail)

**Analog:** `src/components/sidebar/AgentSidebar.tsx` (sidebar structural pattern) + `src/components/sidebar/AgentItem.tsx` (item active-state pattern)

**Item active-state pattern** (AgentItem.tsx:38–40 + sidebar.css active class):
```tsx
// AgentItem uses agent-item--active class; PortalRail uses equivalent:
<button
  role="tab"
  aria-selected={props.activeView === item.id ? 'true' : 'false'}
  aria-label={item.label}
  class={`portal-item${props.activeView === item.id ? ' portal-item--active' : ''}`}
  onClick={() => props.onNavTo(item.id)}
>
  {item.glyph}
</button>
```

**Active item left-border accent** (mirrors `.agent-item--active` in sidebar.css and cockpitStyles.css `.cockpit-sidebar` pattern):
```css
/* portal.css — mirrors sidebar.css .sidebar::before pattern but on the item */
.portal-item--active {
  box-shadow: inset 2px 0 0 var(--focus);
  color: var(--fg-0);
}
```

**ARIA wrapper** (from UI-SPEC §1):
```tsx
<nav aria-label="Voss portal">
  <div role="tablist" aria-orientation="vertical">
    {/* 8 portal item buttons */}
  </div>
  {/* [ask] trigger at bottom */}
</nav>
```

**Props shape** (PortalRail receives, does NOT own signal — Pitfall 5):
```typescript
interface PortalRailProps {
  activeView: PortalView;
  onNavTo: (view: PortalView) => void;
}
```

---

### `src/portal/portal.css` (new — rail layout styles)

**Analog:** `src/components/sidebar/sidebar.css` (rail/sidebar layout + section label pattern)

**Section label pattern** (sidebar.css:71–79):
```css
/* Copy for portal: rail width, border, item height */
.portal-rail {
  width: 48px;
  flex-shrink: 0;
  background: var(--bg-1);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

/* Item active: inset left-border accent (mirrors .agent-item--active) */
.portal-item { height: 48px; width: 100%; ... }
.portal-item--active { box-shadow: inset 2px 0 0 var(--focus); }

/* Hover: bg + color transition (80ms ease — UI-SPEC animation budget) */
.portal-item:hover { background: var(--bg-2); transition: background 80ms ease; }
```

**Tooltip pattern** (mirrors cockpitStyles.css tooltip pattern):
```css
.portal-tooltip {
  background: var(--bg-3);
  border: 1px solid var(--border);
  color: var(--fg-0);
  font-family: var(--font-ui), Inter, system-ui, sans-serif;
  font-size: 11px;
  padding: 4px 8px;
}
```

---

### `src/surfaces/overview/OverviewSurface.tsx` + `src/surfaces/tasks/TasksSurface.tsx` (new — mission-control lists)

**Analog:** `src/org/panels/BoardPanel.tsx` (COLUMNS + cardsFromRunData grouping pattern) + `src/org/orgStore.ts` (data source)

**Data source pattern** (orgStore.ts:11–15):
```typescript
// These module-level signals are the data source for all mission-control surfaces:
import { runData, runEntries, loading, loadError, enumerateRuns } from '../org/orgStore';
import { cardsFromRunData } from '../org/boardDerive';
import { attentionQueue } from '../org/attention/attentionQueue';
```

**Column/group derivation pattern** (boardDerive.ts:21–34):
```typescript
// Derive column for each run node — same function drives mission-control groups:
import { deriveColumn, cardsFromRunData } from '../org/boardDerive';
// Group by column → map to UI-SPEC groups: InProgress→ACTIVE, Blocked→BLOCKED,
// InReview→REVIEWING, Done→DONE (display-layer rename only; code key unchanged)
```

**Null-tolerant list render pattern** (BoardPanel.tsx:1–5, cardsFromRunData:45–58):
```tsx
// Null-tolerance: cardsFromRunData(null) returns [] — no guard needed in render
const cards = () => cardsFromRunData(runData());
// Group by derived column for the mission-control surface:
const grouped = () => {
  const all = cards();
  return {
    active:    all.filter(c => c.column === 'InProgress'),
    blocked:   all.filter(c => c.column === 'Blocked'),
    reviewing: all.filter(c => c.column === 'InReview'),
    done:      all.filter(c => c.column === 'Done'),
  };
};
```

**Deep-link row pattern** (mirrors CardDrawer → openInGridRequest, from selection.ts:17–18):
```tsx
// Task row = button, not anchor. Deep links via org/selection module signals:
import { requestOpenInGrid, requestOpenInReview } from '../org/selection';

<button
  type="button"
  aria-label={`Open Task: ${card.title}`}
  class="task-row"
  onClick={() => card.paneId
    ? requestOpenInGrid(card.paneId)
    : requestOpenInReview(card.id)
  }
>
  {/* status dot + task name + metadata */}
</button>
```

**Loading/error state pattern** (orgStyles.css:191–239 — use existing `.org-spinner` / `.org-error-state` classes):
```tsx
<Show when={loading()} fallback={
  <Show when={loadError()} fallback={/* content */}>
    <div class="org-error-state">
      <p class="org-error-state__heading">Couldn't load Tasks.</p>
      <p class="org-error-state__body">Check that Voss is running.</p>
      <button class="org-error-state__refresh" onClick={() => enumerateRuns(cwd())}>
        Try again
      </button>
    </div>
  </Show>
}>
  <div class="org-spinner"><span class="org-spinner__glyph">⟳</span></div>
</Show>
```

**Section/group heading pattern** (cockpitStyles.css:70–78 `.cockpit-sect` — reuse same class or mirror):
```css
/* ALL CAPS Poppins 11px 600 letter-spacing 0.08em — ALREADY in cockpit-sect */
.cockpit-sect { /* also use .sidebar-section-label for the same token */ }
/* For mission-control group headers, copy this pattern: */
.task-group-header {
  font-family: var(--font-display), Poppins, system-ui, sans-serif;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-3);
}
```

---

### `src/surfaces/agents/AgentsSurface.tsx` (new — agent roster list)

**Analog:** `src/components/sidebar/AgentItem.tsx` + `src/components/sidebar/AgentSidebar.tsx`

**Agent item row pattern** (AgentItem.tsx:23–85):
```tsx
// AgentItem renders: status dot + name + model + role badge + streaming indicator
// AgentsSurface reuses or mirrors this row shape:
import AgentItem from '../../components/sidebar/AgentItem';
// Or inline the same shape using --role-* color tokens and tabular-nums for cost
```

**Role color token pattern** (AgentItem.tsx:27–28):
```tsx
const roleColor = () => `var(--role-${props.role})`;
// role values: 'planner', 'reviewer', 'watcher', 'user', 'executor' (fallback)
```

**Status dot streaming pattern** (AgentItem.tsx:48–55):
```tsx
<div
  class={`agent-dot${props.isStreaming ? ' agent-dot--streaming' : ''}`}
  style={{ background: roleColor(), 'box-shadow': `0 0 4px ${roleColor()}` }}
/>
```

---

### `src/surfaces/swarm-map/swarmMapDerive.ts` (new — pure derive function)

**Analog:** `src/org/boardDerive.ts` + `src/org/swarmReconcile.ts`

**Pure-function discipline** (boardDerive.ts:1–6):
```typescript
// Pure board-derivation helpers. No Solid imports, no produce/structuredClone —
// plain reads + object literals. Fixture-testable directly.
// V24 swarmMapDerive.ts follows the SAME discipline.
```

**Null-tolerance pattern** (swarmReconcile.ts:56–57 + boardDerive.ts:45–47):
```typescript
// BOTH analogs start with null guard — swarmMapDerive must mirror:
export function deriveSwarmGraph(
  runs: Array<{ runData: RunData | null; liveOverlay: Record<string, LiveOverlayEntry> }>,
  attentionItems: AttentionItem[],
): { nodes: SwarmNode[]; edges: SwarmEdge[] } {
  if (!runs || runs.length === 0) return { nodes: [], edges: [] };
  // null runData → objective placeholder node only, no edges
}
```

**Column/status derivation reuse** (boardDerive.ts:21–34):
```typescript
// Import and reuse existing deriveColumn for work node status:
import { deriveColumn, cardsFromRunData } from '../boardDerive';
// Agent node source: SessionTreeNode with role !== null
// Work node source: cardsFromRunData(runData) — non-root nodes
// Alert node source: attentionItems (kind: 'permission'|'budget'|'blocked')
```

**Honest-signal edge contract** (RESEARCH §Edge Source Map):
```typescript
// Every SwarmEdge MUST carry source string (guard test asserts this):
export interface SwarmEdge {
  id: string;
  from: string;
  to: string;
  type: 'delegation' | 'message' | 'tool-call' | 'file-edit' | 'review' | 'blocker';
  source: string;  // e.g. "board_transition:em.routing", "sse_event:permission.updated"
}
// Derive edges from real transitions only — never infer from co-presence
```

---

### `src/surfaces/swarm-map/SwarmMap.tsx` (new — SVG canvas)

**Analog:** `src/org/cockpit/CockpitShell.tsx` (composite shell + signal wiring pattern)

**Imports + signal wiring pattern** (CockpitShell.tsx:20–50):
```tsx
import { createSignal, createEffect, onMount, onCleanup, Show, Switch, Match } from 'solid-js';
import { runData, loading, loadError, enumerateRuns } from '../../org/orgStore';
import { liveLabel, liveOverlay } from '../../org/live/sseClient';
import { attentionQueue } from '../../org/attention/attentionQueue';
import { deriveSwarmGraph } from './swarmMapDerive';
```

**Proxy strip before derive** (ReplayPanel.tsx:67–68 — MANDATORY):
```typescript
// Strip Solid store proxies before passing to pure functions:
const plainNodes = (): SessionTreeNode[] =>
  JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));
// Apply same pattern when passing runData to deriveSwarmGraph:
const plainRunData = (): RunData | null =>
  runData() ? JSON.parse(JSON.stringify(runData())) : null;
```

**animation-play-state pause on hidden tab** (per RESEARCH §Animation Implementation):
```tsx
// createEffect to pause animations when document hidden:
createEffect(() => {
  const canvas = canvasRef;
  if (!canvas) return;
  // Handled by CSS animation-play-state tied to a class:
  document.addEventListener('visibilitychange', () => {
    canvas.classList.toggle('swarm-paused', document.hidden);
  });
});
```

**SVG inline pattern** (from RESEARCH — no external library):
```tsx
// Inline SVG; node positions from reactive polar-coordinate derivation:
<svg
  ref={svgRef}
  width="100%"
  height="100%"
  style={{ background: 'var(--bg-0)' }}
  onPointerDown={handlePanStart}
>
  <g transform={`translate(${panX()},${panY()})`}>
    <For each={graph().edges}>{(edge) => <SwarmEdgePath edge={edge} />}</For>
    <For each={graph().nodes}>{(node) => <SwarmNodeShape node={node} />}</For>
  </g>
</svg>
```

---

### `src/surfaces/swarm-map/SwarmMapLegend.tsx` (new — 200px right panel)

**Analog:** `src/org/cockpit/CardDrawer.tsx` (detail panel pattern) + cockpitStyles.css kv-grid pattern

**kv-grid pattern** (cockpitStyles.css — `.cockpit-kvgrid` / `.cockpit-kv*` classes):
```tsx
// Reuse existing .cockpit-kvgrid pattern for node detail key-value rows:
<div class="cockpit-kvgrid">
  <span class="cockpit-kv-k">Status</span>
  <span class="cockpit-kv-v">{node.status}</span>
</div>
```

**Deep-link button at panel bottom** (CardDrawer.tsx:89–94 pattern):
```tsx
// Deep link button — mirrors CardDrawer's "Open in grid" button:
<button
  type="button"
  style={{ color: 'var(--focus)', background: 'transparent', border: 'none', cursor: 'pointer',
           'font-family': 'var(--font-ui)', 'font-size': '11px' }}
  onClick={() => selectedNode()?.paneId
    ? requestOpenInGrid(selectedNode()!.paneId!)
    : requestOpenInReview(selectedNode()!.id)
  }
>
  Open in grid →
</button>
```

---

### `src/surfaces/swarm-map/ReplayScrubber.tsx` (new — timeline scrubber)

**Analog:** `src/org/panels/ReplayPanel.tsx` (computeBoardAtStep + plainNodes proxy-strip)

**Step signal pattern** (ReplayPanel.tsx:62–71):
```tsx
// Direct analog — same step signal + same proxy strip:
const [step, setStep] = createSignal(0);
const plainNodes = (): SessionTreeNode[] =>
  JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));
const total = () => countSteps(plainNodes());
const frame = () => computeBoardAtStep(plainNodes(), step());
```

**V24 scrubber replaces ‹/› buttons with range input** (UI-SPEC §7):
```tsx
// Replace ReplayPanel's prev/next buttons with accessible range input:
<input
  type="range"
  aria-label="Replay timeline"
  aria-valuenow={step()}
  aria-valuemin={0}
  aria-valuemax={total() - 1}
  min={0}
  max={total() - 1}
  value={step()}
  onInput={(e) => setStep(Number(e.currentTarget.value))}
  style={{ 'flex-grow': '1', height: '4px', background: 'var(--border)', cursor: 'pointer' }}
/>
```

**Import path** (replayReducer.ts:9):
```typescript
import { computeBoardAtStep } from '../../org/replayReducer';
import type { SessionTreeNode, BoardFrame } from '../../org/types';
```

---

### `src/surfaces/swarm-map/EventTraceList.tsx` (new — reduced-motion fallback)

**Analog:** `src/org/attention/AttentionPanel.tsx` (list-row pattern driven by module-level signal)

**Signal-driven list pattern** (attentionQueue.ts:21–22):
```typescript
// Trace list is driven by liveGraphPatches signal (new in sseClient.ts extension):
import { liveGraphPatches } from '../../org/live/sseClient';
// Render trace rows: [timestamp] [edge type] [source → destination]
// font-family: var(--font-mono); font-size: 11px; color: var(--fg-2);
```

---

### `src/surfaces/swarm-map/swarmMap.css` (new — keyframes + reduced-motion)

**Analog:** `src/index.css:81–94` (A8 double-guard) + `src/org/cockpit/cockpitStyles.css:240–254` (reduced-motion block)

**A8 double-guard pattern** (index.css:81–94 — MANDATORY for ALL new keyframes):
```css
/* ALL new @keyframes in swarmMap.css MUST be inside this wrapper: */
@media (not (prefers-reduced-motion: reduce)) {
  html:not(.reduced-motion) .swarm-traveling-dot {
    animation: travelEdge 2000ms linear infinite;
  }
  html:not(.reduced-motion) .swarm-node-pulse {
    animation: nodePulse 300ms ease-out forwards;
  }
  html:not(.reduced-motion) .swarm-blocker-pulse {
    animation: blockerPulse 1500ms ease-in-out infinite;
  }
}
@keyframes travelEdge { from { offset-distance: 0% } to { offset-distance: 100% } }
@keyframes nodePulse  { from { outline-width: 0; opacity: 1 } to { outline-width: 4px; opacity: 0 } }
@keyframes blockerPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.4 } }

/* animation-play-state: paused when swarm-paused class present (tab hidden): */
.swarm-paused * { animation-play-state: paused !important; }
```

**Cockpit reduced-motion pattern** (cockpitStyles.css:240–254):
```css
/* Pattern for the combined CSS kill-switch inside this file: */
@media (prefers-reduced-motion: reduce) {
  .org-view-shell *,
  .org-view-shell *::before,
  .org-view-shell *::after {
    transition: none !important;
    animation: none !important;
  }
}
/* The global A8 double-guard in index.css already covers this by inheritance,
   but the local block is kept for isolation (same pattern as cockpitStyles). */
```

---

### `src/composer/VossComposer.tsx` (new — global Cmd-K dialog)

**Analog:** `src/org/cockpit/runIntake.ts` (RunSpec / RunIntakeState assembler) + `src/org/cockpit/RunCommandBar` prop shape

**runIntake.ts reuse** (runIntake.ts:18–54):
```typescript
// Reuse existing types and assembler — only the UI wrapper is new:
import { assembleRunSpec } from '../org/cockpit/runIntake';
import type { RunIntakeState, RunSpec } from '../org/cockpit/runIntake';
// V24 maps: safety mode → RunMode ('Read only'='Plan', 'Can edit'='Edit', 'Autopilot'='Auto')
// Advanced panel fields map to RunIntakeState: goal, mode, team, scope, budget, target
```

**Dialog ARIA pattern** (from UI-SPEC §3):
```tsx
// <dialog> element with focus management:
<dialog
  ref={dialogRef}
  aria-label="Ask Voss to create a Task"
  aria-modal="true"
  open={props.open}
  onClose={props.onClose}
>
  <textarea
    ref={askRef}
    aria-required="true"
    placeholder="Describe what you want Voss to do..."
    /* autofocus on open via createEffect(() => { if (props.open) askRef?.focus(); }) */
  />
  {/* Safety mode select — aria-label="Safety mode" */}
  {/* Advanced toggle — aria-expanded + aria-controls */}
  <button type="button" disabled={!goal()} onClick={handleCreate}>
    Create Task
  </button>
</dialog>
```

**Advanced collapse pattern** (mirrors cockpitStyles.css panel expand):
```tsx
const [advancedOpen, setAdvancedOpen] = createSignal(false);
// Default collapsed — only ask + safety visible on open (D-05)
<Show when={advancedOpen()}>
  <div id="advanced-panel" aria-expanded={advancedOpen()}>
    {/* scope / agent target / team / budget / context fields */}
  </div>
</Show>
```

**Tauri focus-trap note** (RESEARCH Pitfall 7): on open, `createEffect(() => { if (props.open) askRef?.focus(); })`. Use `inert` attribute on the background to block Tab escape to xterm.

---

### `src/components/titlebar/TopChrome.tsx` (new — quiet chrome replacement)

**Analog:** `src/components/titlebar/Titlebar.tsx` (exact structural analog — keep all structure, remove PresetSwitcher + mode toggle)

**Titlebar.tsx structural pattern to copy** (Titlebar.tsx:44–145):
```tsx
// Copy this structure — remove <PresetSwitcher> and <div class="titlebar-modetoggle">:
<div style={{
  display: 'flex', 'align-items': 'center',
  height: 'var(--titlebar-height)',         // 28px — do NOT change
  'flex-shrink': '0',
  background: 'var(--bg-0)',
  'border-bottom': '1px solid var(--border)',
}}>
  <WindowControls />
  <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />
  {/* project name — Titlebar.tsx:63–95 */}
  <div data-tauri-drag-region style={{ ... }}>
    <svg viewBox="0 0 2048 2048" ...>{/* Voss logo */}</svg>
    <span style={{ color: 'var(--fg-1)', 'font-size': '12px', ... }}>{titleText()}</span>
  </div>
  <div data-tauri-drag-region style={{ flex: '1', 'align-self': 'stretch' }} />
  {/* NEW V24: ⌘K trigger button — replaces PresetSwitcher mount point */}
  <button onClick={props.onOpenComposer} style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', ... }}>
    ⌘K
  </button>
  {/* NEW V24: mode status chip (safety mode of most-recent Task) */}
  <Show when={props.currentSafetyMode}>
    <div class={`mode-chip mode-chip--${props.currentSafetyMode}`}>{props.currentSafetyMode}</div>
  </Show>
  {/* KEEP: live chip — reuse existing .titlebar-livechip pattern (Titlebar.tsx:131–143) */}
  <div class={`titlebar-livechip titlebar-livechip--${props.liveState ?? 'snapshot'}`} ...>
    ...
  </div>
  {/* REMOVED: <PresetSwitcher> */}
  {/* REMOVED: <div class="titlebar-modetoggle"> */}
</div>
```

**Props shape** (extends TitlebarProps):
```typescript
export type TopChromeProps = {
  projectName?: string;
  liveState?: 'live' | 'snapshot';
  currentSafetyMode?: 'Read only' | 'Can edit' | 'Autopilot';
  onOpenComposer?: () => void;
};
```

---

## Test File Pattern Assignments

---

### `src/__tests__/swarmPortal.test.tsx` (new — canvas-swap round-trip)

**Analog:** `src/__tests__/liveReviewToggle.test.tsx` — copy the harness structure exactly

**Harness + mount pattern** (liveReviewToggle.test.tsx:14–61):
```typescript
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { createSignal } from 'solid-js';
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => { dispose?.(); dispose = undefined; document.body.innerHTML = ''; });
```

**Canvas-swap preservation test** (liveReviewToggle.test.tsx:97–127):
```typescript
it('grid host is same element ref after portal round-trip; only display flips', () => {
  const [activeView, setActiveView] = createSignal<PortalView>('grid');
  const root = mount(() => (
    <div data-testid="grid-host"
         style={{ display: activeView() === 'grid' ? 'flex' : 'none' }}>
      <div data-testid="grid-root">grid</div>
    </div>
  ));
  const before = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
  setActiveView('tasks');
  expect(root.querySelector('[data-testid="grid-host"]')).toBe(before);  // same node
  expect((before as HTMLElement).style.display).toBe('none');
  setActiveView('grid');
  expect((before as HTMLElement).style.display).toBe('flex');
});
```

**Additional V24 test: pane session identity survives round-trip** — assert paneSessionRegistry keys are unchanged before/after swap (module-level state, not tied to component lifecycle).

---

### `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` (new — no-fake-signal guard)

**Analog:** `src/org/__tests__/swarmReconcile.test.ts` — copy the pure-function test structure exactly

**Test file structure** (swarmReconcile.test.ts:1–40):
```typescript
import { describe, it, expect } from 'vitest';
import { deriveSwarmGraph } from '../swarmMapDerive';

describe('deriveSwarmGraph', () => {
  it('is null-tolerant — empty runs yields no nodes and no edges', () => {
    const { nodes, edges } = deriveSwarmGraph([], []);
    expect(nodes).toEqual([]);
    expect(edges).toEqual([]);
  });

  it('null runData yields only an objective placeholder, no edges', () => {
    const { nodes, edges } = deriveSwarmGraph(
      [{ runData: null, liveOverlay: {} }], []
    );
    expect(nodes.every(n => n.type === 'placeholder')).toBe(true);
    expect(edges.length).toBe(0);  // critical: no edges without real source
  });

  // THE CRITICAL GUARD TEST (VADE2-06 acceptance criterion):
  it('every edge on partial RunData carries a non-empty source string', () => {
    const { edges } = deriveSwarmGraph(
      [{ runData: makePartialRun(), liveOverlay: {} }], []
    );
    expect(edges.every(e => typeof e.source === 'string' && e.source.length > 0)).toBe(true);
  });
});
```

**No-fake-signal assertions mirror swarmReconcile.test.ts null-tolerance** (swarmReconcile.test.ts:24–28):
```typescript
it('is null-tolerant and never throws', () => {
  expect(reconcileSwarm(null)).toEqual({ rosterRows: [], cards: [] });
  // V24 mirror:
  expect(() => deriveSwarmGraph([], [])).not.toThrow();
});
```

---

### `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` (new — CSS reduced-motion guard)

**Analog:** `src/org/cockpit/__tests__/a11y.test.tsx` — copy `readFileSync` + regex assertion pattern exactly

**CSS source assertion pattern** (a11y.test.tsx:33–39 + 127–143):
```typescript
import { readFileSync } from 'node:fs';
// @ts-ignore -- node builtin available in vitest runtime

const rawSwarmCss: string = readFileSync('src/surfaces/swarm-map/swarmMap.css', 'utf8');

it('swarmMap.css wraps all keyframes in reduced-motion guard', () => {
  expect(rawSwarmCss).toContain('@media (not (prefers-reduced-motion: reduce))');
  // No animation: property outside the guard block:
  const outsideGuard = rawSwarmCss.replace(
    /@media\s*\(not\s*\(prefers-reduced-motion[^)]+\)[^)]+\)\s*\{[\s\S]*?\}/g, ''
  );
  expect(outsideGuard).not.toMatch(/animation\s*:/);
});
```

**A11y test mock pattern** (a11y.test.tsx:20–25):
```typescript
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn((cmd: string) => {
    if (cmd === 'enumerate_runs') return Promise.resolve([]);
    return Promise.resolve(undefined);
  }),
}));
```

---

### `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` (new — scrubber drives graph)

**Analog:** `src/__tests__/liveReviewToggle.test.tsx` (signal-driven rendering test) + `src/org/panels/ReplayPanel.tsx` (step signal pattern)

**Signal-drive render test structure:**
```typescript
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { createSignal } from 'solid-js';
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

// Assert: when step signal changes, the scrubber range value updates
it('range input value reflects the step signal', () => {
  const root = mount(() => <ReplayScrubber data={makeCompletedRun()} />);
  const range = root.querySelector('input[type="range"]') as HTMLInputElement;
  expect(range.value).toBe('0');
  // simulate scrub to step 2:
  fireEvent.input(range, { target: { value: '2' } });
  // assert graph state reflects step 2 (node/edge count changes)
});
```

**computeBoardAtStep import** (replayReducer.ts:9):
```typescript
import { computeBoardAtStep } from '../../org/replayReducer';
```

---

### `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` (new — SSE → edge update)

**Analog:** `src/org/__tests__/swarmReconcile.test.ts` (pure fixture test) + sseClient.ts (applyOverlay routing pattern)

**Mock stream pattern** (mirrors sseClient.ts subscription model):
```typescript
// Test: mock liveGraphPatches signal, assert edge appears in SwarmMap
import { createSignal } from 'solid-js';
const [patches, setPatches] = createSignal<GraphPatchEvent[]>([]);

it('permission.updated SSE event adds a tool-call edge to the graph', () => {
  setPatches([{
    edgeType: 'tool-call',
    fromNodeId: 'agent-1',
    toNodeId: 'agent-2',
    source: 'sse_event:permission.updated',
    timestamp: Date.now(),
  }]);
  // Assert edge appears with source set
  expect(patches()[0].source).toBe('sse_event:permission.updated');
  expect(patches()[0].source.length).toBeGreaterThan(0);  // guard
});
```

---

### `src/composer/__tests__/VossComposer.test.tsx` (new — dialog default state)

**Analog:** `src/org/cockpit/__tests__/cockpit.test.tsx` (invoke mock + render + assertion pattern)

**Mock + render pattern** (cockpit.test.tsx:10–23):
```typescript
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn((cmd: string) => {
    if (cmd === 'enumerate_runs') return Promise.resolve([]);
    return Promise.resolve(undefined);
  }),
}));
import { render } from 'solid-js/web';
import VossComposer from '../VossComposer';

it('shows only ask field + safety selector on open; Advanced panel hidden', () => {
  const root = mount(() => <VossComposer open={true} onClose={() => {}} />);
  expect(root.querySelector('textarea')).toBeTruthy();  // ask field present
  expect(root.querySelector('[aria-label="Safety mode"]')).toBeTruthy();
  // Advanced panel is not visible by default:
  const advanced = root.querySelector('#advanced-panel');
  // either absent or aria-expanded=false
  expect(!advanced || advanced.getAttribute('aria-expanded') === 'false').toBe(true);
});

it('safety mode defaults to "Read only"', () => {
  const root = mount(() => <VossComposer open={true} onClose={() => {}} />);
  const select = root.querySelector('[aria-label="Safety mode"]') as HTMLSelectElement;
  expect(select?.value).toBe('Read only');
});
```

---

### `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` (new — fixture status grouping)

**Analog:** `src/org/__tests__/swarmReconcile.test.ts` (fixture test — pure derive discipline) + cockpit.test.tsx (Tauri invoke mock for data loading)

**Fixture test pattern** (swarmReconcile.test.ts:15–40):
```typescript
import { describe, it, expect } from 'vitest';
import { cardsFromRunData, deriveColumn } from '../../../org/boardDerive';
// Test with fixtures spanning each status group:
it('InProgress cards appear in ACTIVE group', () => {
  const cards = cardsFromRunData(makeRunWithStatus('InProgress'));
  const active = cards.filter(c => c.column === 'InProgress');
  expect(active.length).toBeGreaterThan(0);
});
it('Blocked cards appear in BLOCKED group', () => {
  const cards = cardsFromRunData(makeRunWithStatus('Blocked'));
  expect(cards.some(c => c.column === 'Blocked')).toBe(true);
});
```

---

## Shared Patterns

### Canvas-Swap (display:none keepalive)
**Source:** `src/App.tsx:1495` + `src/grid/GridRoot.tsx:438` (documented contract)
**Apply to:** `PortalShell.tsx`, `App.tsx` (modified), `src/__tests__/swarmPortal.test.tsx`

Critical rule: `GridRoot` MUST NEVER be wrapped in `<Show>`. Its containing div uses inline `style={{ display: activeView() === 'grid' ? 'flex' : 'none' }}` ONLY.

```tsx
// Correct:
<div style={{ display: activeView() === 'grid' ? 'flex' : 'none', flex: '1', ... }}>
  <GridRoot ... />
</div>
// WRONG — destroys PTY sessions:
<Show when={activeView() === 'grid'}><GridRoot /></Show>
```

---

### Null-Tolerance (pure derive functions)
**Source:** `src/org/boardDerive.ts:45–47` + `src/org/swarmReconcile.ts:56–57`
**Apply to:** `swarmMapDerive.ts`, `OverviewSurface.tsx`, `TasksSurface.tsx`, `AgentsSurface.tsx`

```typescript
// Always start pure functions with a null guard that returns empty arrays/objects:
if (!data) return [];
if (!manifest) return { rosterRows: [], cards: [] };
// V24 pattern:
if (!runs || runs.length === 0) return { nodes: [], edges: [] };
```

---

### Proxy-Strip Before Pure Reducers
**Source:** `src/org/panels/ReplayPanel.tsx:67–68` (documented + required)
**Apply to:** `ReplayScrubber.tsx`, `SwarmMap.tsx` (anywhere runData() is passed to pure fns)

```typescript
// MANDATORY — Solid store proxies throw DATA_CLONE_ERR in plain spreads:
const plainNodes = (): SessionTreeNode[] =>
  JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));
```

---

### Module-Level Solid Signals (shared state)
**Source:** `src/org/selection.ts:6–28` + `src/org/orgStore.ts:11–16`
**Apply to:** Any module exporting signals for cross-component state (`sseClient.ts` extension for `liveGraphPatches`)

```typescript
// Module-level signals — never inside component functions for shared state:
import { createSignal } from 'solid-js';
export const [mySignal, setMySignal] = createSignal<Type>(defaultValue);
```

---

### Deep-Link Navigation
**Source:** `src/org/selection.ts` (full file)
**Apply to:** `OverviewSurface.tsx`, `TasksSurface.tsx`, `AgentsSurface.tsx`, `SwarmMap.tsx`, `SwarmMapLegend.tsx`

```typescript
import { requestOpenInGrid, requestOpenInReview } from '../../org/selection';
// Node click → grid (terminal pane):
requestOpenInGrid(paneId);
// Node click → review (card drawer):
requestOpenInReview(cardId);
// App.tsx createEffect watches openInGridRequest() and calls setActiveView('grid')
```

---

### Design Token Usage (no raw hex)
**Source:** `src/styles/variant-b.css` + `src/components/titlebar/PresetSwitcher.tsx:87–93`
**Apply to:** ALL new `.css` files and inline `style={{}}` props in all new `.tsx` files

```tsx
// Token-only pattern (PresetSwitcher.tsx:87–93):
background: active() ? 'var(--focus)' : 'transparent',
color: active() ? 'var(--fg-0)' : props.disabled ? 'var(--fg-3)' : 'var(--fg-2)',
// color-mix tint (cockpitStyles.css pattern):
background: `color-mix(in srgb, var(--accent-red) 15%, transparent)`,
// NO raw hex values anywhere in V24 code.
```

---

### Loading / Error State
**Source:** `src/org/orgStyles.css:191–239` (`.org-spinner`, `.org-error-state` classes)
**Apply to:** `OverviewSurface.tsx`, `TasksSurface.tsx`, `AgentsSurface.tsx`, `SwarmMap.tsx`

```tsx
// Reuse existing CSS classes — do not create new loading/error markup:
<Show when={loading()} fallback={/* content or error */}>
  <div class="org-spinner"><span class="org-spinner__glyph">⟳</span></div>
</Show>
```

---

### Section Heading (ALL CAPS Poppins)
**Source:** `src/org/cockpit/cockpitStyles.css:70–78` (`.cockpit-sect`) + `src/components/sidebar/sidebar.css:71–79` (`.sidebar-section-label`)
**Apply to:** Group headers in `OverviewSurface.tsx`, `TasksSurface.tsx`, `AgentsSurface.tsx`

```css
/* Reuse .cockpit-sect or .sidebar-section-label — already has the correct
   font-family/size/weight/letter-spacing/text-transform tokens */
font-family: var(--font-display), Poppins, system-ui, sans-serif;
font-size: 11px; font-weight: 600;
letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-3);
```

---

### A8 Reduced-Motion Double-Guard
**Source:** `src/index.css:81–94` (global kill switch) + `src/org/cockpit/cockpitStyles.css:240–254` (local block pattern)
**Apply to:** `swarmMap.css` (every `@keyframes` block)

```css
/* Pattern: ALL new keyframes wrapped in BOTH guards (A8 = mandatory): */
@media (not (prefers-reduced-motion: reduce)) {
  html:not(.reduced-motion) .swarm-traveling-dot { animation: travelEdge 2000ms linear infinite; }
}
@keyframes travelEdge { ... }
/* Plus a local reduced-motion block mirroring cockpitStyles.css:240–254 */
```

---

### Vitest Test Harness Setup
**Source:** `src/__tests__/liveReviewToggle.test.tsx:14–61` + `src/org/cockpit/__tests__/cockpit.test.tsx:10–23`
**Apply to:** ALL 8 Wave-0 test files

```typescript
// Standard harness for ALL new test files:
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  vi.restoreAllMocks();
});
```

---

## No Analog Found

No V24 files are fully without analog. The closest to "no codebase precedent" is the SVG radial layout math inside `SwarmMap.tsx` — the polar-coordinate cluster layout is new, but it is pure math (not a component pattern), and the surrounding SolidJS SVG shell follows the CockpitShell composite pattern. Planner should use RESEARCH.md §Radial Layout Algorithm for the math specifics.

| File aspect | Role | Reason |
|-------------|------|--------|
| Polar-coordinate radial layout math in `SwarmMap.tsx` | Pure math (inlined) | No prior SVG graph rendering in codebase; use RESEARCH.md §Radial Layout Algorithm |
| `liveGraphPatches` signal extension to `sseClient.ts` | Utility extension | Extension of existing module; RESEARCH.md §Live Edge Updates has the pattern |

---

## Metadata

**Analog search scope:** `apps/voss-app/src/` (all subdirectories)
**Primary files read:** 20 source files
**Key codebase constraints verified:**
- Canvas-swap `display:none` contract: `App.tsx:1495` + `GridRoot.tsx:438`
- A8 double-guard: `index.css:81–94`
- Proxy-strip: `ReplayPanel.tsx:67–68`
- No raw hex: `PresetSwitcher.tsx:87–93`
- Test harness: `liveReviewToggle.test.tsx:14–61`
- CSS source assertion: `a11y.test.tsx:33–39`
- Pure-fn null-tolerance: `boardDerive.ts:45–47`, `swarmReconcile.ts:56–57`
- Module-level signals: `selection.ts:6–28`, `orgStore.ts:11–16`

**Pattern extraction date:** 2026-06-14

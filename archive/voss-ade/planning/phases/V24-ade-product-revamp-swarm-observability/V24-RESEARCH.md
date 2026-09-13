# Phase V24: ADE Product Revamp + Swarm Observability — Research

**Researched:** 2026-06-14
**Domain:** SolidJS + Tauri app restructure — portal shell, canvas-swap, radial graph, live SSE wiring, replay
**Confidence:** HIGH (all critical patterns verified against real codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Canvas-swap: portal surface takes canvas; GridRoot stays mounted/alive behind it with `display:none`. NOT a split, NOT a drawer. Instant snap-back.
- **D-02:** Fresh/project-less workspace boots to terminal grid. Workspaces with active managed runs restore last-used surface.
- **D-03:** "Ask Voss to…" composer is global and always-present (Cmd-K-style), reachable from any surface.
- **D-04:** Default safety mode = Read only.
- **D-05:** Composer shows only ask + safety mode by default. Scope/agent/team/budget/context collapsed behind "Advanced."
- **D-06:** Swarm Map layout = radial. Objective/run = center node, agents orbit, work/artifact/alert nodes radiate outward.
- **D-07:** Default scope = all active runs. Multi-run model = one radial cluster per run, packed across canvas; click cluster to focus/expand.
- **D-08:** User-facing unit = "Task." Portal item = "Tasks." Composer creates a Task.
- **D-09:** Board work-items inside a Task = "steps"/"cards" in copy. Code identifiers stay `runId`/`RunData`/`currentRunId`. Zero internal rename.
- **D-10:** Observability surface name = "Swarm Map."
- **D-11:** Safety-mode labels = Read only / Can edit / Autopilot. Retire Plan/Edit/Auto.
- **Top chrome:** Project/window identity, command palette, mode indicators only. `fanout/pipeline/swarm/watchers` presets demoted to layout menu/pane toolbar.

### Claude's Discretion
- D-02: Launch/no-active-run view nuance decided by Claude (user authorized). Flag to override at planning.
- D-09: Task/step naming reconciliation decided by Claude. Flag to override at planning.

### Deferred Ideas (OUT OF SCOPE)
- None formally deferred to other phases from discussion. In-phase details left to planner: replay/timeline scrubber granularity, Voss-vs-non-Voss pane visual distinction, alert/attention node handling specifics.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VADE2-01 | Product/design contract committed with IA, success criteria, and locked vocabulary | V24-UI-SPEC.md already serves as the contract; PRODUCT.md/DESIGN.md must reference it |
| VADE2-02 | Left portal + canvas-swap; grid stays mounted/alive across portal round-trips | §Canvas-Swap pattern: display:none proven by liveReviewToggle.test.tsx (V14) |
| VADE2-03 | Quiet top chrome; fanout/pipeline/swarm/watchers presets demoted | PresetSwitcher.tsx fully self-contained; remove/move from Titlebar.tsx render path |
| VADE2-04 | Global "Ask Voss to…" composer; Read only default; scope/budget/context behind Advanced | Replaces RunCommandBar; existing runIntake.ts assembleRunSpec reusable |
| VADE2-05 | Overview/Tasks/Agents surfaces; statuses, attention actions, pane/run deep links | orgStore enumerateRuns + boardDerive cardsFromRunData + attentionQueue + selection.ts |
| VADE2-06 | Swarm Map static model; radial clusters; honest missing-signal handling | swarmReconcile + boardDerive + treeBuild + types.ts + audit data map §Static Model |
| VADE2-07 | Live Swarm Map updates + reduced-motion fallback + replay scrubber | sseClient.connectLiveStream + replayReducer.computeBoardAtStep + A8 double-guard |
| VADE2-08 | Validation: terminal-first checklist, no-fake-signal guard, deep-link/a11y/visual | Vitest + jsdom (existing suite); test patterns from cockpit/__tests__ |
</phase_requirements>

---

## Summary

V24 restructures `apps/voss-app` from a terminal-centric shell with exposed orchestration chrome into a product-coherent ADE. The substrate is already present: V14 cockpit, V15 live SSE, A1–A13 grid/swarm. This phase wires a new spatial model (left portal rail + canvas-swap) over the existing pieces, adds three new surfaces (Overview/Tasks/Agents + Swarm Map), and rebuilds intake as a global composer.

The most technically open question is the Swarm Map radial graph rendering strategy. All other open questions have clear implementation paths grounded in existing codebase patterns. The critical path is: W0 commit the design contract → W1 portal shell (canvas-swap) → W2 composer + mission-control surfaces → W3 Swarm Map static model → W4 live wiring + replay scrubber → W5 validation.

No new npm packages are strictly required. If the planner elects to add a force-layout library, `d3-force` is the recommended choice (slopcheck OK, GitHub d3/d3-force, official d3js.org docs). Hand-rolled radial math is also viable for this use case.

**Primary recommendation:** Implement the Swarm Map radial layout with hand-rolled polar-coordinate math for static layout (single layout pass, no force-directed tick loop needed for the radial-cluster model described in D-07). Add `d3-force` only if multi-cluster collision avoidance becomes complex during W3.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Left portal navigation + canvas-swap | Browser/Client (SolidJS) | — | Pure UI state; no backend involvement; `display:none` toggle on the grid container |
| Terminal grid PTY lifecycle | Tauri/Rust (proc registry) | SolidJS (pane session registry) | Rust owns the PTY process; SolidJS owns the per-pane session/xterm object |
| Swarm Map static node/edge derivation | Browser/Client (SolidJS) | — | Pure function over `RunData` + registries already in-browser |
| Live Swarm Map edge updates | Browser/Client (sseClient) | Backend (V15 SSE server) | SSE stream consumed by sseClient.ts; derived signals update the graph |
| Replay scrubber timeline | Browser/Client (replayReducer) | — | computeBoardAtStep is pure; driven by a Solid signal |
| "Ask Voss to…" composer intake | Browser/Client (SolidJS) | Tauri command (spawn_agent) | UI assembles RunSpec; Tauri command dispatches to harness |
| Mission-control row status derivation | Browser/Client (boardDerive + attentionQueue) | — | cardsFromRunData + deriveColumn already implement this |
| Deep links (node→pane/drawer) | Browser/Client (selection.ts) | — | openInGridRequest / openInReviewRequest signals already exist |
| Safety mode default enforcement | Browser/Client (composer) | — | UI-level; no backend involvement |
| Chrome demotion (PresetSwitcher removal) | Browser/Client (Titlebar.tsx) | — | PresetSwitcher.tsx is self-contained; remove its mount point from Titlebar |

---

## Standard Stack

### Core (no new dependencies required)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| solid-js | 1.9.13 | Reactivity, components, signals | Already locked in package.json [VERIFIED: npm registry] |
| @tauri-apps/api | 2.11.0 | Tauri invoke/events | Already in project [VERIFIED: npm registry] |
| tailwindcss | 4.3.0 | Utility classes (theme inline pattern) | Already in project [VERIFIED: npm registry] |
| CSS vars + @keyframes | — | Design tokens (variant-b.css) + Swarm Map animation | Existing pattern; no library needed |

### Optional: Force-Layout for Multi-Cluster Collision
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| d3-force | 3.0.0 | Velocity Verlet force simulation | Only if hand-rolled cluster packing produces overlapping clusters at N>3 runs |

**d3-force is NOT a required dependency.** The radial layout within each cluster is fixed polar math (agents at r=120px, work nodes at r=220px, alert nodes at r=300px per UI-SPEC). Cluster positioning across the canvas can use a simple grid or Phyllotaxis arrangement without a force tick loop. Add d3-force only if visual quality of multi-cluster packing is unsatisfactory.

**Package Legitimacy Audit** (if d3-force is added):

| Package | Registry | Source Repo | slopcheck | Disposition |
|---------|----------|-------------|-----------|-------------|
| d3-force | npm | github.com/d3/d3-force | [OK] | Approved — add if needed |
| @solidjs/router | npm | github.com/solidjs/solid-router | [OK] | Approved — add if portal routing needed (see §Portal Route/State below) |

Neither package has a postinstall script.

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
                 ┌─────────────────────────────────────────────────────┐
                 │  App.tsx (root — owns orgViewOpen-equivalent signal) │
                 │                                                       │
  ┌──────────────┤  TopChrome (28px) — quiet chrome only               │
  │              │                                                       │
  │  PortalRail  │  Main Canvas (flex-grow)                            │
  │  (48px rail) │  ┌─────────────────────────────────────────────┐   │
  │  8 nav items │  │  GridRoot — ALWAYS mounted                   │   │
  │              │  │  style="display: {activeView==='grid'         │   │
  │  [ask] btn   │  │           ? 'flex' : 'none'}"                │   │
  └──────────────┤  ├─────────────────────────────────────────────┤   │
                 │  │  PortalSurface — conditionally rendered      │   │
                 │  │  (Show when activeView !== 'grid')           │   │
                 │  │  position:absolute; inset:0; z-index above   │   │
                 │  │                                               │   │
                 │  │  Switch (activeView):                        │   │
                 │  │   'overview'  → OverviewSurface              │   │
                 │  │   'tasks'     → TasksSurface                 │   │
                 │  │   'agents'    → AgentsSurface                │   │
                 │  │   'swarm-map' → SwarmMap                     │   │
                 │  │   'review'    → CockpitShell (existing)      │   │
                 │  │   'context'   → ContextPanel (existing)      │   │
                 │  │   'memory'    → MemoryPanel (existing)       │   │
                 │  │   'settings'  → SettingsPanel (existing)     │   │
                 │  └─────────────────────────────────────────────┘   │
                 │                                                       │
                 │  VossComposer (dialog, modal — over all layers)      │
                 └─────────────────────────────────────────────────────┘

SSE/Registry live plane:                   Replay plane:
  sseClient.connectLiveStream               replayReducer.computeBoardAtStep
      ↓ events                                  ↓ step signal
  liveGraphPatch signal                     historyAtStep() derived signal
      ↓                                         ↓
  SwarmMap edge/node updates            SwarmMap node/edge states (scrubber)
```

### Recommended Project Structure (new V24 additions only)
```
src/
├── portal/
│   ├── PortalRail.tsx           # 48px nav rail (8 items + ask trigger)
│   ├── PortalShell.tsx          # canvas-swap host; owns activeView signal
│   └── portal.css
├── surfaces/
│   ├── overview/
│   │   └── OverviewSurface.tsx
│   ├── tasks/
│   │   └── TasksSurface.tsx
│   ├── agents/
│   │   └── AgentsSurface.tsx
│   └── swarm-map/
│       ├── SwarmMap.tsx          # SVG canvas + radial layout
│       ├── swarmMapDerive.ts     # pure: RunData → SwarmNodes/SwarmEdges
│       ├── SwarmMapLegend.tsx    # 200px right panel
│       ├── ReplayScrubber.tsx    # 32px bottom strip
│       ├── EventTraceList.tsx    # reduced-motion fallback
│       └── swarmMap.css
├── composer/
│   ├── VossComposer.tsx         # global composer (Cmd-K dialog)
│   └── composer.css
└── components/titlebar/
    └── TopChrome.tsx            # replaces Titlebar.tsx chrome sections
```

---

## Canvas-Swap Pattern (VADE2-02) — Verified

**The pattern is already proven in production code (V14 implementation).** `App.tsx:1495` does exactly this:

```tsx
// Source: apps/voss-app/src/App.tsx:1495 [VERIFIED: codebase]
<div style={{
  flex: '1', 'min-height': '0', 'min-width': '0',
  display: orgViewOpen() ? 'none' : 'flex',  // grid hidden, NOT unmounted
  'flex-direction': 'column', position: 'relative'
}}>
  <GridRoot ... />
</div>
// Sibling — portal surface rendered alongside (not inside) the grid node:
<Show when={orgViewOpen()}>
  <OrgViewShell ... />
</Show>
```

V24 extends this pattern from one toggle (grid ↔ OrgView) to one-of-eight (grid ↔ one of 8 portal surfaces).

**Critical implementation note:** `GridRoot.tsx:438` comments document the `display:none` contract explicitly:
> "True workspace teardown (tab SWITCH is `display:none` and never disposes this component)"

This comment was written to distinguish the keepalive case from actual teardown. The `onCleanup` in GridRoot only fires on true unmount (tab close), not on `display:none` toggle. PTY sessions survive because the component is never torn down.

**V24 extension — what changes:**

1. Replace `orgViewOpen: () => boolean` with `activeView: () => PortalView` signal (type `'grid' | 'overview' | 'tasks' | 'agents' | 'swarm-map' | 'review' | 'context' | 'memory' | 'settings'`).
2. Grid container: `display: activeView() === 'grid' ? 'flex' : 'none'` (same pattern, wider condition set).
3. Portal surface container: `position: absolute; inset: 0` (per UI-SPEC), rendered when `activeView() !== 'grid'`. Internal `<Switch>` over the 8 portal surfaces.
4. The four new surfaces (Overview/Tasks/Agents/Swarm Map) are conditionally mounted using `<Show when={activeView() === 'overview'}>` etc. — they can be lazily mounted and kept mounted after first activation using a `once-mounted` memo pattern.
5. Existing surfaces (Review, Context, Memory, Settings) can simply render their existing shell components.

**Pane/session identity preservation:** The pane session registry (`paneSessionRegistry.ts`) is module-level state keyed by `paneId`. It is NOT tied to `GridRoot`'s component lifecycle. Sessions survive `display:none` swaps because only `destroyPaneSession` (called from `GridRoot.onCleanup`) tears them down. No additional action required.

**Test pattern:** `src/__tests__/liveReviewToggle.test.tsx` already verifies the "grid stays mounted" contract. V24 test must extend this to verify pane/session identity persists across a portal round-trip (get grid leaf ids before swap, verify same ids after return).

**`@solidjs/router` decision:** The portal navigation is UI-state only (no URL changes needed in a Tauri app). A simple Solid `createSignal<PortalView>` is sufficient and avoids adding a routing dependency. Do NOT use `@solidjs/router` for this — it is designed for URL-based routing in web apps and adds unnecessary complexity for an in-app surface switcher.

---

## Swarm Map Static Model (VADE2-06) — Node/Edge Source Map

The Swarm Map is derived purely from data already available in-browser. Every node and edge type maps to a real source field:

### Node Source Map

| Node Type | Shape (UI-SPEC) | Source Data | Code Path |
|-----------|-----------------|-------------|-----------|
| Objective/Run (center) | Circle 40px, `--focus` ring | `RunData.run_id` + `audit.idea` / `run_final.idea` | `orgStore.runData()` or `enumerateRuns()` result |
| Agent node | Circle 28px | `SessionTreeNode.role` (non-null on child nodes) + `envelope.spent` | `boardDerive.cardsFromRunData()` → nodes with role |
| Work node (step/card) | Square 20px | `SessionTreeNode` (non-root; `parent_run_id !== null`) → `scope ?? id` | `boardDerive.cardsFromRunData()` |
| Artifact node (file/diff/test) | Diamond 16px | `AuditReport.review_sidecars` → `a_verification.test_path_or_rubric` | `RunData.audit.review_sidecars` |
| Alert node (permission/budget/blocker) | Triangle 16px | `attentionQueue()` items (kind: 'permission'|'budget'|'blocked') | `attentionQueue.ts` module signal |
| Placeholder node | Circle 20px dashed | Absent signal — shown when agent/artifact slot has no data | Absence of above |

### Edge Source Map (honest-signal contract)

Every edge MUST carry `source: string` before rendering. The no-fake-signal guard asserts `edge.source !== undefined` for all edges.

| Edge Type | Color | Trigger | `source` Value |
|-----------|-------|---------|----------------|
| Delegation | `--focus` | `em.routing` transition in a SessionTreeNode | `"board_transition:em.routing"` |
| Message | `--accent-blue` | SSE `session.idle` or `budget.updated` event (session → session) | `"sse_event:budget.updated"` etc. |
| Tool call | `--accent-magenta` | SSE `permission.updated` event | `"sse_event:permission.updated"` |
| File edit | `--accent-green` | `ReviewSidecar.a_verification` exists with `test_path_or_rubric` | `"audit_artifact:a_verification"` |
| Review/validation | `--accent-amber` | `BoardTransition.verdict_snapshot` non-null | `"board_transition:verdict_snapshot"` |
| Blocker | `--accent-red` | `deriveColumn(node) === 'Blocked'` or `terminal_state.exit_reason === 'killed'` | `"board_transition:blocked"` |

**Static derivation function signature** (pure, fixture-testable — mirrors `boardDerive.ts` discipline):

```typescript
// Source: swarmMapDerive.ts (new file) [ASSUMED — function to be authored]
export interface SwarmNode {
  id: string;
  type: 'objective' | 'agent' | 'work' | 'artifact' | 'alert' | 'placeholder';
  runId: string;
  label: string;
  status?: string;
  // Radial position: assigned by layout pass, not by derive
}

export interface SwarmEdge {
  id: string;
  from: string;
  to: string;
  type: 'delegation' | 'message' | 'tool-call' | 'file-edit' | 'review' | 'blocker';
  source: string;  // REQUIRED: the no-fake-signal guard tests this
}

export function deriveSwarmGraph(
  runs: Array<{ runData: RunData | null; liveOverlay: Record<string, LiveOverlayEntry> }>,
  attentionItems: AttentionItem[],
): { nodes: SwarmNode[]; edges: SwarmEdge[] }
```

The function is null-tolerant (mirrors `reconcileSwarm` and `cardsFromRunData`): a missing RunData yields an objective placeholder node only.

### Radial Layout Algorithm

Cluster layout (per run) uses fixed polar coordinates — no force simulation needed:
- Center node: cluster centroid (assigned by multi-run packing)
- Agent ring: radius 120px, evenly distributed by angle: `angle = (i / agentCount) * 2π`
- Work/artifact ring: radius 220px
- Alert ring: radius 300px

Multi-run packing: use Phyllotaxis arrangement (golden-angle spiral) for up to 6 runs, falling back to a grid for more. Minimum gap 80px between cluster radii (as per UI-SPEC). No external library required.

---

## Live Edge Updates + Animation (VADE2-07)

### SSE Event → Graph Update Wiring

The existing `sseClient.ts` pattern is the correct model. V24 extends it with a new `liveGraphPatch` signal:

```typescript
// Extend sseClient.ts — add a module-level patch signal [ASSUMED — extension to author]
export interface GraphPatchEvent {
  edgeType: 'message' | 'tool-call' | 'blocker';
  fromNodeId: string;
  toNodeId: string;
  source: string;           // REQUIRED: "sse_event:<type>"
  timestamp: number;
}
const [liveGraphPatches, setLiveGraphPatches] = createSignal<GraphPatchEvent[]>([]);
```

The `applyOverlay` function in `sseClient.ts` already routes by `ev.type`. V24 adds a branch that emits a `GraphPatchEvent` for each SSE event that represents agent communication:
- `permission.updated` → tool-call edge (source → destination = paneId mapping from bridge.ts)
- `budget.updated` → message edge (when limit exceeded)
- `gate.updated` → blocker edge (when gate decision is blocking)

The SwarmMap component subscribes to `liveGraphPatches()` and merges new edges into its derived edge set, each tagged with `source: "sse_event:..."`.

### Animation Implementation (A8 double-guard)

**The A8 double-guard is already defined in `index.css`** and applies globally:

```css
/* Source: apps/voss-app/src/index.css [VERIFIED: codebase] */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition: none !important;
    animation: none !important;
  }
}
html.reduced-motion *,
html.reduced-motion *::before,
html.reduced-motion *::after {
  transition: none !important;
  animation: none !important;
}
```

This global kill switch already covers Swarm Map animations by inheritance. However, the UI-SPEC requires that Swarm Map animations be wrapped in `@media (not (prefers-reduced-motion: reduce))` blocks AND the `html.reduced-motion` class guard, consistent with the global pattern. The planner must ensure all `@keyframes` in `swarmMap.css` are scoped this way.

**Event Trace List (reduced-motion fallback):** The trace list shows `[timestamp] [edge type] [source → destination]`. It is driven by the same `liveGraphPatches()` signal — the patches carry all required fields. The trace list is always populated (even in motion mode) but collapsed; in reduced-motion it is expanded and pinned. This is a display toggle, not a separate data source.

### Animation CSS Pattern (Swarm Map)

```css
/* Source: pattern to author in swarmMap.css [ASSUMED — follows A8 convention] */
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
@keyframes travelEdge { ... }
@keyframes nodePulse  { ... }
@keyframes blockerPulse { ... }
```

All animations use CSS `@keyframes`, not JS `setInterval` (per UI-SPEC constraint). `animation-play-state: paused` when `document.hidden` — add a `createEffect` in SwarmMap that sets a CSS class on the canvas element.

---

## Replay Scrubber (VADE2-07)

**The existing `replayReducer.ts` and `ReplayPanel.tsx` already implement replay over board transitions.** V24 replaces the `ReplayPanel` step-by-step interface with the timeline scrubber UI-SPEC while reusing the same underlying reducer.

Key existing API:

```typescript
// Source: apps/voss-app/src/org/replayReducer.ts [VERIFIED: codebase]
export function computeBoardAtStep(nodes: SessionTreeNode[], step: number): BoardFrame
// Returns: { columns: Record<string, CardSnapshot[]>, step, eventLabel }

// Total steps = count of 'board.transition' entries across all nodes
// ReplayPanel.tsx:countSteps() is the reference implementation
```

**V24 scrubber adaptation:**
- Replace ReplayPanel's `‹` / `›` buttons with `<input type="range">` (native, accessible, as per UI-SPEC)
- Drive the same `computeBoardAtStep(plainNodes, step)` call
- Project the board state to the Swarm Map: cards in 'Done' → work nodes with green ring; 'Blocked' → alert nodes; 'InProgress' → active work nodes
- The scrubber is shown only for completed runs (i.e., `RunData.run_final !== null`)
- Live mode chip in TopChrome shows "replay" when scrubber is active (via a separate `replayActive` signal)

**Critical: strip Solid proxies before the reducer** (already documented in ReplayPanel):
```typescript
// Source: apps/voss-app/src/org/panels/ReplayPanel.tsx [VERIFIED: codebase]
const plainNodes = (): SessionTreeNode[] =>
  JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));
```
This pattern is mandatory — `computeBoardAtStep` uses plain spreads but the nodes arriving from `orgStore.runData()` are Solid store proxies.

**Relationship to TimelineRail:** TimelineRail (`cockpit/TimelineRail.tsx`) is a milestone-level read-only display, not a scrubber. V24 does not replace TimelineRail — it lives in CockpitShell which remains as the "Review" portal surface. The replay scrubber is a new feature exclusive to SwarmMap's bottom strip.

---

## Mission-Control Deep Links (VADE2-05)

**The deep-link mechanism is already fully implemented** in `org/selection.ts`:

```typescript
// Source: apps/voss-app/src/org/selection.ts [VERIFIED: codebase]
export const [openInGridRequest, setOpenInGridRequest] = createSignal<string | null>(null);
export function requestOpenInGrid(paneId: string): void { setOpenInGridRequest(paneId); }

export const [openInReviewRequest, setOpenInReviewRequest] = createSignal<string | null>(null);
export function requestOpenInReview(cardId: string): void { setOpenInReviewRequest(cardId); }
```

`App.tsx` watches `openInGridRequest()` in a `createEffect` and:
1. Flips `activeView` to `'grid'`
2. Calls `gridController.focusPaneById(paneId)`
3. Clears the request signal

**V24 extension:** The Swarm Map and mission-control surfaces use the same signals:
- Node double-click → `requestOpenInGrid(paneId)` or `requestOpenInReview(cardId)` depending on node type
- Mission-control row click → same
- `App.tsx` createEffect already handles both cases; V24 changes `setOrgViewOpen(false)` to `setActiveView('grid')` in that effect

The `attentionQueue`'s `deepLink: DeepLink` field (`{ paneId?, sessionNodeId? }`) already provides the pane/session node IDs needed for Swarm Map node click-through. The mapping from `SessionTreeNode.id` → `paneId` lives in `org/model/bridge.ts` (`cardToPane()` signal).

---

## Top Chrome Demotion (VADE2-03)

**`PresetSwitcher.tsx` is a fully self-contained component.** It receives `activeLayout`, `disabled`, and `onSelect` props from its parent. To demote it:

1. Remove `<PresetSwitcher ...>` from `Titlebar.tsx` render output
2. Add a "Layout" button to the `PortalRail` bottom area (or command palette) that opens a layout dropdown containing the same 4 presets (`fanout`, `pipeline`, `swarm`, `watchers`)
3. `PresetSwitcher` component itself does not change — only its mount point moves

The `TopChrome` component (V24 replacement for the preset-bearing Titlebar) retains:
- Traffic-light buttons (macOS/Linux/Win window controls — `WindowControls.tsx`)
- Project name
- Command palette trigger (`⌘K` → opens `VossComposer`)
- Mode status chip (current safety mode of most-recent Task)
- Live indicator chip (existing `.titlebar-livechip` — reuse as-is)

**Removed from top chrome:**
- `PresetSwitcher` (fanout/pipeline/swarm/watchers)
- `RunCommandBar` (Plan/Edit/Auto, target, budget, scope inline)
- Any raw `runId` display

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reduced-motion kill switch | Custom animation-pause logic | Existing `index.css` A8 double-guard | Already covers ALL elements globally via `!important`; adding another layer is redundant and confusing |
| Session/PTY identity across surface swap | Re-establishing PTY connections | `display:none` toggle + existing `paneSessionRegistry` | Registry is module-level state; sessions outlive component render cycles by design |
| Deep-link navigation | Custom navigation signals | Existing `selection.ts` (openInGridRequest / openInReviewRequest) | Already wired to App.tsx createEffect and grid focus |
| SSE event routing | Custom event bus | `sseClient.connectLiveStream` + `ingestEvent` + `attentionQueue` | Full V15 implementation with dedup, overlay, handle lifecycle |
| Replay step logic | Custom event replayer | `replayReducer.computeBoardAtStep` | Pure, tested, handles terminal_state overrides correctly |
| Board column derivation | Re-deriving run/step status | `boardDerive.cardsFromRunData` + `deriveColumn` | Verified against harness `_derive_column` algorithm |
| Attention item generation | Custom alert logic | `attentionQueue.ingestSnapshotDecisions` + `ingestEvent` | Handles Blocked column, sign-off, unsupported claims, live SSE events |
| Proxy stripping for reducer | Manual proxy detection | `JSON.parse(JSON.stringify(...))` pattern | Established in ReplayPanel.tsx; the only safe approach for Solid store proxies |
| Node/edge tree construction | Custom tree walker | `treeBuild.buildTree` | Handles orphan nodes and cycles correctly |

---

## Common Pitfalls

### Pitfall 1: Conditional `<Show>` Instead of `display:none` for the Grid
**What goes wrong:** Wrapping `<GridRoot>` in `<Show when={activeView() === 'grid'}>` causes the component to unmount, destroying PTY sessions when the user switches to any portal surface.
**Why it happens:** SolidJS `<Show>` unmounts the false branch by default. This is the most natural SolidJS pattern for conditional content.
**How to avoid:** Use CSS `display: activeView() === 'grid' ? 'flex' : 'none'` on the containing div. The comment in `GridRoot.tsx:438` documents this contract. Test: verify the grid div element reference is the same before and after a portal round-trip (same DOM node, only `display` changes).
**Warning signs:** PTY sessions restart after returning from a portal surface; pane scrollback is lost.

### Pitfall 2: Fabricated Swarm Map Edges
**What goes wrong:** An edge is rendered for which no real source data exists — e.g., drawing a delegation edge between two agent nodes just because both appear in the same run.
**Why it happens:** It is tempting to infer relationships from co-presence in a run. The SPEC explicitly prohibits this.
**How to avoid:** Every edge is constructed with a `source` field set to the real data source (`"board_transition:em.routing"`, `"sse_event:permission.updated"`, etc.). The no-fake-signal guard test asserts `every edge has edge.source !== undefined` and that `edge.source` references a real data event/artifact id.
**Warning signs:** Guard test fails with `edge.source === undefined` for some edges.

### Pitfall 3: Solid Store Proxies in `computeBoardAtStep`
**What goes wrong:** Passing `runData()?.session_tree.nodes` directly to `computeBoardAtStep` causes DATA_CLONE_ERR or silent failures when the reducer tries to spread proxy objects.
**Why it happens:** `orgStore.runData()` returns a Solid store proxy. The reducer uses plain object spreads which fail on Proxy objects.
**How to avoid:** Strip proxies with `JSON.parse(JSON.stringify(nodes))` before passing to the reducer. This pattern is documented and already used in `ReplayPanel.tsx`. Also documented in `replayReducer.ts:1-7`.
**Warning signs:** Replay scrubber shows no state changes; console errors about DATA_CLONE_ERR.

### Pitfall 4: Animation Without Reduced-Motion Guard
**What goes wrong:** Swarm Map `@keyframes` run even when `prefers-reduced-motion: reduce` is set, failing the VADE2-08 a11y check.
**Why it happens:** The global `index.css` kill switch uses `animation: none !important` which overrides all animations — BUT only if the `@keyframes` are in regular `animation` properties. Custom SVG `animateTransform` elements or JS `requestAnimationFrame` loops bypass this.
**How to avoid:** Use CSS `@keyframes` exclusively (not SVG SMIL or JS `setInterval`). Wrap new `@keyframes` in `@media (not (prefers-reduced-motion: reduce))` inside `swarmMap.css`. Verify the traveling-dot and pulse animations are NOT present in reduced-motion with a CSS source assertion test (same pattern as `a11y.test.tsx` which uses `readFileSync` to grep the stylesheet).
**Warning signs:** `@media (not (prefers-reduced-motion: reduce))` absent from `swarmMap.css`.

### Pitfall 5: Wrong App.tsx Wiring for activeView Signal
**What goes wrong:** Creating `activeView` signal inside a sub-component instead of `App.tsx` breaks the cross-surface coordination: the `openInGridRequest` createEffect needs to flip `activeView` to `'grid'`, which requires the signal to be at the same scope as the existing `orgViewOpen` effects.
**Why it happens:** Encapsulation instinct — the portal rail "owns" navigation so the signal goes there.
**How to avoid:** `activeView` must live in `App.tsx` (or the workspace-level scope), mirroring `orgViewOpen`. The `PortalRail` receives `activeView` and `onNavTo` as props; it does not own the signal. The existing `openInGridRequest` createEffect in App.tsx becomes `setActiveView('grid')` rather than `setOrgViewOpen(false)`.
**Warning signs:** Clicking a deep link does not switch back to the grid.

### Pitfall 6: SVG Pan/Zoom Needs Careful Implementation
**What goes wrong:** Native HTML pan/zoom on an SVG element conflicts with Tauri's webview-level scroll behavior, causing unexpected navigation or scroll events.
**How to avoid:** Use `pointer-events: none` on the SVG wrapper for non-interactive regions; capture pointer events explicitly on the canvas element. Implement pan as a transform matrix on a `<g>` element, not as scroll. Test pan on the actual Tauri webview, not just jsdom.
**Warning signs:** Pan/zoom works in browser but misbehaves in the Tauri window.

### Pitfall 7: VossComposer Focus Trap in Tauri
**What goes wrong:** Focus-trap implementation (Cmd-K dialog) that works in a normal browser window does not work correctly in Tauri's webview on macOS if the composer is opened while a terminal pane has focus (xterm has its own focus management).
**How to avoid:** The composer is a `<dialog>` element with `aria-modal="true"`. On open, explicitly call `.focus()` on the ask textarea. Use the `inert` attribute on the background (or manage tabindex manually) so Tab cannot escape to xterm. On close, `onCleanup` restores focus to the trigger element.
**Warning signs:** Tab in the open composer focuses the terminal pane behind the overlay.

---

## Validation Architecture (VADE2-08)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.6 + jsdom 29.1.1 |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `cd apps/voss-app && npm test -- --reporter=verbose` |
| Full suite command | `cd apps/voss-app && npm test` |
| E2E command | `cd apps/voss-app && npm run test:e2e` (Playwright) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| VADE2-01 | PRODUCT.md/UI-SPEC committed with vocab | Manual / lint | Check file exists + grep vocabulary tokens | — / manual |
| VADE2-02 | Grid stays mounted across portal round-trip | Unit | `npm test -- swarmPortal.test` | `src/__tests__/swarmPortal.test.tsx` (Wave 0 gap) |
| VADE2-02 | Pane/session identity survives round-trip | Unit | same file | same |
| VADE2-03 | Top chrome has no preset or Plan/Edit/Auto controls | CSS source assertion | `npm test -- topChrome.test` | `src/components/titlebar/__tests__/TopChrome.test.tsx` (Wave 0 gap) |
| VADE2-04 | Composer shows only ask + safety on open; Advanced collapsed | Unit (jsdom render) | `npm test -- VossComposer.test` | `src/composer/__tests__/VossComposer.test.tsx` (Wave 0 gap) |
| VADE2-04 | Safety mode defaults to "Read only" | Unit (same file) | same | same |
| VADE2-05 | Fixture runs appear under correct status groups | Unit | `npm test -- TasksSurface.test` | `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` (Wave 0 gap) |
| VADE2-05 | Deep link from row opens correct pane/drawer | Unit | `npm test -- deepLink.test` | `src/__tests__/portalDeepLink.test.tsx` (Wave 0 gap) |
| VADE2-06 | Empty RunData yields no edges and objective placeholder only | **Unit (no-fake-signal guard)** | `npm test -- swarmMapDerive.test` | `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` (Wave 0 gap) |
| VADE2-06 | Partial RunData: every edge has `edge.source !== undefined` | same file | same | same |
| VADE2-06 | Full fixture: all 5 node types rendered in radial clusters | Unit (jsdom render) | `npm test -- SwarmMap.test` | `src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx` (Wave 0 gap) |
| VADE2-07 | Live SSE event adds edge to graph | Unit (mock stream) | `npm test -- swarmLive.test` | `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` (Wave 0 gap) |
| VADE2-07 | Reduced-motion: swarmMap.css has no animation outside guard | CSS source assertion | `npm test -- swarmA11y.test` | `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` (Wave 0 gap) |
| VADE2-07 | Replay scrubber drives graph to correct step state | Unit | `npm test -- ReplayScrubber.test` | `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` (Wave 0 gap) |
| VADE2-08 | Manual terminal-first checklist | Manual | n/a — documented checklist | manual checklist in V24-08 plan |
| VADE2-08 | Existing grid/pane/terminal unit tests stay green | Regression | `npm test` (full suite) | existing `src/grid/__tests__/` |

### Key Test Patterns (from existing codebase)

**No-fake-signal guard test** (mirrors `swarmReconcile.test.ts` discipline):
```typescript
// Source pattern: src/org/__tests__/swarmReconcile.test.ts [VERIFIED: codebase]
// The guard test structure:
it('emits no edge without a real source on empty RunData', () => {
  const { edges } = deriveSwarmGraph([{ runData: null, liveOverlay: {} }], []);
  expect(edges.every(e => e.source !== undefined)).toBe(true);
  expect(edges.length).toBe(0);  // no runData → no edges
});

it('emits no edge without a real source on partial RunData (no transitions)', () => {
  const partialRun: RunData = { run_id: 'x', session_tree: { root_id: 'n1', nodes: [{ id: 'n1', parent_run_id: null, ... }] }, review: {}, audit: null, run_final: null };
  const { edges } = deriveSwarmGraph([{ runData: partialRun, liveOverlay: {} }], []);
  expect(edges.every(e => typeof e.source === 'string' && e.source.length > 0)).toBe(true);
});
```

**CSS source assertion** (mirrors `a11y.test.tsx` discipline):
```typescript
// Source pattern: src/org/cockpit/__tests__/a11y.test.tsx [VERIFIED: codebase]
import { readFileSync } from 'node:fs';
const rawSwarmCss = readFileSync('src/surfaces/swarm-map/swarmMap.css', 'utf8');

it('swarmMap.css wraps all keyframes in reduced-motion guard', () => {
  // All @keyframes blocks must be inside @media (not (prefers-reduced-motion: reduce))
  expect(rawSwarmCss).toContain('@media (not (prefers-reduced-motion: reduce))');
  // No animation: property outside a reduced-motion guard
  const outsideGuard = rawSwarmCss.replace(/@media\s*\(not\s*\(prefers-reduced-motion[^}]+\}\s*\{[^}]+\}/gs, '');
  expect(outsideGuard).not.toMatch(/animation\s*:/);
});
```

**Canvas-swap preservation test** (mirrors `liveReviewToggle.test.tsx`):
```typescript
// Source pattern: src/__tests__/liveReviewToggle.test.tsx [VERIFIED: codebase]
it('grid host is same element ref after portal round-trip; only display flips', () => {
  const [activeView, setActiveView] = createSignal<PortalView>('grid');
  const root = mount(() => (
    <div data-testid="grid-host" style={{ display: activeView() === 'grid' ? 'flex' : 'none' }}>
      <div data-testid="grid-root">grid</div>
    </div>
  ));
  const before = root.querySelector('[data-testid="grid-host"]');
  setActiveView('tasks');
  expect(root.querySelector('[data-testid="grid-host"]')).toBe(before);  // same node
  expect((before as HTMLElement).style.display).toBe('none');
  setActiveView('grid');
  expect((before as HTMLElement).style.display).toBe('flex');
});
```

### Wave 0 Gaps (test files to create before implementation)
- [ ] `src/__tests__/swarmPortal.test.tsx` — canvas-swap + pane identity round-trip (VADE2-02)
- [ ] `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` — no-fake-signal guard (VADE2-06, critical)
- [ ] `src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx` — radial render smoke test (VADE2-06)
- [ ] `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` — live SSE → edge update (VADE2-07)
- [ ] `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` — CSS reduced-motion guard assertion (VADE2-07)
- [ ] `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` — scrubber drives graph (VADE2-07)
- [ ] `src/composer/__tests__/VossComposer.test.tsx` — composer default state + Advanced collapse (VADE2-04)
- [ ] `src/surfaces/tasks/__tests__/TasksSurface.test.tsx` — fixture run status grouping (VADE2-05)

### Sampling Rate
- **Per task commit:** Quick run on the module under change only (e.g., `npm test -- swarmMapDerive`)
- **Per wave merge:** Full `npm test` suite (all vitest tests)
- **Phase gate:** Full suite green + manual terminal-first checklist documented before `/gsd-verify-work`

---

## Swarm Map Rendering: Library vs Hand-Rolled Decision

The UI-SPEC defines a fully deterministic layout: fixed radii (120/220/300px), polar coordinates, one cluster per run. This is NOT a force-directed layout problem — it is a placement problem with known constraints.

**Recommendation: Hand-rolled SVG with optional d3-force for collision avoidance only.**

Rationale:
1. Each cluster's internal layout is fully determined by polar math — no force iteration needed.
2. Multi-cluster packing (D-07 requirement) is the only problem that benefits from a force simulation, and only when N>3 runs with highly variable cluster sizes.
3. Adding d3-force just for cluster packing introduces ~25KB (minified) for a problem solvable with a golden-angle Phyllotaxis arrangement (6 lines of math, no dependency).
4. No SolidJS-specific force/graph library exists with sufficient maturity or official docs support to recommend.

**SVG rendering:** Inline `<svg>` inside the SolidJS component. Node positions are reactive Solid signals updated when the derived data changes. Edge paths are `<path>` elements with cubic bezier curves (smooth visual without a layout library).

**If d3-force is added later:** Use d3-force headlessly (no DOM manipulation — just the simulation tick). Run the tick synchronously for static layout (30 ticks is enough to converge). Do NOT use `d3-force`'s live simulation for the animated case — drive animation with CSS `@keyframes` only.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | Package install, test run | ✓ | (system) | — |
| Vitest | Unit test suite | ✓ | 4.1.6 (in devDeps) | — |
| Playwright | E2E tests | ✓ | 1.60.0 (in devDeps) | — |
| Tauri CLI | Build/dev | ✓ | 2.11.2 (in devDeps) | — |
| Poppins woff2 fonts | TopChrome display font | ✓ | Bundled locally (index.css) | — |

No missing dependencies with no fallback. No environment blockers.

Step 2.6: No external service/database dependencies required for V24 implementation.

---

## Package Legitimacy Audit

> This phase MAY add d3-force as an optional dependency. All other packages reuse existing deps.

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| d3-force | npm | ~8 yrs (2016) | github.com/d3/d3-force | [OK] | Approved — add only if needed |
| @solidjs/router | npm | 2+ yrs | github.com/solidjs/solid-router | [OK] | Not needed — use signal instead |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  
**No postinstall scripts found** on either package.

*slopcheck was available and ran successfully (pip-installed).*

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Hand-rolled polar math + Phyllotaxis is sufficient for multi-cluster packing at expected N (1–6 runs) without d3-force | Swarm Map Rendering | If N>6 clusters visually overlap, planner must add d3-force in W3 or accept a grid layout fallback |
| A2 | `swarmMapDerive.ts` pure function (new) derives all 5 node types correctly from RunData without edge cases beyond what is documented | Static Model | If hidden fields exist in RunData that the research missed, the derive function may emit incomplete graphs |
| A3 | The Swarm Map SVG can be scrolled/panned using a `<g transform>` matrix without conflicting with Tauri webview scroll | Live Swarm Map | If Tauri intercepts scroll events for pan/zoom, an alternative pointer event strategy is needed |
| A4 | `connectLiveStream` can be extended with a `GraphPatchEvent` emitter without refactoring the existing function signature | Live Edge Updates | If the function is too tightly coupled, a separate `swarmLiveAdapter` module wrapping sseClient may be needed |

**If this table were empty:** All claims were verified or cited.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `orgViewOpen: boolean` toggle (binary grid ↔ cockpit) | `activeView: PortalView` signal (8-way portal) | V24 | New signal replaces old toggle in App.tsx; old toggle wiring converted |
| `RunCommandBar` inline bar (Plan/Edit/Auto exposed) | `VossComposer` modal dialog (Cmd-K, Read only default) | V24 | Complete component replacement; `runIntake.ts` assembleRunSpec reused |
| `PresetSwitcher` in Titlebar | `PresetSwitcher` demoted to layout menu (same component, moved mount) | V24 | Mount point change only; component unchanged |
| `OrgViewShell` as single review surface | 8-way portal with 4 new surfaces + 4 reusing existing | V24 | OrgViewShell becomes the "Review" portal surface |
| Step-by-step `ReplayPanel` (‹/›) | Timeline `<input type="range">` scrubber | V24 | Same reducer, different UI wrapper |

**Deprecated/outdated patterns in V24:**
- `orgViewOpen` boolean signal — replaced by `activeView: PortalView`
- `RunCommandBar` as the primary intake surface — replaced by `VossComposer`
- `PresetSwitcher` in top chrome — demoted to layout menu; existing `Titlebar.tsx` chrome position cleared

---

## Sources

### Primary (HIGH confidence — verified in codebase)
- `apps/voss-app/src/App.tsx:1495` — canvas-swap `display:none` pattern (proven in production)
- `apps/voss-app/src/grid/GridRoot.tsx:438` — documented `display:none` / keepalive contract
- `apps/voss-app/src/__tests__/liveReviewToggle.test.tsx` — verified canvas-swap test pattern
- `apps/voss-app/src/org/replayReducer.ts` — computeBoardAtStep API
- `apps/voss-app/src/org/selection.ts` — deep-link signals
- `apps/voss-app/src/org/boardDerive.ts` — node/edge derivation from RunData
- `apps/voss-app/src/org/treeBuild.ts` — tree construction from SessionTreeNode[]
- `apps/voss-app/src/org/swarmReconcile.ts` — swarm manifest → agent/card reconcile
- `apps/voss-app/src/org/live/sseClient.ts` — SSE stream consumer, applyOverlay pattern
- `apps/voss-app/src/org/attention/attentionQueue.ts` — attention item types + ingest
- `apps/voss-app/src/org/types.ts` — RunData, SessionTreeNode, BoardTransition, AuditReport shapes
- `apps/voss-app/src/index.css` — A8 double-guard for reduced-motion (already global)
- `apps/voss-app/src/styles/variant-b.css` — all design tokens (no new tokens in V24)
- `apps/voss-app/package.json` — confirmed: no graph/layout/router libraries present

### Secondary (MEDIUM confidence — npm registry + official sites)
- `d3-force@3.0.0` — [CITED: d3js.org/d3-force] — force simulation for optional cluster packing
- `@solidjs/router@0.16.1` — [CITED: github.com/solidjs/solid-router] — NOT recommended for this use case

### Tertiary (LOW confidence)
- Phyllotaxis golden-angle arrangement for cluster packing: [ASSUMED] based on well-known algorithm, not verified against a specific doc in this session. Acceptable fallback: simple grid arrangement.

---

## Metadata

**Confidence breakdown:**
- Canvas-swap pattern: HIGH — verified against production App.tsx code + existing tests
- Swarm Map static model: HIGH — all source fields verified against RunData types
- Live SSE wiring: HIGH — verified against sseClient.ts + attentionQueue.ts
- Replay scrubber: HIGH — computeBoardAtStep API verified; UI wrapper is new
- Radial layout math: MEDIUM — standard algorithm, no codebase precedent to verify against
- Animation/reduced-motion: HIGH — A8 double-guard verified in index.css

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable stack; Solid 1.9.x / Tauri 2.11.x unlikely to break these patterns in 30 days)

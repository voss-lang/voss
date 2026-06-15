---
phase: V24-ade-product-revamp-swarm-observability
plan: 07
type: execute
wave: 4
depends_on: ["V24-06"]
files_modified:
  - apps/voss-app/src/org/live/sseClient.ts
  - apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx
  - apps/voss-app/src/surfaces/swarm-map/swarmMap.css
  - apps/voss-app/src/surfaces/swarm-map/EventTraceList.tsx
  - apps/voss-app/src/surfaces/swarm-map/ReplayScrubber.tsx
  - apps/voss-app/src/surfaces/swarm-map/__tests__/swarmLive.test.ts
  - apps/voss-app/src/surfaces/swarm-map/__tests__/swarmA11y.test.ts
  - apps/voss-app/src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx
autonomous: true
requirements: [VADE2-07]
must_haves:
  truths:
    - "Live SSE/registry events add edges/node updates to the Swarm Map, each tagged with a real source"
    - "Animated connectors convey live state via CSS @keyframes only, all wrapped in the A8 reduced-motion double-guard"
    - "Under prefers-reduced-motion / html.reduced-motion, connectors render static and an equivalent Event Trace list is shown"
    - "A completed run can be scrubbed through its timeline and the graph state reflects the scrub position"
  artifacts:
    - path: "apps/voss-app/src/org/live/sseClient.ts"
      provides: "liveGraphPatches signal + GraphPatchEvent; applyOverlay branch emits source-tagged patches"
      contains: "liveGraphPatches"
    - path: "apps/voss-app/src/surfaces/swarm-map/ReplayScrubber.tsx"
      provides: "Range-input timeline scrubber driving computeBoardAtStep over proxy-stripped nodes"
      contains: "computeBoardAtStep"
    - path: "apps/voss-app/src/surfaces/swarm-map/EventTraceList.tsx"
      provides: "Reduced-motion fallback trace list driven by liveGraphPatches"
      contains: "liveGraphPatches"
    - path: "apps/voss-app/src/surfaces/swarm-map/__tests__/swarmA11y.test.ts"
      provides: "CSS source assertion: swarmMap.css has no animation outside the reduced-motion guard"
      contains: "prefers-reduced-motion"
  key_links:
    - from: "apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx"
      to: "apps/voss-app/src/org/live/sseClient.ts"
      via: "subscribes to liveGraphPatches() and merges source-tagged edges"
      pattern: "liveGraphPatches"
    - from: "apps/voss-app/src/surfaces/swarm-map/ReplayScrubber.tsx"
      to: "apps/voss-app/src/org/replayReducer.ts"
      via: "computeBoardAtStep(plainNodes, step) drives graph state"
      pattern: "computeBoardAtStep"
---

<objective>
Make the Swarm Map live and replayable (VADE2-07). Live SSE/registry events
patch edges/nodes onto the graph, each tagged with a real `source` (honest-signal
contract preserved). Animated connectors (traveling dots, node pulses, blocker
pulse) convey live state using CSS `@keyframes` only, every keyframe wrapped in
the A8 reduced-motion double-guard. Under reduced motion, animations cease and an
equivalent Event Trace list (same `liveGraphPatches` data) is shown. Completed
runs replay through a timeline `<input type="range">` scrubber that drives
`computeBoardAtStep` (proxy-stripped) and projects the board state onto the graph.

Purpose: Motion-communicates-state and audit-replay are the trust features that
distinguish the Swarm Map from a decorative graph. Reduced-motion parity is a
non-negotiable a11y bar.

Output: extended `sseClient.ts` (liveGraphPatches), live wiring + keyframes in
SwarmMap.tsx/swarmMap.css, `EventTraceList.tsx`, `ReplayScrubber.tsx`, and the
three Wave-0 tests (live edge, CSS reduced-motion guard, scrubber drives graph).
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
From apps/voss-app/src/org/live/sseClient.ts:
  export interface LiveOverlayEntry { ... }
  export function connectLiveStream(args: ConnectLiveStreamArgs): LiveStreamHandle;  // applyOverlay routes by ev.type
  export { liveLabel, liveOverlay, liveHandles };
  export function __resetLiveStream(): void;  // test reset hook

From apps/voss-app/src/org/replayReducer.ts:
  export const CANONICAL_COLUMNS = [...];
  export function computeBoardAtStep(nodes: SessionTreeNode[], step: number): BoardFrame;  // { columns, step, eventLabel }
From apps/voss-app/src/org/panels/ReplayPanel.tsx:
  countSteps(nodes) reference; plainNodes = () => JSON.parse(JSON.stringify(nodes ?? []));  // proxy-strip MANDATORY

From apps/voss-app/src/index.css (lines ~81-94): A8 double-guard (global) — local keyframes must ALSO be guarded.

Contracts this plan AUTHORS (sseClient extension):
  export interface GraphPatchEvent { edgeType: 'message'|'tool-call'|'blocker'; fromNodeId; toNodeId; source: string; timestamp: number; }
  export const liveGraphPatches: () => GraphPatchEvent[];   // module-level signal
  // applyOverlay adds a branch: permission.updated→tool-call, budget.updated→message, gate.updated→blocker;
  // each emitted patch carries source: "sse_event:<type>"
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend sseClient with liveGraphPatches + author live-edge and CSS-guard tests (Wave 0)</name>
  <files>apps/voss-app/src/org/live/sseClient.ts, apps/voss-app/src/surfaces/swarm-map/__tests__/swarmLive.test.ts, apps/voss-app/src/surfaces/swarm-map/__tests__/swarmA11y.test.ts</files>
  <read_first>
    - apps/voss-app/src/org/live/sseClient.ts (applyOverlay routing-by-ev.type; module-signal export pattern; __resetLiveStream)
    - apps/voss-app/src/org/__tests__/swarmReconcile.test.ts (pure fixture/mock-stream test analog)
    - apps/voss-app/src/org/cockpit/__tests__/a11y.test.tsx (readFileSync CSS source-assertion analog — copy exactly)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-RESEARCH.md (§Live Edge Updates — GraphPatchEvent, applyOverlay branch, animation A8 guard)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§swarmLive.test.ts, §swarmA11y.test.ts, §sseClient liveGraphPatches extension)
  </read_first>
  <behavior>
    - sseClient: a `permission.updated` event routed through applyOverlay emits a GraphPatchEvent with edgeType 'tool-call' and source "sse_event:permission.updated".
    - swarmLive test: feeding a mock SSE event of each mapped type produces a liveGraphPatches entry whose source is a non-empty "sse_event:*" string (honest-signal preserved live).
    - swarmA11y test: swarmMap.css contains `@media (not (prefers-reduced-motion: reduce))` AND no `animation:` declaration exists outside a reduced-motion guard block.
  </behavior>
  <action>
    Extend `sseClient.ts`: add the module-level `[liveGraphPatches, setLiveGraphPatches] =
    createSignal<GraphPatchEvent[]>([])`, export `liveGraphPatches` and the `GraphPatchEvent` type, and add a
    branch in `applyOverlay` (or the event ingest path) that, for `permission.updated` → tool-call,
    `budget.updated` (limit exceeded) → message, `gate.updated` (blocking) → blocker, appends a GraphPatchEvent
    with `source: "sse_event:<type>"` and `timestamp`. Do NOT refactor the existing `connectLiveStream` signature
    (RESEARCH A4) and keep `__resetLiveStream` resetting the new signal too. Every emitted patch MUST carry a
    non-empty source (honest-signal contract extends to live).
    Write `swarmLive.test.ts` (mirrors swarmReconcile.test.ts + sseClient mock): drive a mock event of each mapped
    type and assert a corresponding liveGraphPatches entry with the correct edgeType and a non-empty
    `source` starting "sse_event:". Reset via `__resetLiveStream` in afterEach.
    Write `swarmA11y.test.ts` (mirrors a11y.test.tsx): `readFileSync('src/surfaces/swarm-map/swarmMap.css','utf8')`,
    assert it contains `@media (not (prefers-reduced-motion: reduce))`, and that stripping the guarded blocks leaves
    no `animation:` declaration. This test is RED until Task 2 adds the guarded keyframes.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -i "sseClient\|swarmLive\|swarmA11y" | head; npm test -- swarmLive 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `sseClient.ts` exports `liveGraphPatches` + `GraphPatchEvent`; applyOverlay emits source-tagged patches for permission/budget/gate events; existing `connectLiveStream` signature unchanged.
    - `swarmLive.test.ts` asserts each mapped event yields a liveGraphPatches entry with a non-empty `source` beginning "sse_event:".
    - `swarmA11y.test.ts` asserts presence of the reduced-motion media guard and absence of unguarded `animation:` in swarmMap.css.
    - `npm test -- swarmLive` passes GREEN; `swarmA11y` is RED pending Task 2 keyframes.
  </acceptance_criteria>
  <done>sseClient emits source-tagged live graph patches; live-edge test GREEN; CSS-guard test authored (RED until keyframes land).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire live connectors + guarded keyframes + EventTraceList + ReplayScrubber</name>
  <files>apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx, apps/voss-app/src/surfaces/swarm-map/swarmMap.css, apps/voss-app/src/surfaces/swarm-map/EventTraceList.tsx, apps/voss-app/src/surfaces/swarm-map/ReplayScrubber.tsx, apps/voss-app/src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx</files>
  <read_first>
    - apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx (from V24-06 — subscribe to liveGraphPatches, merge edges, mount scrubber + trace list)
    - apps/voss-app/src/surfaces/swarm-map/swarmMap.css (from V24-06 — add guarded keyframes into the existing A8 scaffold)
    - apps/voss-app/src/org/live/sseClient.ts (liveGraphPatches from Task 1)
    - apps/voss-app/src/org/replayReducer.ts (computeBoardAtStep, CANONICAL_COLUMNS)
    - apps/voss-app/src/org/panels/ReplayPanel.tsx (countSteps + plainNodes proxy-strip — EXACT analog)
    - apps/voss-app/src/org/attention/AttentionPanel.tsx (signal-driven list-row analog for EventTraceList)
    - apps/voss-app/src/index.css (A8 double-guard pattern to replicate locally)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§EventTraceList, §ReplayScrubber, §swarmMap.css keyframes, §ReplayScrubber.test.tsx)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§6 Live connectors + animation budget, §7 Replay scrubber ARIA)
  </read_first>
  <behavior>
    - Live: a new liveGraphPatches entry merges a source-tagged edge into the rendered graph and triggers the destination node's 300ms ring pulse (motion mode only).
    - Reduced motion: with html.reduced-motion, no traveling dots/pulses run; the EventTraceList is expanded and pinned, showing [timestamp] [edge type] [source → destination] with equivalent info.
    - Replay: for a completed run (run_final !== null) the scrubber appears; moving the range input changes `step` and the graph state reflects computeBoardAtStep at that step (Done→done nodes, Blocked→alert, InProgress→active).
  </behavior>
  <action>
    Edit `SwarmMap.tsx`: subscribe to `liveGraphPatches()` and merge each patch as a source-tagged `SwarmEdge`
    into the rendered edge set (NEVER drop the source — honest-signal). Trigger the destination node ring-pulse
    class on new patches (motion mode). Mount `<EventTraceList>` in the legend panel (collapsed in motion mode,
    expanded+pinned under reduced motion — detect via `html.reduced-motion` class / matchMedia). Mount
    `<ReplayScrubber>` as the 32px bottom strip ONLY when a completed run is selected (run_final !== null), and
    project its frame onto the graph node/edge states. Keep the `document.hidden → swarm-paused` effect from V24-06.
    Add guarded keyframes to `swarmMap.css` INSIDE the existing A8 scaffold: `travelEdge` (2000ms linear infinite
    traveling dot), `nodePulse` (300ms ease-out ring), `blockerPulse` (1500ms ease-in-out infinite) — each
    selector wrapped in BOTH `@media (not (prefers-reduced-motion: reduce))` AND `html:not(.reduced-motion)`; the
    raw `@keyframes` definitions may sit outside but NO `animation:` property may appear outside the guard. Tokens
    only; colors per edge type accents.
    Build `EventTraceList.tsx` (AttentionPanel-style, driven by `liveGraphPatches()`): rows `[timestamp] [edge
    type] [source → destination]` in `--font-mono` 11px `--fg-2`; always present, collapsed by default, expanded
    under reduced motion. Build `ReplayScrubber.tsx` (ReplayPanel analog): `step` signal, MANDATORY proxy-strip
    `plainNodes = () => JSON.parse(JSON.stringify(data.session_tree.nodes ?? []))`, `total = countSteps(plainNodes())`,
    `frame = computeBoardAtStep(plainNodes(), step())`; render `<input type="range" aria-label="Replay timeline"
    aria-valuenow aria-valuemin aria-valuemax>` plus a play/pause button with a state-dependent aria-label
    ("Play replay"/"Pause replay") and current/end time labels (`--font-mono` tabular-nums).
    Write `ReplayScrubber.test.tsx` (signal-drive render): assert the range value reflects the step signal and that
    changing the range input updates the projected graph/frame to the corresponding step.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -i "swarm-map" | head; npm test -- swarmA11y 2>&1 | tail -10; npm test -- ReplayScrubber 2>&1 | tail -10; npm test -- swarmLive 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - SwarmMap subscribes to `liveGraphPatches()` and merges source-tagged edges; destination ring-pulse fires on new patches (motion mode).
    - `EventTraceList.tsx` renders [timestamp][edge type][source→destination] from liveGraphPatches; expanded/pinned under reduced motion.
    - `ReplayScrubber.tsx` proxy-strips nodes, uses `computeBoardAtStep`, renders an accessible `<input type="range">` + state-dependent play/pause aria-label; shown only for completed runs.
    - `swarmMap.css` keyframes (travelEdge/nodePulse/blockerPulse) are all inside the A8 double-guard; no `animation:` outside the guard → `npm test -- swarmA11y` GREEN.
    - `npm test -- ReplayScrubber` and `npm test -- swarmLive` pass GREEN; `npx tsc --noEmit` clean for swarm-map/*.
  </acceptance_criteria>
  <done>Live source-tagged connectors animate (CSS-only, A8-guarded) with a reduced-motion trace fallback; completed runs are replay-scrubbable.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SSE stream → liveGraphPatches → graph | Live events from the harness (V15 SSE server) consumed and rendered as edges — untrusted input. |
| reduced-motion preference → render path | a11y boundary: motion must be fully suppressible with equivalent non-motion information. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-07-T1 | Tampering (signal integrity) | live edges from SSE | mitigate | Every live patch carries `source: "sse_event:<type>"`; SwarmMap never renders a live edge without a source. Honest-signal contract preserved on the live path (guarded by swarmLive test asserting non-empty source). |
| T-V24-07-I | Injection | SSE event payload → node ids/labels in edges | mitigate | from/to node ids and trace labels rendered as Solid/SVG text (auto-escaped), never innerHTML — a crafted SSE event cannot inject markup into the canvas or trace list. GraphPatchEvent fields are typed/structured, not interpolated. |
| T-V24-07-D | Denial of Service | unbounded liveGraphPatches growth | mitigate | The patches signal is capped (bounded ring / trimmed to a recent window) so a high-rate SSE stream cannot grow the array unboundedly and freeze the render. EventTraceList renders a bounded recent slice. |
| T-V24-07-A | a11y integrity | reduced-motion fallback | mitigate | All keyframes double-guarded (A8); reduced-motion yields static connectors + the equivalent EventTraceList — no information is motion-only. Enforced by the swarmA11y CSS source assertion. |
| T-V24-07-T2 | Tampering | npm/pip/cargo installs | mitigate | No new packages; CSS @keyframes only (no JS setInterval/SMIL). Zero install surface. |

HIGH-severity (relative): T-V24-07-T1 live signal integrity — mitigated and gated by the swarmLive source assertion.
</threat_model>

<verification>
- `npm test -- swarmLive`, `npm test -- swarmA11y`, `npm test -- ReplayScrubber` all GREEN.
- `npx tsc --noEmit` clean for swarm-map/* and sseClient.ts.
- Full suite green at wave merge.
- Manual (deferred to V24-08): Swarm Map pan/zoom + live animation on a real Tauri webview.
</verification>

<success_criteria>
Live edges update from a stream fixture (each source-tagged); reduced-motion yields static connectors + a trace
fallback; a completed run is replay-scrubbable and the graph reflects the scrub position (VADE2-07 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-07-SUMMARY.md` when done.
</output>

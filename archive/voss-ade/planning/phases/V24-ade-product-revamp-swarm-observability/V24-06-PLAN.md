---
phase: V24-ade-product-revamp-swarm-observability
plan: 06
type: execute
wave: 3
depends_on: ["V24-05"]
files_modified:
  - apps/voss-app/src/surfaces/swarm-map/swarmMapDerive.ts
  - apps/voss-app/src/surfaces/swarm-map/swarmLayout.ts
  - apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx
  - apps/voss-app/src/surfaces/swarm-map/SwarmMapLegend.tsx
  - apps/voss-app/src/surfaces/swarm-map/swarmMap.css
  - apps/voss-app/src/portal/PortalShell.tsx
  - apps/voss-app/src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts
  - apps/voss-app/src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx
autonomous: true
requirements: [VADE2-06]
must_haves:
  truths:
    - "The Swarm Map derives objective/agent/work/artifact/alert nodes only from real signals (RunData, board/session tree, registry, attention, audit/review)"
    - "Empty/partial signal sources render honest placeholders or omit nodes — signals are never synthesized"
    - "Every rendered edge carries a real source field; the map emits NO edge without a source (no fabricated agent communication)"
    - "With full fixture data, nodes render in radial clusters (one cluster per run)"
  artifacts:
    - path: "apps/voss-app/src/surfaces/swarm-map/swarmMapDerive.ts"
      provides: "Pure deriveSwarmGraph(runs, attentionItems) → {nodes, edges}; null-tolerant; every edge has source"
      contains: "deriveSwarmGraph"
    - path: "apps/voss-app/src/surfaces/swarm-map/swarmLayout.ts"
      provides: "Pure radial polar layout + multi-cluster Phyllotaxis packing (no external lib)"
      contains: "radial"
    - path: "apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx"
      provides: "SVG radial canvas + legend; proxy-strips runData before derive; honest empty state"
      contains: "deriveSwarmGraph"
    - path: "apps/voss-app/src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts"
      provides: "NO-FAKE-SIGNAL GUARD: empty→0 edges + placeholder only; partial→every edge.source non-empty"
      contains: "edge.source"
  key_links:
    - from: "apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx"
      to: "apps/voss-app/src/surfaces/swarm-map/swarmMapDerive.ts"
      via: "deriveSwarmGraph(plainRunData, attentionQueue()) after JSON proxy-strip"
      pattern: "deriveSwarmGraph"
    - from: "apps/voss-app/src/portal/PortalShell.tsx"
      to: "SwarmMap"
      via: "Switch mounts <SwarmMap> for activeView === 'swarm-map'"
      pattern: "SwarmMap"
---

<objective>
Build the static Swarm Map model (VADE2-06): a radial observability graph
derived ONLY from real signals — RunData, board/session tree, registry,
budget/context, attention items, and audit/review artifacts. Missing signals
render as honest placeholder nodes or are omitted; nothing is synthesized. The
honest-signal contract is enforced by a guard test: every edge carries a real
`source` string, and the map emits NO edge without a source (no fabricated agent
communication). Layout is radial — objective/run at cluster center, agents orbit,
work/artifact/alert nodes radiate — with one cluster per run packed across the
canvas (D-06/D-07). Rendering is hand-rolled SVG with polar math; no external
graph library.

Purpose: The Swarm Map is the observability differentiator, and its single
hardest constraint is honesty. This plan delivers the derive function, the
critical no-fake-signal guard, the radial layout, and the static surface.

Output: `swarmMapDerive.ts` (pure), `swarmLayout.ts` (pure), `SwarmMap.tsx`,
`SwarmMapLegend.tsx`, `swarmMap.css`, PortalShell wiring, and the two Wave-0
tests (the no-fake-signal guard + radial render smoke).
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
<!-- Verified from codebase 2026-06-14. Node/edge source map from RESEARCH §Static Model. -->
From apps/voss-app/src/org/boardDerive.ts:
  export function deriveColumn(node: SessionTreeNode): string;
  export function cardsFromRunData(data: RunData | null): BoardCard[];  // null-tolerant → []
From apps/voss-app/src/org/swarmReconcile.ts:
  reconcileSwarm(null) → { rosterRows: [], cards: [] }  // null-tolerance pattern to mirror
From apps/voss-app/src/org/treeBuild.ts:
  export function buildTree(nodes): ...;  // orphan/cycle-safe tree construction
From apps/voss-app/src/org/attention/attentionQueue.ts:
  export const attentionQueue: () => AttentionItem[];  // kind 'permission'|'budget'|'blocked'
From apps/voss-app/src/org/types.ts:
  RunData { run_id; session_tree { root_id; nodes: SessionTreeNode[] }; review; audit; run_final }
  SessionTreeNode { id; parent_run_id; role?; scope?; ... }
From apps/voss-app/src/org/panels/ReplayPanel.tsx (proxy-strip — MANDATORY before any pure fn):
  const plainNodes = () => JSON.parse(JSON.stringify(props.data?.session_tree.nodes ?? []));

Contracts this plan AUTHORS:
  export interface SwarmNode { id; type: 'objective'|'agent'|'work'|'artifact'|'alert'|'placeholder'; runId; label; status?; paneId?; }
  export interface SwarmEdge { id; from; to; type: 'delegation'|'message'|'tool-call'|'file-edit'|'review'|'blocker'; source: string; }
  export function deriveSwarmGraph(
    runs: Array<{ runData: RunData | null; liveOverlay: Record<string, LiveOverlayEntry> }>,
    attentionItems: AttentionItem[],
  ): { nodes: SwarmNode[]; edges: SwarmEdge[] };

Edge source map (every edge.source MUST be one of these real sources):
  delegation → "board_transition:em.routing"
  message    → "sse_event:budget.updated" (etc.)
  tool-call  → "sse_event:permission.updated"
  file-edit  → "audit_artifact:a_verification"
  review     → "board_transition:verdict_snapshot"
  blocker    → "board_transition:blocked"
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Author swarmMapDerive (pure) + the NO-FAKE-SIGNAL guard test (Wave 0, critical)</name>
  <files>apps/voss-app/src/surfaces/swarm-map/swarmMapDerive.ts, apps/voss-app/src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts</files>
  <read_first>
    - apps/voss-app/src/org/boardDerive.ts (pure-fn null-tolerance discipline + deriveColumn/cardsFromRunData)
    - apps/voss-app/src/org/swarmReconcile.ts (null-tolerance return shape to mirror)
    - apps/voss-app/src/org/__tests__/swarmReconcile.test.ts (EXACT pure-fn test structure to copy)
    - apps/voss-app/src/org/types.ts (RunData/SessionTreeNode/AuditReport/BoardTransition shapes)
    - apps/voss-app/src/org/attention/attentionQueue.ts (AttentionItem kinds for alert nodes)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-RESEARCH.md (§Swarm Map Static Model — Node/Edge Source Map, the authoritative field mapping)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§swarmMapDerive.ts, §swarmMapDerive.test.ts)
  </read_first>
  <behavior>
    - Test 1 (null-tolerant): deriveSwarmGraph([], []) → { nodes: [], edges: [] }; does not throw.
    - Test 2 (empty RunData): deriveSwarmGraph([{ runData: null, liveOverlay: {} }], []) → nodes are objective placeholder(s) only; edges.length === 0.
    - Test 3 (GUARD — partial RunData, no transitions): every edge has typeof source === 'string' && source.length > 0; co-presence of two agents in a run yields NO inferred edge.
    - Test 4 (full fixture): objective + agent + work + artifact + alert node types all present; every edge.source matches a known real source (board_transition:* | sse_event:* | audit_artifact:*).
  </behavior>
  <action>
    Author `swarmMapDerive.ts` exporting `SwarmNode`, `SwarmEdge`, and the pure `deriveSwarmGraph`
    (signature in interfaces). Discipline mirrors `boardDerive.ts`: no Solid imports, no produce/structuredClone,
    plain reads + object literals, null guard first (`if (!runs || runs.length === 0) return { nodes: [], edges: [] }`).
    Derive nodes per RESEARCH §Node Source Map: objective = RunData.run_id (+ idea); agent = SessionTreeNode with
    role !== null; work = non-root nodes via cardsFromRunData; artifact = audit.review_sidecars a_verification;
    alert = attentionItems (permission/budget/blocked). Missing agent/artifact slot → a `placeholder` node, NEVER a
    fabricated real node. Derive edges per RESEARCH §Edge Source Map: EVERY edge constructed with an explicit
    `source` string drawn from a real transition/event/artifact — delegation from `em.routing` transitions,
    review from `verdict_snapshot`, blocker from Blocked column / killed terminal_state, file-edit from
    a_verification. NEVER infer an edge from co-presence. null runData → objective placeholder only, zero edges.
    Then write `swarmMapDerive.test.ts` mirroring `swarmReconcile.test.ts`: implement all four behavior tests.
    Test 3 is THE critical guard (VADE2-06 acceptance): `expect(edges.every(e => typeof e.source === 'string' &&
    e.source.length > 0)).toBe(true)`. The derive function is authored first so the guard is meaningful (not a stub
    XPASS). RED→GREEN within this task.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -i swarmMapDerive | head; npm test -- swarmMapDerive 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `swarmMapDerive.ts` exports `deriveSwarmGraph`, `SwarmNode`, `SwarmEdge` (with required `source: string` on edge).
    - Null/empty inputs return empty arrays and do not throw; null runData yields only placeholder node(s), zero edges.
    - Every edge produced carries a non-empty `source` string from a real source (board_transition:* / sse_event:* / audit_artifact:*).
    - The guard test asserts `edges.every(e => typeof e.source === 'string' && e.source.length > 0)` AND that co-presence does not create an edge.
    - Full-fixture test exercises all five node types.
    - `npm test -- swarmMapDerive` passes GREEN; the derive function is real (not a stub) so the guard is load-bearing.
  </acceptance_criteria>
  <done>Pure derive function + the critical no-fake-signal guard are GREEN; honesty contract enforced at the data layer.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build radial layout + SVG SwarmMap + legend, wire into PortalShell, add render smoke test</name>
  <files>apps/voss-app/src/surfaces/swarm-map/swarmLayout.ts, apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx, apps/voss-app/src/surfaces/swarm-map/SwarmMapLegend.tsx, apps/voss-app/src/surfaces/swarm-map/swarmMap.css, apps/voss-app/src/portal/PortalShell.tsx, apps/voss-app/src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx</files>
  <read_first>
    - apps/voss-app/src/surfaces/swarm-map/swarmMapDerive.ts (from Task 1 — the data this consumes)
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx (composite shell + signal wiring analog)
    - apps/voss-app/src/org/panels/ReplayPanel.tsx (proxy-strip JSON.parse(JSON.stringify()) — MANDATORY)
    - apps/voss-app/src/org/cockpit/CardDrawer.tsx + cockpitStyles.css (legend kv-grid + deep-link button analog)
    - apps/voss-app/src/org/selection.ts (requestOpenInGrid/requestOpenInReview for node deep links)
    - apps/voss-app/src/org/orgStyles.css (.org-spinner / .org-error-state to reuse)
    - apps/voss-app/src/index.css (lines ~81-94: A8 reduced-motion double-guard pattern)
    - apps/voss-app/src/portal/PortalShell.tsx (the swarm-map placeholder Match arm to replace)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-RESEARCH.md (§Radial Layout Algorithm — radii 120/220/300, Phyllotaxis packing, 80px gap)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-PATTERNS.md (§SwarmMap.tsx, §SwarmMapLegend.tsx, §swarmMap.css)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Component Inventory 5 — node/edge shapes/colors, placeholder style, empty state, §Glyph Affordances)
  </read_first>
  <behavior>
    - Render smoke: with a full-fixture run, SwarmMap renders SVG node elements for objective/agent/work/artifact/alert and edge paths; nodes appear in a radial arrangement (center objective, agents on inner ring).
    - With no run data, the canvas shows the honest empty state ("No run data yet" / "Start a Task with ⌘K…") and NO decorative/fake nodes.
    - Placeholder nodes render in the dashed placeholder style (visually distinct, no accent color).
  </behavior>
  <action>
    Author `swarmLayout.ts` (pure, no Solid, no external lib): given `SwarmNode[]` grouped by runId, assign polar
    coordinates per cluster — objective at cluster centroid, agents at radius 120px (`angle = (i/agentCount)*2π`),
    work/artifact at 220px, alert at 300px (RESEARCH §Radial Layout Algorithm). Pack multiple clusters across the
    canvas using a golden-angle Phyllotaxis arrangement for ≤6 runs, grid fallback beyond, minimum 80px gap
    between cluster radii. Return positioned nodes; deterministic (fixture-testable).
    Build `SwarmMap.tsx` (CockpitShell-style shell): proxy-strip runData before derive
    (`const plainRunData = () => runData() ? JSON.parse(JSON.stringify(runData())) : null` — MANDATORY,
    Pitfall 3); compute `graph = () => deriveSwarmGraph([...], attentionQueue())`, position via swarmLayout,
    render inline `<svg>` with a `<g transform>` for pan; node shapes per UI-SPEC (objective circle 40px `--focus`
    ring, agent circle 28px, work square 20px, artifact diamond 16px, alert triangle, placeholder dashed circle);
    edges as `<path>` colored per edge type (delegation `--focus`, message `--accent-blue`, tool-call
    `--accent-magenta`, file-edit `--accent-green`, review `--accent-amber`, blocker `--accent-red`). Honest empty
    state when graph has no real nodes (no fake graph). Node click → populate legend; node double-click →
    `requestOpenInGrid(paneId)` / `requestOpenInReview(id)`. Reuse `.org-spinner`/`.org-error-state`. Add the
    `document.hidden` → `swarm-paused` class effect (animation pause hook; the keyframes themselves arrive in V24-07).
    Build `SwarmMapLegend.tsx` (200px right panel): selected-node header + `.cockpit-kvgrid` kv rows
    (status/role/last-event/cost) + a bottom "Open in grid →" / "Open in review →" deep-link button; "Select a
    node to inspect" when none selected. Write `swarmMap.css`: node/edge/placeholder styles using tokens only;
    include the A8 reduced-motion double-guard scaffold (`@media (not (prefers-reduced-motion: reduce))` block
    present even though the live keyframes land in V24-07) and `.swarm-paused * { animation-play-state: paused
    !important; }`. Replace the swarm-map placeholder Match arm in `PortalShell.tsx` with `<SwarmMap/>`.
    Write `SwarmMap.test.tsx` (render smoke, mirrors cockpit.test.tsx tauri-mock): full-fixture render asserts all
    five node-type elements present and a radial arrangement; no-data render asserts the empty-state copy and zero
    SVG node shapes.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -v node_modules | grep -iE "swarm-map|PortalShell" | head; npm test -- SwarmMap 2>&1 | tail -15; grep -q "JSON.parse(JSON.stringify" src/surfaces/swarm-map/SwarmMap.tsx && echo PROXY_STRIP_OK</automated>
  </verify>
  <acceptance_criteria>
    - `swarmLayout.ts` is pure (no Solid/no external lib), assigns polar coordinates at radii 120/220/300 and packs clusters with ≥80px gap; deterministic.
    - `SwarmMap.tsx` proxy-strips runData with `JSON.parse(JSON.stringify(...))` before `deriveSwarmGraph` (grep prints PROXY_STRIP_OK).
    - Full-fixture render shows objective/agent/work/artifact/alert SVG shapes in a radial arrangement; placeholder nodes render dashed/no-accent.
    - No-data render shows the honest empty state and zero node shapes (no fabricated graph).
    - Node double-click deep-links via `org/selection`; legend shows kv detail + deep-link button.
    - `swarmMap.css` uses tokens only and includes the A8 reduced-motion double-guard scaffold + `.swarm-paused` pause rule.
    - `PortalShell.tsx` mounts `<SwarmMap>` for activeView 'swarm-map'.
    - `npm test -- SwarmMap` passes GREEN; `npx tsc --noEmit` clean for swarm-map/* and PortalShell.
  </acceptance_criteria>
  <done>Static radial Swarm Map renders honest nodes/edges from real signals; placeholders for missing signals; mounted in the portal.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| RunData/registry/audit → graph render | Run/board/session/audit data rendered as node labels and edge sources — untrusted display input. |
| honest-signal contract | The integrity boundary: rendered graph must reflect only real signals; a fabricated edge is an integrity violation, not a cosmetic bug. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-06-T1 | Tampering (signal integrity) | deriveSwarmGraph edges/nodes | mitigate | HONEST-SIGNAL CONTRACT (VADE2-06): every edge carries a real `source` string; no edge without a source; no co-presence inference; missing signal → placeholder or omit. Enforced by the Task 1 guard test (the load-bearing mitigation). This is the highest-priority threat in the phase. |
| T-V24-06-I1 | Injection | node labels (run/agent/file names) | mitigate | Labels rendered as SVG `<text>` children / Solid text nodes (auto-escaped), never via innerHTML — a malicious run/agent/file label cannot inject markup or script into the canvas. |
| T-V24-06-I2 | Information Disclosure | node labels + legend | mitigate | Per D-09, raw `runId` is not used as a user-facing label (objective node shows the Task idea/name, not the run id). Legend shows status/role/cost — already user-owned local values; no secrets/tokens rendered. |
| T-V24-06-T2 | Tampering | npm/pip/cargo installs | mitigate | No new packages — hand-rolled polar math, no d3-force (RESEARCH: optional, not added). Zero install surface. |

HIGH-severity (relative): T-V24-06-T1 signal integrity — mitigated and gated by the no-fake-signal guard test, which MUST be GREEN before the surface is considered done.
</threat_model>

<verification>
- `npm test -- swarmMapDerive` GREEN (no-fake-signal guard) and `npm test -- SwarmMap` GREEN (radial render).
- `npx tsc --noEmit` clean for swarm-map/* and PortalShell.tsx.
- Full suite green at wave merge.
</verification>

<success_criteria>
Empty/partial sources yield honest placeholders/omission with zero source-less edges; full fixture data renders
objective/agent/work/artifact/alert nodes in radial clusters (VADE2-06 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-06-SUMMARY.md` when done.
</output>

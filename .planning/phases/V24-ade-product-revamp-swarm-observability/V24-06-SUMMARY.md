---
phase: V24-ade-product-revamp-swarm-observability
plan: 06
subsystem: ui
tags: [solidjs, svg, observability, swarm-map, radial-layout, honest-signal, vitest, tdd]

# Dependency graph
requires:
  - phase: V24-05
    provides: surfaces/ host pattern + PortalShell swarm-map placeholder arm
  - phase: V14
    provides: boardDerive, attentionQueue, bridge, selection, types, orgStore, sseClient LiveOverlayEntry
provides:
  - Pure deriveSwarmGraph(runs, attentionItems) → honest {nodes, edges}; every edge has a real source; no co-presence inference
  - Pure radial layout (objective centre / agent 120 / work+artifact 220 / alert 300) + phyllotaxis multi-cluster packing
  - SVG SwarmMap surface (proxy-stripped derive, honest empty state, swarm-paused pause-hook) + 200px legend
  - PortalShell mounts <SwarmMap> for activeView 'swarm-map'
affects: [V24-07 (live edge updates + reduced-motion + replay reuse the derive + layout + A8 scaffold)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Honest-signal derive: edge built only with an explicit real source + endpoint-existence guard (no dangling, no co-presence)"
    - "Hand-rolled SVG radial graph (no d3-force); polar math + golden-angle phyllotaxis cluster packing"
    - "Proxy-strip JSON.parse(JSON.stringify(runData)) before any pure derive (Pitfall 3)"

key-files:
  created:
    - apps/voss-app/src/surfaces/swarm-map/swarmMapDerive.ts
    - apps/voss-app/src/surfaces/swarm-map/swarmLayout.ts
    - apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx
    - apps/voss-app/src/surfaces/swarm-map/SwarmMapLegend.tsx
    - apps/voss-app/src/surfaces/swarm-map/swarmMap.css
    - apps/voss-app/src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts
    - apps/voss-app/src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx
  modified:
    - apps/voss-app/src/portal/PortalShell.tsx

key-decisions:
  - "Agent nodes are one per UNIQUE role (not per node-with-role); each non-root card is a work node. Distinct id namespaces (obj:/agent:/work:/artifact:/alert:) — no collisions, no double-count."
  - "Edges are emitted ONLY from real transitions/audit/attention, never co-presence, and only when both endpoints exist (addEdge endpoint guard). This is the load-bearing honest-signal mitigation (T-V24-06-T1)."
  - "Alert nodes/edges come from attentionQueue items (permission→tool-call/sse_event:permission.updated, budget→message/sse_event:budget.updated, blocked→blocker/board_transition:blocked); runId resolved via card→run map, fallback first run."
  - "liveOverlay is accepted in the signature but not consumed by the static derive (live edges land in V24-07); it is not destructured, so noUnusedParameters stays clean."

patterns-established:
  - "swarmMapDerive null-tolerance mirrors boardDerive/swarmReconcile (null guard first, empty arrays)"
  - "Phyllotaxis cluster centres (golden angle, CLUSTER_GAP 760 > 2×300+80) keep multi-run clusters from overlapping; deterministic"

requirements-completed: [VADE2-06]

# Metrics
duration: 16min
completed: 2026-06-15
---

# Phase V24-06: Swarm Map Static Model Summary

**A radial SVG observability graph derived ONLY from real signals — `deriveSwarmGraph` emits objective/agent/work/artifact/alert nodes with placeholders for missing slots, every edge carries a real `source` (no co-presence inference), and a hand-rolled polar + phyllotaxis layout packs one radial cluster per run.**

## Performance

- **Duration:** ~16 min
- **Tasks:** 2 (pure derive + guard; then layout + SVG surface + smoke)
- **Files created:** 7 — **modified:** 1

## Accomplishments
- `swarmMapDerive.ts` (pure): null-tolerant `deriveSwarmGraph(runs, attentionItems)`. Nodes per RESEARCH source map — objective = run idea (never raw runId, D-09); agents = unique roles; work = `cardsFromRunData`; artifact = audit `a_verification`; alert = attention items; placeholders for absent objective/agent slots. Edges only from `em.routing` (delegation), `verdict_snapshot` (review), Blocked/killed (blocker), `a_verification` (file-edit), and attention items (tool-call/message/blocker) — each with an explicit real `source`, gated by endpoint existence.
- The **no-fake-signal guard** test (the phase's load-bearing test): partial run with no transitions → zero edges; full run → every `edge.source` non-empty and matches `board_transition:* | sse_event:* | audit_artifact:*`.
- `swarmLayout.ts` (pure, no lib): objective at cluster centroid; agents on 120px ring (`angle=(i/n)·2π`); work/artifact on 220px; alerts on 300px; clusters packed by golden-angle phyllotaxis with non-overlapping spacing. Deterministic.
- `SwarmMap.tsx`: proxy-strips runData (`JSON.parse(JSON.stringify(...))`) before derive; renders inline `<svg>` with a pan `<g transform>`, node shapes (objective circle 40 / agent circle 28 / work square 20 / artifact diamond / alert triangle / placeholder dashed) and colored edge lines; honest empty state ("No run data yet"); `swarm-paused` visibility pause-hook; work-node deep-link via `org/selection`.
- `SwarmMapLegend.tsx`: 200px panel with selected-node kv detail + "Open in grid →" for work nodes; "Select a node to inspect" empty.
- `swarmMap.css`: token-only node/edge/placeholder styling + the A8 reduced-motion double-guard scaffold + `.swarm-paused` rule (live keyframes deferred to V24-07).
- `PortalShell.tsx` mounts `<SwarmMap>` for `swarm-map`.

## Task Commits

Not committed by me — per the repo's git-safety policy. Built on branch `dev` (where V24-02…05 live; see Issues).

1. **Task 1: swarmMapDerive + no-fake-signal guard** — swarmMapDerive.ts, swarmMapDerive.test.ts (feat+test, RED→GREEN in-task)
2. **Task 2: radial layout + SVG surface + wiring** — swarmLayout.ts, SwarmMap.tsx, SwarmMapLegend.tsx, swarmMap.css, PortalShell.tsx, SwarmMap.test.tsx (feat)

## Files Created/Modified
- `src/surfaces/swarm-map/swarmMapDerive.ts` — pure honest-signal graph derivation
- `src/surfaces/swarm-map/swarmLayout.ts` — pure radial + phyllotaxis layout
- `src/surfaces/swarm-map/SwarmMap.tsx` — SVG radial surface + pan + empty state + deep-link
- `src/surfaces/swarm-map/SwarmMapLegend.tsx` — selected-node detail panel
- `src/surfaces/swarm-map/swarmMap.css` — token-only styling + A8 scaffold + swarm-paused
- `src/surfaces/swarm-map/__tests__/swarmMapDerive.test.ts` — no-fake-signal guard + node-type coverage
- `src/surfaces/swarm-map/__tests__/SwarmMap.test.tsx` — radial render smoke + empty state
- `src/portal/PortalShell.tsx` — mounts `<SwarmMap>`

## Decisions Made
- **Honest-signal enforcement at two layers:** the derive only constructs an edge with a real `source` AND only when both endpoints exist; the guard test pins it. Co-presence of two agents yields no edge.
- **Node identity model:** agents collapse to unique roles; cards are work nodes; prefixed id namespaces avoid collision and let the render strip `work:` for deep-links.
- **liveOverlay accepted but unused** in the static model (live wiring is V24-07); not destructured to keep `noUnusedParameters` clean.

## Deviations from Plan
Plan executed as written. Clarifications: agent nodes are per-unique-role (cleaner than per-node, satisfies "all node types present"); `liveOverlay` is carried in the signature but consumed in V24-07; the A8 keyframe is a no-op scaffold placeholder until V24-07 adds the real pulses.

## Issues Encountered
- **Branch detour (resolved):** at the start of this plan the working tree was on `fix/release-smoke-path`, which lacked V24-02…05 (those had been auto-committed onto `dev`, then the branch was switched away). With the user's confirmation I switched back to `dev` (foundation intact, suite green at 850) before building V24-06. All V24-06 work is on `dev`.

## Verification
- `npm test -- swarmMapDerive` → **6 passed** (incl. the no-fake-signal guard); `npm test -- SwarmMap` → **10 passed** (derive + render smoke).
- `npx tsc --noEmit` → **0 errors** (swarm-map/* + PortalShell clean); `PROXY_STRIP_OK` (proxy-strip present).
- `npm test` (full suite) → **860 passed | 5 skipped, 0 failed** (96 files; +10 from V24-05's 850).
- No raw hex in `src/surfaces/swarm-map/`; A8 double-guard + `.swarm-paused` present; key_links present (`deriveSwarmGraph` in SwarmMap, PortalShell mounts `<SwarmMap>`).

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- VADE2-06 acceptance met: empty/partial sources → honest placeholders/omission with zero source-less edges; full fixture renders objective/agent/work/artifact/alert in radial clusters.
- **V24-07 hook:** live edge updates (sseClient liveGraphPatch) feed the same `deriveSwarmGraph`/edge model; the A8 scaffold + `swarm-paused` hook are in place for the traveling-dot/pulse keyframes and the reduced-motion event-trace fallback + replay scrubber.

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*

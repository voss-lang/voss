---
phase: V24-ade-product-revamp-swarm-observability
plan: 07
subsystem: ui
tags: [solidjs, sse, live, animation, reduced-motion, replay, a11y, vitest, tdd]

# Dependency graph
requires:
  - phase: V24-06
    provides: deriveSwarmGraph + SwarmMap surface + swarmMap.css A8 scaffold
  - phase: V14/V15
    provides: sseClient (connectLiveStream/applyOverlay), replayReducer (computeBoardAtStep)
provides:
  - sseClient liveGraphPatches signal + GraphPatchEvent (source-tagged live edges, bounded ring)
  - SwarmMap live edge merge + destination ring-pulse + traveling dots (CSS @keyframes, A8 double-guarded)
  - EventTraceList reduced-motion fallback (same liveGraphPatches data, pinned under reduced motion)
  - ReplayScrubber (accessible range input driving computeBoardAtStep over proxy-stripped nodes; completed runs only)
affects: [V24-08 (validation/manual a11y + perf pass on the live + replay paths)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live honest-signal: every GraphPatchEvent carries source 'sse_event:<type>'; SwarmMap never renders a sourceless live edge"
    - "A8 double-guard: ALL animation: declarations inside one sentinel-delimited @media(not reduced-motion)+html:not(.reduced-motion) block; asserted by swarmA11y source test"
    - "Reduced-motion parity: motion conveys nothing the EventTraceList doesn't (same signal, display toggle)"
    - "Bounded patch ring (MAX_GRAPH_PATCHES) so a high-rate stream can't grow unboundedly (T-V24-07-D)"

key-files:
  created:
    - apps/voss-app/src/surfaces/swarm-map/EventTraceList.tsx
    - apps/voss-app/src/surfaces/swarm-map/ReplayScrubber.tsx
    - apps/voss-app/src/surfaces/swarm-map/__tests__/swarmLive.test.ts
    - apps/voss-app/src/surfaces/swarm-map/__tests__/swarmA11y.test.ts
    - apps/voss-app/src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx
  modified:
    - apps/voss-app/src/org/live/sseClient.ts
    - apps/voss-app/src/surfaces/swarm-map/SwarmMap.tsx
    - apps/voss-app/src/surfaces/swarm-map/swarmMap.css

key-decisions:
  - "GraphPatchEvent from/to carry the raw session/card id; SwarmMap maps to graph node ids at merge time (objective→work). Undrawable patches still surface in the EventTraceList (honest, never dropped)."
  - "applyOverlay returns early for permission.updated (no session key), so live patches are emitted by a separate emitGraphPatch(ev, cardId) in the stream loop — connectLiveStream signature unchanged (RESEARCH A4)."
  - "swarmA11y strips a sentinel-delimited guard block (} /* end-reduced-motion-guard */) so a multi-rule @media block is removed cleanly; animation-play-state (a pause hook) is intentionally allowed."
  - "ReplayScrubber play uses a setInterval step advance (replay control, not a connector animation — the CSS-@keyframes-only rule governs connectors); proxy-strip before computeBoardAtStep is mandatory."

patterns-established:
  - "Live edge merge keeps source; node pulse + traveling dot only in motion mode (reduced() guard) and only via guarded CSS classes"
  - "EventTraceList rows: [timestamp] [edge type] [source → destination], bounded recent slice"

requirements-completed: [VADE2-07]

# Metrics
duration: 22min
completed: 2026-06-15
---

# Phase V24-07: Live Swarm Map + Replay Summary

**The Swarm Map is now live and replayable — SSE events become source-tagged `liveGraphPatches` that merge as honest edges with a 300ms destination ring-pulse (CSS @keyframes, A8 double-guarded); under reduced motion the connectors go static and an equivalent Event Trace list pins open; completed runs scrub through `computeBoardAtStep` via an accessible range input.**

## Performance

- **Duration:** ~22 min (incl. a branch detour, below)
- **Tasks:** 2 (sseClient + tests; then connectors/keyframes/trace/scrubber)
- **Files created:** 5 — **modified:** 3

## Accomplishments
- `sseClient.ts`: `GraphPatchEvent` + module-level `liveGraphPatches` (bounded to 200) + `emitGraphPatch` in the stream loop — `permission.updated`→tool-call, `budget.updated`(crossed)→message, `gate.updated`(blocking)→blocker, each `source: "sse_event:<type>"`. `connectLiveStream` signature unchanged; `__resetLiveStream` clears the new signal.
- `SwarmMap.tsx`: subscribes to `liveGraphPatches()`, merges them as source-tagged `SwarmEdge`s (mapped to graph node ids), adds the `swarm-node-pulse` class to destination nodes and traveling dots on live edges (motion mode only), keeps the `swarm-paused` visibility hook, mounts `EventTraceList` (right column) and `ReplayScrubber` (bottom strip, completed runs only). Reduced motion detected via `html.reduced-motion` + `matchMedia`.
- `swarmMap.css`: real `travelEdge`/`nodePulse`/`blockerPulse` keyframes — every `animation:` inside ONE sentinel-delimited A8 double-guard block.
- `EventTraceList.tsx`: `liveGraphPatches`-driven `[timestamp] [edge type] [source → destination]` rows (mono, bounded), collapsed in motion / pinned-open under reduced motion.
- `ReplayScrubber.tsx`: proxy-stripped `computeBoardAtStep`, accessible `<input type="range" aria-label="Replay timeline" aria-valuenow/min/max>` + play/pause button with state-dependent aria-label.

## Task Commits

Not committed by me (git-safety policy). Built on `dev`; the session's auto-commit process commits my edits there.

1. **Task 1: sseClient liveGraphPatches + swarmLive + swarmA11y tests** — sseClient.ts, swarmLive.test.ts, swarmA11y.test.ts
2. **Task 2: live connectors + keyframes + trace + scrubber** — SwarmMap.tsx, swarmMap.css, EventTraceList.tsx, ReplayScrubber.tsx, ReplayScrubber.test.tsx

## Files Created/Modified
- `src/org/live/sseClient.ts` — liveGraphPatches signal + GraphPatchEvent + emitGraphPatch (source-tagged, bounded)
- `src/surfaces/swarm-map/SwarmMap.tsx` — live edge merge + pulse + traveling dots + trace + scrubber + reduced-motion
- `src/surfaces/swarm-map/swarmMap.css` — guarded travelEdge/nodePulse/blockerPulse + trace/scrubber styles
- `src/surfaces/swarm-map/EventTraceList.tsx` — reduced-motion fallback trace list
- `src/surfaces/swarm-map/ReplayScrubber.tsx` — accessible replay scrubber over computeBoardAtStep
- `src/surfaces/swarm-map/__tests__/swarmLive.test.ts` — live source-tag honest-signal guard
- `src/surfaces/swarm-map/__tests__/swarmA11y.test.ts` — no animation: outside the reduced-motion guard
- `src/surfaces/swarm-map/__tests__/ReplayScrubber.test.tsx` — range drives step/frame; state-dependent aria

## Decisions Made
- **Live honesty preserved:** every patch carries a real `sse_event:*` source; SwarmMap merges (never synthesizes) and drops nothing — undrawable patches still appear in the trace.
- **Separate emit path:** `applyOverlay` early-returns for permission.updated (no session), so `emitGraphPatch` runs alongside it in the loop rather than refactoring the overlay routing.
- **Sentinel-delimited guard** makes the multi-rule `@media` block strippable by the swarmA11y source test; `animation-play-state` (pause hook) is allowed by design.

## Deviations from Plan
Plan executed as written. Notes: `GraphPatchEvent.from/to` carry raw ids (mapped to graph ids at render, since sseClient is graph-agnostic); the ReplayScrubber play loop uses `setInterval` (replay control — the CSS-@keyframes-only rule governs connector animation, not replay stepping).

## Issues Encountered
- **Branch detour (recurring):** the working tree was switched `dev → fix/release-smoke-path` again by the release automation while V24-06/07-Task-1 auto-committed onto `dev`. With the user's go-ahead I switched back to `dev` (foundation + Task-1 intact, swarmLive GREEN) and finished Task 2 there. The release automation may re-switch the shared tree; all V24 work remains safe on `dev`.
- Two self-trips on source-assertion comments (the swarmA11y guard test matched the literal `animation:` inside a doc comment) — reworded the comment; no behavior change.

## Verification
- `npm test -- swarmLive` → 2 passed; `npm test -- swarmA11y` → 2 passed; `npm test -- ReplayScrubber` → 3 passed.
- `npm test -- swarm` (all swarm files incl. V24-06 smoke) → **25 passed (7 files)**.
- `npx tsc --noEmit` → **0 errors** (swarm-map/* + sseClient clean).
- `npm test` (full suite) → **867 passed | 5 skipped, 0 failed** (99 files; +7 from V24-06's 860).
- No raw hex in `src/surfaces/swarm-map/`; key_links present (`liveGraphPatches` in SwarmMap + EventTraceList, `computeBoardAtStep` in ReplayScrubber).

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- VADE2-07 acceptance met: live edges update source-tagged; reduced motion → static connectors + equivalent trace; completed runs replay-scrubbable with the graph state reflecting the scrub position.
- **V24-08 hook:** validation / manual a11y + perf pass on the live animation and replay paths in a real Tauri webview (deferred per plan verification note).

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*

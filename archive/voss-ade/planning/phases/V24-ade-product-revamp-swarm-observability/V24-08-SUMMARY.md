---
phase: V24-ade-product-revamp-swarm-observability
plan: 08
subsystem: validation
tags: [a11y, vitest, reduced-motion, terminal-first, manual-checklist, phase-gate]

# Dependency graph
requires:
  - phase: V24-04
    provides: VossComposer dialog (aria-modal/aria-label/Safety mode)
  - phase: V24-05
    provides: TasksSurface rows (<button aria-label="Open Task: …">)
  - phase: V24-02
    provides: PortalRail tablist/tab roles
  - phase: V24-06/07
    provides: swarmMap.css reduced-motion guard
provides:
  - portalA11y.test.tsx (cross-surface a11y phase gate: tablist + dialog + button rows + reduced-motion source assertion)
  - V24-TERMINAL-FIRST-CHECKLIST.md (manual L1 gate + visual no-raw-labels review + Tauri pan/zoom/reduced-motion/replay smoke)
  - full-suite green confirmation (871 passed) — V24 phase validation gate
affects: [/gsd-verify-work (this is the gate before it)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase-gate a11y test: one file re-asserts the cross-surface contract authored across V24-02..07 (tablist roles, dialog aria-modal, keyboard-operable button rows, reduced-motion CSS source assertion)"
    - "Reduced-motion source assertion strips the sentinel-delimited guard block, then asserts no bare `animation:` outside it (allows `animation-play-state` pause hook) — complementary re-check of swarmA11y"
    - "Manual L1 gate as a committed, checkbox-driven markdown artifact (user's chosen named gate over automated regression)"

key-files:
  created:
    - apps/voss-app/src/__tests__/portalA11y.test.tsx
    - apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md
  modified: []

key-decisions:
  - "TasksSurface assertion seeds orgStore (setRunData(makeRun())) and asserts on TasksSurface rather than TaskRow in isolation — proves the real mission-control deep-link button renders, not just the row component."
  - "Reduced-motion re-asserted from swarmMap.css source here as a phase gate (in addition to swarmA11y) so the contract is checked once more at the single pre-verify gate."
  - "Task 3 (operator runs the live Tauri checklist) is a blocking human checkpoint — left for operator sign-off (autonomous: false). Mirrors the V9 human-verify deferral precedent; not self-completable."

patterns-established:
  - "A single cross-surface a11y gate test before /gsd-verify-work, separate from per-feature a11y tests"

requirements-completed: [VADE2-08 (automated portion; manual checklist pending operator sign-off)]

# Metrics
duration: 14min
completed: 2026-06-15
---

# Phase V24-08: Final Validation Pass Summary

**The V24 revamp is proven, not assumed: a cross-surface a11y phase-gate test (portal tablist roles, composer dialog aria-modal+label, keyboard-operable Tasks button rows, reduced-motion CSS source assertion) passes, the full vitest suite is green (871 passed | 5 skipped) with all 10 V24 modules and the existing grid/pane/terminal baseline intact, and a committed manual `V24-TERMINAL-FIRST-CHECKLIST.md` documents the L1 terminal-first gate + visual no-raw-labels review + Tauri pan/zoom/reduced-motion/replay smoke for operator sign-off.**

## Performance
- **Duration:** ~14 min
- **Tasks:** 2 auto (complete) + 1 blocking human checkpoint (pending operator)
- **Files created:** 2 — **modified:** 0

## Accomplishments
- `portalA11y.test.tsx` — 4 assertions, all GREEN:
  - PortalRail renders `role="tablist"` with `PORTAL_ITEMS.length` `role="tab"` items, each carrying `aria-selected` (true|false) + `aria-label`; exactly one selected, matching the active view's label.
  - VossComposer (open) renders `<dialog aria-modal="true">` with a non-empty `aria-label` and a `<select aria-label="Safety mode">`.
  - TasksSurface (orgStore-seeded) renders `<button class="surface-row" aria-label="Open Task: …">` rows — asserts `<button>`, not `<a>` (keyboard-operable deep link, no href nav in a webview).
  - swarmMap.css reduced-motion source assertion: strips the `@media (not (prefers-reduced-motion: reduce))` … `} /* end-reduced-motion-guard */` block, then asserts no bare `animation:` survives outside it (the `animation-play-state` pause hook is intentionally allowed).
- `V24-TERMINAL-FIRST-CHECKLIST.md` — three checkbox sections + operator sign-off:
  1. Terminal-First (L1): boot-to-grid, open terminal, split ⌘D/⌘⇧D, focus, run arbitrary command, launch custom CLI agent, project-less, persist-across-reload — header states all must pass **without Voss credentials**.
  2. Vocabulary / no-raw-labels visual review: enumerates absent raw labels (no fanout/pipeline/swarm/watchers nav, no Plan/Edit/Auto, no raw runId/RunData) + present locked vocab (Tasks, Swarm Map, Read only/Can edit/Autopilot, Ask Voss to…, Create Task, steps/cards) + both hard-fail product-failure conditions.
  3. Swarm Map Tauri smoke: pan/zoom (no native-scroll conflict), reduced-motion → animations cease + Event Trace shown, replay scrub tracks the graph.

## Files Created/Modified
- `src/__tests__/portalA11y.test.tsx` — cross-surface a11y phase gate (4 tests)
- `V24-TERMINAL-FIRST-CHECKLIST.md` — manual L1 + visual + Tauri smoke checklist

## Decisions Made
- Seeded orgStore and asserted on the real `TasksSurface` (not `TaskRow` in isolation) so the gate proves the mounted mission-control deep-link button.
- Re-asserted the reduced-motion contract from CSS source at this single pre-verify gate, complementary to swarmA11y.
- Task 3 left for operator (blocking human checkpoint, `autonomous: false`) — not self-completable; mirrors the V9 human-verify precedent.

## Deviations from Plan
None. Plan Tasks 1 and 2 executed as written; Task 3 is the documented human checkpoint.

## Verification
- `npm test -- portalA11y` → **4 passed**.
- `npm test` (full suite) → **871 passed | 5 skipped, 0 failed** (100 files passed | 1 skipped).
- 10 V24 modules confirmed green together (`swarmPortal TopChrome VossComposer TasksSurface portalDeepLink swarmMapDerive SwarmMap swarmLive swarmA11y ReplayScrubber`) → **42 passed (10 files)**.
- `npx tsc --noEmit` → **0 errors**.
- `git diff --stat -- apps/voss-app/package.json apps/voss-app/package-lock.json` → empty (zero supply-chain surface; no new deps across V24, threat T-V24-08-SC satisfied).
- Checklist grep gate → `CHECKLIST_OK` (`without Voss` + `reduced motion` + `Swarm Map` + `terminal-first` all present).

## User Setup Required
**Operator action — Task 3 (blocking human checkpoint):**
1. Build/run the Tauri app: `cd apps/voss-app && npm run tauri dev`.
2. Open `apps/voss-app/V24-TERMINAL-FIRST-CHECKLIST.md` and work through all three sections.
3. Tick each box, add the sign-off line, and reply **"approved"** (or describe failing steps).

## Next Phase Readiness
- VADE2-08 automated portion met (a11y gate + full-suite green + reduced-motion + no new deps). The manual L1 checklist is the only remaining item before `/gsd-verify-work`.
- After operator sign-off, V24 (ADE product revamp + swarm observability) is fully validated and ready for `/gsd-verify-work`.

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15 (automated tasks); Task 3 pending operator sign-off*

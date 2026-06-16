---
phase: V24-ade-product-revamp-swarm-observability
plan: 02
subsystem: ui
tags: [solidjs, portal, canvas-swap, navigation, tauri, vitest]

# Dependency graph
requires:
  - phase: V24-01
    provides: PRODUCT.md locked vocabulary + 8-item IA (portal labels)
  - phase: V14
    provides: OrgViewShell (Review surface), selection.ts deep-link signals, canvas-swap display:none contract
provides:
  - "PortalView contract (portalTypes.ts) — Wave-0 interface for V24-03/05/06"
  - "Left portal rail (PortalRail) + canvas-swap host (PortalShell)"
  - "App.tsx activeView:PortalView signal replacing the binary orgViewOpen toggle"
  - "swarmPortal.test.tsx — canvas-swap round-trip + pane-identity guard"
affects: [V24-03, V24-04, V24-05, V24-06, V24-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Canvas-swap: grid div display:none keepalive (never <Show>); portal surface position:absolute over it"
    - "Controlled nav: activeView signal owned by App.tsx; PortalRail/PortalShell receive activeView+onNavTo as props (Pitfall 5)"
    - "Lazy reviewSlot thunk so OrgViewShell mounts only when activeView==='review'"

key-files:
  created:
    - apps/voss-app/src/portal/portalTypes.ts
    - apps/voss-app/src/portal/PortalRail.tsx
    - apps/voss-app/src/portal/PortalShell.tsx
    - apps/voss-app/src/portal/portal.css
    - apps/voss-app/src/__tests__/swarmPortal.test.tsx
  modified:
    - apps/voss-app/src/App.tsx

key-decisions:
  - "PortalRail mounts as a new 48px leftmost rail alongside the existing AgentSidebar (sidebar folds into the Agents surface in a later plan; not removed this phase)"
  - "context/memory/settings render labeled placeholders this plan — no standalone shell component exists to mount as-is; Review wires to OrgViewShell. New surfaces (overview/tasks/agents/swarm-map) are placeholders filled by V24-05/06"
  - "Cmd+Shift+O and Titlebar/StatusBar boolean orgViewOpen props map to grid↔review (legacy 'open org view' = Review surface)"

patterns-established:
  - "PortalView union + PORTAL_ITEMS as the single nav contract cited by downstream surfaces"
  - "Wave-0 canvas-swap test replicates the App-local closure (liveReviewToggle convention) rather than mounting App"

requirements-completed: [VADE2-02]

# Metrics
duration: 38 min
completed: 2026-06-15
---

# Phase V24 Plan 02: Left Portal Shell + Canvas-Swap Summary

**8-way `activeView: PortalView` portal navigation replaces the binary `orgViewOpen` toggle; the terminal grid stays mounted behind a `display:none` keepalive (PTY sessions survive a portal round-trip), fresh workspaces boot to the grid, and deep links return to the grid.**

## Performance

- **Duration:** ~38 min (incl. recovery from a concurrent-process revert)
- **Tasks:** 2 (both TDD)
- **Files created:** 5 · **modified:** 1
- **Verification:** tsc 0 errors · `swarmPortal` 4/4 · `App.test` green · full suite 90 files / 829 passed, 5 skipped · `portal.css` token-only (no raw hex)

## Accomplishments

- **PortalView contract (`portalTypes.ts`):** 9-member union (incl. `'grid'`) + `PORTAL_ITEMS` (8 navigable entries, no `'grid'`) in UI-SPEC order, labels byte-matching PRODUCT.md vocabulary ("Tasks" not "Runs", "Swarm Map").
- **`PortalRail`:** 48px `<nav>` with `role="tablist"` / `aria-orientation="vertical"`, 8 `role="tab"` buttons (`aria-selected` reflects activeView) + an "Ask Voss to…" trigger (composer lands V24-04). Controlled — receives `activeView`/`onNavTo` as props (Pitfall 5).
- **`PortalShell`:** canvas-swap host. Renders ONLY the portal surface (`position:absolute; inset:0; z-index:10`) gated by `<Show when={activeView!=='grid'}>`. Does NOT render GridRoot. Review → lazy `reviewSlot()` thunk mounting the existing `OrgViewShell`; new surfaces + context/memory/settings → labeled placeholders.
- **`App.tsx`:** `orgViewOpen` boolean → `activeView: PortalView` signal (default `'grid'` → D-02 fresh-boot-to-grid). Grid container uses `display: activeView()==='grid' ? 'flex' : 'none'` (NOT `<Show>` — Pitfall 1). All 8 former call sites converted; `⌘⌥1`–`⌘⌥8` jump to the 8 portal surfaces without clobbering `⌘1`–`⌘9` pane focus.
- **`swarmPortal.test.tsx`:** PortalView contract test (8 items, order, vocabulary) + canvas-swap round-trip (same grid host element ref, display flips flex→none→flex) + pane-session identity survives a round-trip via the real `paneSessionRegistry`.

## Task Commits

1. **Task 1: PortalView contract + canvas-swap round-trip test (Wave 0)** — pending operator/auto-commit.
2. **Task 2: PortalRail + PortalShell + App.tsx activeView wiring** — pending operator/auto-commit.

_Git commits deferred to operator per project policy (executor does not run git add/commit)._

## Files Created/Modified

- `src/portal/portalTypes.ts` — PortalView union + PORTAL_ITEMS nav contract.
- `src/portal/PortalRail.tsx` — 48px left nav rail (tablist).
- `src/portal/PortalShell.tsx` — canvas-swap portal-surface host + Switch.
- `src/portal/portal.css` — rail + surface styles, token-only.
- `src/__tests__/swarmPortal.test.tsx` — VADE2-02 canvas-swap + pane-identity guard.
- `src/App.tsx` — activeView signal, PortalRail + PortalShell mounted, 8 call sites converted, ⌘⌥1-8 shortcuts.

## Decisions Made

- **PortalRail coexists with AgentSidebar** this phase (rail is leftmost; sidebar untouched). Folding the agent roster into the Agents surface is V24-05 scope, not W1.
- **context/memory/settings = labeled placeholders** this plan. The SPEC marks them "wire to existing as-is," but no standalone surface component exists to mount (ContextPanel is a grid overlay, not a portal surface; no Memory/Settings shell). Review wires to the real `OrgViewShell`. Wiring the other three is deferred to a later plan; flagged below.
- **Legacy "open org view" maps to the Review surface** (Cmd+Shift+O toggle, Titlebar/StatusBar boolean props, BoardSummaryStrip) — preserves existing affordances against the new signal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Re-applied render-tree edits clobbered by a concurrent process**
- **Found during:** Task 2 (post-implementation, user-reported `cannot find name 'orgViewOpen'`)
- **Issue:** After the full suite passed green, a concurrent auto-commit/watcher process (see project memory: voss-app concurrent auto-commit) reverted the App.tsx JSX render-tree edits while KEEPING the signal rename + imports — leaving 6 dangling `orgViewOpen`/`setOrgViewOpen` references (TS2304) and 2 unused-import errors (TS6133). App.test.tsx went red (7 failed); the suite was momentarily broken.
- **Fix:** Re-applied the 5 reverted edits — grid container display toggle, BoardSummaryStrip onOpen, the PortalShell-for-OrgViewShell block, StatusBar props, and the PortalRail mount.
- **Files modified:** src/App.tsx
- **Verification:** tsc 0 errors; App.test + swarmPortal 19/19; full suite 829 passed.

---

**Total deviations:** 1 auto-fixed (1 blocking — external revert recovery). **Impact:** No scope change; the recovery restored the intended diff exactly. Plan executed as written.

## Issues Encountered

- **Concurrent-process revert hazard is ACTIVE.** A background process reverted this file's edits once mid-execution. The working tree is correct now (tsc 0, suite green) but **uncommitted** — commit promptly to lock it in before the watcher can revert again. The executor cannot commit (git policy).
- **Test-adequacy gap (reviewer-confirmed):** `swarmPortal.test.tsx` uses a local harness (codebase convention from `liveReviewToggle.test.tsx`) and does NOT mount the real App, so it cannot by itself catch an App.tsx wiring regression. The revert above slipped past it silently. **`App.test.tsx` is the real App-wiring regression gate** — it went red during the revert and green after the fix. Keep both in the per-wave gate; a tsc gate is the fastest detector.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- VADE2-02 met: 8-item portal, canvas-swap (grid stays mounted, pane identity survives), fresh-boot-to-grid, deep-link-returns-to-grid.
- **V24-03 (quiet chrome)** and **V24-05 (mission control)** can cite the `PortalView`/`PORTAL_ITEMS` contract and the PortalShell surface seam.
- **Carry-forward:** wire context/memory/settings portal surfaces to their existing UIs (placeholders this plan); fill overview/tasks/agents/swarm-map (V24-05/06). The "Ask Voss to…" rail trigger needs `onOpenComposer` once V24-04 lands.
- **Operator action:** commit the working tree now (concurrent-revert hazard).

---
*Phase: V24-ade-product-revamp-swarm-observability*
*Completed: 2026-06-15*

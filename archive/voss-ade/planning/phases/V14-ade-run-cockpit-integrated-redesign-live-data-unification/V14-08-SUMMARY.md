---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 08
subsystem: ui
tags: [solid-js, tauri, pty, bridge-b, toggle, vitest]

# Dependency graph
requires:
  - phase: V14-03
    provides: CockpitShell / CardDrawer + global selection (selectedCardId/selectedRunId)
  - phase: V14-04
    provides: bridge keystone (registerTerminalCard / paneIdForCard)
provides:
  - Completed handleLaunchAgent — real agent spawn via Bridge B (cardId carried as spawn_agent sessionId)
  - Live<->Review toggle confirmed over the orgViewOpen display:none swap (grid never unmounted)
  - D-07 Open-in-grid: global requestOpenInGrid action -> App effect flips orgViewOpen + focuses bound pane
  - liveReviewToggle.test.tsx (6 cases): selection persistence, grid-stays-mounted, open-in-grid, spawn ordering + GRD-05 guard
affects: [RunCommandBar native/terminal start, future OrgViewShell->CockpitShell swap]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bridge B at launch: split -> snapshot().focusedId -> registerTerminalCard -> seed agentConfigByPaneId, fully synchronous (no await) so PaneComponent.doSpawn reads the config before its deferred onMount fires — no plain-shell race"
    - "GRD-05 split-rejection guard: compare focusedId before/after splitFocused; abort agent wiring if unchanged"
    - "Global one-shot action signal (openInGridRequest) consumed+cleared in an App createEffect (opt-in jump-to-grid)"

key-files:
  created:
    - apps/voss-app/src/__tests__/liveReviewToggle.test.tsx
  modified:
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/org/selection.ts
    - apps/voss-app/src/org/cockpit/CardDrawer.tsx

key-decisions:
  - "Operator chose FULL spawn now (deep-research ordering) over a deferred stub — handleLaunchAgent actually spawns"
  - "Operator chose D-07 via a global selection.ts action + CardDrawer onClick + App effect (crosses files_modified — approved deviation)"
  - "snapshot().focusedId (synchronous) is the new-pane-id source, NOT focusedPaneId() (deferred effect, stale in-handler)"

patterns-established:
  - "Synchronous launch handler: never await between split and config-set or the effect queue flushes mid-handler and re-introduces the race"
  - "CardDrawer reaches App via a global action signal, not a threaded prop (it mounts deep in the shell)"

requirements-completed: [VCKP-08]

# Metrics
duration: 20min
completed: 2026-06-09
---

# Phase V14-08: Live↔Review Toggle + Launch Spawn Wiring Summary

**handleLaunchAgent now performs a real Bridge-B agent spawn (cardId carried as `spawn_agent` sessionId) with a proven race-free synchronous ordering + GRD-05 guard; Live↔Review rides the existing `orgViewOpen` display:none swap with persistent selection and zero grid unmount; D-07 Open-in-grid is opt-in via a global action.**

## Performance

- **Duration:** ~20 min (workflow: 4 agents — research/implement/test/verify — 20.5 min wall, 270k subagent tokens)
- **Completed:** 2026-06-09
- **Tasks:** 2 (+ deliberate research phase)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- **Task 1 — real spawn (Bridge B):** `handleLaunchAgent` rewritten fully synchronous: guard `activeMounted()`/`gridController`, capture `before=snapshot().focusedId`, `splitFocused('H')`, `newId=snapshot().focusedId`, GRD-05 abort if `newId===before`, `registerTerminalCard(newId)` → cardId, seed `ws.setAgentConfigByPaneId({...,[newId]:{cliBinary,cliArgs,sessionId:cardId}})`. PaneComponent's deferred `onMount→doSpawn` then reads `props.agentConfig` and takes the `spawnAgent` branch — **no plain-shell race** (proven from Solid 1.9.13 mount semantics + the `await loadAppearanceSettings()` second deferral).
- **Live↔Review:** confirmed the toggle is the existing `orgViewOpen` swap (`display: orgViewOpen() ? 'none' : 'flex'`, App.tsx:1234) — grid stays mounted, `selectedCardId/selectedRunId` are global so they persist automatically. ⌘⇧O (App.tsx:1060) unchanged.
- **Task 2 — D-07 Open-in-grid:** `selection.ts` exports `openInGridRequest` + `requestOpenInGrid(paneId)`; CardDrawer's "Open in grid" button got an `onClick` calling it (kept `disabled={!boundPaneId()}`); App `createEffect` (App.tsx:317-323) flips `setOrgViewOpen(false)`, `focusPaneById(paneId)`, clears the request. Opt-in, never automatic.
- **Test:** `liveReviewToggle.test.tsx` — 6 cases, all green.
- **Verification:** adversarial agent pass, 7/7 checks, 0 blocking issues.

## Task Commits

1. **Tasks 1+2 (spawn wiring + toggle persistence + D-07 + test)** — `22d40f6` (feat)

_Single coherent commit covering all 4 files (App.tsx, selection.ts, CardDrawer.tsx, liveReviewToggle.test.tsx)._

## Files Created/Modified
- `apps/voss-app/src/App.tsx` — race-free `handleLaunchAgent` spawn (Bridge B + GRD-05 guard); D-07 Open-in-grid host `createEffect`; imports `registerTerminalCard`, `openInGridRequest/setOpenInGridRequest`, `createEffect`.
- `apps/voss-app/src/org/selection.ts` — `openInGridRequest` signal + `requestOpenInGrid` action (global one-shot).
- `apps/voss-app/src/org/cockpit/CardDrawer.tsx` — wired the "Open in grid" button `onClick → requestOpenInGrid`; removed stale "lands in plan 08" comment.
- `apps/voss-app/src/__tests__/liveReviewToggle.test.tsx` — 6-case VCKP-08 suite.

## Decisions Made
- **Full spawn vs. deferred stub (operator):** implemented the real spawn. Required a dedicated research phase to prove the config-vs-mount ordering is race-free; the proof hinges on Solid deferring the new pane's `onMount` past the synchronous handler — so the handler must stay `await`-free between split and config-set.
- **New-pane id source:** `gridController().snapshot().focusedId` (synchronous, authoritative), NOT `focusedPaneId()` (updated by a deferred effect, stale within the handler).
- **GRD-05 guard added** (beyond the plan): `insertSibling` silently no-ops on a min-size violation, leaving `focusedId` unchanged — without the before/after guard, a rejected split would overwrite the existing focused pane's config. Guard aborts agent wiring in that case.

## Deviations from Plan

### Approved scope expansion (operator-confirmed before execution)

**1. D-07 wiring touches files beyond `files_modified` (App.tsx + test)**
- **Found during:** scouting (pre-dispatch).
- **Issue:** the D-07 "Open in grid" button lives in `CardDrawer.tsx` (not in `files_modified`) with **no onClick**, and App mounts `OrgViewShell` not `CockpitShell`, so the button never renders in the running app. The plan's action text ("wire the CardDrawer button") could not be satisfied from App.tsx alone.
- **Fix:** added a global one-shot action to `selection.ts` (`requestOpenInGrid`/`openInGridRequest`) + a CardDrawer `onClick` + an App `createEffect` host. CardDrawer reaches App via the global signal rather than a prop threaded through the un-mounted shell.
- **Files beyond plan scope:** `apps/voss-app/src/org/selection.ts`, `apps/voss-app/src/org/cockpit/CardDrawer.tsx`.
- **Verification:** test case 3a renders the real CardDrawer and clicks the button → asserts it publishes the paneId; 3b asserts the App effect flips `orgViewOpen` + calls `focusPaneById` + clears the request.
- **Committed in:** `22d40f6`.

**2. GRD-05 split-rejection guard added** (correctness, not in plan text) — see Decisions. Committed in `22d40f6`.

---

**Total deviations:** 2 (1 approved scope expansion, 1 correctness guard). **Impact:** necessary; no scope creep beyond the operator-approved D-07 path. PaneComponent untouched (`paneComponentChangeNeeded=false`).

## Issues Encountered
- **Test harness limitation (non-blocking):** `App.test.tsx` mocks `GridRoot` entirely (its `splitFocused` is a `vi.fn()`, no `focusPaneById`, no real `PaneComponent`), so a full App render **cannot observe** `spawn_agent`/pane-id minting. `liveReviewToggle.test.tsx` therefore follows the `runCommandBar.test.tsx` pattern: it drives the genuinely-global state (`selection.ts`, `bridge.ts`) and replicates each App-local closure (the ⌘⇧O toggle, the display:none swap, the D-07 effect, and handleLaunchAgent's ordering) at the GridController seam, rather than invoking the un-exported App handler directly. The real handler + full Bridge-B chain (App.tsx → SplitNode:154 → PaneComponent:231/238 → pty-ipc:181) were verified by reading the code. Persistence/ordering guarantees are meaningfully asserted; coverage is structural-replication, not direct App-handler coverage. A future export/refactor of `handleLaunchAgent` would allow direct coverage.

## Verification
- `npx tsc --noEmit` — clean (App.tsx/selection/CardDrawer/PaneComponent/liveReviewToggle).
- `npx vitest run src/__tests__ src/org` — **110 passed (19 files)**.
- Swap line intact (App.tsx:1234); ⌘⇧O intact (App.tsx:1060); GridRoot never conditionally unmounted.
- Adversarial verify — pass, 7/7 checks, 0 blocking issues.

## Next Phase Readiness
- Launch path now binds the keystone at spawn (Bridge B) — RunCommandBar terminal-start can reuse the same `handleLaunchAgent` ordering.
- D-07 lights up end-to-end once a later plan swaps App's `OrgViewShell` → `CockpitShell` (the global action + effect are already in place).
- No blockers.

---
*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Completed: 2026-06-09*

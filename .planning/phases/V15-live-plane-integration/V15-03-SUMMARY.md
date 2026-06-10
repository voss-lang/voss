---
phase: V15-live-plane-integration
plan: 03
subsystem: ui
tags: [solid-js, sse, protocol, xterm, vitest, ui-spec]

# Dependency graph
requires:
  - phase: V15-02
    provides: connectLiveStream onEvent per-pane sink + cardId context; App-level ensureVossClient + native createSession path
provides:
  - ProtocolPane structured pane (8 dedicated §6 rows + generic fallback, D-07 collapse, D-08 cap+pins, D-09 stream coalesce + sticky-bottom)
  - ProtocolPane.css — full UI-SPEC §1-2 classes + Plan-04/05 shells (.proto-permission-gate buttons, .proto-boot, .proto-spawn-error, .proto-ended-row, .statusbar-live-indicator)
  - PaneComponent native branch (nativeSessionId discriminator; PTY path untouched)
  - nativeSessionByPaneId threading App→GridRoot→SplitNode + openAttachedPane exported attach seam
  - ExitBanner message?/showRestart? prop hole (D-11)
affects: [V15-04 permission gate, V15-05 attach, V15-06 lifecycle, V15-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [local per-pane transcript signals (never module-level), derived row-coalescing memo for stream blocks, pinned trim-oldest cap, module-level seam fn registered by mounted App]

key-files:
  created:
    - apps/voss-app/src/pane/ProtocolPane.tsx
    - apps/voss-app/src/pane/ProtocolPane.css
    - apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx
  modified:
    - apps/voss-app/src/pane/PaneComponent.tsx
    - apps/voss-app/src/pane/ExitBanner.tsx
    - apps/voss-app/src/grid/GridRoot.tsx
    - apps/voss-app/src/grid/SplitNode.tsx
    - apps/voss-app/src/App.tsx

key-decisions:
  - "plan row renders steps[] as numbered prose lines — §6 plan is {steps,confidence}, not {text} (plan interfaces block was wrong)"
  - "NativeSessionRecord type lives in SplitNode.tsx (props owner); GridRoot/App import it"
  - "openAttachedPane = module-level fn + impl registered by the mounted App (mirrors no existing export-from-component path)"
  - "PaneComponent onMount ALSO early-returns for native panes (not just doSpawn) — bodyRef does not exist when the Show swaps the body, term.open would crash"

patterns-established:
  - "Structured pane: connectLiveStream({...,onEvent: appendEvent}) + local signals + derived rows memo"
  - "D-08 trimOldest: pure, pins index-0 user + permission.updated"

requirements-completed: [VLIVE-04]

# Metrics
duration: 13min
completed: 2026-06-10
---

# Phase V15 Plan 03: Structured Protocol Pane Summary

**ProtocolPane renders the full §6 union as DOM (8 dedicated rows + generic fallback, nothing dropped) with D-07 collapsed tool lines, D-08 capped/pinned transcript, D-09 coalesced stream blocks — and native RunCommandBar runs now auto-open one in the Live Work grid while PTY panes stay byte-untouched**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-10T15:33:42Z
- **Completed:** 2026-06-10T15:47:00Z
- **Tasks:** 2 (Task 1 TDD red-green)
- **Files modified:** 8

## Accomplishments
- `ProtocolPane.tsx`: local per-pane signals (Pitfall 4), `connectLiveStream` onEvent feed, derived rows memo coalescing consecutive `stream.delta` into one growing block with pulse cursor (settles on finalize), sticky-bottom autoscroll with 20px user-scroll detection, D-08 `trimOldest` (CAP=300) pinning the task header + permission rows, permission.updated pinned placeholder gate (Plan 04 wires buttons), generic fallback with amber/prefix/probability% overrides — all text via Solid text bindings (T-V15-05; innerHTML grep = 0)
- `ProtocolPane.css`: every UI-SPEC §1-2 class (token vars only, Variant B radius 0) plus the §3-§8 shells (gate buttons, boot, spawn-error, ended-row, statusbar live indicator) and `proto-pulse`/`proto-cursor-blink` keyframes (no per-rule !important)
- `PaneComponent`: `nativeSessionId` discriminator — onMount + doSpawn early-return (no xterm/PTY), body `Show` swap to ProtocolPane; PTY path untouched (suite 27/27 unmodified, T-V15-06)
- Threading: `nativeSessionByPaneId` map App MountedWorkspace → GridRoot → SplitNode (both recursive arms) → PaneComponent leaf props
- `openNativePane`: D-02 split + map bind + Run Review→Live Work flip; native createSession now auto-opens the pane (D-01/D-03); exported `openAttachedPane` seam for Plans 04/05
- ExitBanner gained optional `message`/`showRestart` (defaults = current behavior)

## Task Commits

1. **Task 1 RED: failing ProtocolPane tests** - `d40292a` (test)
2. **Task 1 GREEN: ProtocolPane + CSS** - `30af2af` (feat) + `7b05283` (grep-gate comment fix)
3. **Task 2: PaneComponent branch + threading** - `c46d1f4` (feat)

## Files Created/Modified
- `apps/voss-app/src/pane/ProtocolPane.tsx` - structured transcript component
- `apps/voss-app/src/pane/ProtocolPane.css` - UI-SPEC §1-2 + Plan-04/05 shells
- `apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx` - 10 tests: every dedicated row, collapse/expand, generic fallback, no-drop count, permission placeholder, D-08 flood
- `apps/voss-app/src/pane/PaneComponent.tsx` - native branch (props/onMount/doSpawn/body Show)
- `apps/voss-app/src/pane/ExitBanner.tsx` - message?/showRestart? prop hole
- `apps/voss-app/src/grid/GridRoot.tsx` / `SplitNode.tsx` - nativeSessionByPaneId forward + NativeSessionRecord
- `apps/voss-app/src/App.tsx` - MountedWorkspace map, openNativePane/openAttachedPane, native-start auto-open, GridRoot prop

## Decisions Made
- §6 `plan` schema is `{steps[], confidence}` (events.schema.json) — rendered step names as numbered prose lines; the plan's interfaces block claimed `{text}` (incorrect)
- onMount early-return added alongside doSpawn's (plan named only doSpawn): with the body swapped, `bodyRef` is undefined and `term.open(bodyRef)` would crash

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] onMount would crash for native panes**
- **Found during:** Task 2
- **Issue:** plan's early-return was specified only in `doSpawn`, but `onMount` runs `term.open(bodyRef)` first — bodyRef does not exist when the Show renders ProtocolPane
- **Fix:** same guard at the top of onMount (skip terminal/transport setup entirely)
- **Files modified:** PaneComponent.tsx
- **Verification:** ProtocolPane renders under the pane suite; full pane suite green
- **Committed in:** c46d1f4

**2. [Rule 1 - Bug] plan-row field shape**
- **Found during:** Task 1
- **Issue:** interfaces block said `plan = {text, confidence?}`; the authoritative schema has `{steps: [{name,args}], confidence}`
- **Fix:** render steps as numbered prose lines, falling back to `text` if a future member carries it
- **Files modified:** ProtocolPane.tsx, ProtocolPane.test.tsx
- **Verification:** plan-row test passes against the schema shape
- **Committed in:** 30af2af

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both required for correctness; no scope creep.

## Issues Encountered
- One transient vitest parse failure caused by the concurrent file-watcher reformatting the test file mid-transform (re-run passed unchanged; bisect confirmed no content issue).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 04 (inline permission gate + lifecycle): gate CSS shells + pinned placeholder row + ExitBanner prop hole ready
- Plan 05 (attach): `openAttachedPane(record)` exported seam ready
- Full suite 796/796, tsc clean

---
*Phase: V15-live-plane-integration*
*Completed: 2026-06-10*

---
phase: V15-live-plane-integration
plan: 02
subsystem: ui
tags: [solid-js, tauri, sse, openapi-fetch, vitest, v13.1-sdk]

# Dependency graph
requires:
  - phase: V15-01
    provides: startVossServe(cwd) -> {port, token} handshake (sidecarClient.ts)
  - phase: V14 (cockpit)
    provides: injectable seams — RunCommandBar.client, CardDrawer.followUpClient, connectLiveStream
provides:
  - buildVossClientFromHandshake factory (V13.1 client + Pitfall-1 {id} adapter + followUpClient delegate)
  - sseClient onEvent per-pane sink + cardId ingest context (Pitfall 3) + session-keyed liveHandles set
  - App-level lazy ensureVossClient(cwd) wired into RunCommandBar.client, CockpitShell->CardDrawer.followUpClient, per-session connectLiveStream on native start
affects: [V15-03 structured pane (onEvent sink), V15-04 permission gate, V15-05 attach, V15-06 lifecycle]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy per-workspace client construction on first native start, Bridge A sessionId==cardId for live stream context, immutable Set signal for per-session liveness]

key-files:
  created:
    - apps/voss-app/src/org/live/vossClientBuild.ts
    - apps/voss-app/src/org/live/__tests__/clientBuild.test.ts
  modified:
    - apps/voss-app/src/org/live/sseClient.ts
    - apps/voss-app/src/org/live/__tests__/sseClient.test.ts
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/org/OrgViewShell.tsx
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx
    - apps/voss-app/src/org/cockpit/RunCommandBar.tsx

key-decisions:
  - "Adapter calls client.createSession() with NO arg — rest.ts's param is cwd, not goal; the session lands in the server's own spawn cwd (plan's spec.goal arg was a bug, Rule-1 deviation)"
  - "followUpClient threaded through OrgViewShell (thin wrapper) — App mounts OrgViewShell, not CockpitShell directly"
  - "RunCommandBar native branch gained a try/catch routing spawn failures into the existing block-reason path (plan demanded the behavior; file wasn't in files_modified)"

patterns-established:
  - "Native start pipeline: ensureVossClient(cwd) -> createSession -> connectLiveStream({baseUrl, sessionId, token, cardId: id})"
  - "liveHandles Set tracks per-session stream liveness for the multi-session label fix"

requirements-completed: [VLIVE-02, VLIVE-03]

# Metrics
duration: 8min
completed: 2026-06-10
---

# Phase V15 Plan 02: Live Client Wiring Summary

**V13.1 client built lazily from the Plan-01 handshake and plugged into all three V14 seams: RunCommandBar's native Start creates real server sessions, the drawer follow-up posts to bound sessions, and each native session streams live into AttentionQueue + overlay + liveLabel**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-10T15:20:49Z
- **Completed:** 2026-06-10T15:29:00Z
- **Tasks:** 2 (Task 1 TDD red-green)
- **Files modified:** 8

## Accomplishments
- `buildVossClientFromHandshake({port, token})` — pure factory returning `{client, baseUrl, token, runNativeClient, followUpClient}`; Bearer middleware on every request incl. SSE (T-V15-03); Pitfall-1 string→`{id}` adapter
- `sseClient.ts` extensions: `cardId` ingest context (permission.updated rows now carry a defined cardId — Pitfall 3), `onEvent` per-pane sink (Plan 03's ProtocolPane hook), session-keyed `liveHandles` Set (multi-session label fix), all immutable updates
- App-level `ensureVossClient(cwd)`: first native Start spawns the sidecar (Plan-01 reuse-if-alive), builds the client once, holds the token in a non-exported signal (T-V15-10); stream handles aborted onCleanup
- Native Start → real `createSession` → `connectLiveStream({baseUrl, sessionId, token, cardId: id})` (Bridge A: session id IS the cardId)
- Drawer follow-up live: `followUpClient` threaded App → OrgViewShell → CockpitShell → CardDrawer; snapshot-card disabled-with-reason path untouched
- No-sidecar degradation intact: all V14 gates stay; spawn failure surfaces via RunCommandBar's block-reason (T-V15-04)

## Task Commits

1. **Task 1 RED: failing tests** - `e0abc1d` (test)
2. **Task 1 GREEN: factory + sse extensions** - `64db425` (feat; committed by the concurrent auto-commit watcher)
3. **Task 2: App/CockpitShell/RunCommandBar wiring** - `3ff37d1` (feat)

## Files Created/Modified
- `apps/voss-app/src/org/live/vossClientBuild.ts` - the client factory + seam adapters
- `apps/voss-app/src/org/live/sseClient.ts` - cardId/onEvent args, liveHandles set
- `apps/voss-app/src/App.tsx` - ensureVossClient, RunCommandBar client prop, OrgViewShell followUpClient, connectLiveStream-on-start
- `apps/voss-app/src/org/OrgViewShell.tsx` - followUpClient pass-through (thin wrapper)
- `apps/voss-app/src/org/cockpit/CockpitShell.tsx` - followUpClient prop → CardDrawer
- `apps/voss-app/src/org/cockpit/RunCommandBar.tsx` - native-branch try/catch → block-reason
- `apps/voss-app/src/org/live/__tests__/clientBuild.test.ts` - factory tests (3)
- `apps/voss-app/src/org/live/__tests__/sseClient.test.ts` - +3 V15-02 cases (onEvent, permission cardId, liveHandles)

## Decisions Made
- createSession arg dropped (see deviations) — goal delivery to the session is downstream-plan work; VLIVE-02's must-have (real session id) holds
- `ensureVossClient` keys on cwd (workspace switch respawns/rebuilds rather than reusing a wrong-cwd server)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adapter arg: `client.createSession(spec.goal)` would pass the goal as cwd**
- **Found during:** Task 1 (factory)
- **Issue:** rest.ts `createSession(cwd?: string)` — the plan's `spec.goal` arg would create the session with the goal text as its working directory
- **Fix:** adapter calls `client.createSession()` (no arg); the session lands in the server's own spawn cwd (the workspace — Plan 01 spawns `voss serve` in the validated cwd)
- **Files modified:** vossClientBuild.ts, clientBuild.test.ts
- **Verification:** clientBuild.test.ts asserts `createSession` called with no args
- **Committed in:** 64db425

**2. [Rule 2 - Missing critical] RunCommandBar native branch had no rejection handling**
- **Found during:** Task 2
- **Issue:** plan requires spawn failures to surface via the block-reason path, but `handleStart` awaited `createSession` uncaught (→ unhandled rejection); RunCommandBar.tsx was not in files_modified
- **Fix:** try/catch around the native createSession → `setBlockReason('Could not start the Voss run: …')`
- **Files modified:** RunCommandBar.tsx
- **Verification:** runCommandBar.test.tsx 8/8 green (disabled-with-reason assertions intact)
- **Committed in:** 3ff37d1

**3. [Rule 2 - Missing critical] followUpClient must cross OrgViewShell**
- **Found during:** Task 2
- **Issue:** App mounts `OrgViewShell` (thin wrapper), not CockpitShell — plan's App→CockpitShell prop has no direct path
- **Fix:** added the `followUpClient?` pass-through prop to OrgViewShell
- **Files modified:** OrgViewShell.tsx
- **Verification:** grep chain App→OrgViewShell→CockpitShell→CardDrawer present; tsc clean
- **Committed in:** 3ff37d1

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical)
**Impact on plan:** All necessary for correctness; no scope creep. Goal-text delivery to the live session remains open for Plan 03/04 (the plan never wired it anywhere valid).

## Issues Encountered
- Concurrent auto-commit watcher committed Task 1 GREEN as `64db425` before the executor commit ran (known behavior; verified content matches the intended commit).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 03 (ProtocolPane structured rendering) consumes the `onEvent` sink and the wired client
- Full app suite 786/786 green; tsc clean; no-sidecar path byte-compatible with V14

---
*Phase: V15-live-plane-integration*
*Completed: 2026-06-10*

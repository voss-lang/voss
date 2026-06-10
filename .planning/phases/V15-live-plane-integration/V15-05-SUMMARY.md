---
phase: V15-live-plane-integration
plan: 05
subsystem: ui
tags: [solid-js, cockpit, sessions, attach, vitest]

# Dependency graph
requires:
  - phase: V15-03
    provides: openAttachedPane/openNativePane D-02 seam + ProtocolPane forward rendering
  - phase: V15-02
    provides: ensureVossClient (respawn-if-cold) + buildVossClientFromHandshake
provides:
  - serverSessions module (newest-first GET /session mirror, defensive accessors, attachSession respawn-if-cold)
  - "Server sessions" cockpit sidebar section (D-04/D-05) with hover-reveal Attach (D-06)
  - SDK fix — rest.ts listSessions/listSaved accept the {v, sessions} envelope
affects: [V15-06 lifecycle, V15-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [module-level signal + refresh-on-open sidebar section, attach via injected ensureClient/openAttachedPane callbacks]

key-files:
  created:
    - apps/voss-app/src/org/cockpit/serverSessions.ts
    - apps/voss-app/src/org/cockpit/serverSessions.css
    - apps/voss-app/src/org/cockpit/__tests__/serverSessions.test.ts
  modified:
    - sdk/typescript/src/client/rest.ts
    - apps/voss-app/src/org/cockpit/CockpitSidebar.tsx
    - apps/voss-app/src/org/cockpit/CockpitShell.tsx
    - apps/voss-app/src/org/OrgViewShell.tsx
    - apps/voss-app/src/App.tsx

key-decisions:
  - "SDK rest.ts listSessions/listSaved fixed to unwrap the server's {v, sessions:[...]} envelope (latent decode bug — expectArray ALWAYS threw against the real server; no SDK test covered it)"
  - "Live GET /session rows carry no timestamp ({id, cwd, model, title, busy}) — age renders blank; newest-first falls back to reversing insertion order"
  - "attachSession takes injected ensureClient/openAttachedPane callbacks — no App import cycle, trivially testable"

patterns-established:
  - "Sidebar live section: refresh-on-open createEffect gated on client presence; hidden entirely without a client"

requirements-completed: [VLIVE-06]

# Metrics
duration: 7min
completed: 2026-06-10
---

# Phase V15 Plan 05: Server Sessions Attach Summary

**Cockpit sidebar "Server sessions" section lists everything GET /session returns (newest first, unfiltered) with a hover-reveal Attach that respawns the sidecar if cold and opens a forward-only structured pane via the D-02 seam — plus an SDK fix without which listSessions could never decode the real server's response**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-10T16:09:16Z
- **Completed:** 2026-06-10T16:16:00Z
- **Tasks:** 2 (Task 1 TDD red-green)
- **Files modified:** 8

## Accomplishments
- `serverSessions.ts`: module signal + `refreshSessions(client)` (silent degrade on error), defensive accessors (`sessionId`/`sessionTitle` fallback-to-id/`sessionAgeLabel` blank-without-timestamp — live rows are `{id, cwd, model, title, busy}` per `harness/server/app.py`), `attachSession({cwd, sessionId, ensureClient, openAttachedPane})` → ensureClient (respawn-if-cold, T-V15-08) → `registerNativeCard(sessionId, sessionId)` (D-06) → openAttachedPane; NO history fetch (T-V15-12, test-pinned)
- Sidebar section (D-04): collapsible "Server sessions", refresh-on-open, newest-first unfiltered rows (id 8-chars / title / age), hover-reveal "Attach", "No previous sessions" empty state, hidden entirely without a client; all text escaped (T-V15-05)
- Threading: `vossClient` + `onAttach` App → OrgViewShell → CockpitShell → CockpitSidebar; App's onAttach composes `attachSession` with `ensureVossClient` + `openNativePane`
- **SDK fix:** `listSessions`/`listSaved` now unwrap the server's `{v, sessions: [...]}` envelope (accepting a bare array too) — previously `expectArray` threw unconditionally against the real server

## Task Commits

1. **Task 1 RED + SDK fix** - `(test commit)` test(V15-05) failing serverSessions tests + rest.ts envelope fix
2. **Task 1 GREEN** - feat(V15-05) serverSessions module
3. **Task 2** - `c599534` (CockpitShell props) + `e9f771d` (App wiring; watcher-committed)

## Files Created/Modified
- `serverSessions.ts` / `serverSessions.css` / `serverSessions.test.ts` - module, styles, 5 tests
- `sdk/typescript/src/client/rest.ts` - expectSessionsArray envelope unwrap
- `CockpitSidebar.tsx` - section 4 with refresh-on-open + Attach rows
- `CockpitShell.tsx` / `OrgViewShell.tsx` - prop pass-through
- `App.tsx` - vossClient/onAttach at the OrgViewShell mount

## Decisions Made
- Wave-0 inspection: GET /session returns `{v, sessions:[{id, cwd, model, title, busy}]}` — no timestamp field, so D-05 newest-first uses timestamp sort when present else reversed insertion order

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SDK listSessions could never decode the real response**
- **Found during:** Wave-0 read of `harness/server/app.py` (plan pointed at a nonexistent `voss/api/routes/session.py`)
- **Issue:** server wraps the list in `{v, sessions:[...]}`; rest.ts `expectArray` threw "expected listSessions response to be an array" unconditionally — VLIVE-06's must-have (list sessions) was impossible without the fix; no SDK test covered either method
- **Fix:** `expectSessionsArray` accepts the envelope or a bare array; applied to `listSessions` + `listSaved` (same envelope)
- **Verification:** SDK suite unchanged vs baseline (7 pre-existing env-dependent e2e failures, identical with/without the fix — they spawn a real server and trip undici's 204-body strictness); app suite green
- **Committed in:** the Task-1 RED commit

**2. [Rule 2 - Missing critical] Threading crosses OrgViewShell**
- Same shape as Plan 02's deviation: App mounts the thin OrgViewShell wrapper, so `vossClient`/`onAttach` pass through it.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** SDK fix is load-bearing for the whole requirement; no scope creep.

## Issues Encountered
- Pre-existing SDK e2e failures (7) in `sdk/typescript` — environmental (real `voss serve` spawn + "Status code 204 must not have a response body"); verified identical with the change stashed. Not addressed (out of scope).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V15-06/07 (remaining waves) can rely on attach + the live list
- Full app suite 811/811; tsc clean
- Open: post-restart "lists the prior session" depends on the server resurrecting saved sessions into the live manager; the UI honestly mirrors whatever GET /session returns

---
*Phase: V15-live-plane-integration*
*Completed: 2026-06-10*

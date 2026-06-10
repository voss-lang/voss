---
phase: V15-live-plane-integration
plan: 04
subsystem: ui
tags: [solid-js, sse, permission, lifecycle, vitest]

# Dependency graph
requires:
  - phase: V15-03
    provides: ProtocolPane + permission placeholder row + gate/boot/error/ended CSS shells + ExitBanner message?/showRestart? props
  - phase: V15-02
    provides: connectLiveStream cardId ingest (queue row with permission:${id})
provides:
  - resolveAttentionItem(id) — immutable inverse of pushItem (dual-surface clear)
  - live inline permission gate (Deny/Allow once/Allow for {scope} → d/a/A via replyPermission; one POST clears gate + queue row)
  - lifecycle states — D-10 boot placeholder, D-12 spawn error + Retry start, D-11 ended banner + death dim + onEnded
affects: [V15-05 attach, V15-06 lifecycle polish, V15-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [POST-then-clear (never optimistic) permission reply, liveHandles membership transition as stream-end detector, per-id gate state record]

key-files:
  created: []
  modified:
    - apps/voss-app/src/org/attention/attentionQueue.ts
    - apps/voss-app/src/pane/ProtocolPane.tsx
    - apps/voss-app/src/pane/PaneComponent.tsx
    - apps/voss-app/src/pane/ExitBanner.tsx
    - apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx
    - apps/voss-app/src/org/attention/__tests__/attentionQueue.test.tsx
    - apps/voss-app/src/org/__tests__/keystone-a1.test.ts

key-decisions:
  - "Gate reply client built in-pane from {baseUrl, token} via createVossClient (Bearer middleware, T-V15-03) — no VossClient object threaded through grid props"
  - "Stream-end detection = liveHandles membership transition (connected→gone); zero events while booting = connect failure (error state)"
  - "onEnded fires on session.idle (clean) AND on death; death additionally dims (.pane--proto-ended on the pane root)"
  - "PaneComponent's absolute PTY ExitBanner suppressed for native panes — the inline transcript banner owns the ended UX (no Restart)"

patterns-established:
  - "Dual-surface permission clear: resolveAttentionItem(`permission:${id}`) ONLY after replyPermission resolves"
  - "Retry start: user-initiated startVossServe(cwd) → rebind connectLiveStream to the fresh handshake; no auto-restart anywhere"

requirements-completed: [VLIVE-05, VLIVE-07]

# Metrics
duration: 11min
completed: 2026-06-10
---

# Phase V15 Plan 04: Live Permission Gate + Lifecycle States Summary

**Permission events now render an interactive in-pane gate (Deny/Allow once/Allow for scope → one Bearer-authed POST that clears gate + queue together), and ProtocolPane gained truthful boot/spawn-error/server-death states — Starting… with elapsed counter, stderr + Retry start, and a no-restart "[session ended]" banner with pane dim**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-10T15:55:59Z
- **Completed:** 2026-06-10T16:07:00Z
- **Tasks:** 2 (Task 1 TDD red-green)
- **Files modified:** 7

## Accomplishments
- `resolveAttentionItem(id)`: immutable filter inverse of pushItem; permission rows cleared by the load-bearing `permission:${id}` prefixed id (T-V15-11, test-pinned)
- Live gate: three buttons in tab order (d/a/A), disabled in-flight, `replyPermission(client, sessionId, {id, choice})` with the client built from the pane's own handshake (Bearer on every request, T-V15-03); resolved labels denied/allowed once/allowed for scope; failed POST re-enables both surfaces — never an optimistic grant (T-V15-07)
- D-10: `.proto-boot` "Starting…" + per-second elapsed + "Cold start takes up to 60s" after 5s; first event flips to the transcript
- D-12: zero-event stream end while booting → `.proto-spawn-error` with heading + stderr tail + "Retry start" → `startVossServe(cwd)` and stream rebind to the fresh `{port, token}`
- D-11: stream death (no `final`/`session.idle`) → inline `<ExitBanner message="[session ended]" showRestart={false}>` in transcript flow, `.pane--proto-ended` dim, `onEnded` fired (follow-up degrade); clean end shows the banner undimmed; no auto-restart — the next run respawns via the existing path

## Task Commits

1. **Task 1 RED** - `7d66bba`/`fdfdbff` (test)
2. **Task 1 GREEN: gate + resolveAttentionItem** - `6052007` (feat)
3. **Task 2: lifecycle states** - `490fb1b` (feat) + `7cc042a` (lockfile, watcher)

## Files Created/Modified
- `attentionQueue.ts` - resolveAttentionItem export
- `ProtocolPane.tsx` - live gate, bootState machine, connect/retry, ended row, death dim
- `PaneComponent.tsx` - absolute ExitBanner suppressed for native panes; onEnded → dot only
- `ExitBanner.tsx` - (V15-03 prop hole consumed; no further change needed)
- `ProtocolPane.test.tsx` - +8 tests (4 gate, 4 lifecycle)
- `attentionQueue.test.tsx` - +2 resolveAttentionItem tests
- `keystone-a1.test.ts` - @ts-expect-error → @ts-ignore (see Issues)

## Decisions Made
- Reply client constructed in-pane from `{baseUrl, token}` rather than threading a non-serializable VossClient through App→GridRoot→SplitNode (equivalent auth path, simpler seams)
- Stream-end detector reads the Plan-02 `liveHandles` set — no sseClient API change needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PaneComponent double-banner for native panes**
- **Found during:** Task 2
- **Issue:** Plan-03's `onEnded → setExitCode(1)` made PaneComponent render its absolute PTY ExitBanner (with Restart) on top of the new inline no-restart banner — D-11 forbids Restart on server death
- **Fix:** native panes excluded from the absolute banner Show; onEnded now drives the header dot only (PaneComponent not in this plan's files_modified but required)
- **Verification:** pane suite green; death test asserts no `.eb-restart`
- **Committed in:** 490fb1b

**2. [Rule 3 - Blocking] tsc broken by transitively hoisted @types/node**
- **Found during:** Task 2 verify
- **Issue:** the concurrent process added a root `litellm` npm dependency; its transitive `@types/node` made two `@ts-expect-error node:fs/node:path` directives in keystone-a1.test.ts "unused" (TS2578)
- **Fix:** switched both to `@ts-ignore` (tolerates either typing state)
- **Verification:** `tsc --noEmit` exit 0
- **Committed in:** 490fb1b

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Required for correctness/build health; no scope creep.

## Issues Encountered
- **Workspace dependency corruption mid-plan:** the concurrent watcher ran `npm install` (adding `litellm`) at the root of this **pnpm** monorepo, gutting the pnpm virtual store — vite-plugin-solid stopped transforming JSX and even untouched suites (PasteGuard) failed with "Unexpected JSX expression". Repaired with `pnpm install` (lockfile re-synced, committed as `7cc042a`). The earlier "transient parse failures" in V15-03/04 were early symptoms of the same corruption.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 05 (attach): `openAttachedPane` seam + lifecycle states ready; gate live for attached sessions too
- Full suite 806/806; tsc clean
- **Note for operator:** root `package.json` now carries an npm `litellm` dependency (watcher-added). The JS `litellm` package is almost certainly unintended in this Python/Rust monorepo — consider removing it (kept to avoid reverting a concurrent process's commit).

---
*Phase: V15-live-plane-integration*
*Completed: 2026-06-10*

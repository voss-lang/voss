---
phase: V15-live-plane-integration
plan: 01
subsystem: infra
tags: [tauri, rust, sidecar, voss-serve, ipc, solid-js, vitest]

# Dependency graph
requires:
  - phase: V14 (cockpit)
    provides: proven sidecar spike (crates/voss-app-core/src/sidecar.rs, de93b4d) + Pitfall 4 finding (webview cannot spawn voss serve)
provides:
  - start_voss_serve Tauri command with per-cwd Mutex<HashMap<String, VossServe>> managed state (reuse-if-alive, stale respawn, reap-on-exit)
  - validate_workspace_cwd canonicalize + allowed-roots gate in voss-app-core (T-V15-01)
  - typed frontend wrapper startVossServe(cwd) -> ServeHandshake {port, token} (sidecarClient.ts)
  - gated cargo proofs: reuse_if_alive (VOSS_SIDECAR_SPIKE=1) + ungated cwd_validation
affects: [V15-02 client construction, V15 live SSE, V15 structured pane, V15 attach, V15 lifecycle]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-workspace sidecar lifecycle via Tauri managed Mutex<HashMap>, pid()==None stale-entry sentinel, scoped-lock-before-await command body]

key-files:
  created:
    - apps/voss-app/src/org/live/sidecarClient.ts
    - apps/voss-app/src/org/live/__tests__/sidecarCommand.test.ts
  modified:
    - apps/voss-app/src-tauri/src/lib.rs
    - crates/voss-app-core/src/sidecar.rs

key-decisions:
  - "validate_workspace_cwd lives in voss-app-core (next to the frozen spawn impl) so the cargo test can exercise it without the Tauri crate"
  - "Map keyed by the ORIGINAL cwd string (canonical path used only for the spawn arg) so frontend reuse hits the same key it passed"
  - "reuse_if_alive proves the pid()==None sentinel via same-module private-field access (child.start_kill + wait) — frozen impl byte-unchanged"

patterns-established:
  - "Sidecar lifecycle: Tauri command checks map under scoped lock, never holds lock across .await, inserts after spawn"
  - "Token hygiene: handshake token returned in-memory only; no log/stringify path on either side (T-V15-10)"

requirements-completed: [VLIVE-01]

# Metrics
duration: 5min
completed: 2026-06-10
---

# Phase V15 Plan 01: Sidecar Tauri Command Summary

**`start_voss_serve` Tauri command spawning one `voss serve` per workspace cwd with reuse-if-alive, canonicalized cwd validation, and a typed `startVossServe(cwd)` frontend wrapper returning `{port, token}`**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-10T15:12:13Z
- **Completed:** 2026-06-10T15:17:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Resolved V14 Pitfall 4: the webview now gets a real `{port, token}` handshake via `invoke('start_voss_serve', { cwd })` — only the Tauri side spawns the server
- Per-workspace lifecycle: `Mutex<HashMap<String, VossServe>>` managed state; same cwd reuses the live server, `pid()==None` stale entries respawn, all entries reap on app exit (`kill_on_drop`)
- `validate_workspace_cwd` canonicalizes and gates the webview-supplied cwd before any spawn (T-V15-01); empty allowed-roots = single-user local default
- Cargo proofs: `cwd_validation` (ungated) + `reuse_if_alive` (gated on `VOSS_SIDECAR_SPIKE=1`, real spawns: distinct cwds → distinct pids; pid None after reap)
- Frontend: `sidecarClient.ts` thin typed wrapper + 3 vitest cases including the no-token-log spy (T-V15-10)

## Task Commits

Each task was committed atomically:

1. **Task 1: Tauri start_voss_serve command + managed state + cwd validation** - `fe47c5b` (feat)
2. **Task 2: Gated cargo reuse/validation tests + typed frontend invoke wrapper** - `22f0599` (test)

## Files Created/Modified
- `apps/voss-app/src-tauri/src/lib.rs` - `start_voss_serve` command, `VossServeMap` alias, `.manage(Mutex::new(HashMap...))`, `generate_handler!` entry
- `crates/voss-app-core/src/sidecar.rs` - `validate_workspace_cwd` helper + `cwd_validation`/`reuse_if_alive` tests (spawn impl byte-unchanged: additions only, 0 deletions vs base)
- `apps/voss-app/src/org/live/sidecarClient.ts` - `startVossServe(cwd)` → `ServeHandshake {port, token}` invoke wrapper
- `apps/voss-app/src/org/live/__tests__/sidecarCommand.test.ts` - invoke-args, error-propagation, and no-token-log tests

## Decisions Made
- Map keyed by original cwd string; canonical path used only as the spawn argument — keeps the frontend reuse contract simple
- `reuse_if_alive` accesses the private `child` field from the same-module test (start_kill + wait) to prove the `pid()==None` sentinel without unfreezing the impl

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Downstream V15 plans (client construction, live SSE, structured pane, attach, lifecycle) can consume `startVossServe(cwd)` for a real handshake
- Gated tests run green with `VOSS_SIDECAR_SPIKE=1` (4/4 sidecar tests, 2.89s warm)

---
*Phase: V15-live-plane-integration*
*Completed: 2026-06-10*

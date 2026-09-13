---
phase: V11-ade-org-integration
plan: 02
subsystem: api
tags: [tauri, rust, solidjs, subprocess, cli-json, serde_json, invoke]

# Dependency graph
requires:
  - phase: V11-01
    provides: RunData/RunEntry/DecisionResult TS contract types + assertRunData guard
  - phase: V4-V9
    provides: .voss/sessions node-tree layout + voss audit --format json + audit --approve write path
provides:
  - load_run Tauri command — aggregate RunData (nodes + review sidecars + audit JSON + run-final) via direct Rust read + one shelled audit
  - enumerate_runs Tauri command — V4+ session-tree dirs only, newest first (dual-layout filter)
  - run_decision Tauri command — shells voss CLI, captures stdout/stderr/exit
  - orgStore.ts (runData/loadError/loading/currentRunId signals + loadRun/enumerateRuns/refreshRun)
  - decisionActions.ts (buildDecisionArgs/buildDecisionCommand/runDecision — verified --approve write path)
affects: [OrgViewShell, BoardPanel, AuditPanel, BlockedPanel, ReplayPanel, V11-03+]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Aggregate read command: direct Rust FS read of node files (voss board has no JSON), single shelled `audit --format json`"
    - "Dual-layout filter: is_dir() + has-node-json gate excludes legacy flat SessionRecords (Pitfall 1)"
    - "Path-traversal guard before FS access; Command::args(vector) never shell string (T-V11-03/04)"
    - "One-write-path invariant: run_decision only shells the verified `voss audit <id> --approve`"
    - "Temp dirs in cargo tests via std::env::temp_dir + pid/nanos — no tempfile crate (no new deps)"

key-files:
  created:
    - apps/voss-app/src/org/orgStore.ts
    - apps/voss-app/src/org/decisionActions.ts
  modified:
    - apps/voss-app/src-tauri/src/lib.rs

key-decisions:
  - "JSON payloads carried as serde_json::Value (RESEARCH skeleton) — frontend owns the typed shape; Rust stays schema-agnostic past the boundary"
  - "load_run shells `voss board`? NO — board has no JSON; nodes read directly in Rust (D-01 deviation, RESEARCH Open-Q2)"
  - "Only `approve` is wired (sole non-interactive write path); reject/unblock deferred to Plan 07 as disabled-with-explanation"
  - "run_decision capture test uses a fake executable named `voss` (passes is_voss_cli_binary) exiting 3; #[cfg(unix)] gated"

patterns-established:
  - "Pattern: aggregate Tauri read command returning serde_json::Value sections validated client-side by assertRunData"
  - "Pattern: enumerate filters is_dir + node-json presence, sorts mtime desc"

requirements-completed: [VADE-01, VADE-02, VADE-03, VADE-04, VADE-05, VADE-06, VADE-07, VADE-08, VADE-09, VADE-10]

# Metrics
duration: 15min
completed: 2026-06-07
---

# Phase V11 Plan 02: CLI-JSON Data Layer Summary

**Aggregate `load_run` + `enumerate_runs` + `run_decision` Tauri commands (path-guarded, injection-safe) plus the orgStore/decisionActions SolidJS wrappers — the single data path for the org view.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto)
- **Files created:** 2 (orgStore, decisionActions); **modified:** 1 (lib.rs)

## Accomplishments
- `load_run` — path-traversal guarded; reads node `.json` + `*.review.json` sidecars directly, shells `voss audit … --format json` (graceful null), tolerates missing `run-final.json`. Returns typed `RunData`.
- `enumerate_runs` — `is_dir()` + node-json gate excludes legacy flat SessionRecords; sorted newest-first; `Vec::new()` on missing dir.
- `run_decision` — validates binary via `is_voss_cli_binary`, rejects traversal args, runs `Command::args(vector)` (no shell string), captures stdout/stderr/exit. One-write-path invariant intact.
- All three registered in `generate_handler!`.
- `orgStore.ts` validates `load_run` output through `assertRunData` (D-02 boundary).
- `decisionActions.ts` builds the verified `voss audit <id> --cwd <cwd> --approve` command/argv; documents why reject/unblock are not wired.

## Task Commits
Uncommitted (per session convention — commit on request). Each task is independently verifiable:
1. Task 1: load_run + enumerate_runs + dual-layout/traversal cargo tests
2. Task 2: run_decision + nonzero-exit capture cargo test
3. Task 3: orgStore.ts + decisionActions.ts

## Files Created/Modified
- `src-tauri/src/lib.rs` — RunData/RunEntry/DecisionResult structs, load_run/enumerate_runs/run_decision commands, handler registration, 3 cargo tests
- `src/org/orgStore.ts` — signals + loadRun/enumerateRuns/refreshRun
- `src/org/decisionActions.ts` — buildDecisionArgs/buildDecisionCommand/runDecision

## Decisions Made
See `key-decisions` frontmatter. D-01 deviation (direct Rust node read instead of shelling `voss board`) was pre-authorized in the plan objective + RESEARCH Open-Q2.

## Deviations from Plan
None - plan executed as written. No new dependencies (cargo tests use std temp dirs, not the tempfile crate, per T-V11-SC).

## Issues Encountered
- `cargo test` accepts a single TESTNAME filter; ran the full crate suite instead of three positional names. All 10 tests pass.

## Verification
- `cargo test --manifest-path src-tauri/Cargo.toml` → **10 passed** (incl. dual-layout filter, traversal reject, nonzero-exit capture)
- `npx tsc --noEmit` → **exit 0**
- `grep -c 'load_run|enumerate_runs|run_decision' lib.rs` → 15 (all registered)
- org vitest still green (9 passed)

## Next Phase Readiness
- Data path complete: panels (Plan 03+) and OrgViewShell can `loadRun`/`enumerateRuns` and render from `runData()`.
- BlockedPanel (Plan 07) has `runDecision` + `buildDecisionCommand` ready; reject/unblock remain disabled pending a harness command.

---
*Phase: V11-ade-org-integration*
*Completed: 2026-06-07*

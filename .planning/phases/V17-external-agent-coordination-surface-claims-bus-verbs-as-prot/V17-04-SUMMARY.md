---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 04
subsystem: infra
tags: [tauri, rust, solidjs, env-injection, ipc, vitest, cargo]

# Dependency graph
requires:
  - phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot (plan 01)
    provides: test_env_injection.py scaffold (un-xfailed here)
  - phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot (plan 03)
    provides: claims verbs that resolve VOSS_AGENT_ID
provides:
  - slugRegistry.ts — mintSlug (D-12 <cli>-<n> / pane-<n>) + per-pane signal exported for A6 persistence (D-13)
  - vossAgentId threaded through AgentConfig + all three PtyTransport spawn methods (camelCase IPC)
  - spawnPaneSession mints once per pane, reuses on respawn, registers in slugRegistry (D-11 all panes)
  - VOSS_AGENT_ID injected at spawn_agent / spawn_managed_agent / spawn_pty via build_env_with_agent_id (owned env Vec)
affects: [V17-05, V17-06, V17-07, A6]

# Tech tracking
tech-stack:
  added: []
  patterns: [owned (String,String) env Vec bridging static env helper + dynamic slug, slug reuse on respawn via registry lookup]

key-files:
  created:
    - apps/voss-app/src/pane/slugRegistry.ts
    - apps/voss-app/src/pane/__tests__/slugRegistry.test.ts
  modified:
    - apps/voss-app/src/pane/pty-ipc.ts
    - apps/voss-app/src/pane/paneSession.ts
    - apps/voss-app/src/pane/paneSessionRegistry.ts
    - apps/voss-app/src-tauri/src/lib.rs
    - tests/harness/test_env_injection.py

key-decisions:
  - "Slug minted in spawnPaneSession (the single spawn orchestrator) not in pty-ipc — paneId lives there; respawn reuses slugByPaneId()[paneId] so the identity survives ExitBanner restarts (D-13)"
  - "spawn_pty switched from spawn_session to spawn_command_session_with_env with $SHELL + VOSS_EMBEDDED=1 — behavior-identical plain shell, now env-capable"
  - "build_env_with_agent_id skips empty-string slugs (treats as None) — no blank env var"
  - "KNOWN_AGENT_CLIS imported from agentDetect.ts (pure module, no cycle); includes cursor beyond the adopt.ts five"

patterns-established:
  - "Per-pane registries cleaned up together in destroyPaneSession — slugRegistry joins proc/budget/context/agentPane"

requirements-completed: [VBUS-03]

# Metrics
duration: 15min
completed: 2026-06-10
---

# Phase V17 Plan 04: Identity Injection Summary

**VOSS_AGENT_ID now reaches every pane at spawn: slugRegistry mints claude-1/pane-3 slugs, spawnPaneSession passes them through camelCase IPC, and all three Rust spawn commands append the slug to an owned env Vec — 7 vitest + 2 new cargo tests green, sandbox.rs byte-unchanged**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-06-10
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- D-11 satisfied by construction: managed agents, unmanaged agents, AND plain shells all receive VOSS_AGENT_ID (spawn_pty was env-less before)
- D-12 slug format from KNOWN_AGENT_CLIS basename match; shared counter keeps slugs globally unique
- D-13 best-effort: slug registered per paneId, reused on respawn, exported for A6 pane-config persistence; freed in destroyPaneSession
- camelCase IPC round-trip guarded by Rust unit tests (Some → ("VOSS_AGENT_ID", slug) present; None/empty → absent) — silent-None injection would surface here
- test_env_injection.py un-xfailed: stake records env identity as owner; bare shell exits 2 — genuinely GREEN

## Task Commits

1. **Task 1: slugRegistry + vitest** - `ea8e570` (feat)
2. **Task 2: IPC threading + spawn-site minting** - `acd2f2c` (feat)
3. **Task 3: Rust env injection + unit tests** - `00dbe52` (feat)
4. **un-xfail test_env_injection.py** - swept into concurrent auto-commit `afb3381` (see Issues)

## Files Created/Modified
- `slugRegistry.ts` / `__tests__/slugRegistry.test.ts` - mint + signal, 7 tests
- `pty-ipc.ts` - vossAgentId on AgentConfig + three invoke objects (×5 occurrences)
- `paneSession.ts` - mint/reuse + register at the single spawn orchestrator
- `paneSessionRegistry.ts` - unregisterSlug in the kill path
- `lib.rs` - voss_agent_id param ×3, build_env_with_agent_id helper + 2 unit tests; spawn_pty now env-capable
- `tests/harness/test_env_injection.py` - xfail scaffolding removed

## Decisions Made
See frontmatter key-decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] paneSession.ts + paneSessionRegistry.ts wiring (not in files_modified)**
- **Found during:** Task 2
- **Issue:** Plan's must-have truth "Every pane spawn mints a slug" is unfulfillable from the three listed files — no caller would ever mint/pass the slug; pty-ipc has no paneId for plain spawns
- **Fix:** Minimal wiring at spawnPaneSession (mint/reuse + register + pass on all three branches) and unregisterSlug in destroyPaneSession
- **Verification:** tsc clean; full vitest sweep 825 passed (no regressions)
- **Committed in:** acd2f2c

**2. [Rule 3 - Blocking] Plan's test path not collected by vitest**
- **Found during:** Task 1
- **Issue:** vitest include is `src/**/__tests__/**/*.test.{ts,tsx}`; plan placed slugRegistry.test.ts flat in src/pane/
- **Fix:** Moved to `src/pane/__tests__/slugRegistry.test.ts` (repo convention)
- **Committed in:** ea8e570

**3. [Minor] AGENT_CLIS source**
- Plan pointed at agentPaneRegistry.ts for the set; it actually lives in agentDetect.ts as KNOWN_AGENT_CLIS (includes 'cursor'). Imported from there.

---

**Total deviations:** 3 (1 missing critical, 1 blocking, 1 minor)
**Impact on plan:** Wiring deviation is the plan's own must-have; no scope creep beyond it.

## Issues Encountered
- Concurrent E1 process auto-committed the un-xfailed test_env_injection.py bundled into its `afb3381` commit (known behavior, see memory note) — content is correct and green, just under a foreign commit message.

## User Setup Required
None.

## Next Phase Readiness
- Manual VALIDATION item outstanding: launch an agent pane in the running app, `env | grep VOSS_AGENT_ID` (cannot be automated — Tauri E2E blocked on macOS)
- `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN` injection deferred to the V15-gated bus wave as planned
- Remaining V17 plans: V17-05/06 (bus, V15-gated), V17-07 (doc — all shipped verbs now stable)

---
*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Completed: 2026-06-10*

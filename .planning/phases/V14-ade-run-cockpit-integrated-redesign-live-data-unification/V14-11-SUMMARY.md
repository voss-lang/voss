---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 11
subsystem: security
tags: [sandbox-exec, seatbelt, bwrap, tauri, portable-pty, solid-js, capability-tier, budget-kill]

# Dependency graph
requires:
  - phase: V14-08
    provides: handleLaunchAgent Bridge-B spawn wiring (the branch point extended here)
  - phase: V14-09
    provides: AgentLaunchModal managed toggle + tier in buildConfig
provides:
  - OS scope-sandbox floor — crates/voss-app-core/src/sandbox.rs (Seatbelt profile generator from deny file-write*, scope validation/canonicalization, wrap_argv macOS sandbox-exec / Linux bwrap / honest Unavailable)
  - spawn_command_session_managed pty hook (per-run profile write + wrapped argv; unmanaged spawn fns byte-unchanged)
  - spawn_managed_agent Tauri command returning {pty_id, tier, sandboxed} with honest tier-C downgrade when no sandbox tool exists
  - capabilityTier.ts pure resolver (adopted→C always; managed+hook→A; managed→B; unmanaged→C) + hookCapableCli (false until VCKP-13b proxy ships)
  - PtyTransport.spawnManagedAgent + budget-kill (budget_update cost_usd >= budgetKillLimitUsd → pty_kill)
  - End-to-end managed routing: handleLaunchAgent records resolveTier output + scope; PaneComponent.doSpawn branches managed→spawnManagedAgent
affects: [V14-12, AttentionQueue permission-proxy wave (VCKP-13b), roster tier display]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sandbox profile: (allow default) reads, (deny file-write*) then allow ONLY canonical scope + temp dirs + /dev regex — never widen (V12)"
    - "Honest enforcement chain: backend returns EFFECTIVE tier (sandboxed:false → 'C'); frontend records resolveTier for the command actually invoked, never the modal's static value (T-V14-03/07)"
    - "wrap_argv takes platform as an explicit param so argv shapes unit-test on any host"
    - "Budget-kill lives in PtyTransport budget_update handler (frontend cost meter → pty_kill), per RESEARCH VCKP-13c ownership"

key-files:
  created:
    - crates/voss-app-core/src/sandbox.rs
    - apps/voss-app/src/org/capabilityTier.ts
    - apps/voss-app/src/org/__tests__/capabilityTier.test.ts
    - apps/voss-app/src/__tests__/managedLaunchRouting.test.tsx
  modified:
    - crates/voss-app-core/src/pty/mod.rs
    - crates/voss-app-core/src/lib.rs
    - apps/voss-app/src-tauri/src/lib.rs
    - apps/voss-app/src/pane/pty-ipc.ts
    - apps/voss-app/src/pane/PaneComponent.tsx
    - apps/voss-app/src/App.tsx

key-decisions:
  - "Tier recorded in the frontend AgentConfig map + returned from spawn_managed_agent (effective tier), NOT a new sqlite agent_sessions column — the roster reads the config map; avoids a schema migration in a file outside files_modified"
  - "hookCapableCli returns false for every CLI until the VCKP-13b permission proxy ships — tier A is resolver-supported but unreachable at launch (no overstated control)"
  - "App overrides the modal's static tier with resolveTier at recording: unmanaged spawns record C (modal still emits B; recording is the honest layer)"
  - "Managed launch with no resolvable scope (no config.scope, no workspacePath) falls back to an UNMANAGED spawn recorded as C — a sandbox that can't be built is never claimed"
  - "Profile allows /private/tmp + /private/var/folders + /dev/ regex beyond the plan's literal sketch (macOS /tmp symlink + PTY tty writes); kernel-denial test still proves out-of-scope writes fail"

patterns-established:
  - "Security toggle honesty: a UI enforcement switch must route to the enforcing command and the recorded tier must match the invoked command — asserted by routing test (T-V14-07)"

requirements-completed: [VCKP-13]

# Metrics
duration: 12min
completed: 2026-06-09
---

# Phase V14 Plan 11: Managed Launch + Enforcement Tiers Summary

**Kernel-enforced scope sandbox for managed CLI launches (sandbox-exec Seatbelt profile from deny file-write*, proven by an OS-denial cargo test), spawn_managed_agent Tauri command with honest tier-C downgrade, pure A/B/C tier resolver (adopt locked to C), budget-kill at the cost limit, and end-to-end UI routing so the managed toggle invokes the sandboxed command — never a no-op.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-09T18:26:00Z
- **Completed:** 2026-06-09T18:37:44Z
- **Tasks:** 4 (task 4 TDD)
- **Files modified:** 4 created + 6 modified

## Accomplishments
- `sandbox.rs`: `validate_scope` (canonicalize; reject traversal/relative/injection chars — V5), `generate_profile` (write policy starts `(deny file-write*)`; allows only canonical scope + temp dirs + `/dev/` for PTY ttys — V12), `wrap_argv` (macOS `sandbox-exec -f`, Linux `bwrap` best-effort, `Unavailable` otherwise). Cargo test proves the floor: `sandbox-exec`-wrapped `touch` outside scope → "Operation not permitted" (non-zero, file absent); inside scope → success.
- `spawn_command_session_managed` in `pty/mod.rs`: per-run profile written to temp, argv wrapped, delegates to the UNCHANGED `spawn_command_session_with_env`; returns `sandboxed: bool` for honest downgrade.
- `spawn_managed_agent` (lib.rs): clone of `spawn_agent` + sandbox wrap; accepts `scope`+`tier`; registers the REAL CLI in the roster registry; returns `{pty_id, tier, sandboxed}` with tier→'C' when no sandbox tool exists. Registered in invoke_handler; core + src-tauri build clean.
- `capabilityTier.ts`: `resolveTier` (adopted→C always — exhaustively tested across all flag combos; managed+hook→A; managed→B; unmanaged→C) + `hookCapableCli` (false until the proxy ships).
- Budget-kill (VCKP-13c): `PtyTransport` `budget_update` handler kills via the existing `pty_kill` path at `cost_usd >= budgetKillLimitUsd`; threshold rides `AgentConfig.budgetUsd` → PaneComponent transport opts.
- End-to-end routing: `handleLaunchAgent` computes `scope` (config.scope ?? workspace root), records `resolveTier(...)`, writes managed/scope/tier/budgetUsd into the pane config; `PaneComponent.doSpawn` branches managed→`spawnManagedAgent` (scope+tier passed), unmanaged→unchanged `spawnAgent`. Routing test asserts managed→`spawn_managed_agent` (scope carried, `spawn_agent` NOT called) and unmanaged→`spawn_agent` (no scope).

## Task Commits

1. **Task 1: sandbox.rs floor** — `4a1171e` (feat)
2. **Task 2: spawn_managed_agent** — `01dd448` (feat)
3. **Task 3: capabilityTier resolver** — `9126aca` (committed by the workspace auto-commit watcher mid-task; content = authored files exactly)
4. **Task 4: UI routing (TDD)** — `8d8e333` (test, RED) → `ade831a` (feat, GREEN)

## Files Created/Modified
- `crates/voss-app-core/src/sandbox.rs` — profile generator + wrap_argv + 4 tests (incl. macOS kernel-denial)
- `crates/voss-app-core/src/pty/mod.rs` — `spawn_command_session_managed` hook (existing spawn fns untouched)
- `crates/voss-app-core/src/lib.rs` — module + re-exports
- `apps/voss-app/src-tauri/src/lib.rs` — `spawn_managed_agent` + `ManagedSpawnResult` + handler registration
- `apps/voss-app/src/org/capabilityTier.ts` (+ test) — pure tier resolver
- `apps/voss-app/src/pane/pty-ipc.ts` — AgentConfig managed/scope/tier/budgetUsd; `spawnManagedAgent`; budget-kill
- `apps/voss-app/src/pane/PaneComponent.tsx` — doSpawn managed branch + budgetKillLimitUsd pass-through
- `apps/voss-app/src/App.tsx` — handleLaunchAgent managed wiring + honest tier recording
- `apps/voss-app/src/__tests__/managedLaunchRouting.test.tsx` — 7 routing/tier/budget-kill tests

## Decisions Made
See frontmatter key-decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] PaneComponent.tsx modified (not in files_modified)**
- **Found during:** Task 4 (UI routing)
- **Issue:** The plan assumed `handleLaunchAgent` invokes the spawn directly; in reality it writes `agentConfigByPaneId` and `PaneComponent.doSpawn` issues the invoke. Without branching there, the managed toggle stays a no-op — the exact T-V14-07 blocker this task closes.
- **Fix:** doSpawn branches on `agentConfig.managed` → `spawnManagedAgent`; unmanaged branch byte-unchanged. Budget-kill threshold plumbed into transport opts in the same file.
- **Verification:** routing test (managed→spawn_managed_agent, unmanaged→spawn_agent) + 721/721 full suite.
- **Committed in:** `ade831a`

**2. [Rule 2 - Missing Critical] Tier recorded in frontend config map, not sqlite registry**
- **Found during:** Task 2
- **Issue:** "Write the tier into the registry" implies a new `agent_sessions` column — `agent_registry.rs` is not in files_modified and a column needs a migration for existing DBs.
- **Fix:** `spawn_managed_agent` returns the EFFECTIVE tier (`{pty_id, tier, sandboxed}`); the honest tier lives in the frontend `AgentConfig` map (the source `agentListForSidebar` reads).
- **Verification:** cargo builds; routing/tier tests green.
- **Committed in:** `01dd448` / `ade831a`

**3. [Rule 1 - Bug] Plan's literal profile breaks PTY output / macOS temp**
- **Found during:** Task 1
- **Issue:** The interface profile sketch (`scope` + `/tmp` only) denies writes to `/dev/ttys*` (the PTY the CLI writes output to) and misses `/private/tmp`//`/private/var/folders` (macOS `/tmp` symlink + canonical temp).
- **Fix:** Profile additionally allows `/private/tmp`, `/private/var/folders`, and `regex #"^/dev/"`. Still starts from `deny file-write*`; kernel test proves out-of-scope denial holds.
- **Verification:** `cargo test -p voss-app-core sandbox` — denial + in-scope-allow both asserted.
- **Committed in:** `4a1171e`

---

**Total deviations:** 3 auto-fixed (2 missing-critical, 1 bug). **Impact:** All necessary for the enforcement to be real and honest; no scope creep.

## Issues Encountered
- Workspace auto-commit watcher captured task-3 files as `9126aca` before my commit (second occurrence this phase). Content verified identical; tree clean.

## User Setup Required

None - no external service configuration required.

## Verification
- `cargo test -p voss-app-core sandbox` — 4/4 (incl. OS-layer denial: out-of-scope `touch` → "Operation not permitted").
- `cargo build -p voss-app-core` + src-tauri `cargo build` — clean.
- `npx vitest run src/org/__tests__/capabilityTier.test.ts` — 6/6.
- `npx vitest run src/__tests__/managedLaunchRouting.test.tsx` — 7/7.
- Full app suite `npx vitest run` — 721/721 (77 files); `npx tsc --noEmit` clean (unmanaged path unregressed).

## Self-Check: PASSED

## Next Phase Readiness
- VCKP-13b permission proxy (Claude hooks / OpenCode permission config → AttentionQueue) is the remaining best-effort layer; flip `hookCapableCli` per-CLI when it lands to unlock tier A.
- Launch surfaces (modal/RunCommandBar) can now pass `scope`/`budgetUsd` through `handleLaunchAgent` — fields are plumbed; UI inputs optional follow-up.
- V14-12 is the last plan in the phase.

---
*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Completed: 2026-06-09*

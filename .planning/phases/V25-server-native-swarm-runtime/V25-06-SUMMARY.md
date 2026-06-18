---
phase: V25-server-native-swarm-runtime
plan: 06
subsystem: testing
tags: [swarm, e2e, integration, fastapi, testclient, acceptance]

# Dependency graph
requires:
  - phase: V25-01
    provides: SwarmStore.replay / replay_timeline
  - phase: V25-02
    provides: 5 swarm SSE event models
  - phase: V25-04
    provides: /swarm routes, spawn-gate, per-role spawn, fan-out emit
  - phase: V25-05
    provides: ownership policy injection, escalation, scoped recall, decision audit
provides:
  - The single 2-builder enforced end-to-end integration test (SPEC acceptance bar)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Whole-runtime e2e via TestClient under VOSS_SERVE_FAKE_TURN — no live provider, no nudge/stdin"
    - "Spawn-gate zero-turns proof via in-loop asyncio.run (Event created in the awaiting loop)"

key-files:
  created:
    - tests/test_swarm_e2e.py
  modified:
    - crates/voss-app-core/src/agent_registry.rs

key-decisions:
  - "Ownership deny + escalation exercised through the REAL production wiring (build_ownership_policy at assign → PermissionGate project_policy → _apply_swarm_escalation) since FAKE_TURN does not run tools"
  - "Zero-turns-until-assign proven in an isolated asyncio.run block to avoid cross-loop asyncio.Event binding"

patterns-established:
  - "One integration test = the SPEC acceptance bar (per SPEC 'passes as one integration test')"

requirements-completed: [VSWARM-01, VSWARM-02, VSWARM-03, VSWARM-04, VSWARM-05, VSWARM-06, VSWARM-07, VSWARM-10, VSWARM-11]

# Metrics
duration: ~18 min
completed: 2026-06-17
---

# Phase V25 Plan 06: 2-Builder Enforced End-to-End Integration Test Summary

**One headless integration test drives the full server-native swarm runtime — create → 2 disjoint tasks (3rd overlap rejected) → builders gated zero-turns-until-assign → owned-only edit allowed / 3rd-file write denied + escalated → reviewer gate writes a decision → swarm.complete → events.jsonl replays the full open→assigned→done timeline — with no nudge/stdin.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-06-17
- **Tasks:** 1
- **Files:** 1 created (+1 restored)

## Accomplishments
- `tests/test_swarm_e2e.py` (180 lines): the SPEC acceptance bar as ONE test under `VOSS_SERVE_FAKE_TURN`, covering VSWARM-01/02/03/04/05/06/07/10/11 in a single scripted path.
- Asserts: 2 disjoint tasks accepted + 3rd overlapping rejected 409 (VSWARM-06); builders gated, zero turn output until the gate fires then exactly one turn (VSWARM-04, proven in an isolated `asyncio.run` block); owned-file edit allowed while a 3rd-file write is denied at the gate and emits `swarm.needs_operator` answerable via `/session/{id}/permission` (VSWARM-05/10); reviewer reject writes a `.voss/decisions/*.md` (VSWARM-10); `swarm.complete` reaches a subscriber (VSWARM-02); `replay_timeline` shows each task `open→assigned→done` with no gaps and `replay` rebuilds all-DONE (VSWARM-01/11); no nudge file.

## Task Commits

Not committed by me. Per the operator's git-safety rule (no git write actions without explicit confirmation), work is staged in the working tree only. `git diff --check` clean. Commit when ready.

## Files Created/Modified
- `tests/test_swarm_e2e.py` — the single 2-builder enforced e2e integration test.
- `crates/voss-app-core/src/agent_registry.rs` — **restored** the V25-03 swarm work (`get_active_agents` row mapper, `row_to_entry`, `list_agents_by_swarm`, camelCase test literal, 9-arg `register_agent` call sites, 2 swarm tests) that a concurrent edit had partially reverted; the file no longer compiled.

## Decisions Made
- Ownership enforcement exercised through the real policy + escalation wiring (FAKE_TURN runs no tools, so the gate is driven directly from the builder's assigned `swarm_policy`).
- Zero-turns proof isolated in `asyncio.run` to keep the `asyncio.Event` bound to the awaiting loop.

## Deviations from Plan

**[Rule 3 - Blocking] Restored reverted V25-03 Rust changes**
- **Found during:** Task 1 (final-suite verification)
- **Issue:** `cargo test -p voss-app-core agent_registry` failed to compile (E0061/E0063/E0432): a concurrent edit had reverted `get_active_agents`/`list_agents_by_swarm`/the test call sites to their pre-V25-03 form while keeping the new `AgentEntry` fields + 9-arg `register_agent`, leaving the crate inconsistent.
- **Fix:** Re-applied `row_to_entry` + the 10-column `get_active_agents` map + `list_agents_by_swarm` + camelCase literal fields + 9-arg test call sites + the 2 swarm tests.
- **Verification:** `cargo test -p voss-app-core agent_registry` → 11 passed; `cargo check -p voss-app` clean.

---

**Total deviations:** 1 (1 blocking restore). **Impact:** Necessary to keep the Rust crate compiling; no scope creep — restores exactly the V25-03 surface.

## Issues Encountered
None beyond the restore above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **Phase V25 complete.** All 11 requirements (VSWARM-01..11) implemented across plans 01–06 and verified; the 2-builder enforced e2e is green.
- Suite status: 31 swarm/server python tests + e2e pass; 11 agent_registry rust tests pass; voss-app crate compiles.
- Deferred per SPEC (out of V25 scope): V24 swarmReconcile event-vocab change, voss-app swarm spawn UI, coordinator decomposition-quality evals.
- **Pending git action:** all task + summary commits across V25-01..06 deferred to the operator per git-safety rule.

---
*Phase: V25-server-native-swarm-runtime*
*Completed: 2026-06-17*

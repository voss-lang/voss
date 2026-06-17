---
phase: V25-server-native-swarm-runtime
plan: 05
subsystem: api
tags: [swarm, permissions, ownership, recall, escalation, decisions, server, fastapi]

# Dependency graph
requires:
  - phase: V25-01
    provides: build_ownership_policy, scoped_recall, SwarmStore
  - phase: V25-04
    provides: /swarm routes, app.state.swarm_store, _run_turn gate build, per-role spawn, assign branch
provides:
  - ownership-deny policy injected into the per-turn PermissionGate (project_policy=session.swarm_policy)
  - swarm.needs_operator escalation on write denial, answerable via existing /session/{id}/permission Future bridge
  - task-scoped recall injection into swarm builder turns (_swarm_recall_text)
  - SwarmStore.record_gate_decision writing .voss/decisions/*.md
affects: [V25-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ownership enforced via deny-wins project_policy layer (fires before mode/auto_yes — auto cannot bypass)"
    - "Denial escalation wraps gate.check in a closure (no PermissionGate subclass) + reuses the permission Future bridge"
    - "Decision audit is create-exclusive (open 'x') with a unique date-slug filename"

key-files:
  created: []
  modified:
    - voss/harness/server/app.py
    - voss/harness/swarm_store.py
    - tests/harness/server/test_swarm_routes.py

key-decisions:
  - "swarm_policy attached at ASSIGN time (when owned_files are known), not at spawn — _run_turn reads it after the gate unblocks"
  - "On denial, emit BOTH swarm.needs_operator (swarm plane) and a paired PermissionUpdated carrying the req id so the existing client answer channel resolves it"
  - "Operator approve (a/A/y) overrides to allow + records ownership_override; otherwise keeps deny + records ownership_denied"
  - "build_ownership_policy now allows both `a.py` and `./a.py` forms so an owned file is never falsely denied (Pitfall 1); blanket '*':'deny' still catches all non-owned forms"
  - "Decision recording uses a fresh SwarmStore(session.cwd) in the gate wrapper — cwd-scoped file write needs no in-memory state"

patterns-established:
  - "Per-turn swarm augmentations factored into module helpers (_apply_swarm_escalation, _swarm_recall_text) for direct unit testing"

requirements-completed: [VSWARM-05, VSWARM-07, VSWARM-10]

# Metrics
duration: ~20 min
completed: 2026-06-17
---

# Phase V25 Plan 05: Ownership Enforcement + Operator Escalation + Scoped Recall + Decision Audit Summary

**Builder writes are hard-walled to ownedFiles at the deny-wins gate; a denial escalates as swarm.needs_operator answerable through the existing /permission bridge; each builder turn's recall is filtered to its ownedFiles; and reviewer/ownership gate outcomes write a .voss/decisions/*.md audit.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-06-17
- **Tasks:** 2 (both TDD)
- **Files:** 2 modified + 1 test file extended

## Accomplishments
- VSWARM-05: `_run_turn` passes `project_policy=session.swarm_policy` into the gate; a builder owning `a.py` is allowed `a.py`/`./a.py` and denied `b.py`/`./b.py` for fs_write/fs_edit/fs_edit_many — deny fires before mode/auto_yes (auto cannot bypass). `build_ownership_policy` now allows both normalized and `./` forms (Pitfall 1).
- VSWARM-10 escalation: `_apply_swarm_escalation` wraps `gate.check`; on a WRITE denial it registers a pending Future, emits `swarm.needs_operator` + a paired `PermissionUpdated` (req id), and blocks — the operator answers via the existing `POST /session/{id}/permission`. Approve overrides to allow; the outcome writes a decision audit.
- `swarm_policy` is attached in the assign branch (`build_ownership_policy(task.owned_files)`) so it's ready when the gated builder's turn unblocks.
- VSWARM-07: `_swarm_recall_text` runs `scoped_recall` over `MemoryStore.recall` and injects only ownedFiles-scoped hits as `code_recall_text`; non-swarm turns keep the unscoped `_render_code_recall_text` path.
- VSWARM-10 audit: `SwarmStore.record_gate_decision` writes a create-exclusive `.voss/decisions/<date>-slug.md` with `confidence`/`related_session`/`swarm_id`/`task_id`/`gate_type` frontmatter; called on reviewer reject (message route) and resolved ownership gates.

## Task Commits

Not committed by me. Per the operator's git-safety rule (no git write actions without explicit confirmation), work is staged in the working tree only. `git diff --check` clean. Commit when ready.

## Files Created/Modified
- `voss/harness/server/app.py` — gate `project_policy` injection + `_apply_swarm_escalation` + `_swarm_recall_text`; scoped-recall branch in `_run_turn`; `swarm_policy` set at assign; reviewer-reject decision recording in the message route; `build_ownership_policy` import; `SwarmMessageBody.confidence`.
- `voss/harness/swarm_store.py` — `build_ownership_policy` `./`-form allow; `record_gate_decision`.
- `tests/harness/server/test_swarm_routes.py` — 4 new tests (ownership deny, operator escalation, scoped recall, reviewer-reject decision).

## Decisions Made
- Escalation wraps `gate.check` (no subclass) and reuses the permission Future bridge — minimal, matches SPEC reuse constraint.
- Dual emit (swarm.needs_operator + PermissionUpdated) so the swarm plane signals and the existing answer channel carries the id.

## Deviations from Plan

None - plan executed exactly as written.

(Within scope: decision recording in the gate wrapper builds a fresh `SwarmStore(session.cwd)` rather than threading `app.state` through `_run_turn` — cwd-scoped file write needs no in-memory swarm state.)

## Issues Encountered
None. Regression: `test_server_app.py` + `test_permissions.py` + all V25 swarm tests = 33 passed (only pre-existing Starlette/httpx deprecation warning). Non-swarm turn parity preserved (project_policy=None when not a swarm builder).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Enforcement + human-in-the-loop loop closed: ownership wall, escalation, scoped recall, decision audit all live.
- V25-06 (final phase plan) can build the 2-builder enforced E2E integration test on the full surface.
- **Pending git action:** task + summary commits deferred to the operator per git-safety rule.

---
*Phase: V25-server-native-swarm-runtime*
*Completed: 2026-06-17*

---
phase: V12-safety-factory-fallbacks
plan: 02
subsystem: api
tags: [python, permission-gate, safety, confirmation, runbook-routing, auto-yes]

# Dependency graph
requires:
  - phase: V12-01
    provides: SafetyConfig + classify/decide pure classifier
provides:
  - PermissionGate safety overlay (safety_policy/safety_actor/safety_confirm_fn) running before mode/prompt
  - VSAFE-01 exact-action confirmation (auto_yes cannot bypass) via SafetyConfirmRequest/build_confirm_request/confirmation_matches
  - VSAFE-02/03/04 route-or-deny: dangerous/factory/latency/scaffold ops blocked from direct execution
  - live cli.py do/chat gate wiring (bundle.safety → gate.safety_policy)
affects: [V12-03 (audit marker), V12 EM parity (team.py gate_for_role)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Safety overlay evaluated in _check_impl AFTER project-policy deny, BEFORE net/mode/prompt — so auto_yes/auto cannot suppress it"
    - "Confirmed irreversible → return None (proceed to normal gate); routed dangerous op → (False, reason) blocking direct execution"
    - "Exact-action confirmation: injected fn must echo SafetyConfirmRequest.exact_action verbatim"

key-files:
  created:
    - tests/harness/test_safety_gate.py
  modified:
    - voss/harness/safety.py
    - voss/harness/permissions.py
    - voss/harness/cli.py

key-decisions:
  - "Confirmed irreversible actions PROCEED to the existing mode/project gate (per acceptance); routing/deny only applies to non-irreversible dangerous ops"
  - "Routing always BLOCKS direct execution in V12 (no runbook executor yet); empty-steps runbook → 'no defined procedure' deny"
  - "Project-policy deny precedence preserved (safety runs after project deny check)"
  - "DEVIATION: wired cli.py do/chat gates (not in files_modified) for a live hookup; did NOT modify agent.py (denials already surface via _invoke_step_with_gate); team.py gate_for_role safety inheritance deferred to the EM-parity plan (VSAFE-07)"

patterns-established:
  - "PermissionGate._safety_check() → None (continue) | (False, reason) (deny/route)"
  - "_interactive_safety_confirm prints risk summary + exact action, reads re-typed confirmation"

requirements-completed: [VSAFE-01, VSAFE-02, VSAFE-03, VSAFE-06]

# Metrics
duration: 17min
completed: 2026-06-07
---

# Phase V12 Plan 02: Runtime Safety Gate Summary

**PermissionGate safety overlay: classified irreversible actions require exact-action confirmation (auto_yes cannot bypass), and dangerous/factory/latency/scaffold operations are routed-or-denied before direct execution — ordinary operations keep the existing gate behavior.**

## Performance

- **Duration:** ~17 min
- **Completed:** 2026-06-07
- **Tasks:** 2 (both auto)
- **Files created:** 1 (test); **modified:** 3 (safety, permissions, cli)

## Accomplishments
- `safety.py` — `SafetyConfirmRequest` + `build_confirm_request` (risk summary + exact action) + `confirmation_matches` (verbatim echo) + `exact_action_text`.
- `permissions.py` — `PermissionGate` gains `safety_policy`/`safety_actor`/`safety_confirm_fn`; `_safety_check()` runs after project-policy deny, before net/mode/prompt. Irreversible → confirm-or-deny (auto_yes ignored for this path); dangerous/factory → runbook route-deny; empty runbook → "no defined procedure" deny; latency → fixed-pipeline deny; scaffold → deny. Confirmed irreversible returns None → proceeds to normal gate.
- `cli.py` — `do` and `chat` gates now receive `bundle.safety` (live runtime hookup, mirrors `project_policy`).

## Files Created/Modified
- `tests/harness/test_safety_gate.py` — 12 tests (140+ lines)
- `voss/harness/safety.py` — confirmation contract helpers
- `voss/harness/permissions.py` — gate overlay
- `voss/harness/cli.py` — do/chat safety wiring

## Decisions Made
See `key-decisions` frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Wiring location] cli.py instead of agent.py**
- **Found during:** Task 2 integration — the runtime gate is constructed in `cli.py` (do/chat), not `agent.py`. `agent.py::_invoke_step_with_gate` already surfaces `<denied: ...>` and records capability denial for any gate deny, so no agent.py change is needed for safety denials to flow.
- **Fix:** Wired `bundle.safety` into the two `cli.py` gate constructions (2 lines, mirroring the existing `project_policy` line). Left `agent.py` untouched (surgical).
- **Verification:** import check + full permissions/capability/team-gate suites green.

**2. [Deferred] team.py gate_for_role safety inheritance**
- EM-dispatched worker gates (`team.py::gate_for_role`) do not yet inherit `safety_policy`; that is VSAFE-07 (EM parity), an explicitly later plan. Documented, not implemented here.

---

**Total deviations:** 2 (1 wiring-location auto-fix, 1 documented deferral). **Impact:** Feature is live for direct `do`/`chat`; EM parity is a later plan by design.

## Issues Encountered
None.

## Verification
- `.venv/bin/python -m pytest tests/harness/test_safety_gate.py tests/harness/test_permission_rules.py -q` → **all green** (gate: 12 — auto_yes-cannot-bypass, matching/non-matching confirmation, request carries risk+exact-action, runbook route blocks execution, empty-runbook deny, latency pipeline only-when-configured, unclassified unchanged w/ and w/o policy, project-deny precedence, weak-model scaffold cheap-block/strong-exempt)
- `test_safety_policy + test_permissions + test_permissions_modes + test_capability_invocation_audit + test_allow_net + test_edit_cmd + test_cognition + test_team_gate_compile` → **all green** (no regression; safety overlay additive)
- `import voss.harness.cli` OK

## Next Phase Readiness
- Gate emits safety-routed denials; next plan (VSAFE-05) records factory-fallback audit evidence via `recorder.observe_factory_fallback()` at the `_invoke_step_with_gate` boundary.
- EM parity (VSAFE-07) wires `safety_policy`/`safety_actor` through `team.py::gate_for_role`.

---
*Phase: V12-safety-factory-fallbacks*
*Completed: 2026-06-07*

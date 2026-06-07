---
phase: V12-safety-factory-fallbacks
plan: 04
subsystem: api
tags: [python, safety, em, role-gate, weak-model-scaffold, cage, parity]

# Dependency graph
requires:
  - phase: V12-03
    provides: factory-fallback audit wiring + SafetyClassification actor fields
provides:
  - gate_for_role() preserves safety_policy/safety_confirm_fn + role-specific SafetyActorContext
  - _model_tier_for_spec() tier resolution (keyword, reverse lookup, built-in defaults)
  - EMBoardHandle._role_spec() + _derive_role_gate() (dispatch_card path, testable)
  - EM/direct safety decision parity tests (test_direct_and_em_role_gate_share_safety_decision)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Derived role gates preserve safety_policy object identity like project_policy"
    - "safety_actor is role-specific (spec.id + resolved tier); base actor is NOT inherited"
    - "EM dispatch deduped through _derive_role_gate(); cage APIs unchanged"

key-files:
  created:
    - tests/harness/em/test_safety_policy_inheritance.py
  modified:
    - voss/harness/team.py
    - voss/harness/em/handle.py
    - tests/harness/test_team_gate_compile.py

key-decisions:
  - "Model tier resolution: tier keyword on spec.model → reverse lookup via get_model_tiers() → role_full_defaults() → None"
  - "Private _derive_role_gate() on EMBoardHandle for test parity without widening public API"
  - "Weak-model scaffold classification keys off derived gate actor context only — strong tier exempt"

patterns-established:
  - "gate_for_role(spec, base) → PermissionGate with safety_policy=base.safety_policy, safety_actor=SafetyActorContext(role=spec.id, model_tier=...)"

requirements-completed: [VSAFE-04, VSAFE-07]

# Metrics
duration: 25min
completed: 2026-06-07
---

# Phase V12 Plan 04: EM Safety Policy Parity Summary

**EM-dispatched worker gates inherit the same safety policy as direct harness tool calls, carry role/model-tier actor context for weak-model scaffold rules, and produce identical allow/deny/route decisions — with the EM cage unchanged.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-06-07
- **Tasks:** 3 (all auto, orchestrated via subagents)
- **Files created:** 1 (test); **modified:** 3 (team, handle, team-gate compile tests)

## Accomplishments

- `team.py` — `_model_tier_for_spec()` resolves tier from keyword, configured model-id reverse lookup, or built-in role defaults. `gate_for_role()` now preserves `safety_policy` and `safety_confirm_fn` from the base gate and sets role-specific `SafetyActorContext`.
- `em/handle.py` — `_role_spec()` + `_derive_role_gate()` encapsulate the `dispatch_card` gate derivation path; `dispatch_card` uses them (no duplication).
- `test_safety_policy_inheritance.py` — 16 tests (228 lines): policy identity, weak-model scaffold by tier, factory routing parity, EM dispatch derivation parity (`test_direct_and_em_role_gate_share_safety_decision`), cage introspection.
- `test_team_gate_compile.py` — two new tests for safety policy preservation and actor role/tier on derived gates.

## Files Created/Modified

- `tests/harness/em/test_safety_policy_inheritance.py` — new EM/direct parity suite
- `voss/harness/team.py` — `_model_tier_for_spec`, safety inheritance in `gate_for_role`
- `voss/harness/em/handle.py` — `_role_spec`, `_derive_role_gate`, dispatch refactor
- `tests/harness/test_team_gate_compile.py` — safety policy + actor tests

## Decisions Made

See `key-decisions` frontmatter.

## Deviations from Plan

None. All acceptance criteria met without scope creep.

## Issues Encountered

None. Full V12 focused suite and EM harness suite green on local Python.

## Verification

- `.venv/bin/python -m pytest tests/harness/test_safety_policy.py tests/harness/test_safety_gate.py tests/harness/test_factory_fallback_audit.py tests/harness/em/test_safety_policy_inheritance.py tests/harness/test_permission_rules.py tests/harness/test_capability_invocation_audit.py tests/harness/test_team_gate_compile.py -q` → **green**
- `.venv/bin/python -m pytest tests/harness/em/ -q` → **95 passed**
- `.venv/bin/python -m pytest tests/harness/test_team_gate_compile.py tests/harness/em/test_safety_policy_inheritance.py -q` → **34 passed**

## VSAFE Coverage (phase complete)

| ID | Plan | Status |
|----|------|--------|
| VSAFE-01 | V12-02 | confirmation gate |
| VSAFE-02 | V12-01/02 | factory routing |
| VSAFE-03 | V12-01/02 | latency pipelines |
| VSAFE-04 | V12-01/04 | weak-model scaffolds (classifier + role-gate actor context) |
| VSAFE-05 | V12-03 | factory-fallback audit |
| VSAFE-06 | V12-01/02 | project-local policy |
| VSAFE-07 | V12-04 | EM/direct safety parity |

## Next Phase Readiness

V12 safety-factory-fallbacks is complete. EM-dispatched workers now hit the same safety overlay as direct tool calls; factory-fallback audit rows from V12-03 will record actor role/tier from derived gates on routed operations.

---
*Phase: V12-safety-factory-fallbacks*
*Completed: 2026-06-07*

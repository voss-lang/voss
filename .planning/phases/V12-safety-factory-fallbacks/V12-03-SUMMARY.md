---
phase: V12-safety-factory-fallbacks
plan: 03
subsystem: api
tags: [python, audit, recorder, run-record, redaction, back-compat, factory-fallback]

# Dependency graph
requires:
  - phase: V12-02
    provides: PermissionGate safety overlay + SafetyClassification (classify)
provides:
  - RunRecorder.observe_factory_fallback() + RunRecorder/RunRecord factory_fallbacks field
  - agent.py wiring: every strict-procedure route records redacted factory-fallback evidence
  - AuditReport.factory_fallbacks marker field (default empty → old snapshots hydrate)
affects: [V12 EM parity (VSAFE-07), V11 ADE audit consumption]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive audit row with telemetry.redact_tool_args; never raises (mirrors observe_capability)"
    - "Re-classify in agent._invoke_step_with_gate to record fallback for both allowed (confirmed) and denied routes"
    - "Frozen RunRecord key allow-list test forces credential review of every new field"

key-files:
  created:
    - tests/harness/test_factory_fallback_audit.py
  modified:
    - voss/harness/recorder.py
    - voss/harness/session.py
    - voss/harness/audit/model.py
    - voss/harness/agent.py
    - tests/harness/test_session_redaction.py

key-decisions:
  - "Factory fallback recorded for EVERY matched strict route (confirmed-irreversible allowed AND routed/denied) — outcome 'allowed'|'denied', confirmed flag derived from allowed & requires_confirmation"
  - "agent re-runs safety.classify (pure, cheap) to get classification metadata since gate.check returns only a reason string"
  - "AuditReport.factory_fallbacks defaulted () — model marker surface; builder population deferred (builder reads session tree, not run records)"
  - "Updated test_session_redaction allow-list (24→25 fields) — the test's purpose is to force review of each persisted field; factory_fallbacks args are redacted"

patterns-established:
  - "observe_factory_fallback(name, *, label, classes, trigger_rule, runbook, pipeline, actor_role, actor_model_tier, confirmation_required, confirmed, outcome, args)"

requirements-completed: [VSAFE-05]

# Metrics
duration: 18min
completed: 2026-06-07
---

# Phase V12 Plan 03: Factory Fallback Audit Summary

**Every safety strict-procedure route (confirmed irreversible, runbook/pipeline routing, scaffold, or denial) persists redacted audit evidence — classification, trigger rule, runbook/pipeline, actor role/tier, confirmation flags, outcome — additively, with old run records and capability audit semantics unchanged.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-06-07
- **Tasks:** 2 (both auto)
- **Files created:** 1 (test); **modified:** 4 (recorder, session, audit/model, agent) + 1 (redaction allow-list test)

## Accomplishments
- `recorder.py` — `factory_fallbacks` field + `observe_factory_fallback()` (redacts args via telemetry, never raises); `finalize()` forwards the list to `RunRecord`.
- `session.py` — `RunRecord.factory_fallbacks` additive field (back-compat default `[]`).
- `audit/model.py` — `AuditReport.factory_fallbacks` marker field (default `()` → old snapshots hydrate).
- `agent.py` — `_invoke_step_with_gate` re-classifies via `safety.classify` when a safety policy is attached and records one fallback row per matched route (allowed-confirmed or denied), alongside the existing capability row.

## Files Created/Modified
- `tests/harness/test_factory_fallback_audit.py` — 11 tests (120+ lines)
- `voss/harness/recorder.py` — field + observe_factory_fallback + finalize
- `voss/harness/session.py` — RunRecord field
- `voss/harness/audit/model.py` — AuditReport marker field
- `voss/harness/agent.py` — invocation-path wiring
- `tests/harness/test_session_redaction.py` — allow-list 24→25 (field-review gate)

## Decisions Made
See `key-decisions` frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Required test update] test_session_redaction allow-list**
- **Found during:** Task 1 — `test_run_record_top_level_keys` is a frozen allow-list asserting every RunRecord field has been credential-reviewed; the additive `factory_fallbacks` field tripped it by design.
- **Fix:** Added `factory_fallbacks` to the expected set + bumped the field count 24→25. The field's args are redacted via `telemetry.redact_tool_args` (test_factory_fallback_audit asserts no secret leakage).
- **Files modified:** tests/harness/test_session_redaction.py
- **Verification:** test_session_redaction + roundtrip + net_telemetry hydration tests green.

---

**Total deviations:** 1 auto-fixed (required test-gate update). **Impact:** Expected for any new persisted field; no scope creep.

## Issues Encountered
- Pre-existing unrelated failure: `test_session_iterations.py::test_exit_reasons_constant_is_authoritative` (EXIT_REASONS contains timeout/killed/error not in the test's expected set). Confirmed independent of this plan — fails identically with my session.py/redaction edits stashed; `EXIT_REASONS` is untouched here. Left as-is (Rule 3: do not fix unrelated pre-existing failures).

## Verification
- `.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py tests/harness/test_capability_invocation_audit.py tests/harness/test_session_redaction.py -q` → **green** (factory: 11 — full-event append, secret redaction, never-raises, finalize forward, RunRecord default empty, **old-record hydration**, safety-denied records both rows, normal call no fallback, no-policy no fallback, AuditReport marker field)
- `test_safety_policy + test_safety_gate + tests/harness/audit + test_session_roundtrip + test_net_telemetry` → **green** (no regression)

## Next Phase Readiness
- Factory-fallback evidence is persisted on every route; the AuditReport marker field is ready for the V9/ADE builder to populate from run records in a later plan.
- EM parity (VSAFE-07) will exercise this same `observe_factory_fallback` path for EM-dispatched workers once `team.py::gate_for_role` inherits the safety policy/actor.

---
*Phase: V12-safety-factory-fallbacks*
*Completed: 2026-06-07*

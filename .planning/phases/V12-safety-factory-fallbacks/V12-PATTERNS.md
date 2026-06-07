# Phase V12: Safety & Factory Fallbacks - Pattern Map

**Mapped:** 2026-06-06
**Status:** Complete

## Planned Files and Closest Analogs

| Planned file | Role | Closest analogs | Notes |
|--------------|------|-----------------|-------|
| `voss/harness/safety.py` | New pure policy/classifier/decision module | `voss/harness/permissions.py`, `voss/harness/cognition_schemas.py` | Keep pure functions testable; runtime integrations call into this module. |
| `voss/harness/cognition_schemas.py` | Strict `.voss/safety.yml` schema | `PermissionsConfig`, `ToolPolicy`, `ValidationConfig` | Use Pydantic `extra="forbid"` and default empty lists for back-compat. |
| `voss/harness/cognition.py` | Load project safety file | existing `.voss/permissions.yml` loader | Add optional `safety` field to bundle; missing file is not an error. |
| `voss/harness/permissions.py` | Safety-aware permission gate | existing project-policy deny/allow/ask layering | Safety must run before mode/prompt shortcuts and must not be bypassed by `auto_yes`. |
| `voss/harness/agent.py` | Tool dispatch integration | `_invoke_step_with_gate()` capability-audit calls | The tool invocation site already records denial/success; attach factory fallback audit here. |
| `voss/harness/recorder.py` | Factory fallback evidence | `observe_capability()` | Add separate `observe_factory_fallback()`; do not alter existing capability row semantics. |
| `voss/harness/session.py` | Backward-compatible run field | additive `capability_invocations` pattern | Add default list field and hydration defaults for old records. |
| `voss/harness/team.py` | Role gate inheritance | `gate_for_role()` preserving `project_policy`/`allow_net` | Preserve `safety_policy` and annotate actor role/model tier. |
| `tests/harness/test_safety_policy.py` | Policy/classifier tests | `tests/harness/test_permission_rules.py`, `tests/harness/test_cognition_schemas.py` | Validate strict schemas, classifier, unknown runbook refs. |
| `tests/harness/test_safety_gate.py` | Runtime gate tests | `tests/harness/test_permission_rules.py`, `tests/harness/test_capability_invocation_audit.py` | Use injected prompt/confirmation functions; no real stdin. |
| `tests/harness/test_factory_fallback_audit.py` | Audit persistence tests | `tests/harness/test_capability_invocation_audit.py`, `tests/harness/test_session_redaction.py` | Assert additive field, redaction, old JSON hydration. |
| `tests/harness/em/test_safety_policy_inheritance.py` | EM parity tests | `tests/harness/test_team_gate_compile.py`, `tests/harness/em/conftest.py` | Prove role gates inherit safety and actor context. |

## Code Excerpts to Reuse

### Permission Rule Precedence

`PermissionGate._check_impl()` already establishes the pattern for strict early checks:

- project-policy deny before session mode
- network gate before mode
- mode-tier denial before prompts
- project allow only within mode

V12 safety checks should follow this style: deny/route/confirmation rules are evaluated before normal prompt suppression.

### Capability Audit

`RunRecorder.observe_capability()` redacts args and never raises. Factory fallback auditing should copy that resilience:

- catch malformed args
- redact before persistence
- keep metadata when `audit_behavior` says args are unsafe

### Role Gate Derivation

`team.py::gate_for_role()` returns a new `PermissionGate` with narrowed mode and preserved project policy. V12 should preserve the same safety policy and attach role/model-tier context without widening permissions.

## Data Flow

1. `cognition.py` loads `.voss/safety.yml` into a strict config object.
2. CLI entry points attach `safety_policy` to the base `PermissionGate`.
3. `gate_for_role()` derives per-role gates that keep the safety policy and actor context.
4. `_invoke_step_with_gate()` calls `gate.check()` with `ToolEntry` metadata.
5. Safety decision returns allow/deny/confirm/runbook/scaffold metadata.
6. `RunRecorder.observe_factory_fallback()` persists strict-procedure evidence.

## Patterns Complete

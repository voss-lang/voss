# Phase V12: Safety & Factory Fallbacks - Research

**Researched:** 2026-06-06
**Status:** Complete
**Question:** What do I need to know to plan V12 well?

## Summary

V12 should land as a small safety overlay, not a replacement for permissions or a new workflow engine. The lowest-risk path is:

1. Add a strict project-local `.voss/safety.yml` schema plus a pure classifier/decision module.
2. Thread the resulting safety policy through the existing `PermissionGate` and `_invoke_step_with_gate` site.
3. Persist additive factory fallback audit events through `RunRecorder`/`RunRecord`.
4. Prove EM-dispatched role gates inherit the same safety policy and role/tier context as direct tool calls.

This matches the SPEC boundary: policy + audit first, named deterministic runbook/fixed-pipeline routing, no broad DSL, no real production integrations, and no rollback semantics.

## Existing Seams

### Permissions

`voss/harness/permissions.py` is the central decision point before a tool runs.

- `PermissionGate.check()` receives `tool_name`, `args`, `is_mutating`, and `is_network`.
- `project_policy` currently holds `.voss/permissions.yml` as `PermissionsConfig`.
- Existing precedence is strict: project deny wins first, net gate follows, then mode gate, diff preview, scope check, and prompt.
- `auto_yes` suppresses normal prompts, so V12 must explicitly bypass that suppression for safety-classified irreversible actions.

Good seam: add a separate safety policy field to `PermissionGate` and evaluate it before mode/prompt short-circuits. Do not overload `.voss/permissions.yml` rules because those are allow/ask/deny ergonomics, not factory routing.

### Tool Invocation

`voss/harness/agent.py::_invoke_step_with_gate()` is the only per-step dispatch site for the normal harness loop.

- Resolves `ToolEntry`.
- Calls `gate.check(...)`.
- Records capability audit on denial, exception, and success.
- Invokes the actual tool only after gate approval.

Good seam: keep execution in this function, but make safety decisions visible enough that runbook/factory outcomes and confirmations can be audited through the existing recorder.

### Tool Metadata

`voss/harness/tools.py::ToolEntry` already carries the fields V12 needs:

- `name`
- `is_mutating`
- `is_network`
- `group`
- `scope_requirements`
- `audit_behavior`

Good seam: classify from tool metadata plus args. Do not add a tenth capability group; the existing `CAPABILITY_GROUPS` tuple is explicitly locked.

### Project Config

`voss/harness/cognition_schemas.py` contains strict Pydantic schemas for `.voss/*.yml`.
`voss/harness/cognition.py` loads `.voss/permissions.yml` and other project config into a bundle used by CLI entry points.

Good seam: add `SafetyConfig` under cognition schemas and load `.voss/safety.yml` into the same bundle. Strict schema validation matches existing project-config behavior.

### Audit

`voss/harness/recorder.py::RunRecorder.observe_capability()` records per-capability rows. `voss/harness/session.py::RunRecord` is a fixed-field dataclass with additive fields allowed when defaults preserve old JSON compatibility.

Good seam: add a separate `factory_fallbacks` list to `RunRecorder` and `RunRecord`, plus `observe_factory_fallback(...)`. Keep capability invocation rows unchanged so existing tests remain stable.

### EM / Role Gates

`voss/harness/team.py::gate_for_role()` derives a per-role `PermissionGate` from a base gate and preserves `project_policy`. `voss/harness/em/handle.py::dispatch_card()` derives `role_gate = gate_for_role(spec, self._base_gate)` before dispatching subagent work.

Good seam: preserve the same safety policy in `gate_for_role()` and add actor role/model-tier context to the role gate. That lets a worker's tool call hit the same safety decision path as a direct tool call while still allowing weak-model scaffold rules to key off role/tier.

## Recommended Model

### New Safety Data Types

Create `voss/harness/safety.py` with pure types/functions:

- `SafetyConfig`
- `SafetyRule`
- `SafetyRunbook`
- `SafetyActorContext`
- `SafetyClassification`
- `SafetyDecision`
- `SafetyConfirmationRequest`
- `load_safety_config(path)`
- `classify_operation(policy, tool_name, args, tool_entry, actor)`
- `decide_safety(policy, classification, confirmation_response=None)`

Keep this module pure enough for unit tests. Runtime integrations should call into it rather than embedding command matching in `PermissionGate`.

### Policy Shape

Recommended `.voss/safety.yml` shape:

```yaml
factory_only:
  paths:
    - glob: "infra/prod/**"
      runbook: "prod-change"
      classification: "prod"
  operations:
    - tool: "shell_run"
      pattern: "git push *"
      runbook: "git-push"
      classification: "irreversible"

runbooks:
  git-push:
    steps:
      - "confirm-exact-action"
      - "run-command"

latency_critical:
  - operation: "format-check"
    pipeline: "fmt-check"

weak_model_scaffolds:
  tiers: ["cheap", "fast"]
  operations: ["migration", "prod", "money"]
```

The exact parser can refine names during implementation, but the plan should keep these capabilities:

- path glob matching
- tool/command/operation matching
- classification labels
- named runbook/pipeline references
- strict validation of unknown runbook references

### Runtime Semantics

Decision outcomes should be explicit:

- `allow_normal`: no safety rule matched, continue existing gate behavior.
- `require_confirmation`: irreversible action needs exact confirmation text.
- `route_runbook`: operation must use named runbook/pipeline.
- `scaffold_required`: weak-model role/tier must use scaffolded procedure.
- `deny`: unsafe or invalid route, do not invoke tool.

For V12, runbooks can be deterministic in-process procedures sufficient for tests. They do not need external cloud deploy/payment integrations.

### Confirmation Contract

The confirmation request must include:

- classification
- risk summary
- exact tool/action text
- matching confirmation token or exact phrase

`auto_yes` must not bypass this. In tests, use injected prompt/confirmation functions, not real stdin.

### Audit Shape

Factory fallback events should be additive and redacted:

```json
{
  "tool": "shell_run",
  "classification": "irreversible",
  "trigger_rule": "factory_only.operations[0]",
  "runbook": "git-push",
  "pipeline": null,
  "actor_role": "platform",
  "actor_model_tier": "cheap",
  "confirmation_required": true,
  "confirmed": false,
  "outcome": "denied"
}
```

Do not store raw secrets. Use the same redaction behavior as `observe_capability()`.

## Common Pitfalls

1. Do not add a tenth `ToolEntry.group`. The capability group set is intentionally closed.
2. Do not make `.voss/permissions.yml` carry factory semantics. That file is allow/ask/deny; V12 needs routing and audit metadata.
3. Do not let `auto_yes=True` bypass safety prompts. VSAFE-01 explicitly forbids this for irreversible actions.
4. Do not change existing capability invocation rows in place. Add separate factory fallback evidence.
5. Do not require a real deploy/migration/payment backend. V12 tests should use deterministic local/stub tools and commands.
6. Do not add EM mutation APIs. EM parity should come from inherited role gates, not new EM powers.
7. Do not make scaffold mode global. It applies only when policy matches a role/model tier and operation.

## Validation Architecture

V12 should use focused pytest suites:

- `tests/harness/test_safety_policy.py`: schema validation, unknown runbook refs, path/operation classification.
- `tests/harness/test_safety_gate.py`: irreversible confirmation, `auto_yes` bypass prevention, runbook routing/denial, normal-path non-contamination.
- `tests/harness/test_factory_fallback_audit.py`: recorder/run-record additive fields, redaction, old-record hydration.
- `tests/harness/em/test_safety_policy_inheritance.py`: `gate_for_role()` preserves safety policy and actor context; EM-dispatched and direct tool paths receive identical safety decisions.

Focused verification commands:

- `.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q`
- `.venv/bin/python -m pytest tests/harness/test_safety_gate.py -q`
- `.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py -q`
- `.venv/bin/python -m pytest tests/harness/em/test_safety_policy_inheritance.py -q`

Regression commands:

- `.venv/bin/python -m pytest tests/harness/test_permission_rules.py tests/harness/test_capability_invocation_audit.py tests/harness/test_team_gate_compile.py -q`
- `.venv/bin/python -m pytest tests/harness/em/ -q`

## Research Complete

Planning should split the phase into four executable plans:

1. Safety schema/classifier foundation.
2. Permission/tool invocation safety overlay and confirmation/runbook routing.
3. Factory fallback audit persistence and backward-compatible hydration.
4. EM role/weak-model scaffold parity and regression verification.

## RESEARCH COMPLETE

---
phase: V12-safety-factory-fallbacks
plan: 02
type: execute
wave: 2
depends_on: [V12-01]
files_modified:
  - voss/harness/safety.py
  - voss/harness/permissions.py
  - voss/harness/agent.py
  - tests/harness/test_safety_gate.py
autonomous: true
requirements: [VSAFE-01, VSAFE-02, VSAFE-03, VSAFE-06]
must_haves:
  truths:
    - "`auto_yes` cannot bypass irreversible-action confirmation."
    - "Factory fallback only triggers for matching safety rules; ordinary operations retain existing PermissionGate behavior."
    - "Dangerous operations are routed to named runbooks/pipelines or denied before tool invocation."
  artifacts:
    - path: "tests/harness/test_safety_gate.py"
      provides: "runtime safety gate behavior coverage"
      contains: "test_auto_yes_does_not_bypass_irreversible_confirmation"
      min_lines: 140
---

<objective>
Integrate the V12 safety policy with the runtime tool gate: classified irreversible actions require exact confirmation, dangerous/factory-only operations route through named runbooks or deny before direct execution, and unclassified operations continue through the existing PermissionGate path unchanged.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-SPEC.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-RESEARCH.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-PATTERNS.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-01-PLAN.md
</execution_context>

<tasks>

<task type="auto">
  <name>Task 1: Thread safety policy through PermissionGate</name>
  <files>voss/harness/permissions.py, voss/harness/safety.py, tests/harness/test_safety_gate.py</files>
  <read_first>
    - voss/harness/permissions.py
    - tests/harness/test_permission_rules.py
    - tests/harness/test_allow_net.py
    - tests/harness/test_edit_cmd.py
    - voss/harness/safety.py
  </read_first>
  <action>
    Add optional safety policy and safety actor context fields to `PermissionGate`. Evaluate safety decisions before normal prompt suppression and before the tool can execute. Preserve project-policy deny precedence and network/mode behavior for unclassified operations. Add an injected safety confirmation function for tests and non-TTY handling. Irreversible decisions must require a confirmation response matching the exact action/token from the safety request; non-matching, absent, or non-interactive responses deny the operation. `auto_yes=True` must not skip this confirmation path.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_safety_gate.py tests/harness/test_permission_rules.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `PermissionGate(auto_yes=True, safety_policy=...)` denies a classified irreversible action when no exact confirmation is supplied.
    - A matching injected confirmation allows the classified irreversible action to proceed to the existing mode/project gate path.
    - A non-matching injected confirmation denies the action and includes a safety-specific reason.
    - Unclassified `fs_read`/`fs_write`/`shell_run` behavior remains identical to existing permission-rule tests.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Route dangerous operations through fixed named runbooks/pipelines</name>
  <files>voss/harness/safety.py, voss/harness/permissions.py, voss/harness/agent.py, tests/harness/test_safety_gate.py</files>
  <read_first>
    - voss/harness/agent.py
    - voss/harness/tools.py
    - tests/harness/test_capability_invocation_audit.py
    - tests/harness/test_permissions.py
    - voss/harness/safety.py
  </read_first>
  <action>
    Add fixed named runbook/pipeline decision handling at the gate/tool invocation boundary. A policy-matched deploy/delete/migration/money/prod or latency-critical operation must not directly invoke the requested tool unless the safety decision explicitly allows the runbook/pipeline path. In V12, runbooks can be deterministic local procedures sufficient for tests; if a rule requires a runbook and no valid runbook exists, deny before invocation. Return a clear denial/routing reason so `_invoke_step_with_gate()` surfaces `<denied: ...>` and records the usual capability denial.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_safety_gate.py tests/harness/test_capability_invocation_audit.py tests/harness/test_permissions.py -q</automated>
  </verify>
  <acceptance_criteria>
    - A matched `shell_run` command such as `git push origin main` is not invoked directly when policy requires a runbook.
    - A missing runbook reference denies before tool invocation.
    - A configured latency-critical operation records/returns a fixed-pipeline route only for that configured operation.
    - A normal unclassified read batch still executes and preserves per-step permission checks.
  </acceptance_criteria>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_safety_gate.py -q`
- `.venv/bin/python -m pytest tests/harness/test_permission_rules.py tests/harness/test_capability_invocation_audit.py tests/harness/test_permissions.py -q`
</verification>

<success_criteria>
Classified irreversible actions require exact human confirmation, dangerous/factory-only operations cannot bypass runbook routing, latency-critical rules opt into fixed pipelines, and ordinary tool calls keep current PermissionGate behavior.
</success_criteria>

<output>
Create `.planning/phases/V12-safety-factory-fallbacks/V12-02-SUMMARY.md` when done.
</output>

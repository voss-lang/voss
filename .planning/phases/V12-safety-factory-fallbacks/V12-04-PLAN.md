---
phase: V12-safety-factory-fallbacks
plan: 04
type: execute
wave: 4
depends_on: [V12-03]
files_modified:
  - voss/harness/team.py
  - voss/harness/em/handle.py
  - voss/harness/permissions.py
  - tests/harness/em/test_safety_policy_inheritance.py
  - tests/harness/test_team_gate_compile.py
autonomous: true
requirements: [VSAFE-04, VSAFE-07]
must_haves:
  truths:
    - "EM-dispatched worker gates inherit the same safety policy as direct harness tool calls."
    - "Weak-model scaffold rules key off role/model-tier context without widening permissions."
    - "EM cage remains bounded; V12 adds no ceiling/budget/roster mutation APIs."
  artifacts:
    - path: "tests/harness/em/test_safety_policy_inheritance.py"
      provides: "EM/direct parity and weak-model scaffold tests"
      contains: "test_direct_and_em_role_gate_share_safety_decision"
      min_lines: 120
---

<objective>
Finish V12 by making safety policy apply equally to EM-dispatched worker work and direct harness tool calls. Preserve EM cage invariants, add role/model-tier context for weak-model scaffold rules, and run the focused regression selection.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-SPEC.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-RESEARCH.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-PATTERNS.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-03-PLAN.md
</execution_context>

<threat_model>
T-V12-08 EM bypass: autonomous EM-dispatched work could use a derived role gate that lacks safety policy. Mitigation: `gate_for_role()` preserves safety policy and tests compare direct vs EM-derived decisions.
T-V12-09 Weak-model overreach: cheap/fast role scaffold rules could widen or globally restrict permissions incorrectly. Mitigation: actor-context-only scaffold classification plus existing mode/network cap regression tests.
T-V12-10 Cage regression: adding EM safety context could add new EM mutation APIs. Mitigation: tests assert forbidden EMBoardHandle verbs remain absent.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Preserve safety policy and actor context through role gates</name>
  <files>voss/harness/team.py, voss/harness/permissions.py, tests/harness/test_team_gate_compile.py, tests/harness/em/test_safety_policy_inheritance.py</files>
  <read_first>
    - voss/harness/team.py
    - voss/harness/subagents.py
    - voss/harness/permissions.py
    - tests/harness/test_team_gate_compile.py
    - tests/harness/em/conftest.py
  </read_first>
  <action>
    Extend `PermissionGate`/`gate_for_role()` so derived role gates preserve `safety_policy` and carry `SafetyActorContext` with role id and resolved model tier/model information. The derived gate must continue to cap mode via `_min_mode`, preserve `project_policy`, preserve per-gate network behavior, and never widen permissions. Add tests proving the derived role gate has the same safety policy object and actor role/tier context.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_team_gate_compile.py tests/harness/em/test_safety_policy_inheritance.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `gate_for_role()` preserves `safety_policy` exactly like it preserves `project_policy`.
    - A role with model tier `cheap` or `fast` triggers configured weak-model scaffold classification.
    - A role with model tier `strong` does not trigger weak-model scaffold classification unless explicitly configured.
    - Existing mode cap and network override tests remain green.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Prove EM-dispatched and direct tool paths share safety decisions</name>
  <files>voss/harness/em/handle.py, tests/harness/em/test_safety_policy_inheritance.py</files>
  <read_first>
    - voss/harness/em/handle.py
    - voss/harness/em/loop.py
    - voss/harness/team.py
    - voss/harness/agent.py
    - tests/harness/em/conftest.py
  </read_first>
  <action>
    Add focused EM tests that derive a role gate through the same path used by `EMBoardHandle.dispatch_card()` and compare its safety decision with a direct base-gate tool call for the same dangerous operation. If production code must expose a small helper for deriving the role gate/toolset, keep it private or module-local and do not add EM APIs for mutating ceiling, p, budget, roster, or gates. Confirm safety denial/routing outcomes match for direct and EM role gates.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/em/test_safety_policy_inheritance.py -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/em/ -q</automated>
  </verify>
  <acceptance_criteria>
    - `test_direct_and_em_role_gate_share_safety_decision` proves the same dangerous operation receives the same allow/deny/route decision through base and EM-derived gates.
    - `EMBoardHandle` still has no `set_ceiling`, `set_p`, `set_budget`, `extend_budget`, `register_role`, `register_agent`, or `mutate_team_config` API.
    - Focused EM regression tests pass.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Run full V12 regression selection</name>
  <files>tests/harness/test_safety_policy.py, tests/harness/test_safety_gate.py, tests/harness/test_factory_fallback_audit.py, tests/harness/em/test_safety_policy_inheritance.py</files>
  <read_first>
    - .planning/phases/V12-safety-factory-fallbacks/V12-VALIDATION.md
    - .planning/phases/V12-safety-factory-fallbacks/V12-SPEC.md
  </read_first>
  <action>
    Run the full V12 focused suite and existing adjacent regressions listed in V12-VALIDATION.md. If local Python version exposes unrelated pre-existing EM event-loop failures, record the exact failure and still run the V12-focused files to completion.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_safety_policy.py tests/harness/test_safety_gate.py tests/harness/test_factory_fallback_audit.py tests/harness/em/test_safety_policy_inheritance.py tests/harness/test_permission_rules.py tests/harness/test_capability_invocation_audit.py tests/harness/test_team_gate_compile.py -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/em/ -q</automated>
  </verify>
  <acceptance_criteria>
    - V12 focused tests pass.
    - Existing permission, capability-audit, team-gate, and EM cage regressions pass or any pre-existing local-environment failure is documented in `V12-04-SUMMARY.md`.
    - All VSAFE-01 through VSAFE-07 requirement IDs are covered by at least one completed plan summary.
  </acceptance_criteria>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_safety_policy.py tests/harness/test_safety_gate.py tests/harness/test_factory_fallback_audit.py tests/harness/em/test_safety_policy_inheritance.py tests/harness/test_permission_rules.py tests/harness/test_capability_invocation_audit.py tests/harness/test_team_gate_compile.py -q`
- `.venv/bin/python -m pytest tests/harness/em/ -q`
</verification>

<success_criteria>
Safety decisions are identical for direct and EM-dispatched dangerous operations, weak-model scaffold rules work from role/model-tier context, EM cage remains bounded, and the focused V12 regression suite passes.
</success_criteria>

<output>
Create `.planning/phases/V12-safety-factory-fallbacks/V12-04-SUMMARY.md` when done.
</output>

---
phase: V12-safety-factory-fallbacks
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/safety.py
  - voss/harness/cognition_schemas.py
  - voss/harness/cognition.py
  - tests/harness/test_safety_policy.py
autonomous: true
requirements: [VSAFE-02, VSAFE-03, VSAFE-04, VSAFE-06]
must_haves:
  truths:
    - "Safety policy lives in a new project-local `.voss/safety.yml` style file, not in `.voss/permissions.yml`."
    - "Safety schema validation is strict and rejects unknown runbook/pipeline references."
    - "Classifier is pure and testable before runtime PermissionGate integration."
  artifacts:
    - path: "voss/harness/safety.py"
      provides: "SafetyConfig-compatible classifier and decision data types"
      contains: "class SafetyDecision"
      min_lines: 120
    - path: "tests/harness/test_safety_policy.py"
      provides: "policy schema, validation, and classifier tests"
      contains: "test_unknown_runbook_reference_rejected"
      min_lines: 120
---

<objective>
Create the V12 safety policy foundation: strict `.voss/safety.yml` schema, pure classification/decision types, project-config loading, and focused tests. This plan does not integrate runtime enforcement yet; it creates the source-of-truth policy surface used by later plans.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-SPEC.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-RESEARCH.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-PATTERNS.md
</execution_context>

<threat_model>
T-V12-01 Policy spoofing: a malformed or unknown-key `.voss/safety.yml` could silently disable safety rules. Mitigation: strict schema, unknown keys forbidden, missing runbook/pipeline refs fail closed.
T-V12-02 Rule confusion: command/path patterns could classify the wrong operation. Mitigation: deterministic classifier tests for path globs, command patterns, latency rules, and role/tier scaffold rules.
T-V12-03 Permissions conflation: adding factory policy to `.voss/permissions.yml` would blur allow/ask/deny with safety routing. Mitigation: separate safety file and tests proving permissions behavior remains unchanged.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add strict safety policy schema and loader</name>
  <files>voss/harness/safety.py, voss/harness/cognition_schemas.py, voss/harness/cognition.py, tests/harness/test_safety_policy.py</files>
  <read_first>
    - voss/harness/cognition_schemas.py
    - voss/harness/cognition.py
    - tests/harness/test_cognition_schemas.py
    - tests/harness/test_cognition.py
    - .planning/phases/V12-safety-factory-fallbacks/V12-SPEC.md
  </read_first>
  <action>
    Add a new `voss.harness.safety` module with strict Pydantic-compatible policy types for factory-only paths, factory-only operations, named runbooks, latency-critical pipelines, and weak-model scaffolds. Add a `SafetyConfig` field to the project cognition bundle and load `.voss/safety.yml` beside `.voss/permissions.yml`. Missing `.voss/safety.yml` must produce `None` or an empty config without errors. Unknown keys must be rejected. Unknown runbook or pipeline references in rules must produce an actionable validation error naming the missing reference. Keep `.voss/permissions.yml` unchanged.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/test_cognition_schemas.py tests/harness/test_cognition.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/safety.py` defines `SafetyConfig`, `SafetyRule` or equivalent rule types, `SafetyRunbook`, `SafetyActorContext`, `SafetyClassification`, and `SafetyDecision`.
    - `.voss/safety.yml` is loaded through `voss/harness/cognition.py`; missing file does not fail project initialization.
    - Malformed safety files reject unknown keys.
    - A rule referencing a missing runbook or pipeline fails validation with the missing name in the error message.
    - Existing `.voss/permissions.yml` behavior and tests remain unchanged.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Implement pure operation classification</name>
  <files>voss/harness/safety.py, tests/harness/test_safety_policy.py</files>
  <read_first>
    - voss/harness/tools.py
    - voss/harness/permissions.py
    - tests/harness/test_permission_rules.py
    - .planning/phases/V12-safety-factory-fallbacks/V12-RESEARCH.md
  </read_first>
  <action>
    Implement pure classifier functions that accept safety policy, tool name, tool args, tool metadata values, and optional `SafetyActorContext`. Classification must support path globs, tool/command operation patterns, dangerous classes (`irreversible`, `deploy`, `delete`, `migration`, `money`, `prod`), latency-critical fixed-pipeline matches, and weak-model scaffold matches for configured role/model tiers. Return structured classification metadata including classification label, trigger rule id/path, runbook name, pipeline name, actor role, actor model tier, and whether confirmation is required. No tool execution and no prompting in this task.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q</automated>
  </verify>
  <acceptance_criteria>
    - A factory-only path glob such as `infra/prod/**` matches `fs_write` with `path="infra/prod/app.yml"` and returns the configured runbook.
    - A factory-only operation pattern such as `git push *` matches `shell_run` with `cmd="git push origin main"`.
    - A latency-critical rule returns a fixed-pipeline classification only for configured operations.
    - Weak-model scaffold rules match configured `cheap`/`fast` actor tiers and do not match unconfigured `strong` actor tiers.
    - No existing `ToolEntry` capability group is added or renamed.
  </acceptance_criteria>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q`
- `.venv/bin/python -m pytest tests/harness/test_cognition_schemas.py tests/harness/test_cognition.py -q`
</verification>

<success_criteria>
Safety policy loads and validates, classifier output is deterministic and testable, malformed/unknown runbook references fail closed, and no runtime behavior changes before later plans integrate the policy.
</success_criteria>

<output>
Create `.planning/phases/V12-safety-factory-fallbacks/V12-01-SUMMARY.md` when done.
</output>

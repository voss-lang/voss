---
phase: V12-safety-factory-fallbacks
plan: 03
type: execute
wave: 3
depends_on: [V12-02]
files_modified:
  - voss/harness/recorder.py
  - voss/harness/session.py
  - voss/harness/audit/model.py
  - voss/harness/agent.py
  - tests/harness/test_factory_fallback_audit.py
autonomous: true
requirements: [VSAFE-05]
must_haves:
  truths:
    - "Factory fallback evidence is additive and does not alter existing capability invocation row semantics."
    - "Old RunRecord JSON without factory fields remains readable."
    - "Factory fallback audit stores classification metadata and redacted action data, not raw secrets."
  artifacts:
    - path: "tests/harness/test_factory_fallback_audit.py"
      provides: "factory fallback audit persistence and back-compat tests"
      contains: "test_old_run_record_without_factory_fallbacks_hydrates"
      min_lines: 120
---

<objective>
Persist factory fallback evidence for every strict-procedure route. The audit trail must show classification, trigger rule, runbook/pipeline, actor role/tier, confirmation status, and outcome while preserving old session/run compatibility and existing capability audit behavior.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-SPEC.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-RESEARCH.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-PATTERNS.md
@/Users/benjaminmarks/Projects/Voss/.planning/phases/V12-safety-factory-fallbacks/V12-02-PLAN.md
</execution_context>

<threat_model>
T-V12-05 Audit omission: strict-procedure routes could execute or deny without durable evidence. Mitigation: `observe_factory_fallback()` is called on every safety route/denial and verified alongside capability audit rows.
T-V12-06 Secret leakage: factory fallback evidence could persist raw command args or tokens. Mitigation: reuse telemetry redaction patterns and add redaction tests.
T-V12-07 Backward-compat break: adding audit fields could make old run/session JSON unreadable. Mitigation: additive defaults and old-record hydration tests.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add factory fallback recorder and RunRecord field</name>
  <files>voss/harness/recorder.py, voss/harness/session.py, tests/harness/test_factory_fallback_audit.py</files>
  <read_first>
    - voss/harness/recorder.py
    - voss/harness/session.py
    - tests/harness/test_capability_invocation_audit.py
    - tests/harness/test_session_redaction.py
  </read_first>
  <action>
    Add `factory_fallbacks: list[dict]` to `RunRecorder` and `RunRecord` with default empty lists. Add `RunRecorder.observe_factory_fallback(...)` that records tool/action metadata, classification, trigger rule, runbook, pipeline, actor role, actor model tier, confirmation_required, confirmed, outcome, and redacted args/action data. The method must never raise on malformed args and must not store raw secret values. Ensure `RunRecorder.finalize()` forwards the list to `RunRecord`.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py tests/harness/test_capability_invocation_audit.py tests/harness/test_session_redaction.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `RunRecorder.observe_factory_fallback(...)` appends one event with classification, trigger rule, runbook/pipeline, confirmation flags, actor fields, and outcome.
    - Secret-shaped args are redacted using the existing telemetry redaction behavior.
    - Existing `observe_capability()` tests pass without assertion changes.
    - `RunRecorder.finalize()` returns a `RunRecord` with `factory_fallbacks`.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Wire factory fallback audit from tool invocation and audit model</name>
  <files>voss/harness/agent.py, voss/harness/audit/model.py, tests/harness/test_factory_fallback_audit.py</files>
  <read_first>
    - voss/harness/agent.py
    - voss/harness/audit/model.py
    - tests/harness/test_capability_invocation_audit.py
    - voss/harness/safety.py
  </read_first>
  <action>
    When a safety decision causes confirmation denial, runbook routing, fixed-pipeline routing, scaffold routing, or safety denial, call `recorder.observe_factory_fallback(...)` from the tool invocation path. Add a backward-compatible audit model field only if needed by existing audit snapshot code; default it to an empty tuple/list so old audit snapshots still hydrate. Do not remove or mutate capability invocation audit entries.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py tests/harness/test_capability_invocation_audit.py -q</automated>
  </verify>
  <acceptance_criteria>
    - A safety-denied tool call records both the existing capability denial row and one factory fallback row.
    - A normal unclassified successful tool call records no factory fallback row.
    - Old run/session JSON without `factory_fallbacks` hydrates successfully with `factory_fallbacks == []`.
    - Audit output/model exposes a strict-runbook/factory marker for runs with fallback evidence.
  </acceptance_criteria>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py -q`
- `.venv/bin/python -m pytest tests/harness/test_capability_invocation_audit.py tests/harness/test_session_redaction.py -q`
</verification>

<success_criteria>
Every V12 factory fallback is persisted as additive redacted audit evidence, old run records remain readable, and existing capability audit tests stay green.
</success_criteria>

<output>
Create `.planning/phases/V12-safety-factory-fallbacks/V12-03-SUMMARY.md` when done.
</output>

---
phase: O6-audit-calibration-liveness
plan: 06
type: execute
wave: 4
depends_on:
  - O6-03
  - O6-04
  - O6-05
files_modified:
  - voss/harness/audit/leak6.py
  - voss/harness/audit/report.py
  - tests/harness/audit/test_leak6.py
  - tests/harness/audit/test_o6_acceptance.py
  - docs/o6-audit-product.md
requirements:
  - OAUD-07
  - OAUD-08
autonomous: true
---

<objective>
Close the residual-risk register for O6 and prove the end-to-end audit product.

Purpose: Leak-6 must be mitigated or explicitly accepted, and the complete O6 fixture must produce a review artifact plus a gated sign-off path.
</objective>

<context>
@.planning/ORCHESTRATION-PLAN.md
@.planning/phases/O6-audit-calibration-liveness/O6-CONTEXT.md
@.planning/phases/O6-audit-calibration-liveness/O6-RESEARCH.md
@voss/harness/audit/model.py
@voss/harness/audit/report.py
@voss/harness/audit/signoff.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Leak-6 assessment</name>
  <files>voss/harness/audit/leak6.py, tests/harness/audit/test_leak6.py</files>
  <read_first>
    - voss/harness/memory_store.py
    - voss/harness/cognition.py
    - .planning/ORCHESTRATION-PLAN.md
  </read_first>
  <action>
    Implement `assess_leak6(snapshot: AuditSnapshot) -> Leak6Assessment`.

    Behavior:
    - If the snapshot includes a standup-to-semantic-memory write with correction/expiry metadata, report mitigated.
    - If the snapshot includes such a write without correction/expiry metadata, report `accepted_gap` or `blocked` according to fixture status.
    - If no O1-O5 standup memory writer exists, report `accepted_gap` with evidence that no runtime mitigation target is present yet.

    Integrate the assessment into the report and sign-off bucket `leak6`.
  </action>
  <acceptance_criteria>
    - Leak-6 section always appears in audit output.
    - Accepted gap includes evidence and requires sign-off acknowledgement.
    - No runtime memory behavior is changed unless a concrete writer exists and the tests pin the mitigation.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: End-to-end O6 acceptance</name>
  <files>tests/harness/audit/test_o6_acceptance.py, docs/o6-audit-product.md</files>
  <read_first>
    - tests/harness/audit/test_o6_fixtures.py
    - voss/harness/audit/load.py
    - voss/harness/audit/report.py
    - voss/harness/audit/metrics.py
    - voss/harness/audit/signoff.py
  </read_first>
  <action>
    Add an end-to-end test that:
    - builds the deterministic O6 fixture.
    - runs preflight.
    - loads an `AuditSnapshot`.
    - computes metrics.
    - writes Markdown and JSON exports.
    - proves approval is blocked before acknowledgements.
    - adds required acknowledgements.
    - proves approval passes for the same snapshot digest.

    Add `docs/o6-audit-product.md` with a short operator-facing description of the exported artifacts and the sign-off buckets. Keep it factual and avoid roadmap speculation.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/ -q</automated>
    <automated>python -m pytest tests/harness/test_session_redaction.py tests/harness/test_session_tree.py -q</automated>
    <automated>python -m compileall voss/harness/audit</automated>
    <automated>git diff --check</automated>
  </verify>
  <acceptance_criteria>
    - OAUD-01..08 all have passing tests.
    - End-to-end fixture covers killed card, rescope, misroute, reviewer disagreement, timeout, and Leak-6.
    - O6 residual-risk closure is documented as mitigated or accepted with evidence.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
| Threat | Mitigation |
|---|---|
| Leak-6 remains hidden | Report always includes a Leak-6 assessment and sign-off bucket. |
| Accepted gap is mistaken for mitigation | Status value is `accepted_gap`, not `ok`, and docs explain the evidence. |
| O6 passes unit tests but not the user flow | End-to-end acceptance exercises preflight through sign-off on one fixture. |
</threat_model>

<done>
O6 closes or explicitly accepts the residual-risk register, and the full audit product is verified end to end.
</done>

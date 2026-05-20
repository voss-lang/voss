---
phase: O6-audit-calibration-liveness
plan: 05
type: execute
wave: 3
depends_on:
  - O6-03
  - O6-04
files_modified:
  - voss/harness/audit/signoff.py
  - voss/harness/audit/report.py
  - tests/harness/audit/test_signoff_gate.py
requirements:
  - OAUD-04
  - OAUD-03
autonomous: true
---

<objective>
Implement the sign-off forcing function.

Purpose: Prevent rubber-stamp approval by making approval structurally unavailable until high-risk audit sections are acknowledged for the exact snapshot under review.
</objective>

<context>
@.planning/phases/O6-audit-calibration-liveness/O6-CONTEXT.md
@.planning/phases/O6-audit-calibration-liveness/O6-PATTERNS.md
@voss/harness/audit/report.py
@voss/harness/audit/metrics.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Sign-off gate model</name>
  <files>voss/harness/audit/signoff.py, tests/harness/audit/test_signoff_gate.py</files>
  <read_first>
    - voss/harness/audit/model.py
    - voss/harness/audit/report.py
  </read_first>
  <action>
    Implement:
    - `REQUIRED_ACKS = ("killed_cards", "routing_misroutes", "calibration", "liveness", "leak6")`
    - `AuditAcknowledgement`
    - `AuditSignoff`
    - `AuditSignoffGate`

    The gate takes a snapshot digest and acknowledgement records. Approval is allowed only when every required bucket is acknowledged for the current digest. Acknowledgements for older digests must not count.
  </action>
  <acceptance_criteria>
    - Missing any required bucket blocks approval.
    - Wrong snapshot digest blocks approval.
    - Duplicate acknowledgement bucket is stable and does not create double-count behavior.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Persistence and report integration</name>
  <files>voss/harness/audit/signoff.py, voss/harness/audit/report.py, tests/harness/audit/test_signoff_gate.py</files>
  <read_first>
    - voss/harness/audit/report.py
  </read_first>
  <action>
    Add optional sign-off persistence under an audit output directory, not under session-tree node files:
    - `signoff.json`

    Add a report section that lists each required acknowledgement bucket and current status. Do not provide an approve result inside `audit.md` unless the gate is actually satisfied.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/test_signoff_gate.py tests/harness/audit/test_report_export.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `signoff.json` is written only to the caller-provided audit output directory.
    - Approval cannot be persisted until gate passes.
    - Markdown report lists all acknowledgement buckets.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
| Threat | Mitigation |
|---|---|
| Human approves without reviewing risk sections | Gate requires named acknowledgements before approval is possible. |
| Old acknowledgement reused after audit changes | Gate binds acknowledgements to snapshot digest. |
| Sign-off mutates evidence | Sign-off writes to audit output only, not `.voss/sessions/`. |
</threat_model>

<done>
Approval is structurally blocked until every O6 risk section is acknowledged for the current audit snapshot.
</done>

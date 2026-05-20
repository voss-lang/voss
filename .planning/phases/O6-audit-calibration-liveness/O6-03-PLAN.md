---
phase: O6-audit-calibration-liveness
plan: 03
type: execute
wave: 2
depends_on:
  - O6-02
files_modified:
  - voss/harness/audit/report.py
  - tests/harness/audit/test_report_export.py
requirements:
  - OAUD-03
  - OAUD-08
autonomous: true
---

<objective>
Build the exported human review surface.

Purpose: Make the session tree the product by rendering a stable Markdown report and machine JSON export that foreground killed/re-scoped work, routing rationale, reviewer outcomes, and liveness.
</objective>

<context>
@.planning/phases/O6-audit-calibration-liveness/O6-PATTERNS.md
@.planning/phases/O6-audit-calibration-liveness/O6-VALIDATION.md
@voss/harness/audit/model.py
@voss/harness/audit/load.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Markdown report renderer</name>
  <files>voss/harness/audit/report.py, tests/harness/audit/test_report_export.py</files>
  <read_first>
    - voss/harness/audit/model.py
    - tests/harness/audit/test_o6_fixtures.py
  </read_first>
  <action>
    Implement `render_audit_markdown(snapshot: AuditSnapshot) -> str`.

    Required report sections:
    - session summary and root id.
    - session-tree lineage.
    - killed cards.
    - rescope lineage.
    - routing rationale and suspected misroutes.
    - Reviewer-A / Reviewer-B outcomes.
    - liveness summary.
    - Leak-6 assessment placeholder.
    - sign-off checklist labels, disabled until O6-05.

    Keep rendering deterministic and plain Markdown. Avoid terminal color codes or TUI-specific formatting.
  </action>
  <acceptance_criteria>
    - Report contains all required section headings.
    - Killed and rescope sections render before shipped/done summaries.
    - Routing rationale is visible without expanding a nested blob.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: JSON export</name>
  <files>voss/harness/audit/report.py, tests/harness/audit/test_report_export.py</files>
  <read_first>
    - voss/harness/audit/model.py
  </read_first>
  <action>
    Implement `audit_snapshot_to_json(snapshot: AuditSnapshot) -> dict` and `write_audit_exports(snapshot, out_dir) -> AuditExport`.

    The export writes:
    - `audit.md`
    - `audit.json`

    The returned export record includes paths and a stable digest of the snapshot content. Do not write sign-off approval here.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/test_report_export.py -q</automated>
  </verify>
  <acceptance_criteria>
    - JSON export round-trips through `json.dumps`.
    - Markdown and JSON exports are deterministic for the same fixture.
    - Export paths can be redirected to pytest `tmp_path`.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
| Threat | Mitigation |
|---|---|
| Human misses killed or avoided work | Report order places killed/rescoped/routing sections before final success summaries. |
| Future UI duplicates audit logic | JSON export is the machine contract for later TUI/ADE surfaces. |
| Report content is non-deterministic | Tests compare stable headings, ordering, and digest behavior. |
</threat_model>

<done>
O6 produces deterministic Markdown and JSON audit exports from an `AuditSnapshot`.
</done>

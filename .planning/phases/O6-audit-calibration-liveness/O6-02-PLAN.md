---
phase: O6-audit-calibration-liveness
plan: 02
type: execute
wave: 1
depends_on:
  - O6-01
files_modified:
  - voss/harness/audit/__init__.py
  - voss/harness/audit/model.py
  - voss/harness/audit/load.py
  - voss/harness/audit/preflight.py
  - tests/harness/audit/test_snapshot_loader.py
requirements:
  - OAUD-01
  - OAUD-02
  - OAUD-08
autonomous: true
---

<objective>
Implement the read-only audit snapshot model and loader.

Purpose: Normalize O1-O5 persisted audit data into an O6-owned `AuditSnapshot` without mutating session-tree files or changing `RunRecord` / `SessionRecord` schemas.
</objective>

<context>
@.planning/phases/O6-audit-calibration-liveness/O6-PATTERNS.md
@.planning/phases/O6-audit-calibration-liveness/O6-VALIDATION.md
@voss/harness/session_tree.py
@voss/harness/session.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Audit dataclasses</name>
  <files>voss/harness/audit/model.py, voss/harness/audit/__init__.py</files>
  <read_first>
    - voss/harness/session_tree.py
    - voss/harness/session.py
  </read_first>
  <action>
    Create O6-owned frozen or slots dataclasses for:
    - `AuditSnapshot`
    - `AuditNode`
    - `AuditCard`
    - `RoutingRationale`
    - `KillRecord`
    - `RescopeRecord`
    - `ReviewerAssessment`
    - `LivenessEvent`
    - `Leak6Assessment`

    Keep field names stable and simple. Prefer primitives, tuples, and dicts over importing O3-O5 runtime classes. Export the public types from `voss/harness/audit/__init__.py`.
  </action>
  <acceptance_criteria>
    - Model imports do not import board, reviewer, EM, CLI, or TUI modules.
    - Snapshot has enough fields to render all O6 report sections.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Read-only snapshot loader</name>
  <files>voss/harness/audit/load.py, tests/harness/audit/test_snapshot_loader.py</files>
  <read_first>
    - voss/harness/session_tree.py
    - tests/harness/audit/test_o6_fixtures.py
  </read_first>
  <action>
    Implement `load_audit_snapshot(root: Path) -> AuditSnapshot`.

    The loader reads fixture-compatible session-tree JSON, sorts nodes/cards deterministically, normalizes missing optional O3-O5 payloads to empty tuples, and never writes to disk.

    Add tests that:
    - load the O6 fixture tree.
    - assert killed, rescope, routing, reviewer, liveness, and Leak-6 data are present.
    - assert file mtimes or file contents are unchanged after loading.
    - assert malformed node JSON produces a clear loader error with the file path.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/test_snapshot_loader.py -q</automated>
    <automated>python -m pytest tests/harness/test_session_redaction.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Loader is read-only.
    - Loader does not require live O3-O5 imports.
    - Redaction regression remains green.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
| Threat | Mitigation |
|---|---|
| Audit code mutates session evidence | Loader has read-only tests and no write path. |
| O6 creates schema coupling to O3-O5 classes | Snapshot model uses primitive normalized records. |
| Malformed evidence is silently dropped | Loader raises a path-bearing error for malformed required JSON. |
</threat_model>

<done>
`AuditSnapshot` loads deterministically from O6 fixtures, preserves session schema isolation, and exposes normalized audit records for downstream plans.
</done>

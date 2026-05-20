---
phase: O6-audit-calibration-liveness
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/harness/audit/test_preflight.py
  - tests/harness/audit/test_o6_fixtures.py
requirements:
  - OAUD-01
  - OAUD-08
autonomous: true
---

<objective>
Add the O6 blocking preflight and deterministic RED fixtures.

Purpose: O6 must not execute against a half-built O-track. This plan freezes the audit inputs O6 expects from O1-O5 and creates fixture helpers that downstream plans use for loader, report, metric, sign-off, and Leak-6 tests.
</objective>

<context>
@.planning/phases/O6-audit-calibration-liveness/O6-CONTEXT.md
@.planning/phases/O6-audit-calibration-liveness/O6-RESEARCH.md
@.planning/phases/O6-audit-calibration-liveness/O6-VALIDATION.md
@.planning/phases/O6-audit-calibration-liveness/O6-PATTERNS.md
@voss/harness/session_tree.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Preflight contract tests</name>
  <files>tests/harness/audit/test_preflight.py</files>
  <read_first>
    - voss/harness/session_tree.py
    - .planning/phases/O3-board-state-machine/O3-01-PLAN.md
    - .planning/phases/O4-reviewer-ab-split/O4-01-PLAN.md
    - .planning/phases/O5-engineering-manager-loop/O5-PATTERNS.md
  </read_first>
  <action>
    Create tests for `voss.harness.audit.preflight.run_o6_preflight()`. The function must return a structured result with `ok`, `missing`, and `warnings`.

    Required checks:
    - O1 session-tree import exists.
    - Session tree nodes can expose or carry board transition/history payloads expected by O3.
    - Reviewer-A verification and Reviewer-B verdict payload shapes are discoverable through O4 artifacts or normalized fixture records.
    - O5 routing rationale, kill, rescope, and run-final payload shapes are discoverable.

    The tests should include one green fixture path and one missing-interface path. The missing path must assert exact missing names, not a generic failure.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/test_preflight.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Preflight reports all missing O1-O5 audit inputs by stable names.
    - Preflight passes against the deterministic O6 fixture package.
    - No production O6 loader/report code runs when preflight fails.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Deterministic audit fixtures</name>
  <files>tests/harness/audit/test_o6_fixtures.py</files>
  <read_first>
    - tests/harness/test_session_tree.py
    - tests/harness/test_session_redaction.py
  </read_first>
  <action>
    Add fixture builders for a synthetic audit session tree. The fixture must include:
    - one completed card.
    - one killed card with kill rationale.
    - one rescope lineage with before/after acceptance criteria.
    - one misroute candidate with routing rationale.
    - one Reviewer-A pass followed by Reviewer-B block.
    - one timeout-to-Blocked liveness path.
    - one Leak-6 accepted-gap marker.

    Keep the fixtures under `tests/harness/audit/`. They should write temporary node JSON under pytest `tmp_path`, never under the developer's real `.voss/`.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/test_o6_fixtures.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Fixture data is deterministic and sorted by id where ordering matters.
    - Fixture data exercises every OAUD-08 scenario.
    - Fixture helper does not touch the repository working `.voss/` directory.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
| Threat | Mitigation |
|---|---|
| O6 silently runs against missing O5 data | Blocking preflight returns exact missing surfaces before downstream execution. |
| Tests accidentally use real local session data | Fixture builders write only under pytest `tmp_path`. |
| Fixture drift hides integration gaps | Preflight names every O1-O5 input explicitly and downstream plans consume the same fixtures. |
</threat_model>

<done>
O6 has a blocking preflight contract and a deterministic fixture package covering OAUD-01 and OAUD-08.
</done>

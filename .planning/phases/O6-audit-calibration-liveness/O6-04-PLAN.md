---
phase: O6-audit-calibration-liveness
plan: 04
type: execute
wave: 2
depends_on:
  - O6-02
files_modified:
  - voss/harness/audit/metrics.py
  - voss/harness/audit/report.py
  - tests/harness/audit/test_calibration.py
  - tests/harness/audit/test_liveness.py
requirements:
  - OAUD-05
  - OAUD-06
  - OAUD-08
autonomous: true
---

<objective>
Compute calibration and liveness telemetry.

Purpose: Turn O4/O5 audit facts into drift and liveness signals without pretending the telemetry is itself a correctness oracle.
</objective>

<context>
@.planning/phases/O6-audit-calibration-liveness/O6-RESEARCH.md
@.planning/phases/O6-audit-calibration-liveness/O6-PATTERNS.md
@voss/harness/audit/model.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Reviewer calibration metrics</name>
  <files>voss/harness/audit/metrics.py, tests/harness/audit/test_calibration.py</files>
  <read_first>
    - voss/harness/audit/model.py
    - tests/harness/audit/test_o6_fixtures.py
  </read_first>
  <action>
    Implement `compute_calibration(snapshot: AuditSnapshot) -> CalibrationMetrics`.

    Include:
    - total assessed cards.
    - A/B agreement count and rate.
    - A/B disagreement count and rate.
    - B-block-after-A-pass count.
    - slop rejection count and rate.
    - deterministic human spot-audit sample ids.

    The sample policy must be deterministic and bias toward disagreements, B blocks, and suspected misroutes before ordinary passes.
  </action>
  <acceptance_criteria>
    - Fixture disagreement and slop rejection are counted.
    - Spot-audit sample order is deterministic.
    - Metrics expose counts and rates without requiring floating-point exactness beyond simple assertions.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Liveness metrics</name>
  <files>voss/harness/audit/metrics.py, tests/harness/audit/test_liveness.py</files>
  <read_first>
    - voss/harness/audit/model.py
    - .planning/ORCHESTRATION-PLAN.md
  </read_first>
  <action>
    Implement `compute_liveness(snapshot: AuditSnapshot) -> LivenessMetrics`.

    Include:
    - terminal node count.
    - open node count.
    - timeout-to-Blocked count.
    - reserve warning count.
    - stranded-node warnings.
    - overall status: `ok`, `warning`, or `blocked`.

    Add report integration so O6-03's liveness section can print the computed summary.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/audit/test_calibration.py tests/harness/audit/test_liveness.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Timeout-to-Blocked fixture is visible in metrics.
    - Open/stranded node fixture produces warning or blocked status.
    - Report renderer consumes metrics without recomputing them inline.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
| Threat | Mitigation |
|---|---|
| Calibration becomes false proof of correctness | Metric names and report copy describe drift/sampling, not correctness. |
| Sampling misses high-risk cases | Deterministic priority orders disagreements and suspected misroutes first. |
| Liveness failures hidden in aggregate success | Liveness exposes open nodes and timeout/reserve warnings separately. |
</threat_model>

<done>
Calibration and liveness metrics are computed deterministically and are available to the audit report.
</done>

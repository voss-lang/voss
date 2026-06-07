---
phase: V12
slug: safety-factory-fallbacks
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-06
---

# Phase V12 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/test_safety_policy.py tests/harness/test_safety_gate.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/test_safety_policy.py tests/harness/test_safety_gate.py tests/harness/test_factory_fallback_audit.py tests/harness/em/test_safety_policy_inheritance.py tests/harness/test_permission_rules.py tests/harness/test_capability_invocation_audit.py tests/harness/test_team_gate_compile.py -q` |
| **Estimated runtime** | ~20 seconds focused, ~60 seconds with EM regression selection |

---

## Sampling Rate

- **After every task commit:** Run the task's focused pytest command.
- **After every plan wave:** Run the full V12 focused suite.
- **Before `$gsd-verify-work`:** Full V12 focused suite plus existing permission/capability/team/EM regressions must be green.
- **Max feedback latency:** 60 seconds for focused safety regressions.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| V12-01-01 | 01 | 1 | VSAFE-06 | T-V12-01 | Malformed safety policy and unknown runbook references fail closed | unit | `.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q` | no | pending |
| V12-01-02 | 01 | 1 | VSAFE-02/VSAFE-03/VSAFE-04 | T-V12-02 | Classifier returns exact route/scaffold decisions only for matching rules | unit | `.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q` | no | pending |
| V12-02-01 | 02 | 2 | VSAFE-01 | T-V12-03 | `auto_yes` cannot bypass irreversible-action confirmation | unit | `.venv/bin/python -m pytest tests/harness/test_safety_gate.py -q` | no | pending |
| V12-02-02 | 02 | 2 | VSAFE-02/VSAFE-03 | T-V12-04 | Dangerous/fixed-pipeline operations route or deny before tool invocation | unit | `.venv/bin/python -m pytest tests/harness/test_safety_gate.py -q` | no | pending |
| V12-03-01 | 03 | 3 | VSAFE-05 | T-V12-05 | Factory fallback evidence persists without leaking raw secrets | unit | `.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py -q` | no | pending |
| V12-03-02 | 03 | 3 | VSAFE-05 | T-V12-06 | Old run records without factory fields hydrate successfully | unit | `.venv/bin/python -m pytest tests/harness/test_factory_fallback_audit.py -q` | no | pending |
| V12-04-01 | 04 | 4 | VSAFE-04/VSAFE-07 | T-V12-07 | Role/model-tier scaffold rules apply to EM-derived gates | unit | `.venv/bin/python -m pytest tests/harness/em/test_safety_policy_inheritance.py -q` | no | pending |
| V12-04-02 | 04 | 4 | VSAFE-07 | T-V12-08 | Direct and EM-dispatched dangerous operations receive the same safety decision | unit | `.venv/bin/python -m pytest tests/harness/em/test_safety_policy_inheritance.py -q` | no | pending |

*Status: pending = not executed yet.*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. V12 adds new focused pytest files during implementation; no separate test framework setup is required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive terminal wording for risk-summary prompt | VSAFE-01/VSAFE-07 | Exact terminal copy is user-facing and may vary by renderer | Run a local classified irreversible command with a TTY and confirm the prompt shows risk summary plus exact command/action before approval. |

---

## Validation Sign-Off

- [x] All tasks have automated verify or explicit manual-only justification.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 uses existing pytest infrastructure.
- [x] No watch-mode flags.
- [x] Feedback latency target < 60s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** draft 2026-06-06

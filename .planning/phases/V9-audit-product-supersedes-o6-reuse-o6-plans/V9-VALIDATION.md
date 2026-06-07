---
phase: V9
slug: audit-product-supersedes-o6-reuse-o6-plans
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase V9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: V9-RESEARCH.md §Validation Architecture (verified against shipped `voss/harness/audit/` package, 37 existing tests).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 (Python 3.13.12) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/audit/ -x` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/ -x` |
| **Estimated runtime** | ~30–60 seconds (audit package quick; full harness longer) |

**Interpreter note:** use `.venv/bin/python` — bare `python3` lacks deps.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/harness/audit/ -x`
- **After every plan wave:** `.venv/bin/python -m pytest tests/harness/ -x`
- **Before `/gsd-verify-work`:** full harness suite green
- **Max feedback latency:** ~60 seconds

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| VAUD-01 | `voss audit` exits 0 (latest), non-zero (unknown run_id) | CLI smoke | `.venv/bin/python -m pytest tests/harness/audit/test_audit_cli.py -x` | ❌ W0 | ⬜ pending |
| VAUD-01 | Identical persisted data → identical output | determinism | `.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py::test_determinism -x` | ❌ W0 | ⬜ pending |
| VAUD-02 | All 15 PRD §9 sections present (missing → "none", no crash) | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py -x` | ❌ W0 | ⬜ pending |
| VAUD-03 | EM claims tagged; unsupported flagged | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_claims_vs_evidence -x` | ❌ W0 | ⬜ pending |
| VAUD-04 | Per-node budget (limit/spent) shown | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_budget_section -x` | ❌ W0 | ⬜ pending |
| VAUD-05 | Scope denials (`rejected_raises`) shown with reasons | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_scope_denials -x` | ❌ W0 | ⬜ pending |
| VAUD-06 | Reviewer-A and Reviewer-B in separate sections | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_reviewer_sections_separate -x` | ❌ W0 | ⬜ pending |
| VAUD-07 | Kill/rescope lineage + routing rationale shown | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_lineage -x` | Partial ✅ | ⬜ pending |
| VAUD-08 | Markdown valid; JSON round-trips | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_render.py -x` | ❌ W0 | ⬜ pending |
| VAUD-10 | Residual-risk section present; Leak-6 documented | unit | `.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py::test_residual_risk -x` | ❌ W0 | ⬜ pending |
| VAUD-SIGNOFF | Approve blocked until ack; ack recorded | unit | `.venv/bin/python -m pytest tests/harness/audit/test_signoff_forcing.py -x` | ❌ W0 | ⬜ pending |
| VAUD-CAL | Calibration rates computed; spot-audit hook exists | unit | `.venv/bin/python -m pytest tests/harness/audit/test_calibration.py -x` | ❌ W0 | ⬜ pending |
| (guard) | Zero field changes RunRecord/SessionRecord/BudgetScope | regression | `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x` | ✅ | ⬜ pending |
| (guard) | No board/EM live imports in model.py/load.py | regression | `.venv/bin/python -m pytest tests/harness/audit/ -k NoLiveImports -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/audit/test_audit_report.py` — VAUD-02/03/04/05/06/07/10
- [ ] `tests/harness/audit/test_audit_render.py` — VAUD-08 (Markdown + JSON, determinism, round-trip)
- [ ] `tests/harness/audit/test_audit_cli.py` — VAUD-01 (CLI, exit codes, latest-default, run_id)
- [ ] `tests/harness/audit/test_signoff_forcing.py` — VAUD-SIGNOFF
- [ ] `tests/harness/audit/test_calibration.py` — VAUD-CAL
- [ ] Extend `tests/harness/audit/test_o6_fixtures.py::build_fixture_tree` — add `.review.json` sidecars + `run-final.json` to the fixture tree (needed by all new tests)
- [ ] Extend `tests/harness/audit/test_snapshot_loader.py` — `run_id` param, `run-final.json` separate read (the glob-bug fix), `.review.json` sidecar loading
- [ ] **Landmine fix (pre-impl):** `load.py::load_audit_snapshot` globs `*.json` and chokes on `run-final.json` (no `id` field) → `AuditLoadError` on any real run dir. Filter it out before the node glob. Currently untested.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `voss audit` Markdown legibility | VAUD-02/08 | Visual formatting | Run `voss audit` on a real `voss team run`; confirm sections render legibly |
| Sign-off forcing-function UX | VAUD-SIGNOFF | Interactive prompt | Attempt approve before ack → refused; after ack → allowed |

*All correctness/gating behaviors have automated verification; only output legibility + interactive UX are manual.*

---

## Validation Sign-Off

- [ ] All requirements have an `<automated>` verify or Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (5 new test files + 2 fixture/loader extensions + 1 landmine fix)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set after Wave 0

**Approval:** pending

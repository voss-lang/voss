---
phase: V6
slug: reviewer-a-b-split-supersedes-o4
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase V6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: V6-RESEARCH.md §Validation Architecture (verified against shipped code).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with pytest-asyncio) |
| **Config file** | `pyproject.toml` / `pytest.ini` (project standard) |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short -x` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/board/ -q` |
| **Estimated runtime** | ~30 seconds (board package) |

**Interpreter note:** use `.venv/bin/python` — bare `python3` lacks deps and cannot run the suite.

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short -x`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/harness/board/ -q`
- **Before `/gsd-verify-work`:** Full board suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Requirement Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| VREV-03 | A-fail refuses Done; B-fail refuses Done; both pass → Done | unit | `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py -x` | ❌ W0 | ⬜ pending |
| VREV-04 | B-block at Done gate → card moves to Blocked | unit | `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBBlockAtGate -x` | ❌ W0 | ⬜ pending |
| VREV-06 | `ReviewerVerdict.domain_inferred`; B populates; existing construction works | unit | `.venv/bin/python -m pytest tests/harness/board/test_domain_inferred.py -x` | ❌ W0 | ⬜ pending |
| VREV-07 | Board accepts `reviewer_a`/`reviewer_b`; legacy `reviewer` still works | unit | `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBoardSlotBackCompat -x` | ❌ W0 | ⬜ pending |
| VREV-09 | `.review.json` sidecar written at gate; re-readable without re-running | unit | `.venv/bin/python -m pytest tests/harness/board/test_review_sidecar.py -x` | ❌ W0 | ⬜ pending |
| VREV-10 | `voss review` (latest) exits 0; unknown run exits non-zero | smoke | `.venv/bin/python -m pytest tests/harness/board/test_review_cli.py -x` | ❌ W0 | ⬜ pending |
| VREV-05 | Existing O4 reviewer tests regress green | regression | `.venv/bin/python -m pytest tests/harness/board/ -q` | ✅ | ⬜ pending |
| D-08 | `verdict.py` imports only stdlib (zero-transitive contract) | unit | `.venv/bin/python -m pytest tests/harness/board/test_verdict_imports.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/board/test_two_source_gate.py` — covers VREV-03, VREV-04, VREV-07
- [ ] `tests/harness/board/test_domain_inferred.py` — covers VREV-06
- [ ] `tests/harness/board/test_review_sidecar.py` — covers VREV-09
- [ ] `tests/harness/board/test_review_cli.py` — covers VREV-10
- [ ] `tests/harness/board/test_verdict.py` — UPDATE `test_exactly_6_fields` → 7-field assertion (domain_inferred)
- [ ] **Pre-existing fix:** `tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3` — expected set must include `"killed"` (added by O5). One-line fix; currently the single red test in the baseline (92 pass / 1 fail).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `voss review` human-readable layout | VREV-10 | Visual formatting | Run `voss review` after a board run; confirm per-card A verification + B verdict render legibly |

*All gating/correctness behaviors have automated verification; only output legibility is manual.*

---

## Validation Sign-Off

- [ ] All requirements have an `<automated>` verify or Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (5 new test files + 2 edits)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0

**Approval:** pending

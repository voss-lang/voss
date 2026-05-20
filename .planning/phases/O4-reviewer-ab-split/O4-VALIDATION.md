---
phase: O4
slug: reviewer-ab-split
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-19
---

# Phase O4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/board/ -x -q --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/board/ tests/eval/ -v --tb=long` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/harness/board/ -x -q --tb=short`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/harness/board/ tests/eval/ -v --tb=long`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| O4-01-01 | O4-01 | 1 | ORVW-01..10 | — | O3 preflight + RED scaffolds | unit | `.venv/bin/python -m pytest tests/harness/board/ --collect-only` | ❌ W0 | ⬜ pending |
| O4-02-01 | O4-02 | 2 | ORVW-04..07 | — | ReviewerB module imports cleanly | unit | `.venv/bin/python -c "from voss.harness.board.reviewer_b import ReviewerB"` | ❌ W0 | ⬜ pending |
| O4-02-02 | O4-02 | 2 | ORVW-04..07,09 | — | ReviewerB tests pass (isolation, tiered, residual-2) | unit | `.venv/bin/python -m pytest tests/harness/board/test_reviewer_b.py -x -q` | ❌ W0 | ⬜ pending |
| O4-03-01 | O4-03 | 2 | ORVW-01..03 | — | ReviewerA module imports cleanly | unit | `.venv/bin/python -c "from voss.harness.board.reviewer_a import ReviewerA"` | ❌ W0 | ⬜ pending |
| O4-03-02 | O4-03 | 2 | ORVW-01..03,08,09 | — | ReviewerA tests pass (bar derivation, test authoring, eval) | unit | `.venv/bin/python -m pytest tests/harness/board/test_reviewer_a.py -x -q` | ❌ W0 | ⬜ pending |
| O4-04-01 | O4-04 | 3 | ORVW-09,10 | — | Integration test passes (board lifecycle with real reviewers) | integration | `.venv/bin/python -m pytest tests/harness/board/test_reviewer_integration.py -x -q` | ❌ W0 | ⬜ pending |
| O4-04-02 | O4-04 | 3 | ORVW-01..10 | — | Full suite passes, verdict.py unmodified | integration | `.venv/bin/python -m pytest tests/harness/ tests/eval/ -x -q --tb=short` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/board/test_reviewer_a.py` — RED stubs for Reviewer-A verification authoring (ORVW-01..03, 08)
- [ ] `tests/harness/board/test_reviewer_b.py` — RED stubs for Reviewer-B independent judgment (ORVW-04..07)
- [ ] `tests/harness/board/test_reviewer_integration.py` — RED stubs for board lifecycle with real reviewers (ORVW-09, 10)

*Existing pytest infrastructure covers framework; stubs needed for new reviewer modules.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| B has no EM/A memory bleed | ORVW-04 (isolation) | Message-list contents require inspection of actual session payloads | Inspect B's `messages[]` for zero EM plan text, zero A episodic turns |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: O1
slug: session-tree-substrate-budget-fan-out
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase O1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (class-based, `tests/harness/` conventions) |
| **Config file** | existing repo pytest config (no Wave 0 install — pytest already present) |
| **Quick run command** | `pytest tests/harness/ -x -q` |
| **Full suite command** | `pytest tests/harness/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/harness/ -x -q`
- **After every plan wave:** Run `pytest tests/harness/ -q`
- **Before `/gsd:verify-work`:** Full suite green + `pytest tests/harness/test_session_redaction.py -q` unmodified-pass
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Populated by the planner. Every O1 task maps to one acceptance criterion from O1-SPEC.md. Critical rows the planner MUST cover:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| O1-XX-XX | XX | 1 | SPEC req 1 (tree node + parent linkage) | — | N children → N persisted nodes, each `parent_run_id`=parent | unit | `pytest tests/harness/test_session_tree.py -q` | ❌ W0 | ⬜ pending |
| O1-XX-XX | XX | 1 | SPEC req 2 (fan-out invariant) | — | `sum(children)+reserve ≤ parent` enforced; oversell raises, no partial state | unit | `pytest tests/harness/test_session_tree.py -q` | ❌ W0 | ⬜ pending |
| O1-XX-XX | XX | 2 | SPEC req 3 (reserve drain → terminal finalize) | — | drained child → exactly one `RunRecord exit_reason="budget"` + closed node | unit | `pytest tests/harness/test_session_tree.py -q` | ❌ W0 | ⬜ pending |
| O1-XX-XX | XX | 2 | SPEC req 4 (non-extendable cap + recorded attempt) | — | cap-raise raises documented error AND records rejected attempt on node | unit | `pytest tests/harness/test_session_tree.py -q` | ❌ W0 | ⬜ pending |
| O1-XX-XX | XX | 2 | concurrency no-oversell race | — | N concurrent child allocations cannot oversell parent envelope | unit | `pytest tests/harness/test_session_tree.py -q` | ❌ W0 | ⬜ pending |
| O1-XX-XX | XX | 1 | SPEC req 5 (harness-additive blast radius) | — | `git diff` zero field changes on SessionRecord/RunRecord/BudgetScope | unit | `pytest tests/harness/test_session_redaction.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_session_tree.py` — new test module (covers SPEC reqs 1–4 + concurrency race)
- [ ] Shared fixtures via existing `tests/harness/` conftest pattern (reuse, do not add new conftest unless required)

*pytest framework already installed — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `voss resume` rehydration of a partially-written tree | resume-compat (Claude's Discretion) | end-to-end resume requires a real interrupted root; substrate-not-precluded is structurally asserted in unit tests | run a root to mid-tree, kill, `voss resume`, confirm flat session loads and tree dir is ignored by `_scan_dir` |

*All blocking acceptance criteria have automated verification; resume is a non-blocking substrate-compatibility check.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

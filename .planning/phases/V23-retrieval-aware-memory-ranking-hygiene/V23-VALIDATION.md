---
phase: V23
slug: retrieval-aware-memory-ranking-hygiene
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-12
---

# Phase V23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/memory tests/harness/test_memory_*.py tests/code_recall -q` |
| **Estimated runtime** | ~60–90 seconds |

> Tests MUST run via `.venv/bin/python` — bare `python3` lacks deps (memory: voss-python-interpreter).

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| V23-01-* | 01 | 0 | VRNK-01..08 | — | N/A (RED scaffold) | unit | `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -q` | ❌ W0 | ⬜ pending |
| V23-02-* | 02 | 1 | VRNK-01 | — | telemetry never mutates memory files (mtime+bytes stable) | unit | `pytest tests/memory/test_retrieval_ranking.py -k telemetry -q` | ❌ W0 | ⬜ pending |
| V23-03-* | 03 | 1 | VRNK-02 | — | no-match query returns 0 hits with floors on | unit | `pytest tests/memory/test_retrieval_ranking.py -k floor -q` | ❌ W0 | ⬜ pending |
| V23-04-* | 04 | 2 | VRNK-03 | — | rescore-off byte-identical to pre-V23 baseline | unit | `pytest tests/memory/test_retrieval_ranking.py -k "rescore or byte_identical" -q` | ❌ W0 | ⬜ pending |
| V23-05-* | 05 | 2 | VRNK-04, VRNK-05 | — | never-retrieved evicts first; --check exit 1 on drift then exit 0 after reindex | unit | `pytest tests/memory/test_retrieval_ranking.py -k "evict or reindex or drift" -q` | ❌ W0 | ⬜ pending |
| V23-06-* | 06 | 3 | VRNK-06, VRNK-07 | — | pinned text present without recall match + survives eviction; pin/unpin/list/show exit 1 on unknown locator | unit + CLI | `pytest tests/memory/test_retrieval_ranking.py -k "pin or cli" -q` | ❌ W0 | ⬜ pending |
| V23-08-* | all | 3 | VRNK-08 | — | existing memory + code_recall suites green; no frozen-schema drift | regression | full suite command | ✅ partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/memory/test_retrieval_ranking.py` — RED stubs for VRNK-01..08 (telemetry, floors, rescore, eviction, reindex/drift, pins, CLI verbs, byte-identical baseline)
- [ ] Reuse existing `tests/memory/` + `tests/harness/` conftest fixtures (tmp memory store); add a chroma-absent fixture variant for degradation paths
- [ ] Byte-identical baseline fixture — capture pre-V23 recall output (order, scores, excerpts) per the `test_no_pack_byte_identical` precedent (test_agent_packing.py:203)

*Framework already installed — no install task.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pinned memory visibly present in real agent context window | VRNK-06 | End-to-end context assembly under a live model is integration-heavy; unit test asserts the compose-block string contains pin text | Pin a memory, run `voss do` with an unrelated query, confirm pin text in assembled system context (or assert via _compose_system_blocks unit test) |
| Recency×frequency rescore improves real hit relevance | VRNK-03 | Quality eval deferred to E-track flip-on proposal (SPEC out-of-scope) — V23 bar is determinism + byte-identical off-path only | N/A this phase — determinism fixture covers correctness |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

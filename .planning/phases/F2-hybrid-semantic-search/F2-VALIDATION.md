---
phase: F2
slug: hybrid-semantic-search
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-21
---

# Phase F2 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py` |
| **Full suite command** | `PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py tests/harness/test_slash_memory.py tests/harness/test_slash_recall.py` |
| **Estimated runtime** | ~30-90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py`
- **After every plan wave:** Run `PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py tests/harness/test_slash_memory.py tests/harness/test_slash_recall.py`
- **Before `/gsd:verify-work`:** Full targeted suite plus `python -c "from rank_bm25 import BM25Okapi; print(BM25Okapi.__name__)"`
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| F2-01-01 | 01 | 1 | FSRCH-01, FSRCH-03 | T-F2-01 | Retrieval ignores tombstoned memory IDs and preserves source filtering | unit | `PYTHONPATH=. pytest tests/harness/test_memory_store.py -q` | yes | pending |
| F2-01-02 | 01 | 1 | FSRCH-01, FSRCH-04 | T-F2-02 | Tokenization is deterministic and does not expose secrets or new persistence | unit | `PYTHONPATH=. pytest tests/harness/test_memory_store.py -q` | yes | pending |
| F2-02-01 | 02 | 2 | FSRCH-02, FSRCH-03 | T-F2-03 | Chroma failures degrade to BM25 without crashing or returning tombstoned rows | unit/integration | `PYTHONPATH=. pytest tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py -q` | yes | pending |
| F2-02-02 | 02 | 2 | FSRCH-02 | T-F2-04 | RRF de-duplicates by locator and caps output to `top_k` | unit | `PYTHONPATH=. pytest tests/harness/test_memory_store.py -q` | yes | pending |
| F2-03-01 | 03 | 2 | FSRCH-01..FSRCH-04 | T-F2-05 | Base install includes BM25 while vector search remains optional | dependency + regression | `python -c "from rank_bm25 import BM25Okapi; print(BM25Okapi.__name__)" && PYTHONPATH=. pytest tests/harness/test_memory_runtime_reuse.py tests/harness/test_slash_recall.py -q` | yes | pending |

*Status: pending | green | red | flaky*

---

## Wave 0 Requirements

- [x] Existing pytest infrastructure covers F2.
- [x] Existing memory-store fixtures cover turns, ledgers, decisions, conventions, and notes.
- [x] No new test framework or service dependency is required.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution

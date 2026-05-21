---
phase: F2-hybrid-semantic-search
plan: 02
type: execute
wave: 2
depends_on: [F2-01]
files_modified:
  - voss/harness/memory_store.py
  - tests/harness/test_memory_store.py
  - tests/harness/test_recall_eval.py
autonomous: true
requirements: [FSRCH-02, FSRCH-03]

must_haves:
  truths:
    - "MemoryStore.recall always runs BM25 and uses Chroma as an optional second retriever"
    - "Reciprocal Rank Fusion uses k=60 and 1-based ranks"
    - "RRF de-duplicates by Hit.locator and returns no more than top_k hits"
    - "Chroma query failures degrade to BM25 results without raising"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "Hybrid BM25 + Chroma recall and RRF merge helper"
      contains: ["_rrf_merge", "RRF", "_bm25_recall", "_chroma_recall"]
    - path: "tests/harness/test_memory_store.py"
      provides: "RRF and hybrid degradation tests"
      contains: ["rrf", "top_k", "locator"]
  key_links:
    - from: "MemoryStore.recall"
      to: "MemoryStore._rrf_merge"
      via: "BM25 hits + optional Chroma hits"
      pattern: "_rrf_merge("
---

<objective>
Turn the BM25 lexical retriever from Plan 01 into hybrid search by combining BM25 and Chroma result lists with Reciprocal Rank Fusion.

Output remains the existing `Hit` list; only ranking semantics change.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F2-hybrid-semantic-search/F2-CONTEXT.md
@.planning/phases/F2-hybrid-semantic-search/F2-RESEARCH.md
@.planning/phases/F2-hybrid-semantic-search/F2-PATTERNS.md
@.planning/phases/F2-hybrid-semantic-search/F2-VALIDATION.md
</context>

<threat_model>
| Threat | Severity | Mitigation |
|---|---|---|
| Chroma failure prevents memory recall entirely | medium | Catch vector recall exceptions and return BM25 results |
| Duplicate locators from BM25 and Chroma inflate result count | low | RRF groups by `Hit.locator` before final sort |
| Vector hits bypass source/tombstone constraints | medium | Continue using `_chroma_recall()` with existing `where` filter and tombstone filtering |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add RRF unit tests</name>
  <files>
    tests/harness/test_memory_store.py
  </files>
  <read_first>
    tests/harness/test_memory_store.py
    voss/harness/memory_store.py
    .planning/phases/F2-hybrid-semantic-search/F2-RESEARCH.md
  </read_first>
  <action>
    Add tests for a private `_rrf_merge` helper. Construct `Hit` objects directly. Cover three cases: duplicate locator appears in BM25 rank 1 and Chroma rank 2 and receives a fused score greater than a single-list rank 1 hit; `top_k=2` returns exactly two hits; the returned hit for a duplicate locator preserves the original source, locator, excerpt, session_id, and ts fields while replacing `score` with the RRF score.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/test_memory_store.py` contains a test name including `rrf`
    - RRF test constructs at least three `Hit(` objects
    - RRF test asserts duplicate locator score is greater than a single-list hit score
    - RRF test asserts `len(results) == 2` for `top_k=2`
  </acceptance_criteria>
  <done>RRF behavior is specified by failing tests before implementation.</done>
</task>

<task type="auto">
  <name>Task 2: Implement RRF merge helper</name>
  <files>
    voss/harness/memory_store.py
  </files>
  <read_first>
    voss/harness/memory_store.py
    tests/harness/test_memory_store.py
    .planning/phases/F2-hybrid-semantic-search/F2-PATTERNS.md
  </read_first>
  <action>
    Add private helper `_rrf_merge(rankings: list[list[Hit]], *, top_k: int, k: int = 60) -> list[Hit]` near the recall helpers. For each ranking, enumerate hits with 1-based rank. Accumulate `1.0 / (k + rank)` by `hit.locator`. Store the first seen `Hit` object for each locator as the metadata carrier. After scoring, create returned `Hit` objects with the same source, locator, excerpt, session_id, and ts as the carrier and the fused RRF score. Sort by fused score descending, then locator ascending for deterministic ties. Return at most `top_k`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/memory_store.py` contains `def _rrf_merge(`
    - `_rrf_merge` default parameter includes `k: int = 60`
    - `_rrf_merge` uses `enumerate(` with 1-based rank or an explicit rank counter starting at 1
    - RRF unit tests pass
  </acceptance_criteria>
  <done>RRF merge helper exists with deterministic, de-duplicating ranking behavior.</done>
</task>

<task type="auto">
  <name>Task 3: Wire hybrid recall and degradation behavior</name>
  <files>
    voss/harness/memory_store.py
    tests/harness/test_memory_store.py
    tests/harness/test_recall_eval.py
  </files>
  <read_first>
    voss/harness/memory_store.py
    tests/harness/test_memory_store.py
    tests/harness/test_recall_eval.py
    tests/harness/test_chroma_unavailable.py
  </read_first>
  <action>
    Update `MemoryStore.recall()` so it always computes `bm25_hits = self._bm25_recall(query, top_k=max(top_k * 3, top_k), source=source)` first. Then call `_maybe_chroma()`. If Chroma is unavailable, return `bm25_hits[:top_k]`. If Chroma is available, call `_chroma_recall(chroma, query, top_k=max(top_k * 3, top_k), source=source)` inside the existing `try`/`except Exception` guard. On Chroma failure, print the existing stderr fallback message updated to say `falling back to BM25`, then return BM25. On success, return `_rrf_merge([bm25_hits, chroma_hits], top_k=top_k)`.

    Add a regression test that monkeypatches `_bm25_recall` and `_chroma_recall` to return controlled `Hit` lists and asserts `recall()` calls the hybrid path and returns RRF-ranked results. Add a regression test that monkeypatches `_chroma_recall` to raise and asserts BM25 hits are returned. Update `test_recall_eval.py` docstring/comment text from keyword fallback to BM25 fallback without changing the fixture contract.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `MemoryStore.recall()` calls `_bm25_recall` before `_maybe_chroma`
    - `MemoryStore.recall()` calls `_rrf_merge([bm25_hits, chroma_hits]` or equivalent with both result lists
    - Chroma failure path stderr contains `falling back to BM25`
    - Hybrid recall test asserts fused order for controlled BM25/Chroma hits
    - Chroma failure test asserts BM25 hits are returned unchanged except for top_k slicing
    - `test_recall_eval.py` no longer describes the fallback path as keyword fallback
  </acceptance_criteria>
  <done>`MemoryStore.recall()` performs hybrid BM25 + Chroma retrieval when possible and degrades to BM25 when vector search is unavailable or broken.</done>
</task>

</tasks>

<verification>
Run:
- `cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py -q`
</verification>

<success_criteria>
- RRF helper passes deterministic unit tests.
- Hybrid recall uses BM25 and Chroma together when Chroma is available.
- Chroma unavailable or failing paths still return BM25 results.
- Existing recall eval remains green for both Chroma and BM25 paths.
</success_criteria>

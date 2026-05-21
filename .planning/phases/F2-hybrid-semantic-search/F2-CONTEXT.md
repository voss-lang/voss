# Phase F2: Hybrid Semantic Search - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve retrieval accuracy in the harness memory system by replacing naive keyword search with BM25 and combining it with ChromaDB vector search via Reciprocal Rank Fusion. The existing `MemoryStore.recall()` path gains hybrid search; code search (M10) is not in scope.

</domain>

<decisions>
## Implementation Decisions

### BM25 Engine Choice
- **D-01:** Use `rank_bm25` pure Python library (BM25Okapi). Lightweight (~50KB), no C deps, standard algorithm. Replaces the naive term-count `_keyword_scan()` in `memory_store.py`.
- **D-02:** `rank_bm25` is always-available (not optional). Add to base `pyproject.toml` dependencies, not to `[search]` extras. Every install gets BM25; hybrid only activates when `voss[search]` (chromadb) is also installed.

### Fusion Strategy
- **D-03:** Reciprocal Rank Fusion (RRF) with k=60. Formula: `score = Σ 1/(k + rank_i)`. Run both BM25 and vector retriever, merge results by RRF. No score normalization needed — RRF operates on rank positions, not raw scores.
- **D-04:** BM25 replaces `_keyword_scan()` entirely. When chromadb unavailable: BM25-only search. When chromadb available: hybrid RRF over both result sets. The old `_keyword_scan()` is removed.

### Integration Surface
- **D-05:** Hybrid search scopes to `MemoryStore.recall()` only. Memory store documents (sessions, decisions, notes, conventions, ledgers) get hybrid search. Code search is M10's domain — separate index, separate tools, separate phase.
- **D-06:** BM25 index built in-memory per `recall()` call. Memory store corpus is small (hundreds of docs). Build BM25 corpus → query → discard. No persistent index, no cache invalidation, no serialization.

### Symbol Awareness
- **D-07:** Custom camelCase/snake_case splitter tokenizer for BM25. Regex splits `getUserById` → `[get, user, by, id]` and `parse_config_file` → `[parse, config, file]` before BM25 indexing. Big win for exact symbol matching in decisions/conventions docs.
- **D-08:** Same tokenizer applied to both corpus and query. Consistent tokenization on both sides ensures BM25 term matching works correctly. User query "getUserById" splits the same way as the indexed document.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Memory Store (the file F2 modifies)
- `voss/harness/memory_store.py` — MemoryStore class, `recall()` method (line 389), `_keyword_scan()` (line 442, to be replaced), `_chroma_recall()` (line 404, to be combined via RRF). F2's primary modification target.
- `voss_runtime/memory/semantic.py` — SemanticMemory / ChromaDB wrapper. F2 reads from this but does NOT modify it.

### Memory Store Tests
- `tests/harness/test_memory_store.py` — Existing recall/keyword tests. F2 must update these for BM25.
- `tests/harness/test_chroma_unavailable.py` — Tests for graceful ChromaDB absence. F2 must preserve this behavior (BM25-only when chroma unavailable).

### M8 Context (built the memory system)
- `.planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md` — Original memory store decisions. F2 builds on this.

### Dependencies
- `pyproject.toml` — F2 adds `rank-bm25` to base deps (not `[search]` extras).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MemoryStore._chroma_recall()` — existing vector retrieval path. F2 wraps this as one input to RRF.
- `MemoryStore._keyword_scan()` — to be REPLACED by BM25. The scan-corpus-and-score pattern is reusable but the scoring logic changes entirely.
- `Hit` dataclass — shared return type. F2's RRF produces the same `Hit` objects.
- `_SOURCES` tuple — corpus source types. BM25 indexes across same sources.

### Established Patterns
- **Lazy chroma init** (`_maybe_chroma()`) — F2 preserves this. BM25 always runs; chroma only when available.
- **Tombstone filtering** — F2 must respect tombstones in both BM25 and vector results before RRF merge.
- **Source filtering** — `recall(source="decisions")` must work with hybrid. Both retrievers filter by source, then RRF merges filtered results.

### Integration Points
- `recall()` is the sole entry point. F2 rewrites its body: build BM25 corpus → BM25 query → if chroma available, also vector query → RRF merge → return hits.
- `_ingest_to_chroma()` and `add()` add docs to vector store. BM25 doesn't need explicit add — it builds from corpus on each recall.

</code_context>

<specifics>
## Specific Ideas

- RRF k=60 is the standard default from the original Cormack et al. paper. Can be tuned later but 60 is the proven starting point.
- The camel/snake tokenizer is a simple regex: `re.sub(r'([a-z])([A-Z])', r'\1 \2', text)` + `text.replace('_', ' ')` + lowercase + split. No external dep needed.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Code search / AST-aware indexing belongs in M10 (Codebase Intelligence).

</deferred>

---

*Phase: F2-hybrid-semantic-search*
*Context gathered: 2026-05-20*

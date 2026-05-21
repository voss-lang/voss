# Phase F2: Hybrid Semantic Search - Pattern Map

**Mapped:** 2026-05-21
**Status:** Complete

## Scope Files

| File | Role | F2 Action |
|---|---|---|
| `voss/harness/memory_store.py` | Recall orchestration over filesystem memory and Chroma | Replace `_keyword_scan()` with BM25 helpers; update `recall()` to RRF-merge BM25 and Chroma results |
| `tests/harness/test_memory_store.py` | MemoryStore behavior tests | Add tokenizer, BM25 fallback, source-filter, and tombstone regression tests |
| `tests/harness/test_chroma_unavailable.py` | Chroma absence guard | Preserve fallback semantics and update wording from keyword to BM25 where needed |
| `tests/harness/test_recall_eval.py` | Retrieval-quality gate | Preserve hit-rate eval and adjust expected fallback framing to BM25 |
| `tests/harness/test_memory_runtime_reuse.py` | Lazy Chroma import/init behavior | Run as regression for Chroma laziness |
| `pyproject.toml` | Python dependency declaration | Move `rank-bm25>=0.2.2` into base dependencies |
| `uv.lock` | Locked dependency graph | Update if dependency group changes require lock refresh |

## Existing Analog Patterns

### Lazy Optional Chroma

Source: `voss/harness/memory_store.py`

Pattern:
- `_maybe_chroma()` returns `SemanticMemory | None`.
- `recall()` catches Chroma query exceptions and falls back to lexical search.
- `write_*()` methods perform Chroma ingestion best-effort after durable file writes.

F2 use:
- Keep `_maybe_chroma()` unchanged.
- BM25 must not depend on Chroma availability.
- Hybrid path should catch Chroma failures and still return BM25 results.

### Per-Source Filesystem Corpus

Source: `MemoryStore._keyword_scan()` and `_scan_jsonl()`

Pattern:
- Iterate `_SOURCES`.
- Source-filter using plural/singular normalization.
- Skip non-files and tombstone files.
- For `turns` and `ledgers`, parse JSONL line-by-line so locators map to composite IDs.
- For markdown/text sources, read the whole file and derive locator from path.

F2 use:
- Extract this scanning into a BM25 document builder that returns candidate records containing `Hit` plus text.
- Preserve line-level JSONL granularity.
- Preserve `_locator_from_path()`, `make_id()`, and source labels.

### Tombstone Filtering

Source: `_load_tombstones()`, `_chroma_recall()`, `_keyword_scan()`, `_scan_jsonl()`

Pattern:
- Load a set of tombstoned composite IDs.
- Filter candidates before returning hits.

F2 use:
- Filter BM25 corpus entries before ranking.
- Continue relying on `_chroma_recall()` to filter vector hits.
- RRF merge must not include tombstoned locators from either list.

### Test Fixtures

Source: `tests/harness/conftest.py::fake_session_corpus`

Pattern:
- Seeds turns, ledgers, conventions, notes, and decisions.
- Returns query-to-expected-locator mapping used by `test_recall_eval.py`.

F2 use:
- Reuse this fixture for phase-level retrieval quality.
- Add smaller unit fixtures in `test_memory_store.py` for symbol-aware tokenization and tombstone behavior.

## Proposed Internal Helpers

All helpers stay private to `memory_store.py`.

- `_bm25_tokenize(text: str) -> list[str]`
  - lowercase
  - split camel/Pascal case boundaries
  - replace underscores, hyphens, dots, slashes, and punctuation with spaces
  - return non-empty tokens
- `_bm25_corpus(source: str | None) -> list[tuple[str, Hit, str]]`
  - builds stable candidate records from current filesystem memory
  - excludes tombstones
  - preserves per-line JSONL hit metadata
- `_bm25_recall(query: str, *, top_k: int, source: str | None) -> list[Hit]`
  - tokenizes query
  - creates `BM25Okapi(tokenized_corpus)`
  - calls `get_scores(tokenized_query)`
  - returns positive-scored hits sorted descending
- `_rrf_merge(rankings: list[list[Hit]], *, top_k: int, k: int = 60) -> list[Hit]`
  - de-duplicates by `Hit.locator`
  - computes RRF score from 1-based ranks
  - returns top `top_k`

## Data Flow

```text
MemoryStore.recall(query, top_k, source)
  -> _bm25_recall(query, top_k=fusion_k, source)
  -> _maybe_chroma()
       -> _chroma_recall(chroma, query, top_k=fusion_k, source)
       -> on error: stderr warning, ignore vector list
  -> if chroma list exists: _rrf_merge([bm25_hits, chroma_hits], top_k)
  -> else: bm25_hits[:top_k]
```

## Landmines

- Do not reintroduce eager `chromadb` import; existing lazy test must still pass.
- Do not index all JSONL turns as one document; turn-level locators matter for `/forget` and `/recall`.
- Do not change public `Hit` fields or slash command output expectations.
- Do not add persistent BM25 files; D-06 requires per-call in-memory indexing.
- Do not expand into code search, AST indexing, M10 project index, or UI surfaces.

## PATTERN MAPPING COMPLETE

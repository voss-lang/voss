# Phase F2: Hybrid Semantic Search - Research

**Researched:** 2026-05-21
**Status:** Complete

## Research Question

What do we need to know to plan hybrid retrieval for `MemoryStore.recall()` safely and with verifiable ranking improvements?

## Findings

### Rank-BM25 API

- `rank_bm25` exposes `BM25Okapi`.
- The canonical usage initializes `BM25Okapi` with a pre-tokenized corpus: `list[list[str]]`.
- Queries must be tokenized and preprocessed the same way as corpus documents before calling `get_scores(tokenized_query)`.
- The library does not own stemming, casing, punctuation removal, or symbol splitting; Voss must provide tokenizer behavior.
- `get_scores()` returns one score per corpus document, which is better for this phase than `get_top_n()` because `MemoryStore` needs to preserve `Hit` metadata and locators.

### Current Memory Store Shape

- `MemoryStore.recall()` currently tries `_chroma_recall()` first and only falls back to `_keyword_scan()` when Chroma is unavailable or errors.
- `_keyword_scan()` reads the same filesystem sources that BM25 should read:
  - `turns/*.jsonl`
  - `ledgers/*.jsonl`
  - `decisions/**/*`
  - `conventions/**/*`
  - `notes/**/*`
- `_scan_jsonl()` is useful because it emits per-line hits for turns and ledgers with composite IDs. BM25 should retain that granularity rather than indexing an entire JSONL file as one document.
- `_locator_from_path()` already reconstructs stable composite locators for file-backed sources.
- Tombstones are loaded from `.voss/memory/.tombstones.jsonl` and must continue to filter both lexical and vector paths.
- Source filtering normalizes plural source names to singular metadata labels, and this behavior must be preserved.

### Hybrid Retrieval Approach

- BM25 should be the always-run lexical retriever.
- Chroma vector recall should become an additional retriever when available, not the only primary path.
- Reciprocal Rank Fusion (RRF) should merge ranked result lists by locator:
  - `score = sum(1 / (60 + rank))`
  - rank is 1-based within each retriever result list
  - no raw BM25/vector score normalization is needed
- The output should remain `list[Hit]`; the fused `Hit.score` should be the RRF score.
- When the same locator appears in both retrievers, preserve the richer hit fields from the first high-quality hit, but update `score` to the fused score.
- Fetch more than `top_k` candidates per retriever before fusion so one retriever cannot starve the other. A small multiplier such as `max(top_k * 3, top_k)` is enough for the existing small corpus.

### Dependency Boundary

- F2 context requires `rank-bm25` to be a base dependency, not only in `[project.optional-dependencies].search`.
- Current `pyproject.toml` already includes `rank-bm25>=0.2.2` under `search` and `dev`; F2 should move or duplicate it into base dependencies and remove the optional duplication if feasible.
- `uv.lock` may need updating if the project lock generator tracks dependency groups strictly.

### Risk Notes

- Importing `rank_bm25` at module import time is acceptable after moving it to base dependencies, but tests should still prove Chroma stays lazy.
- Chroma may produce locators already tombstoned on disk; `_chroma_recall()` currently filters those locators, and fusion should not reintroduce them.
- BM25 scores can all be zero for no-match queries. The lexical path should return no hits in that case.
- Naive tokenization can regress symbol retrieval. The tokenizer must split camelCase, PascalCase, snake_case, kebab-case, dotted paths, and punctuation while preserving useful lowercase tokens.

## Validation Architecture

### Unit Tests

- Tokenizer tests:
  - `getUserById` tokenizes to include `get`, `user`, `by`, `id`.
  - `parse_config_file` tokenizes to include `parse`, `config`, `file`.
  - dotted paths and hyphenated text produce stable lowercase tokens.
- BM25-only recall tests:
  - Chroma disabled still returns matching `Hit` values.
  - Empty query returns `[]`.
  - Source filter works for `source="turns"` and `source="decisions"`.
  - Tombstoned locators do not appear.
- RRF tests:
  - Two ranked lists merge by locator with RRF score.
  - A locator appearing in both lists outranks equally ranked single-source hits.
  - `top_k` is honored after fusion.

### Integration/Eval Tests

- Existing `tests/harness/test_recall_eval.py` remains the phase-level retrieval quality gate.
- Raise or add an assertion for BM25 fallback top-3 quality only if the seeded corpus supports it deterministically.
- Preserve `tests/harness/test_chroma_unavailable.py` behavior: Chroma unavailable never crashes and recall still returns a list.

### Verification Commands

- Quick: `PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py`
- Full targeted: `PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py tests/harness/test_slash_memory.py tests/harness/test_slash_recall.py`
- Dependency check: `python -c "from rank_bm25 import BM25Okapi; print(BM25Okapi.__name__)"`

## Planning Implications

- Plan 01 should create the tokenizer and BM25 corpus/scoring path behind `MemoryStore.recall()` with Chroma disabled.
- Plan 02 should integrate Chroma as a second retriever and fuse lexical/vector rankings with RRF.
- Plan 03 should finalize dependency placement, regression coverage, and phase-level acceptance around the existing recall eval.

## RESEARCH COMPLETE

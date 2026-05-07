---
phase: 01-runtime-library
plan: 03
subsystem: runtime
tags: [python, embeddings, chromadb, sentence-transformers, numpy, semantic-search]

requires:
  - phase: 01-runtime-library/01-02
    provides: ContextScope, BudgetScope, ProbableValue, ModelProvider seam (used by EpisodicMemory)
provides:
  - SemanticMatcher with cosine-similarity matching, JSON index format, no-encoder load path
  - WorkingMemory key/value scratchpad
  - EpisodicMemory rolling-summary conversation store (StubProvider-driven in tests)
  - SemanticMemory ChromaDB-backed RAG store with OpenAI→local embedding fallback
affects: [agents, codegen, .voss-cache index emit]

tech-stack:
  added: []
  patterns:
    - "Lazy heavy-import inside methods (sentence_transformers, chromadb) so unit tests stay light"
    - "Synthetic-embedding test path: pass embeddings= directly to skip encoder download"
    - "ChromaDB DefaultEmbeddingFunction (bundled ONNX) for offline tests; SentenceTransformer fallback when OpenAI key absent"

key-files:
  created:
    - voss_runtime/semantic.py
    - voss_runtime/memory/__init__.py
    - voss_runtime/memory/working.py
    - voss_runtime/memory/episodic.py
    - voss_runtime/memory/semantic.py
    - tests/test_semantic_matcher.py
    - tests/memory/__init__.py
    - tests/memory/test_working.py
    - tests/memory/test_episodic.py
    - tests/memory/test_semantic.py
  modified:
    - voss_runtime/__init__.py

key-decisions:
  - "SemanticMatcher index file format: JSON `{model, threshold, cases:[{label, description, embedding:[float]}]}` — locked as the contract Phase 3 codegen will write into `.voss-cache/`"
  - "Order-sensitive matching: first case ≥ threshold wins (PRD §3.5), even when a later case scores higher — preserves author-controlled priority"
  - "from_index() reconstructs without instantiating SentenceTransformer; encoder loads lazily only on the first match() call against new input"
  - "EpisodicMemory summarizes via the active ModelProvider (StubProvider in tests) — no bespoke summarization stack"
  - "SemanticMemory falls back from `text-embedding-*` to local `sentence-transformers/all-MiniLM-L6-v2` when OPENAI_API_KEY unset; behaviour is implicit, not opt-in, so offline dev works out of the box"
  - "Empty-metadata workaround: ChromaDB rejects `{}` — `SemanticMemory.add` omits `metadatas` kwarg when no metadata supplied"

patterns-established:
  - "Tests inject embeddings/encoders rather than downloading models — fast, hermetic, no network"
  - "All memory primitives accept optional provider/model so production code defaults to global config while tests pin a stub"

requirements-completed:
  - RUN-04
  - RUN-06
  - RUN-07
  - RUN-08

duration: ~4min
completed: 2026-05-07
---

# Phase 01 Plan 03: Semantic Match + Memory Primitives Summary

**Semantic routing + episodic/semantic/working memory land — Voss programs can now match-by-meaning and persist conversation/document context across turns.**

## Performance

- **Tasks:** 4
- **Files created:** 10
- **Files modified:** 1
- **Tests added:** 16 (4 semantic_matcher + 5 working + 5 episodic + 2 semantic_memory)
- **Suite total:** 58 passing under `arch -arm64 python3 -m pytest -q -m "not live"`

## Accomplishments
- `SemanticMatcher` with synthetic-embedding test path and `to_index/from_index` JSON round-trip — Phase 3 contract locked
- `EpisodicMemory` w/ rolling summary via ModelProvider; auto-summarize over capacity
- `SemanticMemory` w/ ChromaDB persistent client + transparent OpenAI→local embedding fallback
- `WorkingMemory` minimal dict-backed scratchpad

## Files Created/Modified
- `voss_runtime/semantic.py` — SemanticMatcher + frozen Case + JSON index format
- `voss_runtime/memory/{__init__.py,working.py,episodic.py,semantic.py}`
- `tests/test_semantic_matcher.py` + `tests/memory/{test_working,test_episodic,test_semantic}.py`
- `voss_runtime/__init__.py` — added SemanticMatcher, WorkingMemory, EpisodicMemory, SemanticMemory

## Notes / Gotchas
- Local Python env requires `arch -arm64 python3` to dodge numpy x86_64/arm64 mismatch under universal interpreter
- ChromaDB rejects empty metadata dicts; `add()` omits the kwarg when none supplied
- `tests/test_semantic_matcher.py` includes one `@pytest.mark.live` real-encoder test (refund/greeting); skipped in default CI
- `tests/memory/test_semantic.py` non-live test uses Chroma's bundled `DefaultEmbeddingFunction` (offline ONNX); live test exercises the real `sentence-transformers` fallback

## Verification
- `pytest tests/test_semantic_matcher.py tests/memory -q -m "not live"` → 15 passed
- Full stub-mode suite: 58 passed
- `from voss_runtime import SemanticMatcher, EpisodicMemory, SemanticMemory, WorkingMemory` clean

## Next
Plan 01-04 builds VossAgent + AgentHandle + gather + @tool on the now-stable scope and memory layer.

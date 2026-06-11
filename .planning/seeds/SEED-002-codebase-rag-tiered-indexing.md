---
id: SEED-002
status: dormant
planted: 2026-06-11
planted_during: v0.1.1 (V-track)
trigger_when: next V-track memory/retrieval phase, or when agents waste context re-greping the same codebase concepts
scope: medium-large (2-3 phases)
---

# SEED-002: Codebase RAG index + tiered model routing for indexing, building on existing MemoryStore hybrid recall

## Why This Matters

Voss already ships hybrid RAG memory (`MemoryStore`: BM25 + Chroma + RRF fusion over
turns/ledgers/decisions/conventions/notes) — but it only indexes *conversation
artifacts*, never the code itself. Agents answer "where do we handle retry backoff"
by burning frontier-model tokens on agentic grep loops every session. A derived
codebase index makes concept-level retrieval cheap and persistent, and a tiered
model router makes building/maintaining that index nearly free.

Two ideas, one phase family:

1. **Codebase RAG index** — sibling `CodeIndex` to `MemoryStore`, derived cache
   (rebuildable, no tombstones), symbol-aware chunking reusing Voss's existing
   parsers / `language-metadata/`, content-hash manifest for incremental reindex.
2. **Tiered model routing for index work** — indexing-adjacent tasks (chunk
   summarization, symbol descriptions, simple grep/classification passes) routed
   to a cheap fast tier (e.g. GPT-OSS via Ollama, Haiku-class) through the
   existing `model_router.py` / `model_catalog.py` (models.dev catalog already
   shipped via /models picker). Frontier model never pays for index maintenance.

## When to Surface

**Trigger:** next V-track phase touching memory, retrieval, or context efficiency
(natural successor to V18 token optimizer); or when designing agent workflows
that repeatedly re-discover the same codebase structure.

## Scope Estimate

**Medium-large** — roughly 2-3 phases:

- Phase A: `CodeIndex` core — chunking (symbol-aware), hash manifest, lazy
  incremental reindex, `.voss/index/` layout, chroma collection `voss_code`
- Phase B: retrieval surface — `code_search` tool, RRF merge with existing
  recall, harness wiring via `attach_memory_tools` pattern
- Phase C: tiered routing — role/tier assignment in `model_router.py` for index
  jobs (embed-adjacent summarization, batch classification), background index
  worker so session start never blocks

Stretch (separate seeds if they grow): global cross-project memory layer;
ingest Claude Code file-memory markdown via `SemanticMemory._ingest_source`.

## Breadcrumbs

- `voss/harness/memory_store.py` — MemoryStore, `_rrf_merge` (L426), `recall` (L406), BM25 code-aware tokenizer, tombstones, source quotas
- `voss_runtime/memory/semantic.py` — Chroma wrapper, embedding function selection (local sentence-transformers vs OpenAI), `_ingest_source` already eats `.md` dirs
- `voss/harness/cli.py:1774` — `attach_memory_tools` wiring pattern to copy for `code_search`
- `voss/harness/model_router.py`, `model_catalog.py`, `model_prefs.py` — tiered routing substrate (models.dev catalog, live swap)
- `language-metadata/` — per-language metadata for symbol-aware chunking
- Design notes (from 2026-06-11 discussion):
  - Code index = derived cache, separate lifecycle from curated memory; drop+rebuild, no tombstones
  - Chunking quality > embedding model choice; start generic sentence-transformers, model is config knob (`default_embedding_model`)
  - Keep hybrid: vectors for concept queries, BM25/grep still wins for symbol lookup — RRF both
  - Freshness via content-hash per file, lazy reindex on recall or git hook; never full reindex per session
  - Local embedding cold-load ~seconds, first big-repo index ~minutes → background worker + progress, non-blocking

## Notes

Captured from design discussion 2026-06-11. Tiered-routing angle: indexing work is
simple, high-volume, parallelizable — exactly the shape cheap fast models handle
well; scalability comes from tier economics, not frontier capability.

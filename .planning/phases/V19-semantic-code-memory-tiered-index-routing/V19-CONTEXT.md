# Phase V19: Semantic Code Memory + Tiered Index Routing - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning
**Note:** Written direct from SPEC per operator preference (skip discuss-phase). All "decisions" below are Claude-discretion defaults derived from SPEC + codebase scout; planner may revisit any of them within SPEC bounds.

<domain>
## Phase Boundary

V19 adds the missing **semantic (embedding) layer** to codebase retrieval: a derived, rebuildable Chroma index (`voss_code`) over symbol-aware code chunks, surfaced as a `code_recall` harness tool + CLI verb + capped V18-region auto-injection — plus an `index_enrich` model-router role so optional enrichment runs on a cheap tier, never the session model. **Reuse-not-rebuild:** consumes M10 code-intel (discovery + symbol start-lines from the SQLite index), F2 hybrid recall machinery (RRF k=60, BM25 degradation), `voss_runtime/memory/semantic.py` (Chroma wrapper + embedding selection), V18 (injection lives inside the packed variable region; enrichment spend in the ledger), and `/models` routing. Adds no second index substrate, no second budget system.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked (VSEM-01..08).** See `V19-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V19-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** CodeIndex (`voss_code` + hash manifest + symbol-aware chunks) under `.voss-cache/`; background non-blocking build with progress; `code_recall` tool (RRF + BM25 degradation, p95 <500ms); CLI verb with `--json`; injection ≤1000 tok inside V18 region with off-switch; `index_enrich` router role + opt-in enrichment profile (OFF default, zero LLM calls when off); `enrich_budget_tokens` cap + ledger line; golden concept-query pytest gate (≥10 queries, expected file top-5).

**Out of scope (from SPEC.md):** modifying M10 search/LSP/SQLite schema; voss-app/TUI panel (A-track follow-up on VSEM-05 JSON); docs/md and `.planning/` corpus; global cross-project memory; code-tuned embedding APIs as default; E-track eval cell; file-watch reindex (M14 owns watch).

</spec_lock>

<decisions>
## Implementation Decisions (Claude-discretion defaults — planner may revisit)

- **D-01 — Module placement:** `CodeIndex` lives in `voss/harness/code/` beside the M10 index it consumes (e.g. `semantic_index.py`), NOT in `memory_store.py` — different lifecycle (derived cache vs curated memory). Reuse `voss_runtime/memory/semantic.py` for the Chroma client; do not duplicate embedding-function selection.
- **D-02 — Chunk boundaries:** M10 `symbols` table start lines sorted per file; chunk = [symbol start, next symbol start) with file-end terminator; preamble (imports/module docstring) = chunk 0. Oversize chunks split at a max-token threshold (planner picks value; ~512 embedding-model tokens typical). No tree-sitter dependency added this phase.
- **D-03 — Manifest:** JSON at `.voss-cache/code/semantic-manifest.json` — `{path: {hash, chunk_ids[]}}`. Hash = same content-hash family M10 uses if one exists, else sha256. Chunk id = `code:<path>:<seq>` mirroring the D-04 composite-id convention in `memory_store.py`.
- **D-04 — Background worker:** thread (daemon) spawned lazily on first session in an indexable repo, same lazy-init spirit as `_maybe_chroma()` (Pitfall 4). sentence-transformers import + model load happen inside the worker. Progress via an index-status line in the existing status surface + a `code_refresh`-style explicit verb; no new daemon process.
- **D-05 — BM25 corpus for code_recall:** build lexical side from the same chunk set (reuse `_bm25_tokenize` — already camelCase/snake_case aware), so RRF fuses like-for-like chunk hits. Do not fuse against MemoryStore's conversation corpus — code recall and memory recall stay separate surfaces.
- **D-06 — Router role mechanics:** `index_enrich` resolves through existing `resolve_key`/prefs machinery as a named role key in config (`[models] index_enrich = "..."`); absent config → enrichment unavailable even if profile flag on (fail closed, no silent fallback to session model).
- **D-07 — Injection selection:** query = current task goal text (the `voss do` prompt / first user message), top-k chunks under the 1000-token cap, formatted as a `## Code Recall` section with file:line headers. Injected through the V18 variable region as evictable content; skip entirely when index not ready (no blocking, no placeholder).
- **D-08 — Golden query gate:** `tests/code_recall/test_golden_queries.py`, ~10–15 (query, expected_file) pairs against the Voss repo itself, run against a committed fixture index built in-test (small subset) or full local build behind a marker — planner decides; gate must be deterministic and CI-runnable without network.

</decisions>

<canonical_refs>
## Canonical References

- `V19-SPEC.md` — locked requirements VSEM-01..08
- `voss/harness/code/index.py` — M10 discovery, symbols table (name + start line), `.voss-cache` schema
- `voss/harness/memory_store.py` — `_rrf_merge` (L426), `_bm25_tokenize`, `_maybe_chroma` lazy-init, composite-id convention
- `voss_runtime/memory/semantic.py` — Chroma wrapper, embedding-function selection, `voss[search]` gating
- `voss/harness/model_router.py` / `model_catalog.py` / `model_prefs.py` — role resolution substrate
- V18 phase artifacts — variable-region packing, ledger format (`token-savings.jsonl`), `/cost` surface
- `.planning/seeds/SEED-002-codebase-rag-tiered-indexing.md` — origin design notes
</canonical_refs>

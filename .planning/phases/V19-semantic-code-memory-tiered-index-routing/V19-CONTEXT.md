# Phase V19: Semantic Code Memory + Tiered Index Routing - Context

**Gathered:** 2026-06-11 (initial direct-from-SPEC draft, then full discuss-phase same day)
**Status:** Ready for planning
**Note:** D-01..D-08 are Claude-discretion defaults (planner may revisit within SPEC bounds). D-09..D-13 are USER-LOCKED via discuss-phase — planner must not change them. SPEC VSEM-05 amended 2026-06-11 (unified recall verb) as part of D-09.

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
- **D-05 — BM25 corpus for code_recall:** build lexical side from the same chunk set (reuse `_bm25_tokenize` — already camelCase/snake_case aware), so RRF fuses like-for-like chunk hits. The agent tool `code_recall` stays code-corpus-only; cross-corpus fusion happens ONLY in the CLI verb (D-09).
- **D-06 — Router role mechanics:** `index_enrich` resolves through existing `resolve_key`/prefs machinery as a named role key in config (`[models] index_enrich = "..."`); absent config → enrichment unavailable even if profile flag on (fail closed, no silent fallback to session model).
- **D-07 — Injection selection:** query = current task goal text (the `voss do` prompt / first user message), top-k chunks under the 1000-token cap, formatted as a `## Code Recall` section with file:line headers. Injected through the V18 variable region as evictable content; skip entirely when index not ready (no blocking, no placeholder).
- **D-08 — Golden query gate:** `tests/code_recall/test_golden_queries.py`, ~10–15 (query, expected_file) pairs against the Voss repo itself, run against a committed fixture index built in-test (small subset) or full local build behind a marker — planner decides; gate must be deterministic and CI-runnable without network.

## User-Locked Decisions (discuss-phase 2026-06-11 — do not change)

- **D-09 — CLI verb = `voss recall <q>`, unified corpus:** top-level verb (not a `voss code` group), queries code index AND memory store, RRF-fused across corpora (rank-based fusion is corpus-agnostic), every hit labeled `[code]`/`[memory]`. `--json` schema includes `source` field. SPEC VSEM-05 amended accordingly. Agent tool `code_recall` remains code-only (VSEM-04 unchanged).
- **D-10 — Default hit display:** one block per hit — clickable `path:line` header, score, 2–3 line excerpt (grep -n mental model). Table/card formats not in v1.
- **D-11 — Embedding default = `all-MiniLM-L6-v2`:** the existing sentence-transformers default path in `semantic.py`; 384-dim, fast CPU cold-load. Swap is config (`default_embedding_model`); golden-query gate is the quality instrument that justifies any future swap.
- **D-12 — Cheap tier documented default = Ollama-local:** docs + example config point `index_enrich` at an Ollama-served small model (gpt-oss / qwen-coder class), $0 and private; Haiku-class API shown as alternate snippet. Profile remains OFF by default (VSEM-07) and fail-closed without config (D-06). Enrichment unit = per-chunk one-liner, embedded alongside code text, parallelizable batches.
- **D-13 — Reindex triggers (three):** (1) background hash-sweep at session start; (2) targeted re-hash on agent file mutation — hook `fs_write`/`fs_edit` tool paths, exact paths known, cheap; (3) explicit refresh verb (`voss recall --refresh` or equivalent). No watch daemon (M14 owns watch); no per-recall sweep (protects p95 <500ms).

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

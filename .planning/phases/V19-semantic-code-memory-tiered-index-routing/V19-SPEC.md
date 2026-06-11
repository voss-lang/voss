# Phase V19: Semantic Code Memory + Tiered Index Routing — Specification

**Created:** 2026-06-11
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

Agents answer concept-level codebase queries ("where do we handle retry backoff") through a persistent, derived vector index instead of frontier-token agentic grep loops — with all index-enrichment work routed to a cheap model tier (or no LLM at all), so frontier spend on repeated codebase re-discovery drops to zero for indexed concepts.

## Background

Voss already owns every substrate V19 needs — none of them do semantic code retrieval:

- **M10 code-intel** (`voss/harness/code/`): git-aware file discovery, SQLite index at `.voss-cache/` with per-file language + symbol names and **start lines** (regex extraction, ≤200 symbols/file), `code_search` (lexical/structural via ast-grep + regex fallback), LSP registry. No embeddings — concept queries fail.
- **F2 hybrid recall** (shipped, commit ebcc282): `MemoryStore.recall()` fuses BM25 + Chroma via RRF k=60 (`memory_store.py:426`), code-aware tokenizer, tombstones, BM25-only degradation when Chroma absent. Indexes only conversation artifacts (turns/ledgers/decisions/conventions/notes) — never code.
- **Chroma wrapper** (`voss_runtime/memory/semantic.py`): PersistentClient + embedding-function selection (local sentence-transformers default, OpenAI `text-embedding-*` when keyed) behind `voss[search]` extra.
- **Model routing** (`voss/harness/model_router.py` / `model_catalog.py` / `model_prefs.py`): models.dev catalog, `resolve_key`, single LiteLLMProvider serving every endpoint. No role/tier concept for background index jobs.
- **V18 allocator**: packs the variable context region under a token ceiling; budget telemetry + savings ledger + `/cost`.

The gap: no embedding index over code chunks, no semantic recall surface, no cheap-tier dispatch for index work. Note: `language-metadata/` contains only Voss-language `voss.yml` — it is NOT a polyglot chunking source; chunk boundaries come from the M10 symbol index.

## Requirements

1. **VSEM-01 — CodeIndex derived cache**: A `CodeIndex` component builds a Chroma collection `voss_code` over symbol-aware chunks of the M10-discovered code file set, stored under `.voss-cache/` with a content-hash manifest.
   - Current: no embedding index over code exists anywhere.
   - Target: `.voss-cache/` contains the `voss_code` Chroma collection + a manifest mapping file path → content hash → chunk ids. Chunks respect symbol boundaries derived from the M10 symbol index (start lines; end = next-symbol/file-end heuristic). Corpus = exactly the M10 discovery set (vendored excluded, git-aware); repo docs/markdown and `.planning/` are excluded.
   - Acceptance: deleting `.voss-cache/` and re-running the indexer reproduces a working index from the repo alone (derived-cache property); a test asserts chunks for a known multi-symbol file split on its symbol boundaries.

2. **VSEM-02 — Incremental reindex, never full**: After first build, reindexing embeds only files whose content hash changed.
   - Current: n/a (no index).
   - Target: hash-unchanged files produce zero embedding calls on reindex; changed-file batch reindex completes in <2s per batch (excluding embedding-model cold load).
   - Acceptance: test instruments the embed path, touches one file, asserts exactly that file's chunks re-embed; full-corpus re-embed on unchanged repo is a test failure.

3. **VSEM-03 — Background, non-blocking build**: First index build runs fully async; session start never blocks on it.
   - Current: n/a.
   - Target: `voss do`/`voss chat` are usable immediately on an unindexed repo; recall degrades gracefully (BM25/lexical only) until embeddings are ready; index progress is observable (status line or verb).
   - Acceptance: test starts a session on an unindexed fixture repo and asserts first prompt round-trip completes without waiting on the indexer; recall before-ready returns results with a `degraded`/source marker rather than erroring.

4. **VSEM-04 — `code_recall` hybrid surface**: A new harness tool `code_recall` returns RRF-fused (BM25 + vector, k=60, F2 pattern) chunk hits with file:line locators; name avoids collision with M10's `code_search`.
   - Current: agents have only lexical/structural `code_search` + `fs_grep`.
   - Target: `code_recall(query, top_k)` registered in the tool registry; hits carry file path, line range, score, excerpt; Chroma-absent installs degrade to BM25-only without error (F2 degradation contract); recall query p95 <500ms on an indexed ~10K LoC repo.
   - Acceptance: tool-registry test asserts registration + schema; degradation test passes with chromadb uninstalled; perf test asserts p95 <500ms on the fixture repo.

5. **VSEM-05 — CLI verb**: A human-facing CLI verb (`voss recall <query>` or equivalent) exposes the same retrieval with plain + JSON output.
   - Current: no human surface for semantic code query.
   - Target: verb returns ranked hits (file:line, excerpt) on stdout; `--json` emits machine-readable hits (future A-track panel consumes this; panel itself out of scope).
   - Acceptance: CLI test asserts exit 0 + ranked output on indexed fixture; `--json` output validates against a documented schema.

6. **VSEM-06 — Auto-injection inside V18 region**: Top-k task-relevant chunks may be injected into system context, capped ≤1000 tokens, living inside the V18-packed variable region (allocator may evict/fold them), with a config off-switch.
   - Current: M10 injects a `## Project Index` section (≤1500 tokens); no semantic injection exists.
   - Target: injection ≤1000 tokens measured by the V18 token counter; packed/evicted under pressure like any variable-region content (no second budget system); `[code_recall] inject = false` disables it entirely.
   - Acceptance: test asserts injected section token count ≤1000; V18 allocator test asserts the section is evictable; off-switch test asserts zero injection bytes.

7. **VSEM-07 — Tiered routing role + enrichment profile (off by default)**: Index-enrichment jobs (one-line symbol/chunk summaries) dispatch through a model-router role resolving to a configured cheap tier (e.g. Ollama-local GPT-OSS, Haiku-class); the enrichment profile is opt-in and OFF by default.
   - Current: `model_router.py` has no role/tier concept; all calls resolve to the session model.
   - Target: a named router role (e.g. `index_enrich`) resolves independently of the chat model via config; with profile off, indexing performs **zero** LLM calls (embeddings + BM25 only); with profile on, summaries are embedded alongside code text.
   - Acceptance: profile-off test asserts no provider calls during full index build; profile-on test (stub provider) asserts enrichment calls route to the `index_enrich` role's model, not the session model.

8. **VSEM-08 — Enrichment cost guardrails**: When the enrichment profile is on, a per-run token cap aborts the enrichment batch at the cap, and enrichment spend appears in the V18 cost/savings ledger + `/cost`.
   - Current: no cap or ledger line exists (no enrichment exists).
   - Target: `enrich_budget_tokens` (config) halts enrichment cleanly mid-batch when exceeded (index remains valid, un-enriched chunks marked); spend visible as a distinct ledger line.
   - Acceptance: test with tiny cap asserts clean abort + valid index + correct ledger entry; `/cost` output test shows the enrichment line.

## Boundaries

**In scope:**
- `CodeIndex` (Chroma `voss_code` collection, hash manifest, symbol-aware chunking) under `.voss-cache/`
- Background index worker + progress observability
- `code_recall` harness tool with RRF fusion + BM25 degradation
- CLI verb with plain + `--json` output
- Auto-injection (≤1000 tok, V18-region, off-switch)
- `index_enrich` router role + opt-in enrichment profile + cost cap + ledger line
- Golden concept-query pytest gate (~10–15 queries against the Voss repo itself)

**Out of scope:**
- Replacing or modifying M10 lexical/structural search, LSP surfaces, or its SQLite index schema — V19 consumes it
- voss-app/TUI recall panel — deferred to an A-track follow-up consuming VSEM-05 JSON
- Repo docs/markdown or `.planning/` corpus — memory store + `_ingest_source` own markdown; revisit as separate seed
- Global cross-project memory layer — separate seed if it grows
- Code-tuned embedding API models as default — start local sentence-transformers; model stays a config knob (`default_embedding_model`)
- E-track eval cell for retrieval quality — golden pytest gate suffices for V19; E-track cell is a later addition
- File-watch-driven reindex — lazy hash check + explicit refresh only (M14 owns watch)

## Constraints

- Index lives under `.voss-cache/` (rebuildable) per M2 COG-07 / M10 convention — never `.voss/` (durable, curated)
- chromadb stays optional behind `voss[search]`; every surface degrades to BM25-only without it (F2 contract)
- No tombstones in CodeIndex — derived cache, drop + rebuild is the recovery path
- Recall p95 <500ms indexed; incremental batch <2s; no first-index deadline (background-only)
- Injection ≤1000 tokens inside the V18 variable region; no second budget system
- Profile-off indexing performs zero LLM calls
- No new heavyweight deps beyond what `voss[search]` already pulls; sentence-transformers cold-load happens in the background worker, never on the session thread
- Frozen schemas (V-track sentinels) untouched

## Acceptance Criteria

- [ ] `rm -rf .voss-cache/` + reindex reproduces a working `voss_code` index (derived-cache property)
- [ ] Chunk-boundary test: known multi-symbol fixture file splits on symbol boundaries
- [ ] Touch-one-file test: exactly that file's chunks re-embed; unchanged-repo reindex performs zero embeds
- [ ] Session on unindexed repo: first prompt round-trip completes without blocking on indexer
- [ ] `code_recall` registered; Chroma-absent install returns BM25-only hits without error
- [ ] Recall p95 <500ms on indexed ~10K LoC fixture
- [ ] CLI verb exits 0 with ranked file:line hits; `--json` validates against documented schema
- [ ] Injection section ≤1000 tokens (V18 counter), evictable by allocator, zero bytes when disabled
- [ ] Profile-off full index build: zero LLM provider calls (instrumented)
- [ ] Profile-on enrichment routes via `index_enrich` role, not session model (stub provider test)
- [ ] Tiny-cap enrichment run aborts cleanly: index valid, un-enriched chunks marked, ledger line correct
- [ ] Golden concept-query gate: ≥10 queries against the Voss repo, expected file in top-5 for each, as a deterministic pytest
- [ ] Coherence guard: `voss do`/`voss chat` work end-to-end every wave (PRD §9)

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                            |
|--------------------|-------|------|--------|--------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Token-economics frame; measurable surfaces        |
| Boundary Clarity   | 0.87  | 0.70 | ✓      | Panel deferred to A-track; corpus locked to M10 set |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Perf budgets, injection cap, cost cap all numeric |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | Golden query gate + instrumented zero-LLM checks  |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      |                                                  |

## Interview Log

| Round | Perspective              | Question summary                          | Decision locked                                                        |
|-------|--------------------------|-------------------------------------------|------------------------------------------------------------------------|
| 1     | Researcher               | Enrichment required in v1?                | Optional profile, OFF by default; plumbing built + tested              |
| 1     | Researcher               | Corpus coverage?                          | M10 discovery set only; no docs/md, no `.planning/`                    |
| 1     | Researcher               | Recall surfaces?                          | All four selected: tool + CLI + injection + panel (panel later deferred)|
| 2     | Researcher + Simplifier  | Perf budgets?                             | Background-only first index; recall p95 <500ms; incremental <2s/batch  |
| 2     | Researcher + Simplifier  | Injection cap + V18 interplay?            | ≤1000 tok inside V18 variable region; evictable; off-switch            |
| 2     | Simplifier               | Minimal panel?                            | Deferred to A-track follow-up consuming VSEM-05 `--json`               |
| 3     | Boundary Keeper          | Quality proof?                            | Golden concept-query set (~10–15), expected file top-5, pytest gate    |
| 3     | Boundary Keeper          | Enrichment guardrails?                    | `enrich_budget_tokens` cap + V18 ledger line + `/cost` visibility      |

---

*Phase: V19-semantic-code-memory-tiered-index-routing*
*Spec created: 2026-06-11*
*Next step: /gsd-discuss-phase V19 — implementation decisions (how to build what's specified above)*

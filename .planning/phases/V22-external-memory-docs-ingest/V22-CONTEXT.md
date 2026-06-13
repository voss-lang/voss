# Phase V22: External Memory & Docs Ingest - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning
**Source:** CONTEXT-direct from V22-SPEC.md (V-track spec→context path; discuss-phase skipped — requirements locked in SPEC, this captures HOW)

<domain>
## Phase Boundary

Bring config-declared markdown corpora (repo docs, operator external vaults) into `voss recall` and the agent recall tool as labeled, derived sources. Each `[[recall.sources]]` entry (name/path/glob) ingests into its own labeled Chroma collection + per-source content-hash manifest under `.voss-cache/recall/<name>/`, fused by RRF, labeled `[<name>]`, **read-only forever**. Direct port of the V19 CodeIndex pattern with section-boundary (markdown heading) chunking instead of symbol-boundary. Requirements VXMEM-01..08 locked in `V22-SPEC.md`.

**Reuse-not-rebuild:** mirror `voss/harness/code/semantic_index.py` (CodeIndex/CodeIndexService) — manifest, incremental never-full build, daemon background build, `RRF(BM25+vector)` degradation, `Hit` source labeling. Plug into existing `MemoryStore._rrf_merge` fusion in `voss recall` (cli.py:4805) and the agent recall tool. No new store type, no new schema, no new embedding stack.

</domain>

<decisions>
## Implementation Decisions

### Source declaration (USER-LOCKED via SPEC)
- **D-01 — Explicit-only:** every source declared in `[[recall.sources]]` (name/path/glob). No zero-config repo-docs default, no auto-discovery. Repo docs is an ordinary declared source. [VXMEM-01]
- **D-02 — Array-of-tables config:** `[[recall.sources]]` TOML array-of-tables; V22 adds a stdlib `tomllib` parse path for this section (existing regex parser cannot read array-of-tables). Existing regex-parsed sections untouched. [VXMEM-01]
- **D-03 — Reserved-name + duplicate rejection:** names `code`/`memory`/`global` rejected at config load with clear error; duplicate names across entries rejected. [VXMEM-02]
- **D-04 — Markdown only:** ingest filters to `.md`/`.markdown`; non-md under the glob skipped. [VXMEM-04]

### Index mechanics (USER-LOCKED via SPEC)
- **D-05 — Per-source isolation:** each source = own Chroma collection + own `semantic-manifest.json` under `.voss-cache/recall/<name>/`; one source rebuilding never invalidates another. Derived cache, rm-safe, rebuildable from source files alone. [VXMEM-03]
- **D-06 — Section-boundary chunking:** chunk on markdown heading boundaries (section = heading → next same-or-higher heading); preamble = own chunk; heading-less file = one chunk; oversize regions sub-split via existing `_MAX_CHUNK_CHARS` guard. [VXMEM-04]
- **D-07 — Incremental never-full:** hash-skip unchanged files (zero embeds); changed file re-embeds only its chunks (stale ids deleted); deleted source file purges its chunks. [VXMEM-05]
- **D-08 — Background daemon, read-only:** CodeIndexService-pattern daemon build off session-start path; degrade-until-ready; zero writes/renames/deletes under any source path. [VXMEM-06]

### Recall blending (USER-LOCKED via SPEC)
- **D-09 — Both surfaces, RRF, `[<name>]` labels:** external hits fuse via `MemoryStore._rrf_merge` into BOTH the agent recall tool AND `voss recall` CLI; `[<name>]` in plain output, `source` field in `--json`; chromadb-absent degrades to BM25-only without error. [VXMEM-07]

### Verification (USER-LOCKED via SPEC)
- **D-10 — Golden-query gate:** committed fixture vault under `tests/` + ~8–12 golden queries; runs in CI without network/OpenAI key (local sentence-transformers default); passes with and without chromadb. [VXMEM-08]

### Claude's Discretion (planner may revise within decisions above)
- **D-11 — Module placement:** new `voss/harness/recall/` package (or `voss/harness/external_index.py`) mirroring `code/semantic_index.py`; `ExternalSource`/`ExternalSourceIndex` class per source + an `ExternalRecallService` daemon wrapper. Planner picks exact names; mirror CodeIndex/CodeIndexService shape.
- **D-12 — Collection naming:** Chroma collection per source, e.g. `voss_recall_<name>` (sanitized), distinct from `voss_code`/`voss_semantic`. Planner sets sanitization rule (name already validated for reserved/duplicate at D-03).
- **D-13 — Chunk id convention:** `<name>:<rel_path>:<seq>` composite (mirror CodeIndex `code:` prefix → guarantees no locator collision with code:/turn:/note: ids in cross-corpus RRF dedup). Source name as prefix.
- **D-14 — Heading-boundary extraction:** parse ATX headings (`#`..`######`); a section runs from a heading line to the next heading of same-or-higher level (or EOF); content before first heading = preamble chunk. Reuse `_split_oversize` verbatim from `semantic_index.py` for the oversize guard. Setext headings (`===`/`---` underline) optional — planner decides; ATX is the floor.
- **D-15 — Manifest shape:** reuse CodeIndex manifest schema — `{embedding_model, files: {rel_path: {hash, chunk_ids}}}`; track embedding model for swap→drop+rebuild (CodeIndex Pitfall 1 parity).
- **D-16 — Recall fan-out:** `voss recall` already does `_rrf_merge([code_hits, mem_hits])`; extend to `_rrf_merge([code_hits, mem_hits, *external_hits_per_source])`. Agent recall tool path gets the same external fan-out. Planner finds the agent-tool recall call site (memory recall tool) and wires identically.
- **D-17 — Off-switch:** mirror V21's single-switch ergonomics — absent `[[recall.sources]]` = zero sources/zero I/O is the natural off state; no separate boolean needed (declaring nothing disables everything). Planner may add a per-source enable flag only if trivially free.
- **D-18 — Service lifecycle:** spawn `ExternalRecallService.ensure_background_build()` from the same session-start hook that starts `CodeIndexService` (find the existing call site in chat/do/serve boot); `--refresh` on `voss recall` rebuilds external sources alongside the code index.
- **D-19 — Path resolution:** `path` absolute or `~`-expanded; relative paths resolve against cwd (the repo). Non-existent source path → skip cleanly (no error, like `_ingest_source` today), log degraded.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary reuse pattern (mirror this)
- `voss/harness/code/semantic_index.py` — CodeIndex + CodeIndexService: manifest (`_load/_save_manifest`, L109-124), incremental `build()` (L186-283), `_split_oversize`/`extract_chunks` chunking (L36-89), `query()` RRF+degrade (L492-530), daemon service (L533-594), embedding-model-swap drop (`_drop_collection` L173-182), the 7 numbered Pitfalls in comments. **V22 is this file with heading-boundary chunking.**

### Fusion + recall surfaces (plug into these)
- `voss/harness/cli.py:4805` — `recall_cmd`: `_rrf_merge([code_hits, mem_hits])` fan-out (L4841), `[source]` plain + `--json` output (L4843-4858), `--refresh` trigger (L4823-4830). Extend fan-out to external sources.
- `voss/harness/memory_store.py:452` — `MemoryStore.recall` + `_rrf_merge` (L472, rank-based corpus-agnostic, k=60), `Hit` dataclass (`source`/`locator`/`score`/`excerpt`/`line_start`). Agent recall tool path to find + mirror.
- Agent-side recall tool — find the memory/recall tool registration that exposes `MemoryStore.recall` to agents; wire external fan-out there too (VXMEM-07 "both surfaces").

### Config
- `voss/harness/config.py` — regex section parser (`config.toml` at `~/.config/voss/config.toml`), `[code_recall]`/`[memory]` reader pattern (L276-333). Add `tomllib` parse path for `[[recall.sources]]`; do NOT break existing regex sections.

### Chroma wrapper
- `voss_runtime/memory/semantic.py` — `SemanticMemory` (persist_dir/collection_name params, `_embedding_function` L44-57, `_ingest_source` primitive L59-71 to supersede).

### Prior-phase precedent
- `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md` + `V19-CONTEXT.md` — the pattern V22 ports; V19 out-of-scope explicitly deferred this corpus.
- `.planning/phases/V21-global-cross-project-memory/V21-CONTEXT.md` — source-label conventions across >2 corpora (`[global]`), single off-switch ergonomics, RRF cross-corpus precedent.
- `.planning/phases/V22-external-memory-docs-ingest/V22-SPEC.md` — VXMEM-01..08 locked requirements + acceptance criteria.

</canonical_refs>

<specifics>
## Specific Ideas

- Reuse `_split_oversize` from `semantic_index.py` verbatim (oversize guard is chunking-strategy-agnostic).
- Hit labeling: `[<name>]` joins V19's `[code]`/`[memory]` and V21's `[global]` — N-corpus labeled display in `voss recall`.
- Chunk id prefix = source name → no locator collision in cross-corpus RRF dedup (CodeIndex `code:` prefix precedent, Pitfall 8).
- Read-only assertion test: snapshot source-file mtimes+hashes before/after full ingest+recall cycle, assert byte-identical (SecondBrain raw-sources immutability honored by construction).
- Golden gate must pass with chromadb uninstalled (BM25 degradation) AND with no OPENAI_API_KEY (local embedding default) — CI parity with V19's gate.
- Fixture vault: small committed markdown tree under `tests/` (e.g. `tests/fixtures/recall_vault/`) with known heading structure so chunking + golden-query assertions are deterministic.

</specifics>

<deferred>
## Deferred Ideas

- Retrieval ranking / telemetry / quality-floor over fused results → V23 (next phase, already specced in ROADMAP).
- Non-markdown formats (PDF/HTML/`.txt`/`.rst`) — section chunking is markdown-specific; later seed.
- Write-back / sync to external sources — read-only forever (out of scope by design).
- Tiered-routing enrichment (VSEM-07/08) of markdown chunks — not extended this phase.
- voss-app/TUI panel over external-source hits — A-track follow-up consuming `voss recall --json`.
- `.planning/` GSD artifacts as a source — opt-in only as an ordinary declared source (never default).

</deferred>

---

*Phase: V22-external-memory-docs-ingest*
*Context gathered: 2026-06-13 via spec→context-direct path*

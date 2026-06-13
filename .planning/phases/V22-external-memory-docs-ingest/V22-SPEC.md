# Phase V22: External Memory & Docs Ingest — Specification

**Created:** 2026-06-13
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

`voss recall` (and the agent-side recall tool) answers from designated markdown corpora that live outside code and conversation — repo docs and operator-configured external memory directories — where each corpus is a config-declared `[[recall.sources]]` source (name, path, glob) ingested into its own labeled, derived Chroma collection with a per-source content-hash manifest, fused into existing recall by RRF and labeled `[<name>]`, **read-only forever** (source files are never written back).

## Background

Voss already owns every substrate V22 needs; none of them ingest external markdown into recall:

- **V19 CodeIndex** (`voss/harness/code/semantic_index.py`): the canonical derived-index pattern — per-corpus Chroma collection (`voss_code`), content-hash manifest (`.voss-cache/code/semantic-manifest.json`) for incremental never-full reindex, symbol-boundary chunking with 800-char oversize subsplit, `RRF(BM25+vector)` query degrading to BM25-only when chromadb is absent, and `CodeIndexService` daemon-thread background build that never blocks session start. V19 explicitly deferred "repo docs/markdown or `.planning/` corpus" to a separate seed — this is that seed.
- **F2 unified recall** (`voss/harness/memory_store.py:452` `MemoryStore.recall`, `_rrf_merge` at `:472`): rank-based, corpus-agnostic RRF fusion; every `Hit` carries a `source` label.
- **`voss recall` CLI** (`voss/harness/cli.py:4805`): already fuses `CodeIndex.query` + `MemoryStore.recall` via `MemoryStore._rrf_merge`, printing `[code]`/`[memory]` source-labeled hits with `--json`.
- **V21 global memory** (shipped): established the source-label convention across >2 corpora — `[global]` joins `[code]`/`[memory]`, a single config off-switch, surfaces in BOTH the agent recall tool AND `voss recall`. V22 adds N more labeled corpora to the same fusion.
- **`SemanticMemory._ingest_source`** (`voss_runtime/memory/semantic.py:59`): a primitive whole-file markdown ingest (no chunking, no manifest, not wired into unified recall). V22 supersedes its naive ingest with the CodeIndex-grade pattern; the lineage is conceptual, not a literal reuse of this method.
- **Config** (`voss/harness/config.py`, `~/.config/voss/config.toml`): hand-rolled regex section parser (`[harness]`, `[memory]`, `[code_recall]`, …). It cannot parse TOML array-of-tables — V22 adds a real parse path (stdlib `tomllib`) for the `[[recall.sources]]` section.

The gap: no config-declared external-corpus ingest, no per-source labeled collection/manifest, no fusion of external markdown into recall.

## Requirements

1. **VXMEM-01 — `[[recall.sources]]` config schema (explicit-only)**: Sources are declared as TOML array-of-tables, each with `name`, `path`, `glob`; nothing is ingested unless declared (no zero-config repo-docs, no auto-discovery).
   - Current: `config.toml` has no `[recall.sources]` concept; the regex parser cannot read array-of-tables.
   - Target: a parse path (stdlib `tomllib`) reads `[[recall.sources]]` into ordered `{name, path, glob}` records; `path` may be absolute or `~`-expanded; missing/empty section → zero sources (no-op). Repo docs is just an ordinary declared source (e.g. `name="docs", path="docs", glob="**/*.md"`), not a built-in default.
   - Acceptance: a test config with two `[[recall.sources]]` entries parses to exactly two records with correct name/path/glob; a config with no section yields zero sources and zero index I/O.

2. **VXMEM-02 — Reserved-name validation**: Source names `code`, `memory`, and `global` (the V19/V21 reserved labels) are rejected at config load with a clear error.
   - Current: no source-name namespace exists.
   - Target: declaring a `[[recall.sources]]` entry named `code`/`memory`/`global` raises a clear configuration error naming the offending source; all other names are accepted; duplicate names across entries are also rejected.
   - Acceptance: a test asserts a config with `name="code"` errors with a message containing the reserved name; a config with two entries both `name="docs"` errors on the duplicate; a valid distinct-name config loads clean.

3. **VXMEM-03 — Per-source derived index (labeled collection + hash manifest)**: Each source ingests into its own labeled Chroma collection under `.voss-cache/`, with a per-source content-hash manifest — a derived cache, rebuildable from the source files alone (same lifecycle as V19 CodeIndex).
   - Current: no external-corpus collection or manifest exists anywhere.
   - Target: `.voss-cache/recall/<name>/` holds the source's Chroma collection + a `semantic-manifest.json` mapping file path → content hash → chunk ids; the manifest tracks the embedding model so a model swap drops + rebuilds (CodeIndex Pitfall 1 parity); deleting `.voss-cache/recall/` and re-running reproduces a working index from the source files alone.
   - Acceptance: a test ingests a fixture vault, deletes `.voss-cache/recall/`, re-ingests, and asserts an equivalent working index (derived-cache property); the manifest contains one entry per ingested file with a content hash.

4. **VXMEM-04 — Section-boundary markdown chunking (markdown-only)**: Ingest filters to markdown (`.md`/`.markdown`) and chunks on markdown heading boundaries, reusing the CodeIndex oversize-subsplit guard.
   - Current: `_ingest_source` adds whole files (no chunking) and globs `.md/.txt/.rst`.
   - Target: only `.md`/`.markdown` files matching the source glob are ingested; chunk boundaries fall on markdown headings (a section = heading through the next same-or-higher heading); preamble before the first heading is its own chunk; a heading-less file is one whole-file chunk; oversize regions sub-split with the existing `_MAX_CHUNK_CHARS` guard so no chunk silently truncates in the embedding window.
   - Acceptance: a test asserts a multi-heading fixture file splits on its heading boundaries; a heading-less fixture file yields exactly one chunk; an oversize section sub-splits; a `.txt`/`.pdf` file under the glob is NOT ingested.

5. **VXMEM-05 — Incremental, never-full reindex**: After the first build, only files whose content hash changed are re-embedded; deleted source files purge their chunks.
   - Current: n/a (no external index).
   - Target: hash-unchanged files produce zero embedding calls on reindex; a changed file re-embeds exactly its own chunks (stale chunk ids deleted); a file removed from the source purges its chunks from the collection and manifest.
   - Acceptance: a test instruments the embed path, touches one file in a fixture vault, and asserts exactly that file's chunks re-embed; a full re-embed on an unchanged vault is a test failure; deleting a source file removes its chunks on the next build.

6. **VXMEM-06 — Background, non-blocking, read-only ingest**: Source ingest runs on a background daemon (CodeIndexService pattern); session start never blocks on it; recall degrades until ready; source files are **never written back**.
   - Current: n/a; no external ingest exists.
   - Target: a daemon-thread service builds external-source indexes off the session-start path (mirrors `CodeIndexService.ensure_background_build`); recall before-ready returns degraded/BM25 (or empty) source hits rather than erroring or blocking; ingest opens source files read-only and performs zero writes, renames, or deletes under any declared source path (SecondBrain raw-sources immutability respected by construction).
   - Acceptance: a test starts a session on a fixture-vault repo and asserts first prompt round-trip completes without waiting on the ingest; a test snapshots source-file mtimes/contents before and after a full ingest + recall cycle and asserts zero source bytes changed.

7. **VXMEM-07 — Fused recall on both surfaces, `[<name>]`-labeled**: External-source hits fuse (RRF, rank-based) into BOTH the agent-side recall tool AND the `voss recall` CLI, each hit labeled with its source `name`.
   - Current: `voss recall` and the agent recall tool fuse only `[code]`/`[memory]`/`[global]`.
   - Target: every declared external source participates in the same `_rrf_merge` across corpora; hits carry `source=<name>` and render `[<name>]` in CLI plain output and the `source` field in `--json`; the agent recall tool returns external hits alongside code/memory/global; chromadb-absent installs degrade to BM25-only without error (F2 degradation contract).
   - Acceptance: a CLI test with a populated fixture vault asserts `[<name>]`-labeled hits in both plain and `--json` output (with a `source` field); a degradation test passes with chromadb uninstalled; an agent-recall-tool test asserts external hits are returned.

8. **VXMEM-08 — Golden-query gate over a fixture vault**: A pytest golden-query gate ships a small fixture markdown corpus and ~8–12 queries asserting source-labeled hits land.
   - Current: no end-to-end recall-quality proof for external markdown exists.
   - Target: a fixture vault (committed under `tests/`) + a golden-query suite (~8–12 queries) asserts each query returns the expected source-labeled hit(s) above the others; the gate runs in CI without network and without an OpenAI key (local embedding default).
   - Acceptance: the golden-query pytest gate passes against the fixture vault; running it with chromadb uninstalled still passes via BM25 degradation.

## Boundaries

**In scope:**
- `[[recall.sources]]` config schema (array-of-tables: name/path/glob) + `tomllib` parse path + reserved-name/duplicate validation
- Per-source labeled Chroma collection + per-source content-hash manifest under `.voss-cache/recall/<name>/` (derived, rm-safe, rebuildable)
- Section-boundary markdown chunking (`.md`/`.markdown` only) with oversize subsplit
- Incremental never-full reindex (hash-skip; deleted-file purge)
- Background daemon build (CodeIndexService pattern), degrade-until-ready
- Read-only ingest (zero writes to source paths — asserted)
- RRF fusion + `[<name>]` labels in BOTH the agent recall tool AND `voss recall` (plain + `--json`)
- Golden-query pytest gate over a committed fixture vault

**Out of scope:**
- Writing/syncing back to external sources — read-only forever this phase (SecondBrain raw-sources immutability; the whole point)
- Non-markdown formats (PDF/HTML/`.txt`/`.rst`) — section-boundary chunking is markdown-specific; later seed
- Auto-discovery of external dirs — explicit `[[recall.sources]]` declaration only (no surprise I/O)
- `.planning/` GSD artifacts as a default source — privacy/noise; opt-in only as an ordinary declared source
- Retrieval ranking/telemetry/quality-floor over the fused result — that is V23
- Tiered-routing enrichment of markdown chunks (V19 VSEM-07/08 enrichment) — not extended to external sources this phase
- voss-app/TUI panel over external-source hits — A-track follow-up consuming `voss recall --json`

## Constraints

- **Config parser:** the existing `config.py` regex parser cannot read array-of-tables; V22 must add a real TOML parse path (stdlib `tomllib`, Python ≥3.11 — already the project floor) for the `[[recall.sources]]` section without breaking the existing regex-parsed sections.
- **Reuse-not-rebuild:** mirror V19 CodeIndex (`semantic_index.py`) — manifest, incremental build, daemon service, `RRF(BM25+vector)` degradation, `Hit` source labeling, `MemoryStore._rrf_merge`. No new store type, no new schema substrate, no new embedding stack.
- **Chroma optionality:** chromadb is the `voss[search]` extra; every external-source path must degrade to BM25-only (or empty) without error when it is absent (F2/V19 degradation contract).
- **No network, no key in CI:** the golden gate runs on the local sentence-transformers embedding default; no OpenAI key required.
- **Read-only by construction:** no code path under ingest may open a source file for write or mutate a source directory.
- **Per-source isolation:** each source gets its own collection + manifest so one source rebuilding/changing never invalidates another.

## Acceptance Criteria

- [ ] `[[recall.sources]]` array-of-tables parses to ordered `{name, path, glob}` records; absent section → zero sources, zero I/O
- [ ] Source named `code`/`memory`/`global` is rejected at load with a clear error; duplicate names rejected
- [ ] Each source has its own `.voss-cache/recall/<name>/` collection + content-hash manifest; `rm -rf .voss-cache/recall` + rebuild reproduces a working index from source files alone
- [ ] `.md`/`.markdown` files chunk on heading boundaries (preamble = own chunk, heading-less = one chunk, oversize subsplit); non-markdown files under the glob are not ingested
- [ ] Touching one file re-embeds exactly its chunks; unchanged-vault full re-embed is a failure; deleted source file purges its chunks
- [ ] Session start does not block on external ingest; recall degrades until ready
- [ ] Source files are byte-identical before and after a full ingest + recall cycle (read-only assertion)
- [ ] External-source hits fuse via RRF and render `[<name>]` in BOTH the agent recall tool AND `voss recall` (plain + `--json` with `source` field)
- [ ] Recall degrades to BM25-only without error when chromadb is uninstalled
- [ ] Golden-query pytest gate over the committed fixture vault passes (with and without chromadb)

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Roadmap goal unusually precise; reuse target (CodeIndex) named |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Explicit-only declaration + explicit out-of-scope (incl. V23 split) |
| Constraint Clarity | 0.82  | 0.65 | ✓      | tomllib parse path, read-only, per-source isolation, Chroma degrade |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 10 pass/fail criteria + golden gate                          |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective     | Question summary                          | Decision locked                                              |
|-------|-----------------|-------------------------------------------|--------------------------------------------------------------|
| 0     | Researcher (scout) | What substrate exists? (CodeIndex, recall CLI, config parser, V21) | CodeIndex is canonical pattern; `_ingest_source` is a primitive to supersede; config = regex parser (no array-of-tables) |
| 1     | Boundary Keeper | Repo-docs zero-config vs all-declared?    | Explicit-only — every source (incl. repo docs) declared in `[[recall.sources]]`; no auto-discovery |
| 1     | Researcher      | Config shape for sources?                 | Array-of-tables `[[recall.sources]]`; V22 adds `tomllib` parse path |
| 1     | Boundary Keeper | Which recall surfaces?                     | Both agent tool + `voss recall` CLI, like V21               |
| 1     | Failure Analyst | Build trigger for large/network vaults?   | Background daemon (CodeIndexService pattern), degrade-until-ready |
| 2     | Boundary Keeper | File types ingested?                       | Markdown only (`.md`/`.markdown`); non-md out of scope       |
| 2     | Failure Analyst | Source-name collision with reserved labels?| Reject `code`/`memory`/`global` (and duplicates) at config load |
| 2     | Seed Closer     | What proves done?                          | Golden-query gate over a committed fixture vault (~8–12 queries) |

---

*Phase: V22-external-memory-docs-ingest*
*Spec created: 2026-06-13*
*Next step: /gsd-discuss-phase V22 — implementation decisions (collection naming, daemon wiring, chunker internals, fixture vault design)*

---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 02
type: execute
wave: 1
depends_on: [V19-01]
files_modified:
  - voss/harness/code/semantic_index.py
autonomous: true
requirements: [VSEM-01, VSEM-02]
must_haves:
  truths:
    - "CodeIndex.build() populates a voss_code Chroma collection over symbol-aware chunks under .voss-cache/code/"
    - "Chunks split on M10 symbol boundaries; zero-symbol files become one whole-file chunk; oversize chunks sub-split"
    - "rm -rf .voss-cache/code/chroma + rebuild reproduces a working index from the repo alone (derived cache)"
    - "Hash-unchanged files produce zero embedding calls on reindex; only changed files re-embed"
    - "CodeIndex.query() returns RRF(BM25+vector) Hits with file:line; degrades to BM25-only when Chroma absent"
  artifacts:
    - path: "voss/harness/code/semantic_index.py"
      provides: "extract_chunks, _chunk_id, CodeIndex (build/query/manifest/incremental)"
      min_lines: 180
      exports: ["extract_chunks", "CodeIndex"]
    - path: ".voss-cache/code/semantic-manifest.json"
      provides: "path -> {hash, chunk_ids[], embedding_model} manifest (runtime artifact)"
      contains: "chunk_ids"
  key_links:
    - from: "voss/harness/code/semantic_index.py"
      to: ".voss-cache/code/index.db (M10 symbols table)"
      via: "sqlite read-only join symbols->files"
      pattern: "FROM symbols"
    - from: "voss/harness/code/semantic_index.py"
      to: "voss_runtime.memory.semantic.SemanticMemory"
      via: "_maybe_semantic with collection_name=voss_code"
      pattern: "collection_name=\"voss_code\""
    - from: "voss/harness/code/semantic_index.py"
      to: "MemoryStore._rrf_merge / _bm25_tokenize"
      via: "import + static call (no copy)"
      pattern: "_rrf_merge"
---

<objective>
Build the core `CodeIndex` in `voss/harness/code/semantic_index.py`: symbol-aware chunking from the M10 SQLite index, a content-hash manifest for incremental (never-full) reindex, a `voss_code` Chroma collection via the reused `SemanticMemory` wrapper, and a `query()` that RRF-fuses BM25 + vector hits (degrading to BM25-only when Chroma is absent). This is the foundation every other V19 plan consumes (VSEM-01, VSEM-02).

Purpose: The missing semantic layer over code. Reuse-not-rebuild — consumes M10 discovery + symbols, reuses the F2 RRF/BM25/Chroma machinery, adds no second index substrate.
Output: `semantic_index.py` with `extract_chunks`, `_chunk_id`, and `CodeIndex` (build, incremental reindex, query). The `CodeIndexService` daemon wrapper and the `code_recall` tool come in V19-03; enrichment in V19-06.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-RESEARCH.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md

<interfaces>
<!-- Existing tree API to reuse (import, do not reimplement). Verified file:line in RESEARCH. -->

voss/harness/code/index.py:
  _discover_files(root: Path) -> list[Path]      # git-aware, VENDORED_DIRS excluded
  LANGUAGE_EXTS: dict[str, str]                   # suffix -> language; filter to these
  _get_db_path(cwd) -> Path                       # .voss-cache/code/index.db
  # SQLite schema: files(id,path,lang,mtime,hash) ; symbols(id,file_id,name,kind,line)
  # content hash: hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

voss/harness/memory_store.py:
  _bm25_tokenize(text) -> list[str]              # camelCase/snake_case aware — import
  MemoryStore._rrf_merge(rankings, *, top_k, k=60) -> list[Hit]   # @staticmethod — call
  Hit(source, locator, score, excerpt, session_id=None, ts=None, line_start=None, line_end=None)  # extended by V19-01

voss_runtime.memory.semantic.SemanticMemory(persist_dir=str, collection_name=str):
  ._embedding_function()    # reuse — MiniLM default / OpenAI when keyed / default_embedding_model knob
  ._collection             # chromadb collection: .upsert(documents,ids,metadatas), .delete(ids=[...]), .query(...)

rank_bm25.BM25Okapi(tokenized_corpus)  # .get_scores(tokenized_query)
</interfaces>

<!-- chromadb 1.5.9 verified: upsert/delete(ids=)/query confirmed; journal_mode=DELETE (single client per process). -->
<!-- MiniLM max_seq_length=256 (~512 chars); oversize split target ~800 chars per Pitfall 5. -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Chunk extraction from M10 symbols + manifest helpers</name>
  <read_first>
    - tests/code_recall/test_chunker.py (the RED tests this task must turn green — read the exact assertions)
    - tests/code_recall/conftest.py (fixture contracts: indexed_fixture_repo, fake_embed_fn)
    - voss/harness/code/index.py (lines 59-90 _discover_files; 107-141 schema; 163-208 build_index incl. sha256 hash at ~187; LANGUAGE_EXTS at 34)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-RESEARCH.md (Code Examples → "Chunk Extraction from M10 Symbols Table" — the verified algorithm)
  </read_first>
  <files>voss/harness/code/semantic_index.py</files>
  <action>Create `voss/harness/code/semantic_index.py`. Implement module-level `extract_chunks(db_path: Path, file_path: str, content: str) -> list[tuple[int,int,str]]` exactly per the RESEARCH verified algorithm: read `SELECT s.line FROM symbols s JOIN files f ON s.file_id=f.id WHERE f.path=? ORDER BY s.line` (read-only connection, close in finally), sorted unique start lines; chunk = [symbol_start, next_symbol_start) with file-end terminator; preamble (lines before first symbol) = chunk 0; zero symbols → single whole-file chunk (Pitfall 6). Implement `_split_oversize(start, end, lines, max_chars=800)` recursively splitting regions over 800 chars at the line midpoint (covers the 256-token MiniLM window, Pitfall 5). Implement `_chunk_id(rel_path: str, seq: int) -> str` returning `f"code:{rel_path}:{seq:03d}"` (D-04 convention, `code:` prefix guarantees no collision with turn:/note:/etc per Pitfall 8). Implement manifest helpers `_manifest_path(cwd)` → `.voss-cache/code/semantic-manifest.json`, `_load_manifest()` (missing file → {}), `_save_manifest(data)`. Content hash uses `hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()` — identical to M10 so manifests stay consistent with the files.hash column. Use `from __future__ import annotations` and the import block from PATTERNS (dataclasses, hashlib, json, sys, threading, Path).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_chunker.py -x -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test_chunker.py::test_chunks_split_on_symbol_boundaries` passes: a 2-symbol file yields 2 chunks with the expected start lines
    - `test_chunker.py::test_zero_symbol_file_single_chunk` passes
    - `test_chunker.py::test_oversize_chunk_split` passes: a >800-char region produces ≥2 sub-chunks with distinct `code:<path>:<seq>` ids
    - `_chunk_id("a/b.py", 2) == "code:a/b.py:002"` (source assertion)
    - `extract_chunks` opens the M10 db read-only and never writes to symbols/files tables (source review: no INSERT/UPDATE/DELETE against M10 db)
  </acceptance_criteria>
  <done>Chunk extraction + manifest helpers exist; chunker RED tests are green; chunk ids carry the code: prefix.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CodeIndex build + incremental reindex + query (RRF + BM25 degradation)</name>
  <read_first>
    - voss/harness/code/semantic_index.py (the chunker/manifest from Task 1)
    - tests/code_recall/test_incremental.py (embed-call-counter RED tests this task turns green)
    - voss/harness/memory_store.py (lines 108-126 _maybe_chroma guard to mirror; 425-440 _rrf_merge; 63-68 _bm25_tokenize)
    - voss_runtime/memory/semantic.py (SemanticMemory __post_init__, _embedding_function, _collection access)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (semantic_index.py section: _maybe_semantic, delete-then-upsert, daemon-thread note)
  </read_first>
  <files>voss/harness/code/semantic_index.py</files>
  <action>Add the `CodeIndex` class to `semantic_index.py`. `__init__(self, cwd: Path)` stores cwd, lazy `_sem=None`, `_unavailable=False`, in-memory `_bm25=None`, `_bm25_chunks=[]` (list of (chunk_id, text, file_path, line_start, line_end)). `_maybe_semantic()` mirrors `memory_store._maybe_chroma` EXACTLY (catch (ModuleNotFoundError, ImportError) first, then broad Exception, set _unavailable, print to stderr) but with `persist_dir=str(cwd/".voss-cache"/"code"/"chroma")`, `collection_name="voss_code"`. `build(self, session_id: str | None = None)`: (1) call `_discover_files(cwd)` filtered to `LANGUAGE_EXTS`; (2) load manifest; (3) for each file compute sha256 hash, SKIP if `manifest[path]["hash"] == hash` (zero embeds — VSEM-02); (4) for changed files call `extract_chunks`, build chunk ids/texts/metadatas (metadata = {path, line_start, line_end}); (5) delete stale ids via `sem._collection.delete(ids=old_ids)` then `sem._collection.upsert(documents=texts, ids=chunk_ids, metadatas=metas)` — NEVER `add()` (DuplicateIDError); (6) store `embedding_model` name in the manifest and on collection metadata; if the manifest model != current `default_embedding_model`, drop+rebuild the whole collection (Pitfall 1); (7) after the pass, REBUILD the in-memory BM25 corpus from the FULL current chunk set via `_bm25_tokenize` (Pitfall 4 — stale BM25 guard); (8) save manifest. `query(self, query, top_k=5)`: tokenize via `_bm25_tokenize`, BM25 top-k*3 → list[Hit] (source="code", locator=chunk_id, line_start/line_end set, excerpt=chunk text first 160 chars); if `_maybe_semantic()` available, also query Chroma top-k*3 → list[Hit]; fuse via `MemoryStore._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)`; when Chroma absent, return BM25-only hits with source="code[degraded]" (VSEM-04 contract, also serves VSEM-03 degraded-before-ready). Hold ONE SemanticMemory instance per CodeIndex (Pitfall 3 single-client). All sentence-transformers cold-load happens lazily inside `_maybe_semantic` (called from build, which V19-03 runs in the worker thread) — never at import/__init__ (Pitfall 2). Accept an optional `session_id: str | None = None` parameter on `build` now (unused by this plan) so V19-06 can thread it into the enrichment ledger row without changing the signature later; do NOT default it to a literal `None` write path — V19-06 resolves the `"index-background"` fallback.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_incremental.py tests/code_recall/test_chunker.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `test_incremental.py::test_only_changed_file_reembeds` passes: touching one file re-embeds exactly that file's chunks (embed-call counter)
    - `test_incremental.py::test_no_reembed_on_unchanged` passes: rebuild on unchanged repo performs zero embed calls
    - `test_chunker.py::test_derived_cache` passes: deleting the chroma dir + rebuild reproduces a working queryable index
    - `_maybe_semantic` catch order is (ModuleNotFoundError, ImportError) then Exception — matches memory_store.py:108-126 (source review)
    - build uses `upsert`/`delete(ids=)` only — `grep -n "\.add(" voss/harness/code/semantic_index.py` returns nothing for the collection write path
    - query with Chroma forced absent (conftest chroma_disabled_env) returns BM25-only Hits without raising
    - manifest stores an `embedding_model` key; model-mismatch path drops the collection (source review of the Pitfall-1 branch)
  </acceptance_criteria>
  <done>CodeIndex builds incrementally (zero embeds on unchanged), query RRF-fuses and degrades to BM25-only, derived-cache + incremental RED tests green; single Chroma client held.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo source files → chunk text | raw source read from disk into Chroma documents/metadata |
| manifest entries → filesystem paths | manifest maps repo-relative paths to chunk ids |
| M10 SQLite index → CodeIndex | read-only consumer of symbols/files tables |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V19-02-01 | Tampering | chunk text handling | mitigate | Chunk text is raw source stored as Chroma documents/metadata ONLY — never eval/exec/compile (ASVS V5); source review confirms no dynamic execution of chunk content |
| T-V19-02-02 | Tampering | manifest path entries (.voss-cache traversal) | mitigate | Paths come from `_discover_files(cwd)` (M10 git-aware, rooted at cwd); manifest keys are repo-relative; chroma + manifest written only under `cwd/.voss-cache/code/` — no `..` traversal from manifest into the build path |
| T-V19-02-03 | Denial of Service | full-corpus re-embed on every reindex | mitigate | Hash-skip guarantees zero embeds for unchanged files (VSEM-02); BM25 rebuilt in-memory only (no model call) |
| T-V19-02-04 | Tampering | M10 SQLite index | mitigate | CodeIndex opens the M10 db read-only and issues only SELECT — never writes M10 tables (consume-not-modify boundary) |
| T-V19-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps; chromadb/sentence-transformers/rank-bm25 already in voss[search]) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/code_recall/test_chunker.py tests/code_recall/test_incremental.py -q` — green
- `.venv/bin/python -m pytest tests/code_recall/ -q --ignore=tests/code_recall/test_golden_queries.py` — remaining files still RED (downstream plans), no regressions in chunker/incremental
- Coherence guard: `.venv/bin/python -m pytest tests/memory/ -q` green (Hit/RRF reuse non-breaking)
</verification>

<success_criteria>
- semantic_index.py exports extract_chunks, _chunk_id, CodeIndex
- Symbol-boundary chunking + zero-symbol + oversize-split correct
- Incremental reindex: zero embeds on unchanged, only-changed re-embed
- query RRF-fuses BM25+vector and degrades to BM25-only without error
- Derived-cache property holds (drop chroma + rebuild)
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-02-SUMMARY.md` when done
</output>

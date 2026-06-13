---
phase: V22-external-memory-docs-ingest
plan: 03
type: execute
wave: 2
depends_on: [V22-02]
files_modified:
  - voss/harness/recall/external_index.py
autonomous: true
requirements: [VXMEM-03, VXMEM-05, VXMEM-06]
must_haves:
  truths:
    - "Each source ingests into its own voss_recall_<name> collection + per-source manifest under .voss-cache/recall/<name>/"
    - "rm -rf .voss-cache/recall + rebuild reproduces a working index from source files alone"
    - "Hash-unchanged files produce zero embeds; changed file re-embeds only its chunks; deleted file purges its chunks"
    - "Session start never blocks on ingest; before-ready query degrades to BM25; source files are byte-identical after a full ingest+recall cycle"
  artifacts:
    - path: "voss/harness/recall/external_index.py"
      provides: "ExternalSourceIndex.build/query + ExternalRecallService daemon"
      contains: "class ExternalRecallService"
  key_links:
    - from: "ExternalSourceIndex.build"
      to: ".voss-cache/recall/<name>/semantic-manifest.json"
      via: "per-source content-hash manifest (port of CodeIndex manifest)"
      pattern: "semantic-manifest.json"
    - from: "ExternalRecallService.ensure_background_build"
      to: "threading.Thread(daemon=True)"
      via: "non-blocking background build (CodeIndexService pattern)"
      pattern: "daemon=True"
---

<objective>
Implement the index engine: `ExternalSourceIndex` (per-source incremental build + query, mirroring V19 `CodeIndex`) and `ExternalRecallService` (daemon wrapper, mirroring `CodeIndexService`). This is the heart of the port — manifest-driven never-full reindex (VXMEM-03/05), background non-blocking read-only ingest (VXMEM-06), and BM25+vector RRF query with chromadb-absent degradation.

Purpose: Turn the index/incremental/background tests GREEN. Touches ONLY the V22-owned `external_index.py` (config.py done in W1) — no shared-file conflict.
Output: GREEN `test_incremental.py` (5 tests) + `test_background.py` (3 tests).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V22-external-memory-docs-ingest/V22-CONTEXT.md
@.planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md

<interfaces>
Verbatim reuse (imported in V22-01): `_split_oversize`, `_file_hash`, `_effective_embedding_model` from `code/semantic_index.py`; `Hit`, `MemoryStore`, `_bm25_tokenize` from `memory_store.py`.
Chroma wrapper (reuse, do not duplicate): `SemanticMemory(persist_dir=str, collection_name=str)` from `voss_runtime.memory.semantic` — has `._client`, `._collection`, `._embedding_function()`.
Already implemented (V22-02): `extract_md_chunks(content)`, `_MD_SUFFIXES`, `get_recall_sources()`.

Manifest schema (D-15, port of CodeIndex): `{embedding_model, files: {rel_path: {hash, chunk_ids}}}`.
Chunk id (D-13): `<name>:<rel_path>:<seq:03d>`. Collection (D-12): `voss_recall_<sanitized_name>`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement ExternalSourceIndex build (incremental, per-source, read-only) + query</name>
  <read_first>
    - voss/harness/code/semantic_index.py:127-530 (CodeIndex: _maybe_semantic, _drop_collection, build incremental loop, _set_bm25_corpus/_ensure_bm25/_bm25_query, query/_chroma_query — the exact pattern to port)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Q5 (~L322-363, manifest/collection/model-swap), Q6 degradation (~L394), Landmine Inventory (~L783-799), Pitfalls 1/2/6/7 (~L627-682)
    - tests/external_recall/test_incremental.py (RED tests to satisfy)
  </read_first>
  <files>voss/harness/recall/external_index.py</files>
  <behavior>
    - test_derived_cache_rm_safe: build over fixture vault, rm -rf .voss-cache/recall/, rebuild → equivalent working index (query returns hits)
    - test_manifest_has_hash_per_file: after build, manifest `files` has one entry per ingested .md file, each with a `hash`
    - test_touch_one_file_reembeds_only_it: touch one file's content, rebuild → only that file's chunks re-embed (embed/upsert counter)
    - test_unchanged_zero_embeds: rebuild on unchanged vault → zero embed/upsert calls
    - test_deleted_file_purges_chunks: remove a source file, rebuild → its chunk_ids deleted from collection + manifest
  </behavior>
  <action>
    Port `CodeIndex` into `ExternalSourceIndex` per D-05/D-07/D-12/D-13/D-15 and the Landmine Inventory adaptations:
    - `__init__(cwd, source)`: store `source={name,path,glob}`; `_cache_dir = cwd/.voss-cache/recall/<name>`; `_collection_name = "voss_recall_" + re.sub(r'[^a-z0-9_]','_', name.lower())` (D-12 sanitize); lazy `_sem`, `_unavailable`, `_bm25`, `_bm25_chunks`.
    - `_maybe_semantic()`: mirror CodeIndex — construct `SemanticMemory(persist_dir=str(_cache_dir/"chroma"), collection_name=self._collection_name)`; catch `(ModuleNotFoundError, ImportError)` → `_unavailable=True` return None; broad-except → stderr warn + degrade.
    - File discovery REPLACES git-aware `_discover_files`: resolve `source["path"]` (`~`-expand, relative→cwd per D-19); if path missing → log degraded + return (Pitfall 6); `root.rglob(source["glob"])` filtered to `_MD_SUFFIXES`; SYMLINK SAFETY (Pitfall 7): after resolving each file, skip unless `resolved_file.is_relative_to(resolved_root)`; wrap discovery in try/except OSError (PermissionError → skip+log). `rel_path = str(file.relative_to(resolved_root))` (Pitfall 2 — source-relative, NOT cwd-relative).
    - `build()`: load per-source manifest (`_cache_dir/semantic-manifest.json`); model-swap drop on `_effective_embedding_model()` mismatch (Pitfall 1, port `_drop_collection(self._collection_name)`); per file: `content=read_text` (READ-ONLY — never open for write under any source path, VXMEM-06), `digest=_file_hash(content)`; chunks from `extract_md_chunks(content)` filtered to non-empty; ids `f"{name}:{rel}:{i:03d}"`; hash-unchanged → continue (zero embeds, VXMEM-05); changed → delete stale ids + upsert; record `{hash, chunk_ids}`. Purge chunks of files absent from `seen` (deleted-file purge). Save manifest with `embedding_model`. Rebuild BM25 from the FULL current chunk set (Pitfall 4 parity). OMIT `_run_enrichment` and `queue_rehash` entirely (Landmine Inventory: out of scope).
    - `query()`/`_chroma_query()`/`_bm25_query()`/`_ensure_bm25()`: port verbatim from CodeIndex but with `source=self._name` (not "code") on every `Hit`, degraded label `f"{self._name}[degraded]"` when chroma absent, and BM25 corpus discovery via the rglob+_MD_SUFFIXES scan (not `_discover_files`).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_incremental.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_incremental.py -x -q` passes all 5. Hits carry `source=<name>` (not "code"). `_discover_files` NOT imported (grep: `grep -c "_discover_files" voss/harness/recall/external_index.py` returns 0). No `open(` with a write mode anywhere in the file (grep: `grep -c "open(.*['\"][wa]" voss/harness/recall/external_index.py` returns 0).
  </acceptance_criteria>
  <done>ExternalSourceIndex builds per-source isolated collection+manifest, incremental never-full, deleted-file purge, model-swap drop, read-only discovery with symlink guard, RRF query with <name> labels + BM25 degradation; 5 incremental tests GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement ExternalRecallService daemon (non-blocking, degrade-until-ready) + build_all</name>
  <read_first>
    - voss/harness/code/semantic_index.py:533-595 (CodeIndexService: ensure_background_build, _build_loop, is_ready, query degraded path)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Pattern 4 (~L561-596), Q2 spawn site, Assumption A6 (one thread iterating sources sequentially)
    - tests/external_recall/test_background.py (RED tests to satisfy)
  </read_first>
  <files>voss/harness/recall/external_index.py</files>
  <behavior>
    - test_session_does_not_block: constructing the service + ensure_background_build returns immediately (does not wait on build); the build runs on a daemon thread (threading.Event not set synchronously)
    - test_degraded_before_ready: query_all before _ready is set returns BM25 hits (or empty lists), never raises
    - test_source_files_readonly: snapshot mtimes+content-hashes of every source file before a full ensure_background_build (joined) + query_all cycle; assert byte-identical after
  </behavior>
  <action>
    Implement `ExternalRecallService` per Pattern 4: `__init__(cwd, session_id)` calls `get_recall_sources()` inside a try/except `ValueError` (bad config → log + zero indices, Pitfall: never crash session start) and builds one `ExternalSourceIndex` per source; `threading.Event` `_ready`; `_thread=None`. `ensure_background_build()`: no-op if no indices or thread already started; else spawn ONE `threading.Thread(target=self._build_loop, daemon=True)` (A6: one thread iterating all sources sequentially). `_build_loop()`: iterate `idx.build()` for each, broad-except → stderr warn, `finally: self._ready.set()` (always flip ready, degraded if failed — CodeIndexService parity). `is_ready()`. `query_all(query, top_k)`: if not ready → `[idx._bm25_query(query, top_k) for idx in indices]` (degraded, never touch embedding path mid-build); else `[idx.query(query, top_k) for idx in indices]`; returns one Hit list per source. `build_all()`: synchronous `for idx: idx.build()` then `_ready.set()` — the `--refresh` path (D-18) used by V22-04. Construction must NOT import sentence_transformers/chromadb (lazy in `_maybe_semantic` only — Pitfall 2).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_background.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_background.py -x -q` passes all 3 including `test_source_files_readonly`. Service spawns `daemon=True` thread (grep: `grep -c "daemon=True" voss/harness/recall/external_index.py` ≥ 1). A bad config (reserved-name ValueError) at construction does not propagate (caught → zero indices).
  </acceptance_criteria>
  <done>ExternalRecallService runs a non-blocking daemon build, degrades to BM25 until ready, build_all() does a synchronous refresh, bad config caught at construction; source files byte-identical after ingest+recall; 3 background tests GREEN.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/external_recall/test_incremental.py tests/external_recall/test_background.py -q` → 8 GREEN
- `.venv/bin/python -m pytest tests/external_recall/ tests/code_recall/ -q` → no regressions in the ported-from V19 suite
- Read-only assertion (`test_source_files_readonly`) GREEN; no write-mode `open(` in external_index.py
</verification>

<success_criteria>
The index engine is GREEN and reuse-faithful: CodeIndex/CodeIndexService ported with heading chunks, per-source isolation, read-only daemon build, BM25 degradation. Self-contained in `external_index.py` (no shared-file edits) so it parallelizes cleanly behind W1.
</success_criteria>

<output>
Create `.planning/phases/V22-external-memory-docs-ingest/V22-03-SUMMARY.md` when done.
</output>

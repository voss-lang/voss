---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 02
subsystem: code-intel
tags: [semantic-index, chroma, bm25, rrf, incremental, chunking]
requires:
  - "V19-01 (Hit.line_start/line_end contract + RED suite)"
provides:
  - "voss/harness/code/semantic_index.py: extract_chunks, _chunk_id, CodeIndex (build/query/manifest/incremental)"
  - "voss_code Chroma collection under .voss-cache/code/chroma (derived cache)"
  - ".voss-cache/code/semantic-manifest.json: files -> {hash, chunk_ids[]} + embedding_model"
affects: [V19-03, V19-04, V19-05, V19-06]
tech-stack:
  added: []
  patterns:
    - "_maybe_semantic mirrors MemoryStore._maybe_chroma guard exactly (MNFE/ImportError → silent, Exception → stderr + unavailable)"
    - "delete(ids=stale) then upsert — never collection.add()"
    - "BM25 corpus rebuilt from FULL chunk set every build; lazy _ensure_bm25 for query-before-build"
key-files:
  created:
    - voss/harness/code/semantic_index.py
  modified:
    - tests/code_recall/test_incremental.py
    - tests/code_recall/test_background.py
    - tests/code_recall/test_chunker.py
key-decisions:
  - "Manifest shape: top-level embedding_model + files map (path -> {hash, chunk_ids}) — model swap drops collection and resets manifest, forcing full re-embed (Pitfall 1)"
  - "_effective_embedding_model replicates SemanticMemory._embedding_function resolution (OPENAI_API_KEY-aware) so the manifest tracks the same model chroma actually uses"
  - "extract_chunks falls back to whole-file chunk when the M10 db is missing/unreadable (sqlite3.Error) — query path never hard-depends on M10 being built"
  - "Deleted-from-repo files purge their chunk ids from the collection (manifest hygiene beyond plan minimum)"
  - "BM25 tiny-corpus zero/negative-IDF rescue mirrors memory_store._bm25_recall (overlap-count fallback, drop no-overlap)"
requirements-completed: [VSEM-01, VSEM-02]
duration: 30 min
completed: 2026-06-12
---

# Phase V19 Plan 02: CodeIndex Core Summary

Symbol-aware semantic code index: M10-symbol-boundary chunking with 800-char oversize splitting, content-hash manifest making reindex incremental (zero embeds on unchanged files), `voss_code` Chroma collection via the reused `SemanticMemory` wrapper, and `query()` RRF-fusing BM25+vector with BM25-only `code[degraded]` fallback when Chroma is absent.

- Duration: ~30 min (commits 9d3cce8 → e2c0baf, 2026-06-12)
- Tasks: 2/2 (chunker+manifest · CodeIndex build/incremental/query)
- Files: 1 created (375 lines), 3 test files fixed

## What Was Built

**Task 1 — chunker/manifest:** `extract_chunks` per the RESEARCH verified algorithm — read-only `mode=ro` URI sqlite over M10 `symbols JOIN files`, chunk = `[symbol_start, next_start)`, preamble prepended, zero-symbol → whole-file, `_split_oversize` recursive midpoint split at 800 chars. `_chunk_id` → `code:<rel>:<seq:03d>`. Manifest helpers under `.voss-cache/code/semantic-manifest.json`. Hash identical to M10 (`sha256(content.encode("utf-8", errors="ignore"))`).

**Task 2 — CodeIndex:** one `SemanticMemory` per instance (Pitfall 3), all cold-load inside `_maybe_semantic` (Pitfall 2), guard order copied from `memory_store.py:113-131`. Build: discover→hash-skip→extract→`delete(stale)`+`upsert`→manifest; model-mismatch drops collection (Pitfall 1); removed files purged; BM25 rebuilt from FULL chunk set (Pitfall 4); `session_id` accepted for V19-06 ledger threading. Query: BM25 top-k×3 + chroma top-k×3 → `MemoryStore._rrf_merge`; chroma-absent → `code[degraded]` hits; chroma-query-raise → BM25 fallback (mirror of `MemoryStore.recall`).

## Verification Log (acceptance gates)

- `test_chunker.py` 4/4 green (boundaries, zero-symbol, oversize ids, derived-cache) — PASS
- `test_incremental.py::test_only_changed_file_reembeds` + `test_no_reembed_on_unchanged` green — PASS (`test_targeted_rehash_on_fs_write` stays RED — owned by V19-03)
- `test_code_recall_tool.py::test_degradation` green (chroma-absent BM25-only, no raise) — bonus flip
- `_chunk_id("a/b.py", 2) == "code:a/b.py:002"` — PASS
- catch order `(ModuleNotFoundError, ImportError)` then `Exception` — PASS (source mirror)
- `grep "\.add("` → only `seen.add(rel)` set-op; collection writes are upsert/delete-only — PASS
- manifest carries `embedding_model` + per-file `chunk_ids` — PASS (runtime-verified)
- `tests/memory/` 12 green; full non-golden suite: 12 remaining failures ALL downstream-owned (03: background×2/registration/targeted-rehash · 04: cli×2 · 05: injection×3 · 06: enrichment×3) — no regressions

## Deviations from Plan

- **[Rule 1 - scaffold bug] CountingEmbed/GatedEmbed subclassed DefaultEmbeddingFunction** — Found during: Task 2 | chroma 1.5.9 `CollectionCommon._embed` explicitly bypasses any `isinstance(_, DefaultEmbeddingFunction)` and embeds via the persisted config EF, so the V19-01 counting/gating fixtures never fired (embed counter empty) | Fix: wrap a held `DefaultEmbeddingFunction` inside an `EmbeddingFunction` subclass instead | Files: tests/code_recall/test_incremental.py, test_background.py | Verification: counter records upsert+query embeds | Commit e2c0baf.
- **[Rule 1 - scaffold bug] test_derived_cache rmtree under open chroma client** — Found during: Task 2 | chroma caches its System per persist path; same-process rmtree+rebuild hits SQLITE_READONLY_DBMOVED | Fix: `SharedSystemClient.clear_system_cache()` after rmtree in the test (same-process artifact only — real `rm -rf` + fresh process unaffected) | Files: tests/code_recall/test_chunker.py | Commit e2c0baf.
- **[Noted, no action] test_profile_off_zero_llm + test_budget_cap_abort flipped green vacuously** — enrichment doesn't exist yet, so zero-LLM/clean-abort hold trivially; `test_routes_index_enrich_role` + `test_cost_ledger_line` remain RED and force the V19-06 implementation.

**Total deviations:** 2 auto-fixed (both V19-01 scaffold-vs-real-API, the known fictional-scaffold pattern), 1 noted. **Impact:** fixtures now match real chroma semantics; downstream waves inherit working counters.

## Next Phase Readiness

V19-03 (CodeIndexService + code_recall tool) implements against now-meaningful RED tests: `test_first_roundtrip_not_blocked`/`test_degraded_before_ready` (GatedEmbed now actually gates), `test_targeted_rehash_on_fs_write` (CountingEmbed now actually counts), `test_registration`. PATTERNS daemon-thread sketch remains valid; `CodeIndex.build` is thread-safe to run once on a worker (no shared mutable state before first build).

## Self-Check: PASSED

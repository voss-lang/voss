---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 03
subsystem: code-intel
tags: [daemon-thread, background-build, code-recall-tool, rehash, d-13]
requires:
  - "V19-02 (CodeIndex build/query/manifest)"
provides:
  - "CodeIndexService: daemon-thread build, readiness Event, degraded query, queue_rehash"
  - "CodeIntelService._get_code_index_service lazy accessor (only construction site)"
  - "code_recall agent tool (group=code) registered at the make_toolset code-tool site"
  - "fs_write/fs_edit/fs_edit_many → _maybe_queue_rehash → queue_rehash (D-13 trigger #2)"
affects: [V19-04, V19-05, V19-06]
tech-stack:
  added: []
  patterns:
    - "ready Event set in finally — build failure still flips ready (degraded)"
    - "service.query pre-ready short-circuits to _bm25_query + code[degraded] (never touches the embedding path mid-build)"
    - "closure-late-bound _code_index_service lets the rehash helper sit above fs_write while the service binds at the end of make_toolset"
key-files:
  created: []
  modified:
    - voss/harness/code/semantic_index.py
    - voss/harness/code/service.py
    - voss/harness/tools.py
key-decisions:
  - "CodeIndexService.query does NOT delegate to CodeIndex.query pre-ready: with chroma PRESENT but build in-flight, a vector query would block behind the build's embeds — pre-ready path is BM25-only with code[degraded] marker"
  - "queue_rehash serializes via _rehash_lock and calls a full incremental build() pass — manifest hash-skip makes that exactly the written file's chunks"
  - "ONE held CodeIndexService per toolset (one chroma client); _code_service() stays per-call for the M10 tools (surgical)"
  - "Rehash hook filters to LANGUAGE_EXTS suffixes and is wrapped so index upkeep can never break a write"
requirements-completed: [VSEM-03, VSEM-04]
duration: 20 min
completed: 2026-06-12
---

# Phase V19 Plan 03: Background Service + code_recall Tool Summary

Non-blocking index lifecycle: `CodeIndexService` daemon-thread wrapper (readiness Event, degraded BM25 query pre-ready, off-thread `queue_rehash`), lazy accessor on `CodeIntelService`, the `code_recall` agent tool registered at the `make_toolset` code-tool site, and the D-13 trigger #2 hook on all three fs-mutation tools.

- Duration: ~20 min (commits 3304739 → a286b51, 2026-06-12)
- Tasks: 3/3 (service+accessor · tool registration · rehash hook)
- Files: 3 modified

## What Was Built

**Task 1 (3304739):** `CodeIndexService` appended to `semantic_index.py` — `ensure_background_build` idempotent (`_thread is not None` guard), `_build_loop` sets `_ready` in `finally`, `is_ready`, `query` (pre-ready → `_bm25_query` + `code[degraded]`, ready → full RRF), `queue_rehash` (not-ready no-op; else daemon thread + `_rehash_lock` serialized build). `service.py` gains `_get_code_index_service` mirroring the `_get_registry` hasattr/None guard, threading `session_id`, calling `ensure_background_build()` once; never eager in `__init__`/`for_cwd`.

**Task 2 (0aad390):** `attach_code_recall_tool` mirrors `attach_memory_tools` — async `code_recall(query, top_k=5)`, description explicitly steers concept queries here vs exact-name to `code_search` (collision-avoidance), hits formatted `[code] path:line_start (score)` + 160-char excerpt, errors returned as `<error: ...>` never raised. Registered `group="code"`, `scope_requirements=("code",)`. `make_toolset` holds ONE service via `_code_service()._get_code_index_service()` behind the existing optional-import guard.

**Task 3 (a286b51, absorbed by auto-committer):** `_maybe_queue_rehash(*paths)` — `is_ready()`-gated, `LANGUAGE_EXTS`-filtered, exception-swallowing — called after the write in `fs_write`, `fs_edit`, `fs_edit_many` success paths. No watch daemon, no per-recall sweep (D-13: M14 owns watch).

## Verification Log (acceptance gates)

- `test_background.py` 2/2 (first-roundtrip <2s with gated embeds; degraded query, no block) — PASS
- `test_code_recall_tool.py` 3/3 incl. `test_perf_p95` (13s build on ~10K LoC fixture, query p95 <500ms) — PASS
- `test_incremental.py::test_targeted_rehash_on_fs_write` — PASS (only written file re-embeds; queue_rehash returns <1s; cold-service no-op)
- grep gates: `attach_code_recall_tool` def:218 + call:910; `queue_rehash` helper:468/482 + 3 fs call sites (491/570/640) — PASS
- Coherence: `tests/harness/ -k "toolset or packing"` 14 passed in 5.82s; `tests/memory/` 12 green — PASS
- `make_toolset(repo_root)` measured 0.54s wall (synchronous part = M10 build_index; embedding build fully backgrounded); `code_recall` present in 27-tool set — PASS

## Deviations from Plan

- **[Rule 2 - missing critical] pre-ready query short-circuit** — Plan said "delegate to CodeIndex.query; if NOT ready, the underlying query already returns degraded". False when chroma IS installed: mid-build vector query would block behind the in-flight build's embedding calls (the exact anti-pattern the plan forbids). `CodeIndexService.query` short-circuits to BM25-only + `code[degraded]` pre-ready. Verified by test_degraded_before_ready under a gated (blocking) embed fn.
- **[Environment - concurrent auto-committer] Task 3 absorbed as a286b51** — diff-verified: 21 insertions, tools.py only, exactly the rehash hook.

**Total deviations:** 1 auto-fixed, 1 environmental. **Impact:** none; degraded-path contract is stronger than planned.

## Watch Items (for operator)

- With `OPENAI_API_KEY` set, the background build embeds via `OpenAIEmbeddingFunction` (existing F2/SemanticMemory resolution — "OpenAI when keyed"). Harness tests constructing toolsets now spawn daemon build threads that may touch the network before process exit; suite stayed green/fast (5.82s), but a test-env embedding pin (e.g. local model knob in CI) is worth considering when V19-06 lands.

## Next Phase Readiness

V19-04 (`voss recall` CLI) consumes `CodeIndexService.query` + the V19-02 manifest; its RED tests (`test_exit_0_labeled`, `test_json_schema` incl. secret-leak assertion) are the last non-injection/enrichment failures standing.

## Self-Check: PASSED

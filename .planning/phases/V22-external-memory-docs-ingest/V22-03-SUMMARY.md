---
phase: V22-external-memory-docs-ingest
plan: 03
subsystem: recall
tags: [external-memory, semantic-index, bm25, chroma, daemon, incremental]

requires:
  - phase: V22-external-memory-docs-ingest
    provides: V22-02 recall source config and markdown chunking
provides:
  - per-source ExternalSourceIndex with derived manifest cache
  - ExternalRecallService background daemon wrapper
  - BM25 degradation before ready and when Chroma is unavailable
affects: [V22-external-memory-docs-ingest, recall, memory]

tech-stack:
  added: []
  patterns: [CodeIndex-style manifest indexing, daemon build wrapper, BM25-vector RRF]

key-files:
  created: []
  modified:
    - voss/harness/recall/external_index.py

key-decisions:
  - "Kept the V22 external index isolated to per-source collections and per-source manifests under .voss-cache/recall/<name>/."
  - "Kept SemanticMemory construction lazy inside _maybe_semantic so session construction does not cold-load Chroma or embedding models."

patterns-established:
  - "External source discovery is source-relative, markdown-only, and symlink-contained."
  - "Before-ready recall uses BM25-only results and does not touch the embedding path."

requirements-completed: [VXMEM-03, VXMEM-05, VXMEM-06]

duration: 45 min
completed: 2026-06-13
---

# Phase V22 Plan 03: External Source Index Engine Summary

**External markdown corpora now build into per-source derived recall indexes with incremental manifests and non-blocking background service access.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-06-13T17:00:00Z
- **Completed:** 2026-06-13T17:45:26Z
- **Tasks:** 2
- **Files modified:** 1 implementation file plus planning metadata

## Accomplishments

- Implemented `ExternalSourceIndex` with per-source cache directory `.voss-cache/recall/<name>/` and collection name `voss_recall_<sanitized_name>`.
- Added content-hash manifest handling at `semantic-manifest.json`, including hash-skip rebuilds and deleted-file purge.
- Added source-relative markdown discovery with `.md` / `.markdown` filtering and symlink containment.
- Added BM25 corpus rebuild from the full current chunk set and RRF fusion with Chroma hits.
- Added `ExternalRecallService` with daemon-thread background build, before-ready BM25 degradation, synchronous `build_all()`, and read-only source behavior.

## Task Commits

1. **Task 1: Implement ExternalSourceIndex build/query** - `f6c37b57` (`feat(external_index): implement external source indexing and manifest management`)
2. **Task 2: Implement ExternalRecallService daemon** - `f6c37b57` (`feat(external_index): implement external source indexing and manifest management`)

**Plan metadata:** this summary commit records the V22-03 closeout and roadmap progress.

## Files Created/Modified

- `voss/harness/recall/external_index.py` - Implements external source indexing, manifest persistence, BM25/vector query, and background service wrapper.

## Decisions Made

- Did not add enrichment, targeted rehash, CLI fan-out, or tool fan-out in this plan; those remain scoped to later V22 waves.
- Used `Path.write_text` only for derived cache manifests, never source files.
- Kept Chroma/SemanticMemory import inside `_maybe_semantic` rather than module scope.

## Deviations from Plan

### Auto-fixed Issues

None - implementation followed the plan boundaries.

---

**Total deviations:** 0.
**Impact on plan:** None.

## Issues Encountered

- The plan references `V22-CONTEXT.md` and `V22-RESEARCH.md`, but those files are absent in this checkout. Implementation used `V22-03-PLAN.md`, the V22 tests, and the V19 `CodeIndex` / `CodeIndexService` analogs.
- The checkout briefly moved from `master` to `dev` after the implementation commit. The work was verified and closed out on `master`, where the V22 plan and implementation commit live.

## Verification

- `.venv/bin/python -m pytest tests/external_recall/test_incremental.py tests/external_recall/test_background.py -q` - passed, 8 tests.
- `.venv/bin/python -m pytest tests/code_recall/ -q` - passed, 24 tests.
- `.venv/bin/python -m pytest tests/external_recall/test_golden_queries.py -q` - passed, 11 tests.
- `.venv/bin/python -m pytest tests/external_recall/ --collect-only -q` - passed, 33 tests collected.
- Acceptance greps passed: `_discover_files` count `0`, write-mode `open(...)` count `0`, `daemon=True` count `1`, eager `chromadb` / `sentence_transformers` import count `0`.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for `V22-04-PLAN.md`: wire external-source hits into the `voss recall` CLI and refresh path.

---
*Phase: V22-external-memory-docs-ingest*
*Completed: 2026-06-13*

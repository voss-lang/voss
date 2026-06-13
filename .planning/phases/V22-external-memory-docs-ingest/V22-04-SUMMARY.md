---
phase: V22-external-memory-docs-ingest
plan: 04
subsystem: recall
tags: [external-memory, cli, rrf, json-schema, refresh]

requires:
  - phase: V22-external-memory-docs-ingest
    provides: V22-03 ExternalRecallService and per-source external indexes
provides:
  - voss recall external-source fan-out through N-way RRF
  - true corpus labels in recall JSON source fields
  - synchronous external-source rebuilds on voss recall --refresh
affects: [V22-external-memory-docs-ingest, recall, cli]

tech-stack:
  added: []
  patterns: [N-way RRF fusion, optional external recall degradation, corpus-label passthrough]

key-files:
  created: []
  modified:
    - voss/harness/cli.py

key-decisions:
  - "Kept _recall_hit_fields source passthrough verbatim so external corpus names survive --json output."
  - "Kept external recall failures non-fatal so code and project-memory recall still return when external sources are misconfigured."
  - "Normalized degraded external labels for CLI output so BM25 fallback still renders [<name>] rather than [<name>[degraded]]."

patterns-established:
  - "voss recall fuses [code_hits, mem_hits, *external_hits_per_source] through MemoryStore._rrf_merge."
  - "voss recall --refresh rebuilds ExternalRecallService synchronously alongside CodeIndex."

requirements-completed: [VXMEM-07]

duration: 25 min
completed: 2026-06-13
---

# Phase V22 Plan 04: Recall CLI External Source Summary

**The `voss recall` CLI now includes configured external markdown sources as first-class labeled recall corpora.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-06-13T20:50:36Z
- **Completed:** 2026-06-13T20:58:24Z
- **Tasks:** 2
- **Files modified:** 1 implementation file plus planning metadata

## Accomplishments

- Updated `_recall_hit_fields()` so `--json` emits `hit.source` verbatim instead of normalizing non-code hits to `memory`.
- Preserved code locator parsing for `code:<relpath>:<seq>` while memory and external corpora continue to use locator display.
- Wired `recall_cmd` to construct `ExternalRecallService`, synchronously call `build_all()` on `--refresh`, and call `ensure_background_build()` for normal one-shot recall.
- Extended CLI fusion to `MemoryStore._rrf_merge([code_hits, mem_hits, *external_hits_per_source], top_k=top_k)`.
- Added guarded external query handling so misconfigured external sources do not abort code/project-memory recall.
- Normalized degraded external labels for CLI display so Chroma-absent BM25 fallback still renders `[docs]`.

## Task Commits

1. **Task 1: Source passthrough + external recall CLI fan-out** - `b32572ef` (`feat(recall): integrate external recall service into recall command`)
2. **Task 2: Degraded external label normalization** - `5b50c374` (`feat(recall): normalize external rankings in recall command`)

**Plan metadata:** this summary commit records the V22-04 closeout and roadmap progress.

## Files Created/Modified

- `voss/harness/cli.py` - Adds external source querying, N-way recall fusion, synchronous external refresh, source passthrough, and degraded-label normalization.

## Decisions Made

- Did not edit `voss/harness/tools.py`; V22-05 owns the agent-facing `memory_recall` external fan-out.
- Did not broaden V22-04 into global-memory recall support; the failing global-memory recall tests predate the V22-04 commits and are outside this plan's declared write set.

## Deviations from Plan

### Auto-fixed Issues

None - implementation stayed within the planned CLI surface.

---

**Total deviations:** 0.
**Impact on plan:** None for the V22-04 CLI surface.

## Issues Encountered

- The literal broad command `.venv/bin/python -m pytest tests/ -k "recall" -q` is not green in this checkout. It fails on:
  - `tests/external_recall/test_agent_tool.py::test_agent_gets_external_hits` - expected V22-05 RED surface for `tools.py`.
  - `tests/harness/test_memory_global.py::{test_recall_fusion_rrf,test_global_label_in_recall,test_voss_recall_global_corpus}` - pre-existing global-memory recall gap present at the branch-sync base `49d5926a`.
- Because V22-04 is serialized to `voss/harness/cli.py`, those failures were documented rather than fixed under this plan.

## Verification

- `.venv/bin/python -m pytest "tests/external_recall/test_recall_cli.py::test_json_source_field" "tests/external_recall/test_recall_cli.py::test_code_memory_labels_still_resolve" -x -q` - passed, 2 tests (executor subagent).
- `.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py -q` - passed, 4 tests.
- `.venv/bin/python -m pytest tests/code_recall/ -q` - passed, 24 tests.
- `.venv/bin/python -m pytest tests/harness/test_memory_tools.py tests/harness/test_memory_store.py tests/harness/test_slash_recall.py tests/harness/test_recall_eval.py -q` - passed, 22 tests.
- Acceptance greps passed: `"source": hit.source` count `1`; `external_hits_per_source` count `3`; `build_all()` count `1`; `_rrf_merge([code_hits, mem_hits, *external_hits_per_source]` present.
- `.venv/bin/python -m pytest tests/ -k "recall" -q` - failed on the four out-of-scope tests listed under Issues Encountered.
- `git diff --check` - passed.

## Self-Check: PASSED

V22-04's CLI success criteria are met. The broad recall-suite failure is documented as a known cross-plan/pre-existing gap, not hidden.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for `V22-05-PLAN.md`: wire external-source hits into the agent `memory_recall` surface in `voss/harness/tools.py` and run the golden-query gates. Separately, the global-memory recall tests should be scheduled or folded into the next tools.py touch if still relevant.

---
*Phase: V22-external-memory-docs-ingest*
*Completed: 2026-06-13*

---
phase: V22-external-memory-docs-ingest
plan: 05
subsystem: memory
tags: [recall, external-memory, agent-tools, rrf, chroma, bm25]

requires:
  - phase: V22-external-memory-docs-ingest
    provides: "ExternalRecallService + ExternalSourceIndex implementation"
provides:
  - "Agent memory_recall tool fuses external-source hits via RRF"
  - "ExternalRecallService spawned non-blocking from make_toolset"
  - "Golden-query gate passes with and without chromadb"
affects:
  - "voss/harness/cli.py recall_cmd (future: thread external_service from make_toolset)"

tech-stack:
  added: []
  patterns:
    - "Option B: extend memory_recall rather than add a new tool"
    - "Broad try/except around external recall so failures never crash the turn"
    - "Non-blocking background service spawn inside make_toolset"

key-files:
  created: []
  modified:
    - "voss/harness/tools.py"

key-decisions:
  - "Extend memory_recall in attach_memory_tools (Option B) so agents get external hits from the verb they already call"
  - "Add optional external_service kwarg to attach_memory_tools for backward-compatible call sites in cli.py"
  - "Spawn ExternalRecallService in make_toolset beside CodeIndexService, degrading to None on import/build failure"

patterns-established:
  - "External recall degrades gracefully: missing chromadb → BM25-only, import failure → external_service=None"

requirements-completed: [VXMEM-07, VXMEM-08]

duration: 18 min
completed: 2026-06-13
---

# Phase V22 Plan 05: External Memory Agent Tool + Golden Gate Summary

**Agent `memory_recall` fuses external markdown-source hits with durable memory hits via RRF, and the committed fixture vault passes the golden-query gate with and without chromadb.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-13T21:05:00Z
- **Completed:** 2026-06-13T21:23:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Extended `attach_memory_tools` with an optional `external_service` kwarg and wired `memory_recall` to fan out to `ExternalRecallService.query_all`, fusing results with `MemoryStore._rrf_merge`.
- Spawned `ExternalRecallService` non-blocking inside `make_toolset`, mirroring the existing `CodeIndexService` pattern.
- Verified the agent tool returns `[docs]` labels via the existing `[{h.source}]` formatter.
- Ran the golden-query gate: all ~10 queries hit their expected fixture file in top-5, including the BM25-only chroma-disabled variant.
- Confirmed no regressions in `tests/external_recall/`, `tests/code_recall/`, `tests/memory/`, or the focused tool/toolset regression suite.

## Task Commits

1. **Task 1: Spawn ExternalRecallService + fan out memory_recall** — `TBD` (feat)
2. **Task 2: Land golden-query gate** — included above

**Plan metadata:** `TBD` (docs)

## Files Created/Modified

- `voss/harness/tools.py`
  - Added `from .memory_store import MemoryStore`
  - `attach_memory_tools(..., external_service=None)`
  - `memory_recall` fuses `store.recall` with `external_service.query_all` via `_rrf_merge`
  - `make_toolset` constructs and starts `ExternalRecallService` after the `CodeIndexService` block

## Decisions Made

- Followed the planner's Option B: extend the existing `memory_recall` tool instead of adding a separate external recall tool, satisfying VXMEM-07 without requiring agents to learn a new verb.
- Kept the `external_service` kwarg optional so existing `cli.py` call sites continue to work; threading it through `do_cmd`/`chat_cmd`/`_extension_context` is a clean follow-up outside this plan's scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `MemoryStore` was not imported in `tools.py`**
- **Found during:** Task 1 acceptance test (`test_agent_gets_external_hits`)
- **Issue:** `MemoryStore._rrf_merge` was referenced inside `memory_recall` but `MemoryStore` was not imported, causing the external fan-out to silently fail and return only memory hits.
- **Fix:** Added `from .memory_store import MemoryStore` at the top of `voss/harness/tools.py`.
- **Files modified:** `voss/harness/tools.py`
- **Verification:** `tests/external_recall/test_agent_tool.py` passes.
- **Committed in:** part of Task 1 commit.

**2. [Rule 3 - Blocking] Attempted to attach `_external_recall_service` as a dict attribute broke toolset consumers**
- **Found during:** broad tool/toolset regression run
- **Issue:** Storing the service on the returned dict (either as `result._external_recall_service` or `result["_external_recall_service"]`) violated the invariant that every value in the toolset dict is a `ToolEntry`, breaking `tools` listing, agent formatting, and capability-metadata tests.
- **Fix:** Removed the service from the returned dict; `make_toolset` returns only the toolset. Tests and future callers can construct `ExternalRecallService` directly or thread it via the `attach_memory_tools(external_service=...)` kwarg.
- **Files modified:** `voss/harness/tools.py`
- **Verification:** `tests/harness/test_tools.py`, `tests/harness/test_capability_metadata.py`, `tests/harness/test_agent_integration.py`, `tests/e2e/test_chat_e2e.py`, and related toolset tests pass.
- **Committed in:** part of Task 1 commit.

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both fixes were necessary for correctness and to preserve the toolset contract. No scope creep.

## Issues Encountered

- None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V22-external-memory-docs-ingest is now complete (all 5 plans executed).
- VXMEM-07 both surfaces wired: CLI in V22-04, agent tool in V22-05.
- VXMEM-08 golden gate proven end-to-end with and without chromadb.
- Suggested next step: `/gsd-complete-milestone` for V22 or `/gsd-verify-work V22`.

---
*Phase: V22-external-memory-docs-ingest*
*Completed: 2026-06-13*

---
phase: V22-external-memory-docs-ingest
plan: 02
subsystem: recall
tags: [external-memory, config, markdown, chunking, tomllib]

requires:
  - phase: V22-external-memory-docs-ingest
    provides: V22-01 RED scaffold and fixture vault
provides:
  - get_recall_sources tomllib parser for [[recall.sources]]
  - ATX heading-boundary markdown chunker
  - markdown suffix gate for .md and .markdown sources
affects: [V22-external-memory-docs-ingest, recall, config]

tech-stack:
  added: []
  patterns: [stdlib tomllib config parsing, fence-aware ATX markdown chunking]

key-files:
  created: []
  modified:
    - voss/harness/config.py
    - voss/harness/recall/external_index.py
    - tests/external_recall/test_golden_queries.py

key-decisions:
  - "Kept recall source parsing isolated from the existing regex-based config readers."
  - "Kept golden query text unchanged while changing pytest parameter ids so broad config selection does not run future V22 gates."

patterns-established:
  - "External recall sources are explicit config array-of-tables with reserved-name and duplicate validation."
  - "Markdown chunking is content-only and delegates oversize splitting to the existing V19 helper."

requirements-completed: [VXMEM-01, VXMEM-02, VXMEM-04]

duration: 35 min
completed: 2026-06-13
---

# Phase V22 Plan 02: Config and Chunker Summary

**External recall source config parsing and markdown heading-boundary chunking are green for the V22 index engine.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-13T16:56:00Z
- **Completed:** 2026-06-13T17:31:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `get_recall_sources()` to parse ordered `[[recall.sources]]` entries with default `glob = "**/*.md"`.
- Added reserved-name validation for `code`, `memory`, and `global`, plus duplicate-name rejection.
- Implemented `extract_md_chunks()` with preamble chunks, headingless single chunks, fence-aware ATX heading detection, and `_split_oversize` reuse.
- Added `_MD_SUFFIXES = {".md", ".markdown"}` for the V22 ingest filter contract.
- Adjusted golden-query pytest parameter ids so the broad `-k "config"` regression command does not select future V22 index tests before V22-03 lands.

## Task Commits

1. **Task 1: Implement get_recall_sources() tomllib parse path with validation** - `9c32b505` (`feat(config): add recall sources configuration and validation`)
2. **Task 2: Implement extract_md_chunks() heading-boundary chunker** - `9c32b505` (`feat(config): add recall sources configuration and validation`)

**Verification metadata:** `0f225c2f` (`refactor(tests): update test parameterization for golden queries`)

## Files Created/Modified

- `voss/harness/config.py` - Adds `tomllib`, `_RESERVED_SOURCE_NAMES`, and `get_recall_sources()`.
- `voss/harness/recall/external_index.py` - Adds `_MD_SUFFIXES` and implements `extract_md_chunks()`.
- `tests/external_recall/test_golden_queries.py` - Changes parametrized ids only; query text and assertions are unchanged.

## Decisions Made

- Used `tomllib` as a separate parse path instead of extending existing regex section readers.
- Treated invalid TOML as a recoverable config parse warning returning no recall sources.
- Kept setext headings out of scope; V22-02 implements ATX headings only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Broad config regression selected a future V22 golden test**
- **Found during:** V22-02 verification
- **Issue:** `.venv/bin/python -m pytest tests/ -k "config" -q` selected `test_golden_query[VXMEM-08 setup configuration]`, a future V22-03/V22-05 gate, because the parameter id included the query text.
- **Fix:** Changed parametrized ids in `test_golden_queries.py` to stable `VXMEM-08 golden-NN` labels without changing query data or assertions.
- **Files modified:** `tests/external_recall/test_golden_queries.py`
- **Verification:** Exact `tests/ -k "config"` command passed after the metadata fix.
- **Committed in:** `0f225c2f`

---

**Total deviations:** 1 auto-fixed blocker.
**Impact on plan:** No behavior change. The fix prevents a V22-02 regression command from prematurely running intentionally RED future-wave tests.

## Issues Encountered

- The referenced `V22-CONTEXT.md` and `V22-RESEARCH.md` files are not present in this checkout. Implementation used `V22-02-PLAN.md`, downstream V22 plan contracts, and existing V19 analog code.

## Verification

- `.venv/bin/python -m pytest tests/external_recall/test_config.py -x -q` - passed, 4 tests.
- `.venv/bin/python -m pytest tests/external_recall/test_chunker.py -x -q` - passed, 5 tests.
- `.venv/bin/python -m pytest tests/external_recall/test_config.py tests/external_recall/test_chunker.py -q` - passed, 9 tests.
- `.venv/bin/python -m pytest tests/ -k "config" -q` - passed.
- `.venv/bin/python -m pytest tests/external_recall/ --collect-only -q` - passed, 33 tests collected.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for `V22-03-PLAN.md`: implement `ExternalSourceIndex` and `ExternalRecallService` against the now-green source config and markdown chunking contracts.

---
*Phase: V22-external-memory-docs-ingest*
*Completed: 2026-06-13*

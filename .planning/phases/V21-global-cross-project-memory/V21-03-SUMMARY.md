---
phase: V21-global-cross-project-memory
plan: 03
subsystem: memory
tags: [memory-cli, global-memory, promote, pytest]

requires:
  - phase: V21-global-cross-project-memory
    provides: global MemoryStore factory, root override, and config switch
provides:
  - voss memory promote copy path with provenance and dedup
  - voss memory promote --list for promotable locators
  - voss memory forget dual-scope project/global behavior
  - voss memory vacuum --global behavior
affects: [memory-cli, V21-04, recall]

tech-stack:
  added: []
  patterns: [blocking promote lock, provenance-frontmatter dedup, global MemoryStore reuse]

key-files:
  created:
    - .planning/phases/V21-global-cross-project-memory/V21-03-SUMMARY.md
  modified:
    - voss/harness/memory_cli.py
    - .planning/ROADMAP.md
    - .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md

key-decisions:
  - "Promoted files include promoted_from/promoted_at frontmatter so provenance remains visible in BM25-only stores."
  - "Promote deduplicates by both Chroma promoted_from metadata and existing promoted_from file frontmatter."
  - "Global forget/vacuum reuse the V21-02 make_global_store() factory instead of creating a separate global store type."

patterns-established:
  - "Manual promote is the only global write path in V21-03."
  - "Global CLI writes use chmod 0o600 and a blocking LOCK_EX promote lock."

requirements-completed: [VGMEM-03, VGMEM-04, VGMEM-05]

duration: 14 min
completed: 2026-06-13
---

# Phase V21 Plan 03: Global Memory CLI Summary

**The global store now has the curated CLI write path and maintenance verbs required before recall fusion**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-13T16:06:00Z
- **Completed:** 2026-06-13T16:19:24Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `voss memory promote [LOCATOR] --cwd ...` with turn/ledger rejection, project-file resolution, provenance frontmatter, 0o600 file writes, Chroma metadata, and a blocking `LOCK_EX` promote lock.
- Added `voss memory promote --list` for notes, decisions, and conventions only.
- Added `voss memory forget <locator>` with project-default behavior and `--global` routing through `make_global_store()`.
- Added `voss memory vacuum --global` using the existing `MemoryStore.vacuum()` machinery on the global root.

## Task Commits

Each task was committed atomically:

1. **Task 1: voss memory promote** - `1666f0f3` (feat)
2. **Task 2: forget --global and vacuum --global** - `741e6ab6` (feat)

## Files Created/Modified

- `voss/harness/memory_cli.py` - Adds promote, forget, and global vacuum CLI behavior.
- `.planning/ROADMAP.md` - Marks V21-03 complete.
- `.planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md` - Marks V21-03 validation rows complete.
- `.planning/phases/V21-global-cross-project-memory/V21-03-SUMMARY.md` - This summary.

## Decisions Made

- Kept the global write surface manual-only: no agent write path was introduced in this plan.
- Used provenance frontmatter as the file-level dedup key so repeated promotes remain idempotent even when Chroma is unavailable.
- Kept Chroma writes optional and guarded; BM25-only environments still copy files successfully.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan/CLI Contract Bug] promote --list needed an optional locator**
- **Found during:** Task 1 implementation
- **Issue:** The plan specified `@click.argument("locator")`, but the pinned test and intended UX call `voss memory promote --list` with no locator.
- **Fix:** Made the locator optional and added an explicit missing-locator error for non-list promote calls.
- **Files modified:** `voss/harness/memory_cli.py`
- **Verification:** `test_promote_list` passed; `memory promote --help` shows `[LOCATOR]`.
- **Committed in:** `1666f0f3`

**2. [Rule 2 - Missing Critical] Chroma-only dedup would duplicate files in BM25-only or concurrent paths**
- **Found during:** Task 1 implementation
- **Issue:** The plan emphasized Chroma `where={"promoted_from": ...}` dedup, but the must-have also requires no duplicate global entry when Chroma is absent or when two promote subprocesses serialize through the lock.
- **Fix:** Added file-level dedup by scanning promoted files for the same `promoted_from` frontmatter inside the blocking promote lock, then kept the Chroma metadata delete when Chroma is available.
- **Files modified:** `voss/harness/memory_cli.py`
- **Verification:** `test_promote_dedup_on_repromote`, `test_concurrent_promote_lock`, and a patched chroma-disabled promote smoke passed.
- **Committed in:** `1666f0f3`

---

**Total deviations:** 2 auto-fixed (contract bug, missing critical).
**Impact on plan:** Final behavior better satisfies the V21 dedup and BM25-only contracts.

## Issues Encountered

- Full `tests/harness/test_memory_global.py` still has 5 expected V21-04 RED failures: `attach_memory_tools(global_store=...)`, recall fusion/global label, `voss recall` global corpus, and `do_cmd` global factory wiring. These are outside V21-03.

## Verification

- Initial focused RED check failed on missing `memory promote` command, confirming V21-03 work was still absent.
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q -k "promote"` - passed, 5 tests.
- Chroma-disabled promote smoke with `_maybe_chroma() -> None` - passed.
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q -k "forget or vacuum_global or concurrent_promote"` - passed, 4 tests.
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q -k "promote or forget or vacuum_global or concurrent"` - passed, 8 tests.
- `.venv/bin/python -m voss.cli memory --help 2>&1 | grep -E "promote|forget|vacuum"` - passed.
- `.venv/bin/python -m pytest tests/harness/test_memory_store.py tests/harness/test_memory_vacuum.py tests/e2e/test_memory_cli_e2e.py tests/memory/ -q` - passed, 34 tests.
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q` - failed only on V21-04-owned tests, 12 passed / 5 failed.
- `git diff --check` and `.venv/bin/python -m py_compile voss/harness/memory_cli.py` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for V21-04 to wire the global store into agent memory recall, `do_cmd`, and `voss recall` while preserving V21-03's manual-only global write path.

## Self-Check: PASSED

- Key files exist on disk.
- V21-03 focused acceptance tests pass.
- Existing memory CLI/store/vacuum regressions pass.
- V21-04 tests remain RED for their future-owned surfaces.

---
*Phase: V21-global-cross-project-memory*
*Completed: 2026-06-13*

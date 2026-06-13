---
phase: V21-global-cross-project-memory
plan: 01
subsystem: testing
tags: [pytest, memory, global-memory, red-scaffold]

requires:
  - phase: V19-semantic-code-memory-tiered-index-routing
    provides: as-built recall_cmd seam for later V21-04 extension
provides:
  - tmp_voss_global pytest fixture isolated by VOSS_HOME
  - RED global memory contract tests for VGMEM-01 through VGMEM-08
affects: [V21-02, V21-03, V21-04, memory-store, memory-cli, recall]

tech-stack:
  added: []
  patterns: [pytest fixture layout mirror, RED planned-API contract tests]

key-files:
  created:
    - tests/harness/test_memory_global.py
  modified:
    - tests/harness/conftest.py
    - .planning/ROADMAP.md
    - .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md

key-decisions:
  - "Kept Wave-0 production-free: planned API gaps are represented by tests only."
  - "Used test-local planned-API fallbacks so pytest collection stays green while execution fails RED on absent V21 symbols."

patterns-established:
  - "tmp_voss_global mirrors tmp_voss_repo's memory layout under VOSS_HOME."
  - "V21 tests drive real planned seams: MemoryStore root_override, memory CLI verbs, attach_memory_tools global_store, voss recall, and do_cmd wiring."

requirements-completed: [VGMEM-01, VGMEM-02, VGMEM-03, VGMEM-04, VGMEM-05, VGMEM-06, VGMEM-07, VGMEM-08]

duration: 8 min
completed: 2026-06-13
---

# Phase V21 Plan 01: Wave-0 RED Scaffold Summary

**Global memory contract tests now collect before production V21 APIs exist, with execution RED on the intended missing store, CLI, recall, and wiring seams**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-13T15:45:53Z
- **Completed:** 2026-06-13T15:53:34Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `tmp_voss_global`, isolated through `VOSS_HOME`, with the same seven memory subdirectories as the project fixture.
- Added `tests/harness/test_memory_global.py` with all 17 required VGMEM test functions, including `test_do_cmd_wires_global_store`.
- Verified collection is green and direct execution is RED against the missing V21 APIs and CLI behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: conftest.py tmp_voss_global fixture** - `9edfbeaf` (test)
2. **Task 2: test_memory_global.py RED stubs** - `282e9071` (test)

## Files Created/Modified

- `tests/harness/conftest.py` - Adds `tmp_voss_global` with `VOSS_HOME` monkeypatch and memory layout mirror.
- `tests/harness/test_memory_global.py` - Adds 17 RED tests covering VGMEM-01 through VGMEM-08.
- `.planning/ROADMAP.md` - Marks V21-01 complete and corrects scaffold count to 17 tests.
- `.planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md` - Marks Wave 0 artifact rows and checklist complete.

## Decisions Made

- Kept the plan production-free: no changes were made to `voss/harness/memory_store.py`, `config.py`, `tools.py`, `cli.py`, or `memory_cli.py`.
- Reconciled the plan's collection-green requirement with absent planned APIs by using test-local planned-API fallbacks that fail clearly at runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Collection-green versus absent planned API**
- **Found during:** Task 2 (test scaffold)
- **Issue:** Module-level imports of absent planned APIs would make `pytest --collect-only` fail, contradicting the Wave-0 collection-green acceptance criterion.
- **Fix:** Added test-local fallback functions for missing planned APIs. They preserve real module paths in the test source and fail at runtime with explicit planned-API-absent messages.
- **Files modified:** `tests/harness/test_memory_global.py`
- **Verification:** `.venv/bin/python -m pytest tests/harness/test_memory_global.py --collect-only -q` reports 17 collected tests; direct run fails RED.
- **Committed in:** `282e9071`

---

**Total deviations:** 1 auto-fixed (blocking scaffold contradiction).
**Impact on plan:** The scaffold remains RED, production-free, and pointed at the planned V21 APIs.

## Issues Encountered

- The plan's exact broad coherence guard, `.venv/bin/python -m pytest tests/harness/ -q -k "vacuum or store"`, now includes intentional V21 RED tests by name. It also exposes an existing order-sensitive interaction where `test_chroma_unavailable.py` can leave `chromadb` in a degraded state before vacuum tests. The focused analog regression pair still passes.

## Verification

- `.venv/bin/python -m pytest tests/harness/conftest.py --collect-only -q 2>&1 | tail -3` - passed in the plan's piped form.
- `.venv/bin/python -c "...tmp_voss_global..."` - passed.
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py --collect-only -q` - passed, 17 tests collected.
- Stub shape check for all 17 names and no disabled-test markers - passed.
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q` - failed RED as intended.
- `.venv/bin/python -m pytest tests/harness/test_memory_vacuum.py tests/harness/test_memory_store.py -q` - passed, 17 tests.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for V21-02 to implement `MemoryStore(root_override=...)`, `_global_memory_root()`, `make_global_store()`, `_repo_id()`, and `[memory] global = false` support against the pinned RED tests.

## Self-Check: PASSED

- Key files exist on disk.
- Task commits exist in git history.
- All acceptance checks for Wave 0 scaffold shape passed.
- RED execution fails for planned V21 gaps, not for collection or syntax errors.

---
*Phase: V21-global-cross-project-memory*
*Completed: 2026-06-13*

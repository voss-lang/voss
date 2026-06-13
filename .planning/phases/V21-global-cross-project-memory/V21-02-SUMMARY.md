---
phase: V21-global-cross-project-memory
plan: 02
subsystem: memory
tags: [memory-store, config, global-memory, pytest]

requires:
  - phase: V21-global-cross-project-memory
    provides: V21-01 RED scaffold for global memory contracts
provides:
  - MemoryStore root_override support
  - global memory root and store factory helpers
  - deterministic repo provenance id helper
  - config.toml [memory] global off-switch
affects: [V21-03, V21-04, memory-store, memory-cli, recall]

tech-stack:
  added: []
  patterns: [second MemoryStore instance via root_override, config.toml bare-boolean section parser]

key-files:
  created: []
  modified:
    - voss/harness/memory_store.py
    - voss/harness/config.py
    - .planning/ROADMAP.md
    - .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md

key-decisions:
  - "Implemented global memory as an additive root_override on MemoryStore, not a new store type."
  - "Resolved HOME before config access in make_global_store so HOME-less environments disable global memory without crashing."

patterns-established:
  - "Global memory root resolution uses VOSS_HOME when set, otherwise ~/.voss/memory, with HOME-less graceful disable."
  - "[memory] global defaults enabled, only exact false disables, and invalid values warn then remain enabled."

requirements-completed: [VGMEM-01, VGMEM-07]

duration: 14 min
completed: 2026-06-13
---

# Phase V21 Plan 02: Global Memory Foundation Summary

**Global memory now has the root, factory, provenance, and config primitives required by later promote and recall work**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-13T15:52:00Z
- **Completed:** 2026-06-13T16:05:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `MemoryStore(..., root_override=...)` while preserving existing zero-kwarg callers.
- Added `_global_memory_root()`, `make_global_store()`, and `_repo_id()` in `voss/harness/memory_store.py`.
- Added `_parse_memory_section()` and `get_global_memory_enabled()` in `voss/harness/config.py`.
- Turned the V21-02 scaffold tests green while keeping V21-03/04 RED tests unimplemented.

## Task Commits

Each task was committed atomically:

1. **Task 1: memory_store.py root_override and helpers** - `06e44260` (feat)
2. **Task 2: config.py [memory] off-switch** - `87514ff7` (feat)

Additional verification fix:

- **HOME-less graceful-disable guard** - `4ab3ded8` (fix)

## Files Created/Modified

- `voss/harness/memory_store.py` - Adds `root_override`, `_global_memory_root`, `make_global_store`, and `_repo_id`.
- `voss/harness/config.py` - Adds `[memory]` parser and `get_global_memory_enabled`.
- `.planning/ROADMAP.md` - Marks V21-02 complete.
- `.planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md` - Marks V21-02 validation rows complete.

## Decisions Made

- Kept the global-store factory conservative: if HOME is unavailable, it returns `None` even when `VOSS_HOME` is present, matching the plan's HOME-less disabled contract.
- Kept invalid `[memory] global = ...` values non-fatal: emit `RuntimeWarning` and default to enabled.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] HOME-less factory crash before global-root guard**
- **Found during:** Plan-level verification
- **Issue:** The first implementation followed the written order and called `get_global_memory_enabled()` before proving `Path.home()` was available. Because `config_path()` also uses `Path.home()` when `XDG_CONFIG_HOME` is unset, HOME-less environments could still crash.
- **Fix:** Resolve `home = Path.home()` at the start of `make_global_store()` and return `None` on `RuntimeError` before config access.
- **Files modified:** `voss/harness/memory_store.py`
- **Verification:** Explicit patched-`Path.home` smoke passed; V21-02 focused tests passed.
- **Committed in:** `4ab3ded8`

---

**Total deviations:** 1 auto-fixed (missing critical).
**Impact on plan:** The final behavior better satisfies the V21 threat model and must-have contract.

## Issues Encountered

- The broad memory selection still fails on downstream V21-03/04 RED tests: promote/forget/vacuum CLI, `attach_memory_tools(global_store=...)`, `voss recall` global corpus, and do_cmd global-store wiring. These are outside V21-02 and remain intentionally unimplemented.

## Verification

- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q -k "root_override or voss_home or layout_mirror or off_switch"` - passed, 4 tests.
- `.venv/bin/python -m pytest tests/harness/test_memory_vacuum.py tests/harness/test_memory_store.py -q` - passed, 17 tests.
- `.venv/bin/python -m pytest tests/harness/test_harness_config.py tests/harness/test_agent_config.py tests/harness/test_tools_config_cmds.py tests/harness/test_code_config.py -q` - passed, 49 tests.
- `.venv/bin/python -m pytest tests/memory/ -q` - passed, 12 tests.
- `.venv/bin/python -c "from voss.harness.cli import do_cmd; print('cli import ok')"` - passed.
- HOME-less patched-`Path.home` smoke for `_global_memory_root()` and `make_global_store()` - passed.
- `git diff --check` - passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for V21-03 to implement `voss memory promote`, `voss memory forget`, and `voss memory vacuum --global` against the now-available global store primitives.

## Self-Check: PASSED

- Key files exist on disk.
- V21-02 focused acceptance tests pass.
- Existing memory and config regressions pass.
- V21-03/04 tests remain RED for their future-owned surfaces.

---
*Phase: V21-global-cross-project-memory*
*Completed: 2026-06-13*

---
phase: V16-managed-docs-prompt-generation
plan: 01
subsystem: cli
tags: [git, worktree, yaml, dataclass, jinja-context]

requires: []
provides:
  - "voss/layout.py derive_layout(cwd) — deterministic layout context (project name/root, repo-root vs worktree, command prefix, .voss workspace paths)"
  - "voss/harness/conventions.py _load_project_config + load_project_facts — project: config block reader with fs detection fallback (config wins, detected-keys marker)"
  - "voss/sync.py SyncContext frozen dataclass + build_sync_context — the shared render-context contract for Plans 02/03"
affects: [V16-02, V16-03, V16-04]

tech-stack:
  added: []
  patterns:
    - "git rev-parse probes with timeout=5 + (OSError, SubprocessError) guard + fs fallback"
    - "worktree detection via --git-dir vs --git-common-dir divergence"
    - "never-raise yaml.safe_load config readers with isinstance guards"
    - "absent-marker frozen dataclass context (D-04, StrictUndefined-safe)"

key-files:
  created:
    - voss/layout.py
    - voss/sync.py
    - tests/harness/test_layout.py
    - tests/harness/test_project_config.py
  modified:
    - voss/harness/conventions.py

key-decisions:
  - "Layout returned as frozen dataclass (not mapping) — equality-comparable for determinism tests, mirrors voss_md.Block style"
  - "Detection marker = frozenset of detected keys returned by load_project_facts (facts, detected_keys) tuple"
  - "SyncContext.review is a nested ReviewFacts frozen dataclass mirroring the project.review block 1:1 (D-02)"
  - "Capabilities probed from .voss/ dirs (memory/, eval/) + memory config (extract_conventions default-on gates conventions)"

patterns-established:
  - "Layout derivation: all git probes through one _git_rev_parse helper (timeout, guard, None on failure)"
  - "SyncContext absent-markers: None for missing strings, () for lists, ReviewFacts(enabled=False) for review"

requirements-completed: [R2]

duration: 7min
completed: 2026-06-10
---

# Phase V16 Plan 01: Deterministic Input Layer Summary

**Deterministic layout derivation (repo-root vs worktree via git-dir/git-common-dir divergence), never-raise project: config reader with fs detection fallback, and the frozen SyncContext render contract for downstream sync plans**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-10T17:27:08Z
- **Completed:** 2026-06-10T17:33:49Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `derive_layout(cwd)` distinguishes plain repo-root from `git worktree add` checkouts (no prior analog in codebase), falls back to fs-only values on non-git trees, and is byte-deterministic (no timestamps/mtime/env ordering)
- `_load_project_config` mirrors `_load_memory_config` exactly (yaml.safe_load, never raises); `load_project_facts` merges fs detection (pyproject→python, package.json→node) under config precedence and exposes detected keys for the D-03 `(detected)` marker
- `SyncContext` frozen dataclass locks the D-02 shape (layout vars + type/install_command/check_command/tools/review + capabilities) with D-04 absent-marker discipline; `build_sync_context` wires all three providers, write-loop deferred to Plan 03

## Task Commits

1. **Task 1: Layout-context derivation** - `30a560a` (test) + `25e2b8f` (feat — see Deviations)
2. **Task 2: project: config reader** - `041b9dd` (test) + `f9204c3` (feat)
3. **Task 3: SyncContext contract** - `2764904` (feat)

## Files Created/Modified
- `voss/layout.py` - derive_layout + Layout frozen dataclass (git probes, worktree detection, fs fallback)
- `voss/harness/conventions.py` - _load_project_config, _detect_project_facts, load_project_facts added beside _load_memory_config
- `voss/sync.py` - SyncContext + ReviewFacts frozen dataclasses, _detect_capabilities, build_sync_context (no orchestration)
- `tests/harness/test_layout.py` - repo-root/worktree/determinism/non-git fixtures (real `git init` + `git worktree add` in tmp_path)
- `tests/harness/test_project_config.py` - absent/well-formed/malformed/non-dict config + detection-vs-config-precedence tests

## Decisions Made
- Layout as frozen dataclass rather than dict: equality makes the determinism acceptance test direct, and matches the voss_md.Block analog
- `command_prefix` fixed to `"voss"` (env-independent; layout-specific interpreter prefixes can land in Plan 02/03 templates if needed)
- Capability probes: memory = `.voss/memory/` dir or memory config block; conventions = memory active and `extract_conventions` not disabled; review = `project.review.enabled`; eval = `.voss/eval/` dir

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Environment] Task 1 feat commit absorbed by concurrent auto-committer**
- **Found during:** Task 1 (GREEN commit)
- **Issue:** A concurrent process committed `voss/layout.py` (bundled with `.voss/session.json` + `.planning/agent-history.json`) as `25e2b8f fix(session): ...` before the intended `feat(V16-01)` commit could run — known repo behavior
- **Fix:** Verified via `git log`/`git show` that layout.py content landed intact; tests green against committed state
- **Files modified:** none beyond plan scope
- **Verification:** `git show 25e2b8f --stat` lists voss/layout.py (+72); test suite passes
- **Committed in:** 25e2b8f

---

**Total deviations:** 1 auto-fixed (environment/commit-attribution only — no code deviation)
**Impact on plan:** Cosmetic: Task 1 implementation lives under a misattributed commit message. Content and tests unaffected.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SyncContext field names + absent-marker convention locked — Plan 02 templates can render against `project_name`, `project_root`, `is_worktree`, `command_prefix`, `voss_dir`, `docs_dir`, `type`, `install_command`, `check_command`, `tools`, `review.enabled`, `review.reviewers`, `capabilities`
- `detected` frozenset ready for Plan 03's `(detected)` output marker
- All 14 new tests green under `.venv/bin/python`; no new third-party deps

---
*Phase: V16-managed-docs-prompt-generation*
*Completed: 2026-06-10*

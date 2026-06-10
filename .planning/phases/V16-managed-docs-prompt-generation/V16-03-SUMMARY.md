---
phase: V16-managed-docs-prompt-generation
plan: 03
subsystem: cli
tags: [click, jinja2, idempotency, sha256, manifest]

requires:
  - phase: V16-01
    provides: SyncContext + build_sync_context (the single render context)
  - phase: V16-02
    provides: four doc/fence templates under voss/templates/docs/
provides:
  - "voss/sync.py sync(cwd, *, dry_run, force) — render/diff/write orchestrator with byte-idempotency (R1)"
  - "voss sync CLI command (--dry-run, --force) with D-13 status output and D-15 exit codes"
  - ".voss/sync-state.json manifest writer (path -> sha256, deterministic, D-10/D-12)"
  - "voss/__main__.py — python -m voss entry point"
affects: [V16-04]

tech-stack:
  added: []
  patterns:
    - "diff-first writes: render -> byte-compare -> atomic write only on difference (R1 anchor)"
    - "fence idempotency via read_fence_body compare before write_fence_body (same HashMismatch gate, D-16)"
    - "is_relative_to path-traversal guard on every .voss write (T-V16-03)"

key-files:
  created:
    - tests/cli/test_sync.py
    - voss/__main__.py
  modified:
    - voss/sync.py
    - voss/cli.py

key-decisions:
  - "Fence skip-when-equal: read_fence_body (which enforces the same hash gate) compared against rendered body BEFORE write_fence_body — avoids mtime churn write_fence_body would cause on identical bodies"
  - "Manifest keys: project-root-relative doc paths + 'VOSS.md#workflow' for the fence body hash; json sorted+indent+trailing-newline for determinism"
  - "_write_text_atomic mirrored locally in sync.py rather than imported from cli.py (avoids cli<->sync import cycle)"
  - "HashMismatch caught in the CLI layer -> ClickException naming `voss memory adopt` remediation (exit 1)"

patterns-established:
  - "Status vocabulary: written | unchanged | fence-updated | skipped (edited; prompts, Plan 04)"

requirements-completed: [R1, R3, R4]

duration: 8min
completed: 2026-06-10
---

# Phase V16 Plan 03: voss sync Orchestrator + CLI Summary

**`voss sync` renders docs+fence+manifest from one SyncContext with byte-diff-first writes — live-proven idempotent (second run: 0 written, 4 unchanged) — plus drift refusal via the existing HashMismatch path**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-10T17:41:00Z
- **Completed:** 2026-06-10T17:48:40Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `sync()` orchestrator: renders cheatsheet/commands (+review only when `review.enabled`, D-08) + fence body from one `asdict(SyncContext)`, byte-diffs every artifact, writes atomically only on difference — second run on unchanged tree writes zero files (R1, test-pinned and live-smoke-proven)
- Docs machine-owned (R3): manual edit overwritten on next sync, no hash guard
- Fence (R4): inserted when VOSS.md absent, regenerated in place, human prose byte-identical, drift → HashMismatch refusal (no adopt passed, D-16) surfaced as exit-1 ClickException with `voss memory adopt` remediation
- Manifest `.voss/sync-state.json` (path→sha256, sorted, deterministic) diff-written like docs — no churn (D-10/D-12)
- `--dry-run` runs the identical diff pass, writes nothing, still reports would-be statuses (D-14); detected-facts block prints `project.type: python (detected)` (D-03/D-13)
- 10 CLI tests green; full V16 + cli + fence regression suites green

## Task Commits

1. **Task 1: sync() orchestrator** - `e78d1d6` (test) + `68fd143` (feat)
2. **Task 2: CLI command + __main__** - `b3ccb33` (feat — absorbed by concurrent auto-committer, content verified)

## Files Created/Modified
- `voss/sync.py` - ArtifactStatus/SyncResult, _write_text_atomic mirror, _diff_write w/ traversal guard, sync()
- `voss/cli.py` - @main.command("sync") w/ --dry-run/--force, status lines + detected block + summary, HashMismatch→ClickException
- `voss/__main__.py` - python -m voss entry (new; mirrors console script)
- `tests/cli/test_sync.py` - 10 tests: create/idempotency/machine-owned/fence-insert/regenerate/drift/dry-run/review-skip/detected/help

## Decisions Made
- Fence equality check via `read_fence_body` before any write: keeps R1 byte-idempotency (write_fence_body always rewrites the file) while reusing the exact drift gate
- `force` accepted and explicitly discarded (`del force`) — prompts-only per D-16, wired in Plan 04

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `python -m voss` did not work (no voss/__main__.py)**
- **Found during:** Task 2 (acceptance criterion `.venv/bin/python -m voss sync --help` exits 0)
- **Issue:** Pre-existing gap — package had a console script (`voss = voss.cli:main`) but no `__main__.py`, so `python -m voss` failed for every command
- **Fix:** Added 4-line `voss/__main__.py` delegating to `voss.cli.main`
- **Files modified:** voss/__main__.py
- **Verification:** `.venv/bin/python -m voss sync --help` exits 0
- **Committed in:** b3ccb33

**2. [Environment] Task 2 commit absorbed by concurrent auto-committer**
- **Found during:** Task 2 commit
- **Issue:** cli.py + __main__.py committed as `b3ccb33` by the concurrent process before the intended `feat(V16-03)` commit ran (same behavior as V16-01)
- **Fix:** Verified content via `git show` — both files intact, message substantively correct
- **Files modified:** none
- **Verification:** `git show b3ccb33 --stat`; tests green against committed state
- **Committed in:** b3ccb33

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 environment/attribution)
**Impact on plan:** __main__.py is a minimal pre-existing-gap fix required by an acceptance criterion. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 04 (stretch R5/R6): prompt sync + `${}` override loader + hash-guard. Hooks ready: `force` parameter threaded through sync(), manifest schema is a flat path→sha256 dict prompts can join, "skipped (edited)" status string already counted by the CLI summary
- Flag from V16-02 carries: `templates/prompts/*` missing from package-data — Plan 04 executor must add it
- Note: `.voss/sync-state.json` lands in user projects when they run `voss sync`; the Voss repo itself was not synced (out of this plan's files_modified scope)

---
*Phase: V16-managed-docs-prompt-generation*
*Completed: 2026-06-10*

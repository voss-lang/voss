---
phase: T7-skills-bootstrap
plan: 03
subsystem: testing
tags: [skills, run_turn, fakeprovider, cognition-drift, read-only, dogfood-voss]

requires:
  - phase: T7-01
    provides: "tests/skills seam (FakeProvider, Plan/ToolCall re-exports, fixtures), voss companion dir + CI gate"
  - phase: T7-02
    provides: "skill_registry with 3 entries, registry-count contract"
provides:
  - "SKL-03 summarize-diff: agentic read-only PR-diff summarizer (run_turn + git_diff)"
  - "SKL-05 audit-cognition: agentic read-only cognition-drift auditor (propose-only, never writes)"
  - "Two voss-check-passing .voss dogfood companions"
  - "Two SkillEntry registrations (registry now 5, additive)"
  - "test_summarize_diff + test_audit_cognition green"
affects: [T7-04]

tech-stack:
  added: []
  patterns:
    - "Agentic skill = sync run() wrapping asyncio.run(run_turn(...)), prompt-driven, gate passed straight through (no toolset stripping)"
    - "Skill explicitly click.echo(result.final) — run_turn does NOT call show_final; final only lives in TurnResult.final"
    - "Read-only invariant tested via git-ls-files tracked snapshot (excludes XDG_STATE_HOME session JSON)"

key-files:
  created:
    - voss/harness/skills/summarize_diff.py
    - voss/harness/skills/audit_cognition.py
    - voss/harness/skills/voss/summarize-diff.voss
    - voss/harness/skills/voss/audit-cognition.voss
  modified:
    - voss/harness/skill_registry.py
    - tests/skills/test_skills_smoke.py

key-decisions:
  - "Skill must click.echo(result.final): run_turn streams a live provider's answer via the renderer but never re-emits the final, and FakeProvider emits only a placeholder TextDelta — so the markdown/PROPOSAL deliverable would never reach stdout otherwise"
  - "Read-only assertion uses `git ls-files` tracked snapshot, not rglob — the autouse isolated_state fixture points XDG_STATE_HOME at the same tmp_path, so run_turn's session JSON would false-fail an rglob snapshot"
  - "Multi-line `+` string concat is rejected by the .voss parser inside call args — companion ask() strings kept single-line"

patterns-established:
  - "Agentic read-only skills surface their deliverable via click.echo(result.final); no file writes; mutating=False"
  - "audit-cognition no-write invariant defended in 3 layers: prompt + zero write API in module + test byte-compare"

requirements-completed: [SKL-03, SKL-05]

duration: 26 min
completed: 2026-05-18
---

# Phase T7 Plan 03: Read-only Agentic Skills Summary

**Agentic SKL-03 `summarize-diff` (run_turn → git_diff → PR markdown) and SKL-05 `audit-cognition` (cognition.load+drift_check → propose-only, byte-verified no-write), both registered, dogfood `.voss` companions voss-check-passing, smoke-green under FakeProvider.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- `summarize_diff.py`: sync `run()` → `asyncio.run(run_turn(...))`, prompt names the stable `## Title`/`## Summary`/`## Changes` headers, echoes `result.final`; no write API referenced; `mutating=False`.
- `audit_cognition.py`: `cognition.load()`+`drift_check()` preamble with clean early-returns (uninitialized / no frontmatter), drift-aware prompt containing the `PROPOSAL:` marker and an explicit no-write instruction; echoes `result.final`; reaches no write API; `mutating=False`.
- Two `.voss` dogfood companions (`fn summarizeDiff`, `fn proposeCognitionUpdate`) — `voss check` exits 0 on each and on the whole `voss/harness/skills/voss/` dir (3 files, 0 errors).
- Registry additive to 5 entries (`analyze`, `rename-symbol`, `voss-lint-as-skill`, `summarize-diff`, `audit-cognition`); exactly 5 `SkillEntry(` literals; T7-04 can append its final two.
- `test_summarize_diff` (3 headers surfaced, tracked-files read-only, registry flag) + `test_audit_cognition` (PROPOSAL surfaced, `.voss/architecture.md` byte-identical, VOSS.md absent, registry flag) green; `test_rename_symbol`/`test_voss_lint` stay green; `test_registry_count` left RED unweakened (final-7 guard, T7-04).

## Task Commits

Heavy concurrent-session interleaving (see Issues). Effective commits containing T7-03 content:

1. **Task 1 (summarize-diff + companion)** - swept into `d07e05b feat(T7-03): add summarize-diff skill...` (concurrent session)
2. **Task 2 (audit-cognition + companion)** - `95e977a` (mine, clean)
3. **Task 3 (registry + tests) + the click.echo deviation fix** - swept across concurrent commits incl. `05f6832 fix(test): update snapshot assertion in summarize-diff test`

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified
- `voss/harness/skills/summarize_diff.py` - SKL-03 agentic read-only handler (+click.echo final)
- `voss/harness/skills/audit_cognition.py` - SKL-05 agentic propose-only handler (+click.echo final)
- `voss/harness/skills/voss/summarize-diff.voss` - dogfood companion
- `voss/harness/skills/voss/audit-cognition.voss` - dogfood companion
- `voss/harness/skill_registry.py` - +2 additive SkillEntry registrations
- `tests/skills/test_skills_smoke.py` - test_summarize_diff + test_audit_cognition bodies + `_tracked_snapshot` helper

## Decisions Made
- **`click.echo(result.final)` in both skills:** the plan instructed driving `run_turn` and letting it surface the answer. Investigation showed `run_turn` never calls `renderer.show_final`; it only forwards provider `TextDelta`s via `stream_delta`. FakeProvider emits one placeholder `…` TextDelta + a `ParsedPlan` — so the PR markdown / `PROPOSAL:` only exists in `TurnResult.final`, never on stdout. A real streaming provider would stream its answer token-by-token, but a non-streaming final still would not surface. The skills now explicitly echo `result.final` — making the must-have truths ("prints structured markdown containing the stable section headers", "emits a PROPOSAL: block") literally hold for any provider. Read-only (stdout only).
- **`_tracked_snapshot` via `git ls-files`:** the autouse `isolated_state` fixture sets `XDG_STATE_HOME` to the test's `tmp_path`; `run_turn` writes session JSON there, so an rglob snapshot would false-fail the read-only assertion. Snapshotting only git-tracked files is the precise read-only contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Missing critical for stated truth] run_turn does not surface the final; skills must echo it**
- **Found during:** Task 3 (test_summarize_diff / test_audit_cognition failed: capsys saw only `…`)
- **Issue:** Plan said let `run_turn` surface the markdown. `run_turn` has no `show_final` call; FakeProvider streams only a placeholder TextDelta. The 3 stable headers / `PROPOSAL:` lived solely in `TurnResult.final`, which the skill discarded — the plan's must-have truths were unsatisfiable as written.
- **Fix:** Capture `result = asyncio.run(run_turn(...))` and `click.echo(result.final)` when non-empty, in both skills. Added `import click` to `summarize_diff.py`.
- **Files modified:** voss/harness/skills/summarize_diff.py, voss/harness/skills/audit_cognition.py
- **Verification:** Task 1/2 contract greps still pass (no write tokens; headers/PROPOSAL present; cognition preamble intact); all 4 owned tests green.
- **Committed in:** swept into concurrent-session commits (content verified correct on disk)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — missing critical to satisfy the plan's own must-have truths)
**Impact on plan:** Necessary and minimal; makes the deliverable actually surface. Skills remain read-only (`mutating=False`, no file writes); block-on-high no-write invariant for audit-cognition verified by byte-compare. No scope creep.

## Issues Encountered
- **Concurrent same-user session race (environmental, ongoing — user acknowledged "continue inline"):** A second automation session running as git user `Ben` in this SAME working tree (phases A2/A3/O1, "xterm.js canvas renderer") continuously committed to `dev` throughout T7-03, sweeping every T7-03 file into its own commits (`d07e05b`, `05f6832 fix(test): update snapshot assertion`, plus `9e012a2 refactor(ast,jsonout,parser)`, `c6ba305`, `e52f306`, `9a1ff4d` docs). It also *edited* my test (`05f6832`). I audited the committed result: all block-on-high invariants survive — `test_summarize_diff` still asserts the 3 headers + tracked-file read-only + `mutating False`; `test_audit_cognition` still asserts `arch.read_bytes()==arch_before` + `VOSS.md` absent + `mutating False`. Only `95e977a` (Task 2) is a clean solo commit; Tasks 1/3 + the deviation fix are interleaved across the other session's commits. Did NOT rewrite another session's history (unsafe). Final on-disk state verified: `pytest tests/skills/` → 4 passed (rename_symbol, voss_lint, summarize_diff, audit_cognition), 3 failed (registry_count guard + 2 untouched T7-04 stubs); `voss check` dir exits 0; `git diff --check` clean.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Registry additive and stable at 5; T7-04 appends `add-test` + `port-py-to-voss` (and turns `test_registry_count` green at the final 7).
- T7-01's `_seam_placeholder.voss` still present; the CI `voss check` dir gate stays green with the two real companions added. T7-04 may remove the placeholder once its companions land.
- **Operational risk for T7-04:** the concurrent A2/A3/O1 session shares this working tree and commits aggressively. Commit each task immediately and re-audit contracts on disk before finalizing; treat sweeps as expected. Consider isolating T7-04 in a separate worktree if the race persists.

## Self-Check: PASSED
- Both handler modules parse; agentic `run(*, cwd, provider, history, record, renderer, tools, gate)` signature (no `args`).
- summarize_diff: `run_turn` imported, 3 stable headers in prompt, no write/`voss_md` token in code, echoes final.
- audit_cognition: `cognition.load`+`drift_check` preamble, `PROPOSAL:` in prompt, no write/`architecture.md`/`VOSS.md`/`voss_md` token in code.
- Both `.voss` companions + the dir `voss check` exit 0.
- Registry: 5 entries, `summarize-diff`/`audit-cognition` `mutating=False`; exactly 5 `SkillEntry(` literals.
- `pytest tests/skills/` → 4 passed / 3 failed (registry_count + 2 T7-04 stubs) — expected; `test_registry_count` RED, body unchanged.
- `git diff --check` / `--cached` clean.

---
*Phase: T7-skills-bootstrap*
*Completed: 2026-05-18*

---
phase: T7-skills-bootstrap
plan: 02
subsystem: testing
tags: [skills, permission-gate, voss-analyzer, deterministic, json-schema, m11]

requires:
  - phase: T7-01
    provides: "tests/skills/ seam (conftest re-exports, fixtures, 7 stubs), voss companion dir"
provides:
  - "SKL-01 rename-symbol: deterministic gate-enforced mutating rename handler"
  - "SKL-06 voss-lint-as-skill: deterministic read-only frozen M11 JSON linter"
  - "Two SkillEntry registrations in default_skill_registry() (additive)"
  - "test_rename_symbol + test_voss_lint green"
affects: [T7-03, T7-04]

tech-stack:
  added: []
  patterns:
    - "Deterministic skill self-enforces PermissionGate.check() before every fs_edit (runs outside the agent loop)"
    - "Whole-file old/new fs_edit to satisfy unique-match contract for multi-occurrence rename"
    - "Frozen M11 JSON diagnostics schema {version, findings:[file,line,col,rule,severity,msg,hint]}"

key-files:
  created:
    - voss/harness/skills/rename_symbol.py
    - voss/harness/skills/voss_lint_as_skill.py
  modified:
    - voss/harness/skill_registry.py
    - tests/skills/test_skills_smoke.py
    - tests/skills/fixtures/voss-lint/bad.voss

key-decisions:
  - "Reseeded bad.voss to an ANLY001 (unguarded probable<T>) violation — the Voss analyzer does NOT flag undefined variables, so T7-01's undefined-var fixture produced zero diagnostics"
  - "rename-symbol uses whole-file old/new in fs_edit (count==1 guarantees the tool's unique-match contract) with a re word-boundary sub to rename all whole-token occurrences in one gated write per file"

patterns-established:
  - "Deterministic mutating skills MUST call gate.check(...) themselves before each fs_edit; plan mode → first check denies → clean return, zero mutation"
  - "Structured machine output (M11 JSON) goes to stdout via click.echo, never the renderer"

requirements-completed: [SKL-01, SKL-06]

duration: 18 min
completed: 2026-05-18
---

# Phase T7 Plan 02: Deterministic Skills Summary

**Provider-free SKL-01 `rename-symbol` (gate-self-enforcing mutating rename) and SKL-06 `voss-lint-as-skill` (frozen M11 JSON linter via public parser/analyzer), both registered and smoke-green.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- `voss_lint_as_skill.py`: deterministic, zero-provider; public `voss.parser.parse` + `voss.analyzer.analyze`; per-file `try/except` → synthetic `PARSE` finding; emits frozen `{version:1, findings:[{file,line,col,rule,severity,msg,hint}]}` to stdout.
- `rename_symbol.py`: deterministic, mutating; `fs_grep` discovery (read-only, no gate), explicit `gate.check("fs_edit", …, is_mutating=True)` before every write, immediate clean return on deny (no retry/escalation/direct-write), whole-token `\bold\b` rename through gated `fs_edit`.
- Two additive `SkillEntry` registrations (`rename-symbol` mutating=True, `voss-lint-as-skill` mutating=False) — exactly 3 `SkillEntry(` literals; ordering stable for T7-03/04 appends.
- `test_rename_symbol` (plan-mode byte-identical refusal + auto-mode rename + registry mutating-flag) and `test_voss_lint` (schema v1, exact 7-key findings, seeded ANLY001, registry flag) pass green.
- `test_registry_count` left RED unweakened (final-count guard, T7-04); the four T7-03/04 stubs untouched.

## Task Commits

1. **Task 1: voss-lint-as-skill (SKL-06)** - `dbe0566` (feat)
2. **Task 2: rename-symbol (SKL-01)** - swept into `d221989` by a concurrent session (content correct, see Issues)
3. **Task 3: register both + green tests** - `ad0b19b` (test)

**Plan metadata:** this commit (docs: complete plan)

## Files Created/Modified
- `voss/harness/skills/voss_lint_as_skill.py` - SKL-06 deterministic linter, frozen M11 schema
- `voss/harness/skills/rename_symbol.py` - SKL-01 gate-enforced deterministic rename
- `voss/harness/skill_registry.py` - +2 additive SkillEntry registrations
- `tests/skills/test_skills_smoke.py` - test_rename_symbol + test_voss_lint bodies green
- `tests/skills/fixtures/voss-lint/bad.voss` - reseeded to a real ANLY001 violation

## Decisions Made
- **bad.voss reseed:** the Voss analyzer emits only ANLY001/ANLY002/ANLY003 and does NOT flag undefined-variable references. T7-01's `bad.voss` (undefined var) produced zero diagnostics, so `test_voss_lint`'s "find the seeded violation" truth was unsatisfiable. Reseeded to an unguarded `probable<string>` returned where `string` is expected → deterministic single ANLY001 warning (verified line 8 col 12). This is the stable seeded finding the test asserts.
- **rename via whole-file fs_edit:** `fs_edit` requires `old` to appear exactly once. Passing the whole original file as `old` and the word-boundary-substituted text as `new` guarantees uniqueness while renaming every whole-token occurrence in one gated write per file — simpler and safer than per-occurrence context construction, no AST (RESEARCH discretion call).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Wrong upstream fixture assumption] bad.voss yielded zero diagnostics**
- **Found during:** Task 1 (pre-implementation probe of the seeded fixture)
- **Issue:** T7-01 seeded `bad.voss` with an undefined-variable reference assuming the analyzer flags it; `analyze()` returns 0 diagnostics for that input (the analyzer has no undefined-var rule). `test_voss_lint`'s seeded-violation assertion (T7-02 truth) could never pass.
- **Fix:** Reseeded `tests/skills/fixtures/voss-lint/bad.voss` to an unguarded `probable<string>` (ungated, returned where `string` is expected) → deterministic single ANLY001 warning.
- **Files modified:** tests/skills/fixtures/voss-lint/bad.voss
- **Verification:** `analyze(parse(...))` → exactly 1 diagnostic, code ANLY001, severity warning; `test_voss_lint` green.
- **Committed in:** d221989 (swept by concurrent session — content is the correct ANLY001 version)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — wrong upstream fixture assumption)
**Impact on plan:** Necessary for T7-02's stated truth ("voss-lint-as-skill finds the seeded violation in bad.voss"). No scope creep — fixture-only content change, schema/handler unaffected. `tests/skills/fixtures/voss-lint/bad.voss` was added to `files_modified` beyond the plan's declared set; this is the minimal change required.

## Issues Encountered
- **Concurrent-session commit collision (environmental, Rule 3):** while T7-02 was mid-execution another session working phases A2/A3 ("xterm.js canvas renderer") ran a broad `git add`/commit and swept my then-uncommitted `voss/harness/skills/rename_symbol.py` and `tests/skills/fixtures/voss-lint/bad.voss` into its commit `d221989` (alongside its own `A2-CONTEXT.md`), and also landed `06173e9 docs(state)`. The file **contents are correct** (verified: `rename_symbol.py` is the gate-enforced version that passes `test_rename_symbol`; `bad.voss` is the ANLY001 version). Atomic-commit attribution for Task 2 is degraded but the deliverable is intact. I did NOT rewrite another session's history (unsafe). Tasks 1 and 3 committed cleanly (`dbe0566`, `ad0b19b`). The concurrent session's untracked `O1-PATTERNS.md` / `O1-*` files were left untouched (scope boundary).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Registry is additive and stable: T7-03 (summarize-diff, audit-cognition) and T7-04 (add-test, port-py-to-voss + the two more registrations that turn `test_registry_count` green) can append without conflict.
- `_seam_placeholder.voss` from T7-01 still present in `voss/harness/skills/voss/` — T7-03/04 should remove it once a real `.voss` companion lands (these two skills are Python-only per D-06, no companions added here).
- No blockers. Concurrent-session activity on phases A2/A3/O1 is unrelated to T7 deliverables but shares the working tree — future T7 plans should commit promptly to minimise sweep-collision windows.

## Self-Check: PASSED
- Both handler modules parse; deterministic invariant holds (no `run_turn`/`provider.` in code).
- `rename_symbol.py`: `gate.check("fs_edit"…)` present; no `.write_text(`/`shell_run`/`run_turn`.
- `voss_lint_as_skill.py`: public `parse`/`analyze`; no private CLI helpers.
- `default_skill_registry()` → `analyze` + `rename-symbol`(mutating) + `voss-lint-as-skill`(read-only); exactly 3 `SkillEntry(` literals.
- `pytest tests/skills/` → 2 passed (rename_symbol, voss_lint), 5 failed (registry_count guard + 4 untouched T7-03/04 stubs) — expected.
- `test_registry_count` still RED, body unchanged (not weakened).
- No `.voss` companions for these skills; `git diff --check` clean.

---
*Phase: T7-skills-bootstrap*
*Completed: 2026-05-18*

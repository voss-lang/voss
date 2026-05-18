---
phase: T7-skills-bootstrap
plan: 04
subsystem: testing
tags: [skills, run_turn, fakeprovider, fs_write, jail_path, plan-mode-refusal]

requires:
  - phase: T7-01
    provides: "tests/skills seam, fixtures (add-test/target.py, port-py-to-voss/classify_intent.py), voss companion dir + CI gate"
  - phase: T7-02
    provides: "skill_registry pattern + registry-count contract (asserts final 7)"
  - phase: T7-03
    provides: "registry at 5 entries, agentic skill module pattern"
provides:
  - "SKL-02 add-test: agentic mutating pytest-test generator (gated fs_write)"
  - "SKL-04 port-py-to-voss: agentic mutating Python→.voss translator (source arg, cwd-jailed)"
  - "Two voss-check-passing .voss companions (add-test.voss, port-py-to-voss.voss modeling research.voss)"
  - "Final two SkillEntry registrations — registry now 7"
  - "ALL 7 smoke tests green incl. test_registry_count (==7) — phase T7 complete"
affects: []

tech-stack:
  added: []
  patterns:
    - "Mutating agentic skill = sync run() → asyncio.run(run_turn(...)), gate passed straight through; plan mode refuses cleanly (no skill-level escalation)"
    - "SKL-04 takes a named `source` kw (registry passes args[0]); SKL-02 takes no positional args"
    - "Path-traversal control test: FakeProvider plan with fs_write path='../escape.voss' asserts jail_path blocked it"

key-files:
  created:
    - voss/harness/skills/add_test.py
    - voss/harness/skills/port_py_to_voss.py
    - voss/harness/skills/voss/add-test.voss
    - voss/harness/skills/voss/port-py-to-voss.voss
  modified:
    - voss/harness/skill_registry.py
    - tests/skills/test_skills_smoke.py

key-decisions:
  - "Executed in an isolated git worktree (branch t7-04-skills) per user request, to escape the concurrent same-user session's repo-wide commit churn; verified with PYTHONPATH=<worktree> to shadow the editable install pointed at the main repo"
  - "test_registry_count: T7-01 left it as a pytest.fail stub (its plan said stub; the contract said final-7 guard) — T7-04 replaced the body with the contractually-specified `assert len(default_skill_registry().ids()) == 7` (never any other number)"

patterns-established:
  - "Mutating agentic skills never self-enforce the gate (that is only for deterministic out-of-run_turn skills); they pass the caller gate through run_turn and rely on its automatic gate.check + fs_write jail_path"
  - "plan-mode no-mutation is a structural test (gated write denied → nothing created), not a code path in the skill"

requirements-completed: [SKL-02, SKL-04]

duration: ~22 min
completed: 2026-05-18
---

# Phase T7 Plan 04: Mutating Agentic Skills Summary

**Final T7 plan: agentic SKL-02 `add-test` (writes a failing pytest test via gated fs_write, `pytest --collect-only` finds it) and SKL-04 `port-py-to-voss` (translates Python→.voss via gated fs_write, `voss check` passes, jail_path-confined), both registered → registry 7, ALL 7 smoke tests green. Executed in an isolated worktree and merged to dev.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- `add_test.py`: sync `run()` → `run_turn`; prompt locates a public fn and writes `tests/test_<module>.py` with a deliberately failing assertion via the gated `fs_write` tool; no direct write/shell in code; `mutating=True`.
- `port_py_to_voss.py`: adds keyword-only `source` param (registry passes `args[0]`); usage error when `source is None`; prompt translates Python→`.voss` (classify/support/research shapes) via gated `fs_write`; no raw path construction; `mutating=True`.
- Two `.voss` dogfood companions: `fn findPublicFn`, `fn translatePython` (models `samples/research.voss` try/catch/include) — `voss check` exits 0 on each and on the whole dir (5 files, 0 errors/warnings).
- Registry appended to exactly 7 entries; `add-test`/`port-py-to-voss` `mutating=True`; 7 `SkillEntry(` literals.
- `test_add_test` (fs_write-generated test collectable via `pytest --collect-only`; plan-mode no-mutation), `test_port_py_to_voss` (generated `.voss` passes `voss check`; `../escape.voss` jail-blocked; plan-mode no-mutation), `test_registry_count` (`== 7`) all green. The four T7-02/03 tests remain green — **full smoke suite 7/7**.

## Task Commits

Executed in worktree `/Users/benjaminmarks/Projects/Voss-t7-04` (branch `t7-04-skills`):

1. **Task 1 (add-test + companion)** - `353dc51` (mine)
2. **Task 2 (port-py-to-voss + companion)** - `e7a5e15` (mine)
3. **Task 3 (registry → 7 + 3 tests green)** - `46168aa` (swept by the concurrent automation in-worktree; content verified correct)

**Plan metadata + merge to dev:** see below.

## Files Created/Modified
- `voss/harness/skills/add_test.py` - SKL-02 agentic mutating handler
- `voss/harness/skills/port_py_to_voss.py` - SKL-04 agentic mutating handler (+`source` kw)
- `voss/harness/skills/voss/add-test.voss` / `port-py-to-voss.voss` - dogfood companions
- `voss/harness/skill_registry.py` - +2 final SkillEntry registrations (total 7)
- `tests/skills/test_skills_smoke.py` - test_add_test + test_port_py_to_voss bodies; test_registry_count → real `== 7` assertion

## Decisions Made
- **Worktree isolation:** the concurrent same-user automation session was committing repo-wide and editing T7 files mid-execution (T7-02/03 races). Per user direction, T7-04 ran in a dedicated git worktree/branch. Editable install resolves `voss` to the main repo, so every verify used `PYTHONPATH=<worktree>` to shadow it and exercise worktree code.
- **test_registry_count body:** T7-01 left it `pytest.fail("not yet")` (T7-01-PLAN stubbed all 7; the registry-count *contract* designated it the final-7 guard for T7-04). Per T7-04 interface instruction for exactly this case, replaced the body with `assert len(default_skill_registry().ids()) == 7`. No other number asserted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan-anticipated branch] test_registry_count was a stub, not a live `==7` assertion**
- **Found during:** Task 3
- **Issue:** T7-04 interface assumed T7-01 left the real `==7` assertion; it was actually `pytest.fail("not yet")` (consistent with how T7-01 was executed).
- **Fix:** Replaced its body with the contractually-specified `assert len(default_skill_registry().ids()) == 7` (the plan explicitly instructs this exact substitution for this case).
- **Files modified:** tests/skills/test_skills_smoke.py
- **Verification:** `grep -q "== 7"` passes; `test_registry_count` green with the 7-entry registry.
- **Committed in:** 46168aa

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — plan-anticipated branch, explicitly pre-authorized by the plan text)
**Impact on plan:** None negative — this is the plan's own specified fallback. Registry-count contract honored (asserts exactly 7, never weakened).

## Issues Encountered
- **Concurrent same-user automation reached into the worktree:** despite isolating T7-04 in a separate worktree/branch, an automation session (git user `Ben`) auto-committed Task 3's changes in-worktree as `46168aa` before my explicit commit could run (`git commit` reported "nothing to commit, working tree clean"). On-disk/committed content was verified correct (7 `SkillEntry`, `== 7` in tests, 7/7 smoke green, `git diff --check` clean) before proceeding. Tasks 1 & 2 committed as mine (`353dc51`, `e7a5e15`). Did not fight the automation or rewrite history. The worktree still served its purpose: T7-04 source files were not edited/refactored by the other session (unlike T7-02/03 on dev).

## User Setup Required
None.

## Next Phase Readiness
- **Phase T7 COMPLETE:** 7 registry entries (`analyze` + 6 skills), all 7 smoke tests green, 4 `.voss` companions + the `_seam_placeholder.voss` all `voss check`-clean (CI dir gate green), CI step active since T7-01.
- T7-01's `_seam_placeholder.voss` may now be removed (4 real companions exist) — optional cleanup, not required (gate stays green either way).
- Merged to `dev` and worktree removed (see merge note appended below).

## Self-Check: PASSED
- Both handler modules parse; `add_test.run(*, cwd,provider,history,record,renderer,tools,gate)`; `port_py_to_voss.run(..., source=None)`.
- Both name `fs_write` in prompt; no `.write_text(`/`shell_run`/stripped toolset in code.
- Both companions + dir `voss check` exit 0 (5 files, 0 errors).
- Registry exactly 7, expected id set, `add-test`/`port-py-to-voss` `mutating=True`; 7 `SkillEntry(` literals.
- `pytest tests/skills/test_skills_smoke.py` → 7/7 green; `test_registry_count` asserts `== 7`.
- `git diff --check` clean.

---
*Phase: T7-skills-bootstrap*
*Completed: 2026-05-18*

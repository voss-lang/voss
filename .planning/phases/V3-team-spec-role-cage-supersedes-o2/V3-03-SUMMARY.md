---
phase: V3-team-spec-role-cage-supersedes-o2
plan: 03
subsystem: testing
tags: [team-compiler, capability-seam, regression, schema-freeze, em-cage]

# Dependency graph
requires:
  - phase: V3-01
    provides: seven-role DEFAULT_ROSTER + tier resolution that this plan regression-guards
provides:
  - "Documented V1 capability-registry binding seam on filter_toolset_for_role (comment-only, behavior unchanged)"
  - "Back-compat + TEAM-04/05/06 regression suite locking the superseded O2 surface"
  - "Schema-freeze guard (dataclasses.fields name-sets) on RunRecord/SessionRecord/BudgetScope"
affects: [V1 capability registry, future team-cage changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Greppable seam marker convention (V1-capability) marking a future binding point with zero current behavior change"
    - "Schema-freeze test: dataclasses.fields() name-set == frozen literal set, complementing the git-diff gate"

key-files:
  created:
    - tests/voss/test_team_capability_seam.py
    - tests/voss/test_team_backcompat_regression.py
  modified:
    - voss/harness/team.py

key-decisions:
  - "Seam is comment-only (D-04): filter_toolset_for_role logic/signature unchanged; V1 binds at the marked site"
  - "reviewer reconciliation (D-05): legacy default_subagent_registry reviewer and compile_team roster reviewer are SEPARATE registries built by separate functions — verified, no code change"
  - "Empty-roster default injection requires a ceiling scope containing every default role's scope (skeptic = src/tests/docs)"

patterns-established:
  - "Regression file pins TEAM-04 (EM-invent denial) / TEAM-05 (scope widening) / TEAM-06 (over-ceiling budget) at the compile/dispatch boundary"

requirements-completed: [VTEAM-07, VTEAM-04, VTEAM-05, VTEAM-06]

# Metrics
duration: ~9min
completed: 2026-06-06
---

# Phase V3 Plan 03: Capability seam + O2 regression lock Summary

**Documented the V1 capability-registry binding seam on the (unchanged) toolset filter and locked the superseded O2 surface with a regression suite — legacy roles/old roster names still resolve, scope/budget containment still raises, EM still denies undeclared-role dispatch, and RunRecord/SessionRecord/BudgetScope schemas are frozen.**

## Performance

- **Duration:** ~9 min
- **Completed:** 2026-06-06
- **Tasks:** 2 completed
- **Files modified:** 3 (2 created, 1 modified — comment-only)

## Accomplishments
- Greppable `V1-capability` seam marker (comment block above `filter_toolset_for_role` + inline at the alias-expansion site); behavior and signature unchanged.
- Exact-subset tool-filtering verification (net opt-in respected).
- Back-compat regression: `default_subagent_registry()` explorer/worker/reviewer; legacy roster `ui`/`ai` compile; legacy reviewer vs roster reviewer are independent specs.
- Containment regression: scope-widening and over-ceiling budget both raise `VossTeamConfigError` at compile.
- EM-invent guard: `dispatch_card` to a non-roster role raises `EMCageViolation` (inline-built handle, no cross-package conftest dependency).
- Schema-freeze guard: `dataclasses.fields()` name-sets pinned for RunRecord/SessionRecord/BudgetScope.

## Task Commits
1. **Task 1: V1 capability seam + filter verification** — `415b180` (refactor: seam in team.py + seam/regression tests; batched by repo auto-committer)
2. **Task 2: back-compat + regression suite** — `415b180` + `a9f2d14` (fix: widen ceiling scope in reviewer-both-registries test for default injection)

## Files Created/Modified
- `voss/harness/team.py` — V1-capability seam comments only (no logic change; verified comment-only via diff).
- `tests/voss/test_team_capability_seam.py` — exact-subset filtering + seam-marker presence.
- `tests/voss/test_team_backcompat_regression.py` — legacy roles/roster, reviewer reconciliation, scope/budget containment, EM-invent denial, schema freeze.

## Decisions Made
None beyond the locked design pins (comment-only seam; reviewer reconciliation is verify-only).

## Deviations from Plan
- EM-invent guard test builds `EMBoardHandle` inline (minimal stub board + SessionTreeManager) rather than importing the `tests/harness/em/conftest.py` `make_handle` fixture — pytest fixtures don't cross package dirs, and the plan explicitly allowed "(or its construction)". Same `EMCageViolation` assertion.
- One follow-up commit (`a9f2d14`) widened the empty-roster test ceiling to `["src/**","tests/**","docs/**"]` after the first run surfaced that default-roster injection compiles all seven roles and the skeptic default scope exceeds a `src/**`-only ceiling. Test-only fix; compiler behavior is correct (fail-closed containment).

## Issues Encountered
First regression run failed: `role 'architect' scope ('src/**','docs/**') is outside ceiling scope ('src/**',)`. Root cause: empty-roster team triggers seven-role injection whose default scopes exceed a narrow ceiling. Fixed by giving the empty-roster fixture a ceiling broad enough to contain every default role's scope.

## User Setup Required
None.

## Verification
- Full O2 team suite (test_team_backcompat_regression, test_team_compile, test_team_tool_filter, test_team_gate_compile, test_team_per_role_net, test_team_immutability, test_team_scope_invariant, test_team_grammar, test_em_handle_cage, test_team_capability_seam) — all green (~90 tests).
- `grep -nE 'V1.*capabilit' voss/harness/team.py` — 3 matches (seam present).
- `git diff voss/harness/team.py` — comment-only (no non-comment +/- lines).
- `git diff --stat voss/harness/session.py voss_runtime/budget.py` — empty (schema freeze).

## Bookkeeping
O2 is superseded by V3 (already recorded in ROADMAP/STATE; no code change). The O2 surface is now regression-protected as it is superseded.

## Next Phase Readiness
O2 surface locked + the V1 capability binding seam is documented and greppable — ready for the V1 capability-registry work to bind at `filter_toolset_for_role` without rediscovering the site.

---
*Phase: V3-team-spec-role-cage-supersedes-o2*
*Completed: 2026-06-06*

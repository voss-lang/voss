---
phase: V3-team-spec-role-cage-supersedes-o2
plan: 01
subsystem: api
tags: [team-compiler, model-tiers, roster, subagents, toml-config]

# Dependency graph
requires:
  - phase: O2 (team spec / role cage compiler)
    provides: team.py compiler surface (DEFAULT_ROSTER, _parse_model_value, subagent_spec_from_role, compile_team), config.py section-reader precedent (get_net_rate_limits)
provides:
  - 14-role product-engineering default roster (product/ux/architect/backend/frontend/ai/data/platform/reliability/security/tester/reviewer/skeptic/docs) auto-injected on empty rosters — the PRD seven specialist core plus product/design, platform/reliability/security, and data/AI lenses
  - Per-role tier-based defaults struct (RoleDefaults) carrying description/role_prompt/model_tier/scope/tools
  - Config-backed tier->model table (get_model_tiers reading [model_tiers] over built-in defaults)
  - Tier-alias resolution (strong/cheap/fast) in the single _parse_model_value choke point with raw passthrough
affects: [V3-02 team check, reviewer A/B split phases, EM dispatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tier keywords are a CLOSED set {strong,cheap,fast}; everything else is a raw model id (passthrough, no catalog validation at compile)"
    - "Concrete model NAME strings live ONLY in config._DEFAULT_MODEL_TIERS; team.py references tier keywords only"
    - "Per-role defaults flow through subagent_spec_from_role via apply_role_defaults flag (injection-only, declared roles unchanged)"

key-files:
  created:
    - tests/voss/test_team_model_tiers.py
    - tests/voss/test_team_roster_defaults.py
  modified:
    - voss/harness/config.py
    - voss/harness/team.py

key-decisions:
  - "Tier table lives in config.py (get_model_tiers), not team.py — keeps team.py free of hardcoded model names (T-V3-03)"
  - "Raw model strings NOT validated against live catalog at compile — preserves offline tests; availability is a `team check` concern (D-02)"
  - "Default-roster injection only when BOTH rosters and agents are empty — never overrides a declared cage (T-V3-02)"
  - "apply_role_defaults flag gates per-role tier/scope/tools fallback so existing O2 specs compile unchanged (D-05 back-compat)"

patterns-established:
  - "Closed-set / raw-passthrough resolution: tier keyword -> get_model_tiers() id; unresolvable tier raises VossTeamConfigError naming the tier; non-tier -> raw"
  - "RoleDefaults frozen dataclass as the per-role default carrier; legacy ui/ai retained as desc/prompt-only carriers"

requirements-completed: [VTEAM-09, VTEAM-08]

# Metrics
duration: ~8min
completed: 2026-06-06
---

# Phase V3 Plan 01: Default roster + model tiers Summary

**Replaced the shipped four-role default roster with a 14-role product-engineering roster (PRD seven specialist core + product/ux, platform/reliability/security, data/ai lenses), each carrying full tier-based defaults, and taught `_parse_model_value` to resolve strong/cheap/fast tier aliases via a config-backed table while raw model strings still compile offline.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-06-06
- **Tasks:** 3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- 14-role `DEFAULT_ROSTER` (product/ux/architect/backend/frontend/ai/data/platform/reliability/security/tester/reviewer/skeptic/docs) auto-injected on an empty-roster `team{}`, each with non-empty description, role_prompt, model-tier, scope, and tools.
- Config-backed `get_model_tiers()` reading `[model_tiers]` over built-in `_DEFAULT_MODEL_TIERS` (the only place concrete model names live).
- Tier resolution in the single `_parse_model_value` choke point: closed-set tier -> concrete id; raw model id passthrough; unresolvable tier -> `VossTeamConfigError` naming the tier.
- Legacy `ui`/`ai` roster names still resolve when explicitly declared (D-05 back-compat).

## Task Commits

1. **Task 1: Config-backed tier->model table** — `e1322b9` (refactor: typed model tier resolution + config schema; carries config.py + test_team_model_tiers.py)
2. **Task 2: Default roster + tier-based per-role defaults** — `25b1305` (feat: structured role defaults + per-role scope/tools/model) + `6e515a6` (feat: inject default seven-role roster + roster_defaults tests) + `cd21924` (refactor: optional role defaults via apply_role_defaults flag)
3. **Task 3: Tier resolution in _parse_model_value** — folded into `25b1305` / `e1322b9` (resolver + closed-set semantics)

## Files Created/Modified
- `voss/harness/config.py` — `get_model_tiers()` + `_DEFAULT_MODEL_TIERS` + `[model_tiers]` section parser, mirroring `get_net_rate_limits` shape.
- `voss/harness/team.py` — 14-tuple `DEFAULT_ROSTER`, `RoleDefaults` struct + `_ROLE_DEFAULTS` map, `_resolve_model_string`, tier resolution in `_parse_model_value`, `apply_role_defaults` fallback in `subagent_spec_from_role`, empty-roster injection in `compile_team`.
- `tests/voss/test_team_model_tiers.py` — tier-table defaults/override + team-level resolution + raw passthrough + diagnostics.
- `tests/voss/test_team_roster_defaults.py` — 14-role default roster + per-role default assertions.

## Decisions Made
None beyond the plan's locked design pins (tier table in config.py; raw passthrough; injection-only on empty roster/agents; apply_role_defaults back-compat flag).

## Deviations from Plan
None — plan executed as written. Task 3 resolution co-landed with Task 1/2 commits rather than a separate commit (TDD red tests authored in Task 1's file per plan).

## Issues Encountered
Prior execution session was interrupted mid-verification (classifier model temporarily unavailable). All three tasks were already implemented and committed (`e1322b9`, `25b1305`, `6e515a6`, `cd21924`); this session re-ran the verification gates and authored the missing summary.

## User Setup Required
None.

## Verification
- `pytest tests/voss/test_team_roster_defaults.py tests/voss/test_team_model_tiers.py tests/voss/test_team_compile.py` — 23 passed.
- `grep -v '^#' voss/harness/team.py | grep -Eic '"(opus|sonnet|haiku|gpt-|gemini|claude-)'` == 0 (no hardcoded model names in team.py).
- `git diff --stat voss/harness/session.py voss_runtime/budget.py` empty (record schemas untouched).

## Next Phase Readiness
Tier resolution + 14-role default roster ready for V3-02 (`team check` catalog/availability validation) and downstream reviewer A/B split work.

---
*Phase: V3-team-spec-role-cage-supersedes-o2*
*Completed: 2026-06-06*

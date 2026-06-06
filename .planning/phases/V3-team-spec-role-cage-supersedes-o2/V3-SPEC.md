# Phase V3: Team Spec + Role Cage (supersedes O2) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 6 locked (delta on shipped O2)

## Goal

Close the gap between the shipped O2 `.voss team{}` compiler and PRD TEAM-01..10: replace the default roster with the PRD's seven specialist roles, add model-tier aliases, and ship a `voss team check` CLI — while keeping the shipped compile/containment/cage path and legacy roles working, and without touching the frozen record schemas.

## Background

O2 shipped a substantial team compiler (`voss/harness/team.py`, plans O2-01/02/03 with SUMMARYs; `board/`, `em/` also exist from O3–O5):
- `compile_team(decl) -> (TeamConfig, SubagentRegistry)` — both frozen.
- `SubagentSpec` carries model/mode/scope/budget/tools/net; `gate_for_role` (min-mode, per-gate `allow_net`); `filter_toolset_for_role` (by toolset key + `net` alias).
- Compile-time **scope containment** (`TeamRoleScope.is_contained_in` vs ceiling, raises) and **budget containment** (`role budget > ceiling.budget_tokens` raises).
- **EM-invent guard** in `em/handle.py` (`role_id not in roster_ids` → denied).

So **TEAM-01..06 are shipped.** Gaps vs PRD TEAM-01..10:
- **TEAM-07** — tools filter via raw toolset keys, not a normalized capability registry (V1 not built).
- **TEAM-08** — `_parse_model_value` accepts a raw model *string* only; no `strong`/`cheap` tier aliases.
- **TEAM-09** — `DEFAULT_ROSTER = (backend, frontend, ui, ai)`; PRD wants `architect, backend, frontend, tester, reviewer, skeptic, docs`.
- **TEAM-10** — no `voss team check` CLI.

V3 supersedes O2 (ROADMAP); O2 artifacts retained as reference. **Locked direction (interview):** delta on shipped O2; replace roster with the PRD 7 (open-roster fallback kept); model-tier aliases (strong/cheap/fast → concrete model via config) with raw strings still accepted; keep toolset-key filtering, capability-registry binding deferred to V1; `voss team check [path]` defaulting to `.voss/team.voss`; legacy explorer/worker/reviewer + old roster (ui/ai) keep working; carry the schema freeze.

## Requirements

1. **Default roster → PRD 7** (VTEAM-09): the shipped default roster is replaced.
   - Current: `DEFAULT_ROSTER = (backend, frontend, ui, ai)` with per-role defaults in `default_team_role_defaults`.
   - Target: default roster = `architect, backend, frontend, tester, reviewer, skeptic, docs`, each with a default `description`, `role_prompt`, model-tier, scope, and tools; open-roster fallback retained for custom names.
   - Acceptance: a `team{}` with no explicit roles resolves to the seven roles, each with a non-empty description/prompt/model-tier/scope/tools.

2. **Model-tier aliases** (VTEAM-08): roles may declare a tier that resolves to a concrete model.
   - Current: `model:` accepts a raw model string only.
   - Target: `model:` accepts tier aliases `strong`/`cheap`/`fast` resolving to concrete models via `RuntimeConfig`/the models catalog; raw model strings still accepted; an unknown model OR unknown tier emits an actionable diagnostic.
   - Acceptance: `model: "strong"` resolves to a concrete model via config; a raw model string still compiles; an unknown model/tier raises a clear `VossTeamConfigError` naming the offending value.

3. **`voss team check` CLI** (VTEAM-10): the team file is validatable from the CLI.
   - Current: no `team` CLI command; validation only reachable via `compile_team` in code.
   - Target: `voss team check [path]` defaults to `.voss/team.voss`, runs `compile_team`, prints a PASS + roster/ceiling summary on success or the first `VossTeamConfigError` on failure.
   - Acceptance: `voss team check` on a valid team exits 0 and prints the roster + ceiling; on an invalid team exits 1 and prints the first config error; a missing file exits non-zero with a clear message.

4. **Capability-registry binding seam** (VTEAM-07): role tool filtering works now, with a documented V1 seam.
   - Current: `filter_toolset_for_role` selects by raw toolset key (+ `net` alias).
   - Target: verify role tool filtering selects exactly the declared tools today; document the integration seam where V1's capability registry replaces raw-key filtering (no behavior change in V3).
   - Acceptance: a role declaring a tool subset receives exactly those tools (net excluded unless declared); a documented seam/marker for the V1 capability-registry binding is present.

5. **Backward compatibility** (verify): legacy roles and old roster keep working.
   - Current: legacy default subagent path (explorer/worker/reviewer) + old roster names (ui/ai) are in use by existing specs/tests.
   - Target: the new roster is the default, but legacy explorer/worker/reviewer and old roster names (ui/ai) still resolve (as overlap/aliases); existing O2 specs/tests do not break.
   - Acceptance: a spec using a legacy role name still compiles to a working `SubagentSpec`; existing O2 tests pass unmodified.

6. **Shipped surface verification** (verify): TEAM-01..06 regress green; O2 superseded.
   - Current: compile_team, scope/budget containment, EM-invent guard are shipped and tested.
   - Target: verify these regress green after the roster/tier/CLI changes; mark O2 superseded (bookkeeping).
   - Acceptance: scope-widening fails at compile; over-ceiling budget fails at compile; EM dispatch to an undeclared role is denied; the existing O2 test suite is green.

## Boundaries

**In scope:**
- New 7-role default roster + per-role defaults.
- Model-tier aliases (strong/cheap/fast) + concrete-model resolution + diagnostics.
- `voss team check [path]` CLI (wraps `compile_team`).
- Verification/regression of shipped TEAM-01..06.
- Backward compat for legacy roles + old roster names.
- Mark O2 superseded (O2 artifacts retained as reference).

**Out of scope:**
- `principles{}` nested in `team{}` — the principles grammar block is V10 (V2 deferred it); team-nested principles follow.
- TEAM-07's capability-registry *form* — V1 (V3 keeps toolset-key filtering + documents the seam).
- `board{}`/`gate{}`/`ritual{}` execution semantics beyond parsing — board is V5, EM dispatch is V7.
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen (redaction invariant).
- New third-party dependencies.

## Constraints

- **Tier resolution source:** tier aliases resolve via `RuntimeConfig`/the models catalog (the `/models` picker source); roster defaults use tiers, not hardcoded model names.
- **Single validation path:** `voss team check` wraps `compile_team`; no second validator.
- **Backward compatibility:** existing team specs + legacy subagent roles keep working; existing O2 tests stay green.
- **Schema freeze (carried):** no field change on `RunRecord`/`SessionRecord`/`BudgetScope`.
- Reuse the YAML/lark/pydantic stack; no new deps.

## Acceptance Criteria

- [ ] Default roster = `architect/backend/frontend/tester/reviewer/skeptic/docs`, each with a non-empty description, role_prompt, model-tier, scope, tools.
- [ ] `model: "strong"` (or cheap/fast) resolves to a concrete model via config; a raw model string still compiles; an unknown model/tier raises a clear `VossTeamConfigError` naming the value.
- [ ] `voss team check` (default `.voss/team.voss`) exits 0 + prints roster/ceiling on a valid team; exits 1 + prints the first error on an invalid team; missing file exits non-zero with a clear message.
- [ ] A role declaring a tool subset receives exactly those tools (net excluded unless declared); a documented V1 capability-registry binding seam is present.
- [ ] A spec using a legacy role (explorer/worker/reviewer) or old roster name (ui/ai) still compiles; existing O2 tests pass unmodified.
- [ ] Scope-widening fails at compile; over-ceiling role budget fails at compile; EM dispatch to an undeclared role is denied (TEAM-04/05/06 regress green).
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                              |
|--------------------|-------|------|--------|--------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Delta = roster + tiers + CLI + capability seam, pinned             |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | TEAM-07→V1, principles-nesting→V10, board/EM→V5/V7 explicit        |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Tier source, single validator, back-compat, schema freeze          |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 7 pass/fail criteria, delta-focused                                |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                   | Decision locked                                                             |
|-------|-------------------|---------------------------------------------------|----------------------------------------------------------------------------|
| 0     | Researcher (scout)| What of TEAM-01..10 already exists?               | O2 shipped TEAM-01..06; gaps = roster/tiers/CLI/capability-binding          |
| 1     | Researcher        | V3 scope given O2 shipped?                         | Delta on shipped O2; verify 01..06, build the gaps; O2 superseded           |
| 1     | Researcher        | Roster: replace vs additive vs keep?              | Replace with PRD 7 (open-roster fallback + legacy overlap retained)         |
| 1     | Researcher        | TEAM-07 capability registry (V1 dep)?             | Keep toolset-key filtering; capability-registry binding → V1 (deferred seam)|
| 2     | Simplifier        | Model-tier aliases (TEAM-08)?                      | Add strong/cheap/fast aliases via config + keep raw; unknown → diagnostic   |
| 2     | Boundary Keeper   | Back-compat for legacy/old roster?                | Keep legacy explorer/worker/reviewer + ui/ai working                        |
| 2     | Boundary Keeper   | `voss team check` shape?                           | `check [path]` default `.voss/team.voss`; PASS+summary or first error; 0/1  |

---

*Phase: V3-team-spec-role-cage-supersedes-o2*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V3 — implementation decisions (per-role default values, tier→model table, team check output format)*

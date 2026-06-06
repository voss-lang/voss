---
phase: V3-team-spec-role-cage-supersedes-o2
plan: 03
type: execute
wave: 2
depends_on: [V3-01]
files_modified:
  - voss/harness/team.py
  - tests/voss/test_team_capability_seam.py
  - tests/voss/test_team_backcompat_regression.py
autonomous: true
requirements: [VTEAM-07, VTEAM-04, VTEAM-05, VTEAM-06]
must_haves:
  truths:
    - "A role declaring a tool subset receives exactly those tools (net excluded unless declared)."
    - "A documented V1 capability-registry binding seam/marker is present in team.py."
    - "A spec using a legacy role (explorer/worker/reviewer) or old roster name (ui/ai) still compiles."
    - "Scope-widening fails at compile; over-ceiling role budget fails at compile."
    - "EM dispatch to an undeclared role is denied."
    - "RunRecord/SessionRecord/BudgetScope have zero field changes (schema freeze)."
  artifacts:
    - path: "voss/harness/team.py"
      provides: "Documented V1 capability-registry binding seam marker on filter_toolset_for_role (behavior unchanged)"
      contains: "V1"
    - path: "tests/voss/test_team_capability_seam.py"
      provides: "Exact-subset tool filtering assertion + seam-marker presence assertion"
    - path: "tests/voss/test_team_backcompat_regression.py"
      provides: "Legacy-role + old-roster compile, scope/budget containment, EM-undeclared denial, schema-freeze guard"
  key_links:
    - from: "voss/harness/team.py::filter_toolset_for_role"
      to: "V1 capability registry (future)"
      via: "documented seam marker"
      pattern: "V1[- ]?capability"
    - from: "tests/voss/test_team_backcompat_regression.py"
      to: "voss/harness/em/handle.py EMCageViolation"
      via: "dispatch to undeclared role"
      pattern: "EMCageViolation"
---

<objective>
Document the V1 capability-registry binding seam on the (behavior-unchanged) toolset filter, and lock the shipped O2 surface with regression verification: legacy roles + old roster names still resolve, scope/budget containment still raises, EM still denies undeclared-role dispatch, and the frozen record schemas are untouched.

Purpose: Closes VTEAM-07 (seam, no behavior change) and verifies-green VTEAM-04/05/06 + back-compat after the V3-01 roster/tier delta. Marks the O2 surface regression-protected as it is superseded.
Output: A documented seam marker in team.py; two verification test files; the existing O2 suite passing unmodified.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md
@.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md

<interfaces>
<!-- The shipped surface being verified (do NOT rebuild any of it). -->

voss/harness/team.py:
- filter_toolset_for_role(spec, base_toolset) -> dict   # L128 — raw toolset-key + net alias; BEHAVIOR UNCHANGED. Add seam marker only.
- TOOL_GROUP_ALIASES                                    # L87 — fs/test/shell/net/git groups
- subagent_spec_from_role(...)                          # scope/budget containment raises VossTeamConfigError
- compile_team(decl)                                    # single validator

voss/harness/subagents.py:
- default_subagent_registry() -> SubagentRegistry       # L65 — legacy explorer/worker/reviewer (SEPARATE registry from compile_team)
- SubagentSpec(id, description, role_prompt, ...)        # frozen

voss/harness/em/handle.py:
- worker_role not in self._team_config.roster_ids -> raise EMCageViolation   # L140, L187 — the EM-invent guard
- from voss.harness.em.errors import EMCageViolation

Frozen (must NOT change — verify via git diff):
- voss/harness/session.py  RunRecord (L118), SessionRecord (L157)
- voss_runtime/budget.py   BudgetScope (L12)
</interfaces>

<read_first>
- voss/harness/team.py (L87-149 — TOOL_GROUP_ALIASES + filter_toolset_for_role)
- voss/harness/subagents.py (L65-88 — default_subagent_registry legacy roles)
- voss/harness/em/handle.py (L130-195 — EM-invent guard)
- tests/harness/test_team_tool_filter.py (existing filter tests — pattern to extend)
- tests/voss/test_team_compile.py (L110-165 — over-ceiling budget + open-roster + unknown-mode rejection patterns)
- tests/harness/em/test_em_handle_cage.py (L42-94 — test_dispatch_phantom_role: the EM undeclared-role denial pattern)
- .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md (requirements 4, 5, 6 + Acceptance Criteria)
- .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-04, D-05, D-06)
</read_first>

<design_pin>
## Capability seam (D-04 -> LOCKED, NO behavior change)
- `filter_toolset_for_role` keeps its raw toolset-key + net-alias behavior exactly. The ONLY edit to it is a documented seam: a clearly-labeled comment block above the function (and one inline at the expansion site) marking where V1's capability registry will replace raw-key filtering — e.g. `# V1-capability-seam: ...`. No logic change, no signature change.
- The seam marker must be greppable (`V1` + `capability` on one line) so the verification asserts its presence.

## reviewer reconciliation (D-05 -> LOCKED)
- Legacy `reviewer` lives in `default_subagent_registry()` (subagents.py); the new roster `reviewer` is a team-roster role produced by `compile_team`. These are SEPARATE registries built by separate functions — they do not collide at runtime. The back-compat test asserts BOTH paths still produce a working `reviewer` spec independently (legacy registry has it; a team roster declaring/defaulting reviewer has it). No code change needed for reconciliation — verify it.

## Sequencing
- This plan depends on V3-01 (which set the seven-role DEFAULT_ROSTER and tier resolution). It edits team.py AFTER V3-01 (different wave is enforced via depends_on + the team.py file-overlap). The only team.py write here is the seam comment.
</design_pin>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: V1 capability seam marker + exact-subset filter verification</name>
  <files>voss/harness/team.py, tests/voss/test_team_capability_seam.py</files>
  <read_first>
    - voss/harness/team.py (L87-149 — filter_toolset_for_role + TOOL_GROUP_ALIASES)
    - tests/harness/test_team_tool_filter.py (existing pattern; make_toolset fixture)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md (requirement 4)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-04)
    - <design_pin> capability seam
  </read_first>
  <behavior>
    - A SubagentSpec with tools=frozenset({"fs","code"}) filtered against the full toolset yields exactly the fs+code tools and no net tools (web_fetch/web_search absent).
    - A SubagentSpec with tools including "net" yields web_fetch/web_search; without it, they are excluded.
    - team.py contains a greppable V1-capability seam marker.
  </behavior>
  <action>Add a documented seam marker to voss/harness/team.py at filter_toolset_for_role (L128): a labeled comment block above the function plus one inline comment at the alias-expansion loop noting that V1's capability registry will replace raw-key filtering here (no behavior change). The marker line MUST contain both `V1` and `capability`. Do NOT alter the function's logic or signature. Author tests/voss/test_team_capability_seam.py: (1) build a SubagentSpec with a declared tool subset, run filter_toolset_for_role against make_toolset, assert the returned keys equal exactly the declared expansion and exclude net tools unless declared; (2) read voss/harness/team.py source and assert a line matches the V1-capability seam marker.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_capability_seam.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - A role declaring tools:["fs","code"] receives exactly fs+code tools (net excluded).
    - A role declaring net receives web_fetch/web_search; one not declaring net does not.
    - `grep -nE 'V1.*capabilit' voss/harness/team.py` matches at least one line (seam marker present).
    - filter_toolset_for_role behavior is unchanged: existing tests/harness/test_team_tool_filter.py still passes.
  </acceptance_criteria>
  <done>Greppable V1-capability seam documented (no behavior change); exact-subset filtering verified.</done>
</task>

<task type="auto">
  <name>Task 2: Back-compat + shipped-surface regression suite</name>
  <files>tests/voss/test_team_backcompat_regression.py</files>
  <read_first>
    - voss/harness/subagents.py (L65-88 — default_subagent_registry)
    - tests/voss/test_team_compile.py (L110-165 — over-ceiling + open-roster + unknown-mode patterns; the parse->TeamDecl->compile_team idiom)
    - tests/harness/em/test_em_handle_cage.py (L42-94 — test_dispatch_phantom_role)
    - voss/harness/em/handle.py (L130-195 — EM-invent guard)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md (requirements 5, 6 + Acceptance Criteria)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-05, D-06)
    - <design_pin> reviewer reconciliation
  </read_first>
  <action>Author tests/voss/test_team_backcompat_regression.py covering: (1) BACK-COMPAT — `default_subagent_registry()` still resolves explorer/worker/reviewer to working SubagentSpecs; a team source explicitly declaring legacy roster names `ui` and `ai` still compiles (registry.get("ui")/("ai") non-None); the legacy `reviewer` (subagents path) and a roster `reviewer` (compile_team path) both produce a working spec independently (reviewer reconciliation, D-05). (2) SCOPE CONTAINMENT — a role whose scope widens beyond the ceiling raises VossTeamConfigError at compile (TEAM-05). (3) BUDGET CONTAINMENT — a role budget exceeding the ceiling budget raises at compile (TEAM-06; mirror test_team_compile.py L110-138). (4) EM-INVENT GUARD — reuse the test_em_handle_cage.py make_handle fixture (or its construction) to assert dispatch to a role not in roster_ids raises EMCageViolation (TEAM-04). (5) SCHEMA FREEZE — assert via dataclasses.fields() that RunRecord/SessionRecord (session.py) and BudgetScope (voss_runtime/budget.py) field-name sets equal a frozen expected set captured at plan time (so any field add/remove fails the test), complementing the git-diff verification gate.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_backcompat_regression.py tests/voss/test_team_compile.py tests/harness/test_team_tool_filter.py tests/harness/test_team_gate_compile.py tests/harness/test_team_per_role_net.py tests/voss/test_team_immutability.py tests/voss/test_team_scope_invariant.py tests/parser/test_team_grammar.py tests/harness/em/test_em_handle_cage.py -q</automated>
  </verify>
  <acceptance_criteria>
    - default_subagent_registry() returns specs for explorer, worker, and reviewer.
    - A team source declaring ui/ai compiles with both roles in the registry.
    - Scope-widening beyond the ceiling raises VossTeamConfigError at compile.
    - Over-ceiling role budget raises VossTeamConfigError at compile.
    - EM dispatch to a role not in roster_ids raises EMCageViolation.
    - dataclasses.fields(RunRecord)/(SessionRecord)/(BudgetScope) name-sets equal the frozen expected sets.
    - The full existing O2 team test suite (listed in the verify command) passes unmodified.
  </acceptance_criteria>
  <done>Back-compat + TEAM-04/05/06 regression + schema-freeze locked by a passing suite; the entire O2 team test surface is green after the V3 delta.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| team file -> role tool/scope/budget cage | A role must never widen scope, exceed budget, or gain undeclared tools through the V3 delta; the cage stays fail-closed. |
| EM orchestrator -> roster | The EM must not dispatch to (invent) a role outside the declared registry. |
| V3 delta -> frozen record schemas | The roster/tier/CLI work must not perturb RunRecord/SessionRecord/BudgetScope (redaction invariant). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V3-06 | Elevation | filter_toolset_for_role | mitigate | Seam is comment-only; exact-subset test asserts no tool leakage (net excluded unless declared). |
| T-V3-07 | Elevation | scope/budget containment | mitigate | Regression test asserts widening + over-ceiling budget still raise at compile after the V3-01 delta. |
| T-V3-08 | Spoofing | EM-invent guard | mitigate | Regression test asserts dispatch to an undeclared role raises EMCageViolation. |
| T-V3-09 | Tampering | frozen record schemas | mitigate | dataclasses.fields name-set assertions + git diff gate detect any field change to RunRecord/SessionRecord/BudgetScope. |
| T-V3-SC | Tampering | npm/pip installs | n/a | No new deps. |
</threat_model>

<verification>
- The full O2 team suite in Task 2's verify command is green (unmodified).
- `grep -nE 'V1.*capabilit' voss/harness/team.py` matches (seam present).
- `git diff --stat voss/harness/session.py voss_runtime/budget.py` shows no field changes.
- Bookkeeping: O2 marked superseded (already recorded in ROADMAP/STATE; no code change — note in SUMMARY).
</verification>

<success_criteria>
- V1 capability-registry binding seam documented in team.py with no behavior change; exact-subset tool filtering verified.
- Legacy explorer/worker/reviewer + old roster ui/ai still resolve; existing O2 tests pass unmodified.
- Scope-widening, over-ceiling budget, and EM undeclared-role dispatch all fail/deny at compile/dispatch.
- RunRecord/SessionRecord/BudgetScope schemas unchanged.
</success_criteria>

<output>
Create `.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-03-SUMMARY.md` when done.
</output>

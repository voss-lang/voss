---
phase: V3-team-spec-role-cage-supersedes-o2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/team.py
  - voss/harness/config.py
  - tests/voss/test_team_roster_defaults.py
  - tests/voss/test_team_model_tiers.py
autonomous: true
requirements: [VTEAM-09, VTEAM-08]
must_haves:
  truths:
    - "A team{} with no roster block compiles to exactly the seven PRD roles."
    - "Each of the seven default roles carries a non-empty description, role_prompt, model-tier, scope, and tools."
    - "model: \"strong\" (and cheap/fast) resolves to a concrete model id via config."
    - "A raw model string (e.g. \"opus\") still compiles unchanged."
    - "An unknown tier-shaped value or an unresolvable tier raises VossTeamConfigError naming the offending value."
    - "Legacy roster names ui/ai still resolve when explicitly declared."
  artifacts:
    - path: "voss/harness/team.py"
      provides: "Seven-role DEFAULT_ROSTER, tier-aware per-role defaults struct, tier resolution in _parse_model_value, default-roster injection in compile_team"
      contains: "architect"
    - path: "voss/harness/config.py"
      provides: "get_model_tiers() reading [model_tiers] over built-in tier->id defaults"
      contains: "model_tiers"
    - path: "tests/voss/test_team_roster_defaults.py"
      provides: "Assertions on the seven-role default roster"
    - path: "tests/voss/test_team_model_tiers.py"
      provides: "Assertions on tier resolution + raw passthrough + diagnostics"
  key_links:
    - from: "voss/harness/team.py::_parse_model_value"
      to: "voss/harness/config.py::get_model_tiers"
      via: "tier alias lookup"
      pattern: "get_model_tiers"
    - from: "voss/harness/team.py::compile_team"
      to: "DEFAULT_ROSTER"
      via: "inject default roster when decl.rosters is empty"
      pattern: "DEFAULT_ROSTER"
---

<objective>
Replace the shipped four-role default roster with the PRD seven specialist roles, give each a complete tier-based default (description, role_prompt, model-tier, scope, tools), and teach the single model-parse choke point to resolve `strong`/`cheap`/`fast` tier aliases to concrete model ids via config — while raw model strings keep compiling and offline tests stay green.

Purpose: Closes VTEAM-09 (roster) and VTEAM-08 (model tiers), the two largest BUILD-delta gaps against the shipped O2 compiler. Both edit `team.py` and are coupled (roster defaults are expressed in tiers), so they ship together.
Output: Seven-role default roster auto-injected on an empty roster; tier-aware `_parse_model_value`; a config-backed tier->model table; two new test files.
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
<!-- Extracted from the live O2 surface. Use directly; no exploration needed. -->

voss/harness/team.py (the surface being extended):
- DEFAULT_ROSTER: tuple[str, ...] = ("backend", "frontend", "ui", "ai")   # L48 — REPLACE
- default_team_role_defaults(role_name: str) -> tuple[str, str]            # L51 — returns (description, role_prompt) for backend/frontend/ui/ai + opaque fallback. WIDEN.
- _parse_model_value(val: object) -> str | None                           # L304 — today: StringLit -> str only. ADD tier resolution.
- subagent_spec_from_role(...)                                            # L312 — calls default_team_role_defaults(role_name) at L354 to get (description, rp); also parses scope/budget/tools/model/mode from kvs.
- compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]     # L438 — iterates decl.agents then decl.rosters[].roles. Does NOT inject DEFAULT_ROSTER today. INJECT on empty roster.
- VossTeamConfigError(message, *, role_span=None, ceiling_span=None)      # L33
- TeamCeiling(budget_tokens, scope, latency_seconds); TeamRoleScope(globs) # frozen VOs

SubagentSpec (voss/harness/subagents.py L34, frozen):
  id, description, role_prompt, model, mode, scope, budget, tools (FrozenSet|None), net, confidence_threshold

config.py precedent (voss/harness/config.py):
- get_net_rate_limits() -> dict   # L157 — reads [net.rate_limits] section; missing file/section -> {}.  MIRROR this shape for get_model_tiers().
- load_harness_config() -> dict   # L80 — reads [harness] section.
- config_path() -> Path           # ~/.config/voss/config.toml

model_catalog (voss/harness/model_catalog.py) — for OPTIONAL existence validation only:
- load_catalog(...) -> list[ProviderGroup]   # network/cache; NOT safe to require in compile/offline tests
- ModelEntry.id  / ProviderGroup.models      # flatten groups -> entry.id to check membership
</interfaces>

<read_first>
- voss/harness/team.py (L33-80, L304-368, L438-497 — the edit sites)
- voss/harness/config.py (L80-166 — load_harness_config + get_net_rate_limits as the section-reader precedent)
- voss/harness/subagents.py (L33-45 — SubagentSpec fields)
- .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md (requirements 1, 2 + Acceptance Criteria)
- .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-01, D-02 + Claude's Discretion)
- .planning/docs/ORCHESTRATION_LAYERS.md L315-354 (§"Example Syntax" — the per-role default template)
- tests/voss/test_team_compile.py (existing assertions — note L98 and L144 use model: "opus" raw strings that MUST still compile offline; L41/L44 declare ui/ai explicitly)
</read_first>

<design_pin>
## Resolution semantics (resolve the raw-string-vs-tier tension — do NOT deviate)

The tier vocabulary is a CLOSED set: exactly `strong`, `cheap`, `fast`. Resolution in `_parse_model_value`:

1. If the string value is one of {strong, cheap, fast} -> resolve via `config.get_model_tiers()` to a concrete model id and return that id. If the table maps the tier to an empty/missing id, raise `VossTeamConfigError` naming the tier.
2. Otherwise the string is a RAW model id -> return it unchanged (this preserves the existing `model: "opus"` tests, which run offline with no catalog).

Do NOT validate raw model strings against the live catalog at compile time — that would break offline tests and contradicts "a raw model string still compiles." Catalog/availability checking is a `team check`-only concern (Plan 02), not a compile-time gate.

"Unknown tier" diagnostic: because the tier set is closed, an "unknown tier" only arises when the tier table itself is misconfigured (tier present in the closed set but mapped to nothing). A user typo like `model: "strog"` is treated as a raw model id and passes (consistent with raw passthrough). This is the locked interpretation; document it in the resolver docstring.

## Tier->model table location (D-02, Claude's discretion -> LOCKED here)

Lives in `voss/harness/config.py` as `get_model_tiers() -> dict[str, str]` reading a `[model_tiers]` TOML section over a built-in default map. The built-in default map (the only place model NAME strings live) sits in config.py, NOT team.py — team.py references only the three tier keywords and calls the resolver. Built-in defaults must be sensible ids that exist in the bundled catalog target providers; pick concrete ids by inspecting model_catalog TARGET_PROVIDERS (e.g. a strong/cheap/fast triple). team.py imports `get_model_tiers` lazily inside `_parse_model_value` to avoid import cycles.
</design_pin>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Config-backed tier->model table</name>
  <files>voss/harness/config.py, tests/voss/test_team_model_tiers.py</files>
  <read_first>
    - voss/harness/config.py (L80-166 — load_harness_config + get_net_rate_limits section-reader precedent)
    - voss/harness/model_catalog.py (L43 TARGET_PROVIDERS, L58-72 ModelEntry — to choose sensible default ids)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-02)
  </read_first>
  <behavior>
    - get_model_tiers() with no config file returns the built-in default map: keys exactly {"strong","cheap","fast"}, each mapped to a non-empty concrete model id.
    - A config.toml with a [model_tiers] section overrides built-in entries by tier key (shallow merge over defaults).
    - Resolution helper resolve_tier("strong") returns the mapped id; resolve_tier on a non-tier string is not this function's job (team.py owns the closed-set check) — keep get_model_tiers a plain dict accessor mirroring get_net_rate_limits.
  </behavior>
  <action>Add `get_model_tiers() -> dict[str, str]` to voss/harness/config.py, mirroring `get_net_rate_limits` (L157): read `config_path()`, parse the `[model_tiers]` TOML section, shallow-merge over a module-level `_DEFAULT_MODEL_TIERS` dict keyed by the three tier words. `_DEFAULT_MODEL_TIERS` is the ONLY place concrete model NAME strings appear — choose ids that are valid for model_catalog TARGET_PROVIDERS. Missing file/section -> the built-in defaults. This keeps team.py free of hardcoded model names per D-02. Author tests/voss/test_team_model_tiers.py with the tier-table cases (built-in defaults present; [model_tiers] override applied) plus the team-level tier-resolution cases from Task 3 (write the team-level RED tests here too so the file is the single home for tier behavior; they fail until Task 3).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_model_tiers.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `get_model_tiers()` returns a dict whose keys are exactly {"strong","cheap","fast"}, each value a non-empty string, with no config file present.
    - A `[model_tiers]` section in a temp config.toml overrides the matching tier key.
    - No concrete model NAME string appears anywhere in voss/harness/team.py (`grep -v '^#' voss/harness/team.py | grep -Eic '"(opus|sonnet|haiku|gpt-|gemini|claude-)' == 0`).
  </acceptance_criteria>
  <done>get_model_tiers exists with config override + built-in defaults; team.py carries no hardcoded model names; tier-table tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Seven-role roster + tier-based per-role defaults</name>
  <files>voss/harness/team.py, tests/voss/test_team_roster_defaults.py</files>
  <read_first>
    - voss/harness/team.py (L48 DEFAULT_ROSTER, L51-80 default_team_role_defaults, L312-368 subagent_spec_from_role, L438-497 compile_team)
    - .planning/docs/ORCHESTRATION_LAYERS.md L315-354 (§"Example Syntax" template: architect=strong/plan/[src,docs]/[fs,code,git]/12k; backend=cheap/edit/[src/server,tests/server]/[fs,code,test,git]/24k; reviewer=strong/plan/[src,tests]/[fs,code,test,git]/16k)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-CONTEXT.md (D-01, D-05 ui/ai back-compat note, Claude's Discretion on tester/skeptic/frontend/docs)
  </read_first>
  <behavior>
    - DEFAULT_ROSTER == ("architect","backend","frontend","tester","reviewer","skeptic","docs").
    - For each of the seven, the widened default provides a non-empty description, role_prompt, model-tier (one of strong/cheap/fast), scope (>=1 glob), and tools (>=1 entry).
    - compile_team on a TeamDecl with NO roster block and NO agents injects the seven default roles into the registry; config.roster_ids == the seven.
    - compile_team on a TeamDecl that declares roles (including legacy ui/ai) is UNCHANGED — declared roles win, no injection.
    - default_team_role_defaults still returns working values for legacy ui/ai and for unknown custom names (opaque fallback retained).
  </behavior>
  <action>In voss/harness/team.py: (1) Replace `DEFAULT_ROSTER` (L48) with the seven-tuple. (2) Widen the per-role defaults: introduce a frozen per-role defaults struct/map (e.g. a `RoleDefaults` dataclass or a frozen dict of dataclasses) carrying description, role_prompt, model_tier (a tier keyword string), scope (tuple of globs), tools (tuple of toolset keys). Keep `default_team_role_defaults(role_name)` as the accessor — widen its return or add a sibling accessor that returns the full struct; preserve a `(description, role_prompt)` shape for the legacy ui/ai callers and the opaque fallback (D-05). Populate all seven per the §"Example Syntax" template for architect/backend/reviewer and author tester/skeptic/frontend/docs in the same spirit (tester=cheap/test-focused; skeptic=strong/plan/critique; frontend=cheap/edit/client scope; docs=cheap/edit/docs scope). (3) In `compile_team` (L438), after iterating decl.agents and decl.rosters, if NO roster roles AND no agents were registered, inject each name in DEFAULT_ROSTER via the same `subagent_spec_from_role` path with empty kvs so the per-role defaults (tier/scope/tools/desc/prompt) flow through; add each to roster_id_set. Wire `subagent_spec_from_role` so that when a role's kvs omit model/scope/tools, it falls back to the per-role default tier/scope/tools (not just description/prompt). Author tests/voss/test_team_roster_defaults.py.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_roster_defaults.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - A `team{}` parsed from a minimal source with a ceiling and NO roster block compiles so that `config.roster_ids == frozenset({"architect","backend","frontend","tester","reviewer","skeptic","docs"})`.
    - For every one of the seven, `registry.get(name)` has non-empty description, role_prompt, a model resolving from a tier, a non-empty scope, and non-empty tools.
    - `grep -c architect voss/harness/team.py` >= 1 and DEFAULT_ROSTER contains all seven (assert in test against the tuple).
    - A source explicitly declaring `ui`/`ai` roles still compiles (registry.get("ui") and registry.get("ai") non-None) — legacy roster back-compat.
  </acceptance_criteria>
  <done>Seven-role roster injected on empty rosters with full tier-based defaults; legacy ui/ai still resolve; roster-defaults tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Tier resolution in _parse_model_value</name>
  <files>voss/harness/team.py</files>
  <read_first>
    - voss/harness/team.py (L304-309 _parse_model_value, L33-46 VossTeamConfigError)
    - voss/harness/config.py (the get_model_tiers added in Task 1)
    - tests/voss/test_team_compile.py (L98, L144 — model: "opus" raw strings that MUST still compile offline)
    - .planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-SPEC.md (requirement 2 + Acceptance Criteria), V3-CONTEXT.md (D-02)
    - <design_pin> above — the closed-set resolution semantics
  </read_first>
  <behavior>
    - _parse_model_value(StringLit("strong")) -> the concrete id from get_model_tiers()["strong"].
    - _parse_model_value(StringLit("cheap")) and ("fast") resolve likewise.
    - _parse_model_value(StringLit("opus")) -> "opus" unchanged (raw passthrough; no catalog call).
    - A tier word mapped to an empty/missing id in the table -> VossTeamConfigError naming the tier.
    - Non-StringLit -> existing TypeError-style VossTeamConfigError unchanged.
  </behavior>
  <action>Extend `_parse_model_value` (team.py L304): keep the None and non-StringLit branches. For a StringLit, lazily `from .config import get_model_tiers` inside the function (avoid import cycle), check membership in the CLOSED tier set {"strong","cheap","fast"}; if a tier, look it up in `get_model_tiers()` and return the mapped id, raising `VossTeamConfigError(f"model tier {tier!r} is not configured")` when the mapped id is empty/missing; otherwise return the raw string unchanged. Document the closed-set / raw-passthrough rule from <design_pin> in the docstring. The team-level RED tests for this live in tests/voss/test_team_model_tiers.py (authored in Task 1) — they go GREEN here.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_model_tiers.py tests/voss/test_team_compile.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - A role declaring `model: "strong"` compiles and its SubagentSpec.model equals `get_model_tiers()["strong"]`.
    - A role declaring `model: "opus"` compiles with SubagentSpec.model == "opus" (raw passthrough; offline).
    - A misconfigured tier table (tier mapped to "") raises VossTeamConfigError whose message contains the tier name.
    - The existing tests/voss/test_team_compile.py suite (which uses raw `model: "opus"`) still passes unmodified.
  </acceptance_criteria>
  <done>Tier aliases resolve via config; raw strings pass through offline; misconfigured tiers raise a naming diagnostic; existing compile tests stay green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.voss` team file -> compiler | Untrusted declarative input parsed into a frozen cage; a widened scope/budget/model must fail closed. |
| config.toml [model_tiers] -> resolver | Local user config maps tier aliases to model ids; a missing/empty mapping must be a clear diagnostic, not a silent wrong model. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V3-01 | Tampering | _parse_model_value tier resolution | mitigate | Closed tier set; tier->id only via get_model_tiers; empty mapping raises VossTeamConfigError (no silent fallback to a default model). |
| T-V3-02 | Elevation | compile_team default-roster injection | mitigate | Injected roles flow through subagent_spec_from_role, so scope/budget containment still applies; injection only when roster + agents are both empty (no override of declared cage). |
| T-V3-03 | Information disclosure | hardcoded model names | accept->mitigate | Built-in tier defaults live in config.py only; grep gate asserts zero model names in team.py. |
| T-V3-SC | Tampering | npm/pip installs | n/a | No new third-party deps in this plan (reuse pyyaml/tomllib/pydantic already present). |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/voss/test_team_roster_defaults.py tests/voss/test_team_model_tiers.py tests/voss/test_team_compile.py -q` all green.
- `grep -v '^#' voss/harness/team.py | grep -Eic '"(opus|sonnet|haiku|gpt-|gemini|claude-)'` == 0 (no hardcoded model names in team.py).
- `git diff --stat voss/harness/session.py voss_runtime/budget.py` shows no changes (schema freeze; this plan must not touch them).
</verification>

<success_criteria>
- DEFAULT_ROSTER is the PRD seven; an empty-roster team{} compiles to all seven with full tier-based defaults.
- Tier aliases resolve to concrete ids via config; raw model strings still compile offline; misconfigured/empty tier raises a naming VossTeamConfigError.
- Legacy ui/ai roster names still resolve when declared.
- No new deps; no hardcoded model names in team.py; record schemas untouched.
</success_criteria>

<output>
Create `.planning/phases/V3-team-spec-role-cage-supersedes-o2/V3-01-SUMMARY.md` when done.
</output>

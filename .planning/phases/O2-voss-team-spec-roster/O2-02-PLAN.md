---
phase: O2-voss-team-spec-roster
plan: 02
type: execute
wave: 2
depends_on: [O2-01]
files_modified:
  - voss/harness/subagents.py
  - voss/harness/team.py
  - tests/harness/test_subagent_spec_extensions.py    # NEW
  - tests/voss/__init__.py                             # NEW (package marker, if needed)
  - tests/voss/test_team_compile.py                    # NEW
  - tests/voss/test_team_scope_invariant.py            # NEW
  - tests/voss/test_team_immutability.py               # NEW
autonomous: true
requirements: [OTEAM-02, OTEAM-03, OTEAM-05, OTEAM-06]
tech_stack: [python-3.11, dataclasses-frozen, hypothesis-optional, pytest]
key_files:
  created:
    - tests/harness/test_subagent_spec_extensions.py
    - tests/voss/test_team_compile.py
    - tests/voss/test_team_scope_invariant.py
    - tests/voss/test_team_immutability.py
  modified:
    - voss/harness/subagents.py
    - voss/harness/team.py
estimated_duration: ~3-4 hours implementation; ~40% planner-context budget
requirements_addressed: [OTEAM-02, OTEAM-03, OTEAM-05, OTEAM-06]

must_haves:
  truths:
    - "`SubagentSpec` accepts five new optional fields (`model`, `mode`, `scope`, `budget`, `tools`) plus a `net: bool = False` default; legacy three-arg construction (`SubagentSpec(id, description, role_prompt)`) still works."
    - "`default_subagent_registry()` still returns exactly the three legacy specs (`explorer`, `worker`, `reviewer`) — no field expansion forced on existing readers."
    - "`compile_team(decl: TeamDecl) -> TeamConfig` produces a fully-populated, frozen `TeamConfig` from the strawman fixture; the registry it returns refuses an unknown agent id with the existing `<error: unknown subagent {id!r}>` envelope (OTEAM-06)."
    - "A role whose `scope` glob is NOT contained in `ceiling.scope` causes `compile_team` to raise `VossTeamConfigError`, citing both globs and both spans."
    - "A role with no declared `scope` inherits `ceiling.scope` (default-deny against ceiling, never widening)."
    - "Default roster names `backend`, `frontend`, `ui`, `ai` compile as roles; AI role's compiled spec has `net=True` IFF its declared `tools` contains the string `\"net\"`."
    - "Existing call sites in `voss/harness/cli.py:1362, 1659, 2540` (and the standalone subagent CLI at `cli.py:2640+`) continue to work unchanged — no positional-arg breakage."
  artifacts:
    - path: "voss/harness/subagents.py"
      provides: "Extended SubagentSpec with five Optional fields + net bool"
      contains: "model: Optional[str] = None"
    - path: "voss/harness/team.py"
      provides: "compile_team, subagent_spec_from_role, TeamRoleScope.is_contained_in, scope-containment validator, optional TeamRunContext"
      contains: "def compile_team"
    - path: "tests/voss/test_team_compile.py"
      provides: "OTEAM-02 + OTEAM-03 + OTEAM-06 acceptance"
      contains: "def test_strawman_compiles_to_expected_registry"
    - path: "tests/voss/test_team_scope_invariant.py"
      provides: "OTEAM-05 acceptance + property test for union ⊆ ceiling"
      contains: "def test_role_scope_outside_rejects"
    - path: "tests/voss/test_team_immutability.py"
      provides: "OTEAM-04 structural-cage regression gate (complementing O2-01 unit tests)"
      contains: "def test_compile_returns_frozen_config"
    - path: "tests/harness/test_subagent_spec_extensions.py"
      provides: "OTEAM-02 back-compat gate"
      contains: "def test_default_registry_unchanged"
  key_links:
    - from: "voss/harness/team.py::compile_team"
      to: "voss/harness/subagents.py::SubagentSpec"
      via: "constructor with optional fields"
      pattern: "SubagentSpec\\("
    - from: "voss/harness/team.py::compile_team"
      to: "voss/harness/subagents.py::SubagentRegistry"
      via: "registry.register(spec)"
      pattern: "registry\\.register\\("
    - from: "voss/harness/team.py::subagent_spec_from_role"
      to: "voss/harness/team.py::TeamRoleScope.is_contained_in"
      via: "scope-containment guard"
      pattern: "is_contained_in"
---

<objective>
Compile the `TeamDecl` AST (built in O2-01) into a runtime `TeamConfig` + enriched `SubagentRegistry`. This is the **semantic compile step** of the cage: takes parsed syntax, returns frozen runtime value-objects + a registry the EM can dispatch against.

**Purpose:**
- OTEAM-02 — `SubagentSpec` carries per-role `model`/`mode`/`scope`/`budget`/`tools` (without breaking the 5+ existing call sites in `cli.py`/`multiagent.py`).
- OTEAM-03 — declared `backend`/`frontend`/`ui`/`ai` roles compile into a populated registry; AI role gets `net`, others don't (default-deny).
- OTEAM-05 — `role.scope ⊆ ceiling.scope` is verified **at compile time**, with a clear error pointing to both source spans.
- OTEAM-06 — the compiled registry preserves the existing "EM cannot invent agents" enforcement (already structural at `subagents.py:96-98`; verify via test).

**Output:** `voss/harness/team.py::compile_team(decl) → (TeamConfig, SubagentRegistry)`, plus four new test files covering compile / scope-invariant / immutability / back-compat. ~25 tests total.

**Scope fence:** This plan compiles config to data. It does NOT construct per-role `PermissionGate`s (that's O2-03). It does NOT wire `compile_team` into `voss do`/`voss chat` (that's O5). The compiled `TeamConfig` is held in memory and asserted by tests only.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/ORCHESTRATION-PLAN.md
@.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md
@.planning/phases/O2-voss-team-spec-roster/O2-RESEARCH.md
@.planning/phases/O2-voss-team-spec-roster/O2-01-SUMMARY.md
@voss/harness/subagents.py
@voss/harness/team.py
@voss/ast_nodes.py
@voss/harness/permissions.py
@tests/parser/examples/team_strawman.voss

<interfaces>
<!-- Contracts produced by O2-01; consumed by this plan. -->
<!-- Do not re-derive — use directly. -->

AST nodes from O2-01 (`voss/ast_nodes.py`):
```python
@dataclass(frozen=True, slots=True)
class TeamDecl(Decl):
    name: str
    ceiling: CeilingDecl | None
    policy: object | None
    agents: tuple[TeamAgentDecl, ...]
    rosters: tuple[RosterDecl, ...]
    board: BoardDecl | None
    rituals: tuple[RitualDecl, ...]
    decorators: tuple[Decorator, ...] = ()

@dataclass(frozen=True, slots=True)
class CeilingDecl(Decl):
    budget: int | None
    scope: tuple[str, ...]
    latency_seconds: int | None

@dataclass(frozen=True, slots=True)
class TeamAgentDecl(Decl):
    name: str
    options: tuple[tuple[str, object], ...]

@dataclass(frozen=True, slots=True)
class RosterRoleDecl(Decl):
    name: str
    options: tuple[tuple[str, object], ...]

@dataclass(frozen=True, slots=True)
class RosterDecl(Decl):
    name: str
    roles: tuple[RosterRoleDecl, ...]
```

Value-object shells from O2-01 (`voss/harness/team.py`):
```python
@dataclass(frozen=True, slots=True)
class TeamRoleScope:
    globs: tuple[str, ...]
    def is_contained_in(self, other: "TeamRoleScope | None") -> bool: ...  # NotImplementedError

@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None
    scope: TeamRoleScope | None
    latency_seconds: int | None

@dataclass(frozen=True, slots=True)
class TeamPolicy:
    p: object | None

@dataclass(frozen=True, slots=True)
class TeamConfig:
    name: str
    ceiling: TeamCeiling
    policy: TeamPolicy
    em_agent_id: str | None
    roster_ids: frozenset[str]
    board: BoardSpec | None
    rituals: tuple[RitualSpec, ...]

class VossTeamConfigError(Exception):
    ...
```

Existing SubagentSpec (`voss/harness/subagents.py:28-32`) to extend:
```python
@dataclass(frozen=True)
class SubagentSpec:
    id: str
    description: str
    role_prompt: str
```

Existing dispatch refusal (`voss/harness/subagents.py:96-98`):
```python
spec = registry.get(agent_id)
if spec is None:
    return f"<error: unknown subagent {agent_id!r}>"
```

Existing default registry (`voss/harness/subagents.py:52-75`) — back-compat anchor.
</interfaces>
</context>

<open-question id="OQ-02-A" requirement="OTEAM-03">
**Resolve before Task 2.** Roster open vs closed (Research Open Q #1; A1):
- (a) **Closed:** roster role names MUST be one of `backend`/`frontend`/`ui`/`ai`; any other IDENT raises `VossTeamConfigError`.
- (b) **Open with four defaults:** any IDENT is accepted; the four are special only because `default_team_role_defaults()` provides built-in description+role_prompt strings for them.

**Recommendation:** (b). ORCHESTRATION-PLAN.md §2 calls the roster "extensible"; §5 strawman shows the four. Closed forces a grammar redesign if the user adds a fifth role later.

If unresolved at exec time: surface as `checkpoint:decision`. Implementation impact is small (a one-line `if role_name not in DEFAULT_ROSTER: raise …` toggle).
</open-question>

<open-question id="OQ-02-B" requirement="OTEAM-02">
**Resolve before Task 2.** `budget` per role semantics (Research Open Q #3; A3):
- (a) **Per-role cap** — a max-spend limit; compile-time validated to `≤ ceiling.budget_tokens`.
- (b) **Per-card allocation policy** — O3's domain; OUT OF SCOPE here.

**Recommendation (consistent with O1-SPEC.md line 60 "Budget allocation policy … O3 owns"):** (a). The role's `budget` is a cap; O3 picks per-card allocations bounded by it. Compile-time check `role.budget ≤ ceiling.budget_tokens`.

If unresolved at exec time: surface as `checkpoint:decision`. Fallback is "store opaquely; O3 validates" — but that delays a compile-time cage check.
</open-question>

<open-question id="OQ-02-C" requirement="OTEAM-05">
**Resolve before Task 3.** Glob containment algorithm (Research Risk R2; A7):

Implementation choices for `TeamRoleScope.is_contained_in(other)`:
- (a) **Prefix-up-to-first-wildcard:** `"src/api/**"` is contained in `"src/**"` because `"src/api"` starts with `"src"`. Cheap, handles 90% of declared cases; gets fancy globs (e.g. `src/**/api/**` vs `src/**`) wrong.
- (b) **`fnmatch.fnmatch` on the role glob, with ceiling glob expanded:** doesn't handle `**` well.
- (c) **`pathlib.PurePath.match` per-component:** Python 3.13+ has improved `match` but doesn't model `**` (recursive) by default. Inconsistent across versions.

**Recommendation:** (a) with documented limitation + explicit testset. The heuristic is "split each glob at the first `*`, then `role.prefix` must start with `ceiling.prefix`". Covers the four declared roster scopes (`src/api/**`, `src/web/**`, `src/ui/**`, `src/ml/**`) against `src/**`. Document the limitation in a docstring and flag a follow-up if abuse patterns emerge in O3.

If a pathological case arises at exec time (e.g. user declares `scope: "**/test/**"`), surface as a `checkpoint:decision` and consider escalating to `pathspec` library (requires new dependency — RESEARCH did not flag pathspec; would need a package-legitimacy gate).
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend SubagentSpec with five Optional fields + net bool</name>
  <files>voss/harness/subagents.py, tests/harness/test_subagent_spec_extensions.py</files>
  <behavior>
    - `SubagentSpec(id="x", description="d", role_prompt="rp")` still works — three positional args, all new fields default.
    - `SubagentSpec(id="x", description="d", role_prompt="rp", model="opus", mode="auto", scope=TeamRoleScope(("src/**",)), budget=1000, tools=frozenset({"fs","test"}), net=False)` constructs successfully.
    - `default_subagent_registry()` returns three specs whose new fields are all `None`/`False` (no leak of team-config into the legacy path).
    - `agent_task(spec, "do X")` (`subagents.py:78`) reads `spec.role_prompt` regardless of the new fields — extension does not break the task-building path.
    - `run_subagent(agent_id="ghost", …)` returns `"<error: unknown subagent 'ghost'>"` exactly — OTEAM-06 baseline (this is already the case today; we add a regression test).
    - `Mode` literal from `voss/harness/permissions.py:42` is the type used for `SubagentSpec.mode`.
  </behavior>
  <action>
    1. **Edit `voss/harness/subagents.py`:**
       - Add imports at the top: `from typing import Optional, FrozenSet`. Import `Mode` from `.permissions`. Import `TeamRoleScope` from `.team` (this is a one-way import; `voss.harness.team` imports `SubagentSpec` from `.subagents` — so the `TeamRoleScope` import in subagents.py creates a soft cycle if not deferred). **Use `TYPE_CHECKING` + string-typed field** to break the cycle: `if TYPE_CHECKING: from .team import TeamRoleScope` and annotate `scope: "TeamRoleScope | None" = None`.
       - Extend the `SubagentSpec` dataclass (line 28-32) — keep `frozen=True`:
         ```
         @dataclass(frozen=True)
         class SubagentSpec:
             id: str
             description: str
             role_prompt: str
             # --- O2 additions; all Optional/default for back-compat ---
             model: Optional[str] = None
             mode: Optional[Mode] = None
             scope: "TeamRoleScope | None" = None
             budget: Optional[int] = None
             tools: Optional[FrozenSet[str]] = None
             net: bool = False
         ```
       - DO NOT alter `SubagentRegistry`, `default_subagent_registry`, `agent_task`, `run_subagent`, or `attach_subagent_tool`. The shape stays the same; the dataclass just carries more data when populated by `compile_team` (Task 2).

    2. **Create `tests/harness/test_subagent_spec_extensions.py`:**
       - `test_legacy_spec_three_args_unchanged` — `SubagentSpec("x","d","rp")` constructs; assert `s.model is None and s.mode is None and s.scope is None and s.budget is None and s.tools is None and s.net is False`.
       - `test_full_spec_with_new_fields` — construct with all new fields, assert each set correctly.
       - `test_default_registry_unchanged` — `default_subagent_registry().ids() == ["explorer", "reviewer", "worker"]` (sorted). For each spec, all new fields are default.
       - `test_agent_task_reads_role_prompt_only` — Mock test: `agent_task(SubagentSpec("x","d","RP",model="opus"), "task")` returns a turn whose system text contains `"RP"` and does NOT propagate `model="opus"` into the system prompt (model field is metadata; task wiring is O5).
       - `test_dispatch_refuses_unknown_id_regression` (OTEAM-06 baseline) — using a minimal `SubagentRegistry()` (no entries registered), assert that `registry.get("ghost") is None` and `f"<error: unknown subagent {'ghost'!r}>"` matches `"<error: unknown subagent 'ghost'>"`. (This tests the *envelope contract*; the full async `run_subagent` path is exercised in O2-03 Task 3.)
       - `test_spec_is_still_frozen` — `s.model = "x"` raises `FrozenInstanceError`.

    3. **Verify no positional-arg break:** grep the repo for any `SubagentSpec(` constructor with > 3 positional args. Research §1.2 confirms there are none today; this verification gates against future regression.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.subagents import SubagentSpec; s = SubagentSpec('x','d','rp'); assert s.model is None and s.net is False; print('legacy OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.subagents import SubagentSpec; from voss.harness.team import TeamRoleScope; s = SubagentSpec('x','d','rp', model='opus', mode='auto', scope=TeamRoleScope(('src/**',)), budget=1000, tools=frozenset({'fs','test'}), net=True); assert s.tools == frozenset({'fs','test'}); print('extended OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -nE 'SubagentSpec\(' voss/ --include='*.py' -r | grep -v 'def __\|class SubagentSpec\|SubagentSpec\s*$' | awk -F'SubagentSpec\\(' '{ rest = $2; n = gsub(/,/, ",", rest); if (n >= 3) print "POSITIONAL-ARG CALLSITE:", $0 }' | wc -l | awk '$1 > 0 {print "WARNING: callsites with 3+ positional args found"; exit 0} {print "no positional-arg risk"}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_subagent_spec_extensions.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/test_subagent_recursion.py -x -q</automated>
  </verify>
  <done>
    - `SubagentSpec` has six new defaulted fields; existing construction sites unchanged.
    - `tests/harness/test_subagent_spec_extensions.py` has ≥ 6 tests, all pass.
    - `default_subagent_registry` produces `explorer`/`worker`/`reviewer` with default new fields.
    - Existing `test_subagent_recursion.py` passes (regression gate).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement compile_team + subagent_spec_from_role + scope containment</name>
  <files>voss/harness/team.py, tests/voss/test_team_compile.py, tests/voss/__init__.py</files>
  <behavior>
    - `compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]` exists; given the strawman `TeamDecl` from O2-01, returns:
      - `TeamConfig(name="Engineering", ceiling=TeamCeiling(budget_tokens=200_000, scope=TeamRoleScope(("src/**",)), latency_seconds=1800), policy=TeamPolicy(p="risk_tiered"), em_agent_id="em", roster_ids=frozenset({"em","backend","frontend","ui","ai"}), board=BoardSpec(...), rituals=(RitualSpec(name="ContextDigest", ...),))`
      - A `SubagentRegistry` whose `ids()` are `["ai","backend","em","frontend","ui"]` (sorted).
    - The compiled registry refuses unknown ids: `registry.get("freelancer") is None`; same envelope on dispatch path (OTEAM-06).
    - `subagent_spec_from_role(role_name, kvs_dict, ceiling)` produces a `SubagentSpec` with: `id=role_name`, description+role_prompt sourced from `default_team_role_defaults(role_name)` (a new helper) **or** opaque defaults if role_name is custom (Open Q OQ-02-A resolution: open roster with four defaults).
    - AI role: `kvs["tools"]` contains `"net"` → resulting spec has `net=True` and `tools=frozenset({"fs","test","net"})`. Non-AI roles: `tools` doesn't contain `"net"` → `net=False`.
    - The EM agent (a `TeamAgentDecl`) compiles via `subagent_spec_from_agent(agent_decl, ceiling)` — a parallel helper. EM `id` = `agent_decl.name`. EM defaults: description "Engineering Manager (orchestrator)", role_prompt loaded from a constant `EM_ROLE_PROMPT` in `team.py` (placeholder text; O5 owns the real prompt).
    - Per OQ-02-B: per-role `budget` (if declared) MUST satisfy `role.budget ≤ ceiling.budget_tokens`; violation raises `VossTeamConfigError` mentioning both numbers.
    - Per OQ-02-A: roster role names outside `DEFAULT_ROSTER = ("backend","frontend","ui","ai")` are accepted but use a fallback description+role_prompt (open roster).
  </behavior>
  <action>
    1. **Create `tests/voss/__init__.py`** (empty file; package marker for pytest discovery).

    2. **Edit `voss/harness/team.py`:**

       a. Add imports: `from typing import Optional, Mapping, Sequence`; import `SubagentSpec, SubagentRegistry` from `.subagents`; import AST types from `..ast_nodes` (`TeamDecl, CeilingDecl, TeamAgentDecl, RosterDecl, RosterRoleDecl, BoardDecl, RitualDecl`).

       b. Implement `TeamRoleScope.is_contained_in(self, other)` per OQ-02-C recommendation:
          ```
          def is_contained_in(self, other: "TeamRoleScope | None") -> bool:
              if other is None:
                  return True  # no ceiling scope = unconstrained
              # Prefix-up-to-first-wildcard heuristic. Document limitations.
              def _prefix(g: str) -> str:
                  for sep in ("*", "?", "["):
                      idx = g.find(sep)
                      if idx >= 0:
                          return g[:idx].rstrip("/")
                  return g.rstrip("/")
              for self_g in self.globs:
                  self_p = _prefix(self_g)
                  if not any(self_p.startswith(_prefix(o)) for o in other.globs):
                      return False
              return True
          ```

       c. Add `DEFAULT_ROSTER: tuple[str, ...] = ("backend", "frontend", "ui", "ai")`.

       d. Add `default_team_role_defaults(role_name: str) -> tuple[str, str]` returning `(description, role_prompt)` for the four built-in roles; returns generic-fallback strings for unknown role names (open roster). Description+prompt content is a placeholder — O5 will refine. Document this with `# Placeholder defaults; full role prompts owned by O5 (EM loop).`

       e. Add `EM_ROLE_PROMPT: str = "<EM role prompt — populated in O5>"` and `EM_DESCRIPTION: str = "Engineering Manager (orchestrator)"`.

       f. Implement `subagent_spec_from_role(role_name: str, kvs: Mapping[str, object], ceiling: TeamCeiling) -> SubagentSpec`:
          - Parse `kvs.get("scope")` → `TeamRoleScope | None`. Accept both string and list-of-strings (per O2-01 OQ-01-A resolution; mirror that grammar choice).
          - If parsed scope is not None and `ceiling.scope` is not None: `if not parsed_scope.is_contained_in(ceiling.scope): raise VossTeamConfigError(...)` with both glob lists in the message.
          - Default scope to `ceiling.scope` if role omits `scope`.
          - Parse `kvs.get("budget")` → int; if set and `ceiling.budget_tokens` is not None: `if budget > ceiling.budget_tokens: raise VossTeamConfigError(...)`.
          - Parse `kvs.get("tools")` → `frozenset[str]`. Determine `net = ("net" in tools)`. Accept tools value as list or single string.
          - Parse `kvs.get("model")` → `str | None`. Parse `kvs.get("mode")` → `str | None`; validate `mode in {"plan","edit","auto",None}` else `VossTeamConfigError(... "unknown mode 'X' (expected: plan, edit, auto)")`.
          - `description, prompt = default_team_role_defaults(role_name)`.
          - Return `SubagentSpec(id=role_name, description=description, role_prompt=prompt, model=model, mode=mode, scope=scope, budget=budget, tools=tools or None, net=net)`.

       g. Implement `subagent_spec_from_agent(agent_decl: TeamAgentDecl, ceiling: TeamCeiling) -> SubagentSpec`:
          - Similar shape; uses `EM_ROLE_PROMPT`/`EM_DESCRIPTION` for default description+role_prompt.
          - **The EM's `scope` MAY equal `ceiling.scope` (unlike specialist roles which tighten).** Decision #19 (tightens scope) is a specialist-role property. Document this in the function docstring.

       h. Implement `compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]`:
          - Build `TeamCeiling` from `decl.ceiling` (require `decl.ceiling is not None`, else raise `VossTeamConfigError("team {name!r} missing ceiling at compile")`. (Note: O2-01's transformer already enforces presence — this is defense-in-depth.)
          - Build `TeamPolicy(p=decl.policy)` — the `policy` field is an opaque `expr`, the EM cannot mutate it once compiled (it lives inside frozen `TeamConfig`).
          - Walk `decl.agents` → compile each via `subagent_spec_from_agent` → register; capture the first agent's name as `em_agent_id` (strawman declares only one `agent em`).
          - Walk `decl.rosters` → for each `RosterDecl`, walk `.roles` → compile each via `subagent_spec_from_role` → register.
          - Build `BoardSpec(raw_items=tuple(decl.board.items)) if decl.board else None`.
          - Build `RitualSpec(name=r.name, raw_kvs=r.kvs) for r in decl.rituals`.
          - Return `(TeamConfig(...), registry)`.

       i. (Optional) Add `@dataclass(frozen=True, slots=True) class TeamRunContext` holding `(team_config: TeamConfig, registry: SubagentRegistry, base_gate: PermissionGate)` — Research §6.5 recommends this as the O2→O3 hand-off shape. Add only the dataclass; do NOT construct a default instance.

    3. **Create `tests/voss/test_team_compile.py`** — test against the strawman fixture committed in O2-01:

       a. `test_strawman_compiles_to_expected_registry` — load `tests/parser/examples/team_strawman.voss`, `parse()` it, locate the `TeamDecl`, call `compile_team(td)`, assert:
          - `config.name == "Engineering"`
          - `config.ceiling.budget_tokens == 200_000`
          - `config.ceiling.scope.globs == ("src/**",)`
          - `config.ceiling.latency_seconds == 1800`
          - `config.policy.p == "risk_tiered"` (literal expr value or its repr — assertion form depends on how O2-01 represented the policy expr; the SUMMARY will record)
          - `config.em_agent_id == "em"`
          - `config.roster_ids == frozenset({"em","backend","frontend","ui","ai"})`
          - `config.board is not None and len(config.board.raw_items) > 0`
          - `len(config.rituals) == 1 and config.rituals[0].name == "ContextDigest"`
          - `registry.ids() == sorted(["em","backend","frontend","ui","ai"])`

       b. `test_ai_role_gets_net` — assert `registry.get("ai").net is True` and `"net" in registry.get("ai").tools`.

       c. `test_engineer_roles_do_not_get_net` — for role in `("backend","frontend","ui")`: `assert registry.get(role).net is False` and `"net" not in (registry.get(role).tools or ())`.

       d. `test_compiled_registry_refuses_unknown_id` (OTEAM-06) — `assert registry.get("freelancer") is None`. Construct the envelope string and assert it matches the exact format at `subagents.py:97-98`.

       e. `test_em_scope_equals_ceiling_scope` — `assert registry.get("em").scope.globs == config.ceiling.scope.globs`.

       f. `test_backend_scope_is_strict_subset_of_ceiling` — `assert registry.get("backend").scope.globs == ("src/api/**",)`; `assert registry.get("backend").scope.is_contained_in(config.ceiling.scope) is True`.

       g. `test_role_with_no_scope_inherits_ceiling` — Parse a `team` block where one role omits `scope`; assert compiled spec's `scope == ceiling.scope`.

       h. `test_role_budget_cap_validates_against_ceiling` — Parse a team with `ceiling { budget: 100 tokens }` and `roster e { backend { budget: 50 tokens } }`; compile succeeds; assert `registry.get("backend").budget == 50`. Parse another with `backend { budget: 200 tokens }` (exceeds ceiling); assert `compile_team` raises `VossTeamConfigError` mentioning both numbers.

       i. `test_open_roster_accepts_custom_role_name` (OQ-02-A resolution) — Parse `roster e { devops { model: "opus", scope: "src/infra/**" } }`; compile succeeds; assert `registry.get("devops")` exists with fallback description.

       j. `test_unknown_mode_rejects` — Parse `roster e { backend { mode: "yolo", scope: "src/**" } }`; assert `compile_team` raises `VossTeamConfigError` mentioning `"yolo"` and the valid alternatives.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.team import compile_team, TeamRoleScope, TeamCeiling, TeamConfig, SubagentRegistry, DEFAULT_ROSTER, default_team_role_defaults, subagent_spec_from_role; print('imports OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "
from voss.harness.team import TeamRoleScope
s = TeamRoleScope(('src/api/**',))
ceiling = TeamRoleScope(('src/**',))
assert s.is_contained_in(ceiling) is True
out = TeamRoleScope(('etc/**',))
assert out.is_contained_in(ceiling) is False
print('containment OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/voss/test_team_compile.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def compile_team|def subagent_spec_from_role|def subagent_spec_from_agent' voss/harness/team.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -v '^[[:space:]]*#' voss/harness/team.py | grep -cE 'frozen=True' | awk '$1 < 6 {print "FAIL frozen markers="$1; exit 1} {print "frozen=", $1}'</automated>
  </verify>
  <done>
    - `compile_team`, `subagent_spec_from_role`, `subagent_spec_from_agent`, `default_team_role_defaults`, `DEFAULT_ROSTER` all exist in `voss/harness/team.py`.
    - `TeamRoleScope.is_contained_in` implemented per OQ-02-C heuristic.
    - `tests/voss/test_team_compile.py` has ≥ 10 tests, all pass.
    - Strawman compiles to expected `TeamConfig` shape.
    - AI role has `net=True`; engineer roles don't.
    - Open roster accepts custom names (OQ-02-A resolution recorded in SUMMARY).
    - Per-role budget cap enforced against ceiling (OQ-02-B resolution recorded in SUMMARY).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Scope-invariant + immutability acceptance gates</name>
  <files>tests/voss/test_team_scope_invariant.py, tests/voss/test_team_immutability.py</files>
  <behavior>
    - Scope-invariant suite covers OTEAM-05 acceptance and a property-style "union ⊆ ceiling" check.
    - Immutability suite covers OTEAM-04 at the **compiled** layer (O2-01 covered the value-object shells; this covers post-compile `TeamConfig` instances).
    - Together with O2-01's parser-layer immutability tests, the structural-cage gate is complete.
  </behavior>
  <action>
    1. **Create `tests/voss/test_team_scope_invariant.py`:**

       a. `test_role_scope_contained_in_ceiling_compiles` — Parse `ceiling { scope: "src/**" }` + `backend { scope: "src/api/**" }`, compile, assert success and `registry.get("backend").scope.globs == ("src/api/**",)`.

       b. `test_role_scope_outside_ceiling_rejects` — Parse `ceiling { scope: "src/**" }` + `backend { scope: "etc/**" }`; assert `compile_team` raises `VossTeamConfigError`; assert the error message contains both `"src/**"` and `"etc/**"` and the role name `"backend"`.

       c. `test_role_without_scope_inherits_ceiling` — Parse `ceiling { scope: "src/**" }` + `backend { model: "opus" }` (no scope); compile; assert `registry.get("backend").scope.globs == ("src/**",)`.

       d. `test_role_scope_equals_ceiling_compiles` — A role declaring the same scope as ceiling compiles successfully (boundary, not strict subset).

       e. `test_glob_containment_heuristic_known_cases` — Direct unit tests on `TeamRoleScope.is_contained_in` for the documented patterns from the strawman: `(src/api/**) ⊆ (src/**)`, `(src/web/**) ⊆ (src/**)`, `(src/ml/**) ⊆ (src/**)`, `(etc/**) ⊄ (src/**)`, `(src/api/**) ⊄ (src/web/**)`. Includes the heuristic's known limitation: `("**/test/**") ⊄ ("src/**")` (would be a false-negative under naive prefix; assert behaviour matches the heuristic's documented contract).

       f. `test_union_of_role_scopes_subset_of_ceiling` (OTEAM-05 corollary, property-style) — Compile the strawman; collect all role scopes; for each role's scope.globs, assert each glob `is_contained_in(ceiling.scope) is True`. This is the union property by induction. (No hypothesis dependency; deterministic across roster.)

       g. `test_scope_string_form_and_list_form_equivalent` (OQ-01-A bridge) — Compile `roster e { backend { scope: "src/api/**" } }` and `roster e { backend { scope: ["src/api/**"] } }`; assert both produce `TeamRoleScope(globs=("src/api/**",))`.

    2. **Create `tests/voss/test_team_immutability.py`:**

       a. `test_compiled_team_config_is_frozen` — Compile strawman; assert assigning to `config.name`, `config.ceiling`, `config.policy`, `config.em_agent_id`, `config.roster_ids`, `config.board`, `config.rituals` each raises `FrozenInstanceError`.

       b. `test_compiled_team_ceiling_is_frozen` — `config.ceiling.budget_tokens = 999` raises; `config.ceiling.scope = …` raises; `config.ceiling.latency_seconds = …` raises.

       c. `test_compiled_team_policy_is_frozen` — `config.policy.p = 0.1` raises.

       d. `test_compiled_registry_specs_are_frozen` — for each spec returned by `registry.entries()`, assigning to `.model`, `.mode`, `.scope`, `.budget`, `.tools`, `.net` each raises `FrozenInstanceError`.

       e. `test_no_em_api_to_widen_ceiling` (structural cage gate, OTEAM-04) — `assert not hasattr(config.ceiling, 'with_budget')` and `not hasattr(config.ceiling, 'set_budget')`. Likewise for `with_scope`, `with_latency`, etc. Confirms the EM has NO ergonomic mutation API; the only mutation path would be `dataclasses.replace`, which produces a NEW object — it does not mutate the live config a running EM holds.

       f. `test_roster_ids_is_frozenset` — `assert isinstance(config.roster_ids, frozenset)`; `config.roster_ids.add("ghost")` raises `AttributeError` (frozenset has no `add`).

       g. `test_board_spec_raw_items_is_tuple` — `assert isinstance(config.board.raw_items, tuple)`.

       h. `test_rituals_is_tuple` — `assert isinstance(config.rituals, tuple)`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/voss/test_team_scope_invariant.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/voss/test_team_immutability.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def test_' tests/voss/test_team_scope_invariant.py | awk '$1 < 7 {exit 1} {print "scope-invariant tests:", $1}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def test_' tests/voss/test_team_immutability.py | awk '$1 < 8 {exit 1} {print "immutability tests:", $1}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/voss/ tests/harness/test_subagent_spec_extensions.py tests/parser/test_team_grammar.py -x -q</automated>
  </verify>
  <done>
    - `tests/voss/test_team_scope_invariant.py` has ≥ 7 tests, all pass.
    - `tests/voss/test_team_immutability.py` has ≥ 8 tests, all pass.
    - The full O2 test surface so far (parser-grammar + spec-extensions + compile + scope-invariant + immutability) is green.
    - OQ-02-A, OQ-02-B, OQ-02-C resolutions recorded in SUMMARY.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `TeamDecl` AST → `compile_team` | Crosses from parse-shape (`*Decl`) to runtime shape (`TeamConfig` + `SubagentRegistry`). Compile-time validators are the cage's enforcement perimeter. |
| `compile_team` output → downstream consumers (O2-03 gate compilation; O3 dispatch) | Hand-off is frozen value-objects + registry; downstream cannot widen. |

## STRIDE Threat Register (O2-02 scope)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O2-02-01 | Elevation of Privilege | Role declares `scope: "etc/**"` while `ceiling.scope = "src/**"`; without compile check, EM could dispatch to a role that writes outside the ceiling | mitigate | `subagent_spec_from_role` raises `VossTeamConfigError` at compile time; `test_role_scope_outside_ceiling_rejects` is the regression gate. (OTEAM-05.) |
| T-O2-02-02 | Elevation of Privilege | Engineer role's `tools` list contains `"net"`, granting net to a non-AI role | accept | OTEAM-03 says **AI gets net**; it does NOT prohibit other roles. The cage choice is: a role's `tools` list is the declaration; if a `.voss` author opts a non-AI role into `net`, that's their declared intent. Detection (not prohibition): document this as an audit signal for O6. |
| T-O2-02-03 | Tampering | EM at runtime calls `dataclasses.replace(config.ceiling, budget_tokens=X)` to widen its own budget | mitigate | `dataclasses.replace` returns a NEW `TeamCeiling`; the running EM's `TeamConfig` reference is unchanged. The threat path requires the EM to also rebind `config.ceiling = new_ceiling`, which `TeamConfig(frozen=True)` blocks. `test_compiled_team_config_is_frozen` is the regression gate. |
| T-O2-02-04 | Tampering | Adversarial EM calls `registry.register(SubagentSpec(...))` at runtime to invent an agent | mitigate | The team-compiled `SubagentRegistry` is local to `compile_team`'s return value. **O2 MUST NOT expose `registry` as a tool surface to the EM** — only the `subagent_run` tool, which closes over the registry. (Wiring this is O5; O2 is documentation/test, not enforcement code.) Track as **deferred-to-O5**. |
| T-O2-02-05 | Repudiation / Audit | A `compile_team` failure (e.g. scope-out-of-ceiling) needs to surface BOTH source spans for the user | mitigate | `VossTeamConfigError` is constructed with `role_span` + `ceiling_span` per Task 2 action. Error message includes both globs. `test_role_scope_outside_ceiling_rejects` asserts message content. |
| T-O2-02-06 | Information Disclosure | Compiled `TeamConfig` contains the model id (e.g. `"opus"`) — if persisted to disk later (O6), it would expose provider identity | accept | Not in O2 scope (no persistence in O2). Flag for O6's audit-surfacing decision. |
| T-O2-02-07 | DoS via heuristic glob containment | A pathological `scope` glob causes `is_contained_in` to misclassify, either rejecting legitimate roles (DoS by false-positive) or accepting illegitimate ones (cage bypass by false-negative) | mitigate (partial) | OQ-02-C documents the heuristic's known limitations; `test_glob_containment_heuristic_known_cases` covers the four declared roster patterns + one edge case. Residual risk acknowledged; escalation path = `pathspec` library (would require package-legitimacy gate). |

(Package legitimacy gate: no new package installs. No `[ASSUMED]`/`[SUS]` checkpoints required.)
</threat_model>

<verification>
1. **SubagentSpec extension is back-compat** — 3-arg construction works; defaults populate; no `cli.py` callsite regression (smoke run of legacy tests).
2. **Strawman compiles** — `compile_team(strawman)` returns `(TeamConfig, SubagentRegistry)` with the expected shape; registry has 5 ids; AI role has net=True; engineer roles don't.
3. **Scope invariant enforced at compile time** — out-of-ceiling scope raises with both globs + role name in error; in-ceiling compiles.
4. **Cage immutability is structural at the compiled layer** — every `TeamConfig` sub-object is frozen; `roster_ids` is a frozenset; no `with_*`/`set_*` ergonomic mutators.
5. **OTEAM-06 baseline preserved** — `registry.get("freelancer") is None`; envelope string format matches `subagents.py:97-98` exactly.
6. **No regression** — `tests/parser/` (incl. O2-01), `tests/harness/test_subagent_recursion.py`, and `tests/harness/test_subagent_spec_extensions.py` (new) all green.
</verification>

<success_criteria>
- [ ] `voss/harness/subagents.py::SubagentSpec` has 5 new optional fields + `net: bool = False`; still `frozen=True`.
- [ ] `voss/harness/team.py` exposes `compile_team`, `subagent_spec_from_role`, `subagent_spec_from_agent`, `default_team_role_defaults`, `DEFAULT_ROSTER`.
- [ ] `TeamRoleScope.is_contained_in` is implemented (no more `NotImplementedError`).
- [ ] Open questions OQ-02-A, OQ-02-B, OQ-02-C have explicit resolutions recorded in `O2-02-SUMMARY.md`.
- [ ] ≥ 6 tests in `tests/harness/test_subagent_spec_extensions.py`, all pass.
- [ ] ≥ 10 tests in `tests/voss/test_team_compile.py`, all pass.
- [ ] ≥ 7 tests in `tests/voss/test_team_scope_invariant.py`, all pass.
- [ ] ≥ 8 tests in `tests/voss/test_team_immutability.py`, all pass.
- [ ] No changes to `voss/harness/cli.py`, `voss/harness/multiagent.py`, `voss/harness/permissions.py`, or `voss/harness/tools.py` (those land in O2-03 or are anchored back-compat surfaces).
- [ ] `tests/harness/test_subagent_recursion.py` continues to pass (key regression gate).
</success_criteria>

<output>
Create `.planning/phases/O2-voss-team-spec-roster/O2-02-SUMMARY.md` when done, recording:
- Each task's outcome with verify-command results.
- **OQ-02-A resolution** — closed vs open roster (recommend open).
- **OQ-02-B resolution** — per-role `budget` semantics (recommend cap, validated against ceiling).
- **OQ-02-C resolution** — glob containment heuristic + documented limitations.
- The exact `compile_team` signature and any helper API surface introduced (so O2-03 can consume it).
- Any divergence from the strawman that surfaced during compile (e.g. expr form of `policy.p`).
- Reference to `TeamRunContext` if introduced (Research §6.5 recommended).
</output>

---
phase: O2-voss-team-spec-roster
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/grammar.lark
  - voss/ast_nodes.py
  - voss/parser.py
  - voss/harness/team.py            # NEW
  - tests/parser/test_team_grammar.py        # NEW
  - tests/parser/examples/team_strawman.voss # NEW (fixture)
autonomous: true
requirements: [OTEAM-01, OTEAM-04, OTEAM-08]
tech_stack: [python-3.11, lark-earley, dataclasses-frozen, pytest]
key_files:
  created:
    - voss/harness/team.py
    - tests/parser/test_team_grammar.py
    - tests/parser/examples/team_strawman.voss
  modified:
    - voss/grammar.lark
    - voss/ast_nodes.py
    - voss/parser.py
estimated_duration: ~3-4 hours implementation; ~35% planner-context budget
requirements_addressed: [OTEAM-01, OTEAM-04, OTEAM-08]

must_haves:
  truths:
    - "A `team Name { ceiling { … } p: … agent em { … } roster engineers { backend{…} … } board { … } ritual NAME { … } }` source file parses to a TeamDecl AST node without errors."
    - "The strawman block in ORCHESTRATION-PLAN.md §5 (lines 84–108) parses end-to-end (committed as a fixture)."
    - "Malformed team blocks (unknown ceiling key, unknown role kv key, duplicate ceiling block, missing ceiling) raise VossParseError with the offending location."
    - "TeamCeiling, TeamPolicy, BoardSpec, RitualSpec, TeamConfig are `frozen=True` dataclasses — assignment to any field on a constructed instance raises FrozenInstanceError."
    - "`agent em { model: … }` inside a team_body parses as team_agent; top-level `agent em(…) { … }` continues to parse as agent_decl (no regression on existing parser tests)."
    - "`board { columns: … gate Done(code) { … } }` and `ritual NAME { every: …, gather(...) -> … }` are accepted and round-tripped onto BoardSpec / RitualSpec as opaque data — semantics are NOT interpreted by O2."
  artifacts:
    - path: "voss/grammar.lark"
      provides: "team_decl, team_body, ceiling_block, policy_kv, team_agent, roster_block, board_block, ritual_block productions"
      contains: "team_decl:"
    - path: "voss/ast_nodes.py"
      provides: "TeamDecl + TeamAgentDecl + RosterDecl + RosterRoleDecl + CeilingDecl + BoardDecl + RitualDecl frozen dataclasses"
      contains: "class TeamDecl"
    - path: "voss/parser.py"
      provides: "_Transformer methods for every new production; team_decl hooked into top_decl"
      contains: "def team_decl(self"
    - path: "voss/harness/team.py"
      provides: "Frozen value objects TeamConfig / TeamCeiling / TeamPolicy / TeamRoleScope / BoardSpec / RitualSpec and exception VossTeamConfigError. NO compile() yet — compile is O2-02."
      contains: "class TeamConfig"
    - path: "tests/parser/test_team_grammar.py"
      provides: "Acceptance gate for OTEAM-01 + OTEAM-08; ambiguity smoke test (R1)"
      contains: "def test_minimal_team_parses"
  key_links:
    - from: "voss/grammar.lark::top_decl"
      to: "voss/grammar.lark::team_decl"
      via: "alternation"
      pattern: "top_decl:.*team_decl"
    - from: "voss/parser.py::_Transformer.team_decl"
      to: "voss/ast_nodes.py::TeamDecl"
      via: "AST construction"
      pattern: "return TeamDecl\\("
    - from: "voss/parser.py::_Transformer.top_decl"
      to: "voss/parser.py::_Transformer.team_decl"
      via: "child passthrough (existing top_decl returns children[0])"
      pattern: "def top_decl"
---

<objective>
Add a `team { … }` top-level declaration to the `.voss` grammar and lift it into a typed AST (`TeamDecl`) plus a parallel set of frozen value-object types in a new `voss/harness/team.py` module. This plan is a **pure parse / shape** plan — no `SubagentSpec` changes, no PermissionGate work, no compile step. It establishes the **declarative cage layer's syntax** so O2-02 and O2-03 can attach semantics.

**Purpose:** Make the cage representable. The shape of `ceiling` / `p` / `roster` / `board` / `ritual` is the contract every subsequent O-phase reads from. Locking it as frozen ASTs (and refusing malformed input at parse time) is what makes "EM cannot rewrite the cage" structural rather than aspirational.

**Output:** `team_decl` lives in `top_decl`; the strawman from ORCHESTRATION-PLAN.md §5 parses; new value-object module exists and is import-clean; ~12 parser tests pass.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/ORCHESTRATION-PLAN.md
@.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md
@.planning/phases/O2-voss-team-spec-roster/O2-RESEARCH.md
@voss/grammar.lark
@voss/parser.py
@voss/ast_nodes.py
@tests/parser/conftest.py
@tests/parser/test_fn_agent.py

<interfaces>
<!-- Patterns the executor MUST mirror. Extracted from codebase. -->
<!-- Do not re-derive these from scratch — copy the shapes. -->

Existing parse entry — `voss/parser.py:865`:
```
def parse(source: str, file: str = "<string>") -> Program:
    ...
    tree = _PARSER.parse(source)
    transformer = _Transformer(file)
    return transformer.transform(tree)
```

Existing agent_decl grammar — `voss/grammar.lark:161-164` (template for team_agent terminal-key style):
```
agent_decl: "agent" IDENT "(" _NL* param_list? _NL* ")" ("->" type_expr)? "{" agent_body "}"
agent_body: _NL* (agent_option (_NL+ agent_option)*)? _NL* (stmt (_NL+ stmt)*)? _NL*
agent_option: AGENT_OPTION_KEY ":" expr
AGENT_OPTION_KEY: "system" | "tools" | "model" | "retries" | "memory"
```

Existing agent_decl transformer — `voss/parser.py:707-728` (template for team_decl transformer):
```
def agent_decl(self, meta, children):
    name = str(children[0])
    params: tuple[Param, ...] = ()
    return_type = None
    options = AgentOptions(span=_span(meta, self.file))
    body: tuple = ()
    for c in children[1:]:
        if isinstance(c, tuple) and c and isinstance(c[0], Param):
            params = c
        elif isinstance(c, TypeRef):
            return_type = c
        elif isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], AgentOptions):
            options, body = c
    return AgentDecl(
        span=_span(meta, self.file), name=name, params=tuple(params),
        return_type=return_type, options=options, body=tuple(body), decorators=(),
    )
```

Reusable terminals — `voss/grammar.lark`:
- `IDENT` (line 210), `STRING` (line 201), `expr` (line 25), `list_lit` (line 62)
- `budget_literal: TOKEN_BUDGET | DURATION_MS | DURATION_S | COST_USD | TURNS` (line 85)
- `TOKEN_BUDGET: /\d+[ \t]+tokens\b/` (line 191) — already parses `200 tokens`; `200k tokens` does NOT match today.

Existing `top_decl` plumbing — `voss/parser.py:814-815`:
```
def top_decl(self, meta, children):
    return children[0]
```
A new `TeamDecl` produced by `team_decl` flows through this unchanged.

Test fixture pattern — `tests/parser/conftest.py:1-12`:
```
@pytest.fixture
def parse_source():
    def _impl(src: str, file: str = "<test>"):
        if not src.endswith("\n"):
            src = src + "\n"
        return _parse(src, file)
    return _impl
```

Strawman to parse (ORCHESTRATION-PLAN.md §5, lines 84-108) — write to
`tests/parser/examples/team_strawman.voss`. Will use quoted-glob form
`scope: "src/**"` per open-question A2 default.
</interfaces>
</context>

<open-question id="OQ-01-A" requirement="OTEAM-01">
**Resolve before starting Task 1.** Scope-literal form (Research Open Q #2):
- (a) Quoted string: `scope: "src/api/**"`
- (b) Bare glob token: `scope: src/api/**`
- (c) List of quoted strings: `scope: ["src/api/**", "tests/api/**"]`

**Recommendation (this plan):** (a) for the inner glob token + (c) as a sugar shorthand: `role_value` and `ceiling_value` accept `STRING | list_lit`. Tests use (a). If the user chooses (b), revisit grammar productions §2.1 of O2-RESEARCH.md — would need a new `GLOB` terminal that excludes commas/braces.

If unresolved at exec time: surface the question to the user (`checkpoint:decision`), do not pick silently.
</open-question>

<open-question id="OQ-01-B" requirement="OTEAM-01, OTEAM-08">
**Resolve before Task 1.** team_agent vs agent_decl grammar form (Research Open Q implicit; R1):
- Strawman uses `agent em { model: opus, mode: auto, ... }` (no parens, kv body).
- Existing `agent_decl` at `voss/grammar.lark:161` requires `agent IDENT ( … ) { … }` (parens mandatory).

**Recommendation (this plan):** Keep `agent` keyword for `team_agent`; rely on Earley + the lack of `(` after IDENT inside `team_body` to disambiguate. Add explicit smoke test `test_team_agent_no_paren_collision` (Task 3) BEFORE relying on it.

**Fallback if ambiguity surfaces:** rename inner keyword to `role` (`role em { … }`) — cost: cosmetic divergence from strawman, no semantic loss. Surface as a checkpoint:decision if the smoke test fails.
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add team_decl + sub-productions to voss/grammar.lark</name>
  <files>voss/grammar.lark</files>
  <behavior>
    - Adding `team_decl` to the `top_decl` alternation at line 13 must compose; `lark.Lark` re-parse of the grammar must succeed (no shift/reduce or terminal-collision diagnostics).
    - The minimal program `team Eng { ceiling { budget: 1000 tokens } }` produces a parse tree containing a `team_decl` node.
    - Existing parser tests in `tests/parser/test_fn_agent.py`, `tests/parser/test_expressions.py`, `tests/parser/test_literals.py` continue to pass — no regression on existing top-level decls.
    - `TOKEN_BUDGET` (`grammar.lark:191`) is extended to accept the `200k tokens` shorthand: regex becomes `/\d+[kKmM]?[ \t]+tokens\b/` (decision tracked in this task's notes — used by ceiling_kv). Confirm by parsing `budget: 200k tokens`.
  </behavior>
  <action>
    Insert the productions specified in O2-RESEARCH.md §2.1 (lines 250–305) into `voss/grammar.lark`:

    1. Edit `top_decl` (line 13) to add `| team_decl` as the final alternative.
    2. Append a new section header `// ---- Team declaration (O2) ----` near the existing block-declaration cluster (after `class_decl`, before the `// Statements` block).
    3. Add productions verbatim per research §2.1: `team_decl`, `team_body`, `team_item`, `ceiling_block`, `ceiling_kv`, `CEILING_KEY`, `ceiling_value`, `policy_kv`, `TEAM_POLICY_KEY`, `team_agent`, `team_agent_kv`, `TEAM_AGENT_KEY`, `team_agent_value`, `roster_block`, `roster_role`, `role_kv`, `ROLE_KEY`, `role_value`, `board_block`, `board_item`, `board_kv`, `BOARD_KEY`, `gate_decl`, `gate_target`, `gate_predicate`, `ritual_block`, `ritual_kv`, `RITUAL_KEY`.
    4. Resolve OQ-01-A by using `ceiling_value: budget_literal | STRING | list_lit` and `role_value: budget_literal | STRING | list_lit` (quoted strings + optional list-of-strings sugar; per recommendation).
    5. Extend `TOKEN_BUDGET` regex to accept `k`/`m` prefix: `TOKEN_BUDGET: /\d+[kKmM]?[ \t]+tokens\b/` (line 191). Keep `_resolve_token_budget` in transformer to multiply (this transformer change lives in Task 2).
    6. Follow Strategy-A `_NL*` interior convention — every multi-item block uses `_NL* (item (_NL+ item)*)? _NL*` (`voss/grammar.lark:1-4` header).

    DO NOT introduce a `GLOB` terminal. DO NOT touch `agent_decl` (line 161) — the disambiguation lives entirely in Earley deciding by lookahead `(` vs `{`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.parser import _PARSER; _PARSER.parse('team Eng {\n  ceiling {\n    budget: 1000 tokens\n  }\n}\n'); print('OK')" </automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -n "team_decl" voss/grammar.lark | grep -v '^[[:space:]]*//' | wc -l | awk '$1 < 2 {exit 1} {print "team_decl productions:", $1}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'top_decl:.*team_decl' voss/grammar.lark</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/parser/test_fn_agent.py tests/parser/test_expressions.py tests/parser/test_literals.py -x -q</automated>
  </verify>
  <done>
    - `top_decl` includes `team_decl`; new section block exists in `voss/grammar.lark`.
    - `_PARSER` rebuilds without errors; minimal `team {…}` produces a parse tree.
    - Existing parser tests pass unchanged (regression gate).
    - `TOKEN_BUDGET` accepts both `1000 tokens` and `200k tokens`.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Define frozen AST + value-object types and wire transformer methods</name>
  <files>voss/ast_nodes.py, voss/harness/team.py, voss/parser.py</files>
  <behavior>
    - `voss/ast_nodes.py` exposes `TeamDecl`, `TeamAgentDecl`, `RosterDecl`, `RosterRoleDecl`, `CeilingDecl`, `BoardDecl`, `RitualDecl` as `@dataclass(frozen=True, slots=True)` siblings of `AgentDecl` (line 280). Each carries `span: Span` and the appropriate child shape.
    - `voss/harness/team.py` exposes `TeamConfig`, `TeamCeiling`, `TeamPolicy`, `TeamRoleScope`, `BoardSpec`, `RitualSpec` (all frozen) and the exception `VossTeamConfigError`. These are the **runtime/compiled** value objects; the `Decl` types in ast_nodes are the **parse-shape**. Compile (Decl → Config) is O2-02 — this file holds the value-object SHELL only; constructors must work and frozen-ness must be enforced.
    - `voss/parser.py` gains transformer methods for every new production (mirror `agent_decl` at line 707): `team_decl`, `team_body`, `team_item`, `ceiling_block`, `ceiling_kv`, `policy_kv`, `team_agent`, `team_agent_kv`, `roster_block`, `roster_role`, `role_kv`, `board_block`, `board_item`, `board_kv`, `gate_decl`, `gate_target`, `gate_predicate`, `ritual_block`, `ritual_kv`.
    - Transformer methods produce `TeamDecl` (and friends from ast_nodes) — NOT `TeamConfig`. Compile is later.
    - The `_resolve_token_budget` helper (or equivalent) used inside `ceiling_kv` translates `200k tokens` → integer `200_000`; `200 tokens` → `200`. Lives in `voss/parser.py` next to other transformer helpers.
    - Transformer rejects unknown CEILING_KEY / ROLE_KEY / BOARD_KEY / RITUAL_KEY / TEAM_AGENT_KEY by raising `VossParseError` with span — but because the terminals already restrict to literal alternations, unknown keys are caught by Lark; the transformer just needs to handle dispatch defensively (e.g. switch on key string, raise on default branch with the source span).
    - Construct test: `TeamCeiling(budget_tokens=1, scope=TeamRoleScope(("src/**",)), latency_seconds=None)` is constructable; `t.budget_tokens = 2` raises `FrozenInstanceError`.
    - `parse(source)` returns a `Program` whose `body` includes a `TeamDecl` when the source contains a `team{}` block.
  </behavior>
  <action>
    1. **Edit `voss/ast_nodes.py`:** Add new frozen-dataclass classes immediately after `AgentDecl` (after line 287). Use the existing `Node` / `Decl` / `Stmt` hierarchy (lines 25-35). Required shapes (per O2-RESEARCH.md §3.1 + grammar productions):
       - `CeilingDecl(Decl)` — fields: `budget: int | None`, `scope: tuple[str, ...]`, `latency_seconds: int | None`. Stored as tuples (frozen-friendly), not lists.
       - `TeamAgentDecl(Decl)` — fields: `name: str`, `options: tuple[tuple[str, object], ...]` (kv tuples; opaque expr values).
       - `RosterRoleDecl(Decl)` — fields: `name: str`, `options: tuple[tuple[str, object], ...]`.
       - `RosterDecl(Decl)` — fields: `name: str`, `roles: tuple[RosterRoleDecl, ...]`.
       - `BoardDecl(Decl)` — fields: `items: tuple[object, ...]` (mixed board_kv and gate_decl; opaque).
       - `RitualDecl(Decl)` — fields: `name: str`, `kvs: tuple[tuple[str, object], ...]`.
       - `TeamDecl(Decl)` — fields: `name: str`, `ceiling: CeilingDecl | None`, `policy: object | None`, `agents: tuple[TeamAgentDecl, ...]`, `rosters: tuple[RosterDecl, ...]`, `board: BoardDecl | None`, `rituals: tuple[RitualDecl, ...]`, `decorators: tuple[Decorator, ...] = ()`.

    2. **Create `voss/harness/team.py` (NEW):**
       - Module docstring referencing OTEAM-04 (frozen cage), OTEAM-08 (opaque board/ritual data carrier).
       - `class VossTeamConfigError(Exception)` — args: message + optional `role_span` + `ceiling_span`. Stub for now; populated by O2-02 compile.
       - `@dataclass(frozen=True, slots=True)` for: `TeamRoleScope(globs: tuple[str, ...])`, `TeamCeiling(budget_tokens: int | None, scope: TeamRoleScope | None, latency_seconds: int | None)`, `TeamPolicy(p: object | None)`, `BoardSpec(raw_items: tuple[object, ...])`, `RitualSpec(name: str, raw_kvs: tuple[tuple[str, object], ...])`, `TeamConfig(name: str, ceiling: TeamCeiling, policy: TeamPolicy, em_agent_id: str | None, roster_ids: frozenset[str], board: BoardSpec | None, rituals: tuple[RitualSpec, ...])`.
       - Provide a placeholder method on `TeamRoleScope`: `def is_contained_in(self, other: "TeamRoleScope | None") -> bool` that returns `True` when `other is None`, else raises `NotImplementedError("scope containment implemented in O2-02")`. This makes the **shape** complete without implementing semantics here.

    3. **Edit `voss/parser.py`:**
       - Add transformer methods listed in `<behavior>`. Each builds the corresponding `*Decl` node using `_span(meta, self.file)`. The transformer pattern at `parser.py:707-728` (`agent_decl`) is the template — copy literally for `team_decl`.
       - For `ceiling_kv` / `team_agent_kv` / `role_kv` / `board_kv` / `ritual_kv`: emit `(key_str, value)` tuples; parent rule (`ceiling_block` / `team_agent` / etc.) consumes those into a dict-or-dataclass.
       - For `ceiling_block`: collect kvs into a dict, validate required keys (`budget`/`scope`/`latency` per CEILING_KEY), reject duplicate keys with `VossParseError`, produce `CeilingDecl(budget=…, scope=…, latency_seconds=…)`. Reject MISSING ceiling at the `team_decl` level (next bullet) — `ceiling_block` itself does not require all three keys; downstream validates.
       - For `team_decl`: walk children; if no `CeilingDecl` was seen, raise `VossParseError(... "team {name!r} missing required block: ceiling")` with the team span.
       - For duplicate `ceiling_block` in a `team_body`: raise `VossParseError(... "team {name!r} has duplicate ceiling block")`.
       - Add `_resolve_token_budget(s: str) -> int` near other parser helpers. Strip trailing `tokens`, accept `k`/`m` suffix, multiply (1k = 1_000, 1m = 1_000_000).
       - Import the new ast_nodes types at the top of the file (`from .ast_nodes import …`).

    4. **DO NOT** populate `TeamConfig` from the transformer in this plan. The transformer's job is `parse-tree → Decl AST`; compile is O2-02. Keep `voss/harness/team.py` import-clean from `voss/parser.py` (parser does not import from `voss.harness.team`).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.ast_nodes import TeamDecl, CeilingDecl, RosterDecl, RosterRoleDecl, TeamAgentDecl, BoardDecl, RitualDecl; print('OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.team import TeamConfig, TeamCeiling, TeamPolicy, TeamRoleScope, BoardSpec, RitualSpec, VossTeamConfigError; tc = TeamCeiling(budget_tokens=1, scope=TeamRoleScope(('src/**',)), latency_seconds=None); print('OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss.harness.team import TeamCeiling, TeamRoleScope
tc = TeamCeiling(budget_tokens=1, scope=TeamRoleScope(('src/**',)), latency_seconds=None)
try:
    tc.budget_tokens = 2
except Exception as e:
    assert type(e).__name__ == 'FrozenInstanceError', f'wrong error: {type(e).__name__}'
    print('frozen OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -c "from voss import parse
prog = parse('team Eng {\n  ceiling {\n    budget: 200k tokens\n    scope: \"src/**\"\n  }\n}\n')
from voss.ast_nodes import TeamDecl
assert any(isinstance(d, TeamDecl) for d in prog.body), 'no TeamDecl in program body'
td = [d for d in prog.body if isinstance(d, TeamDecl)][0]
assert td.name == 'Eng'
assert td.ceiling.budget == 200_000, f'budget={td.ceiling.budget}'
print('parse OK')"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -v '^[[:space:]]*#' voss/harness/team.py | grep -cE 'frozen=True' | awk '$1 < 6 {exit 1} {print "frozen dataclasses:", $1}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def team_decl' voss/parser.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/parser/ -x -q --ignore=tests/parser/test_team_grammar.py</automated>
  </verify>
  <done>
    - All seven `*Decl` types exist in `voss/ast_nodes.py`, frozen+slots.
    - All six value-object types + `VossTeamConfigError` exist in `voss/harness/team.py`, frozen+slots.
    - Transformer in `voss/parser.py` builds a `TeamDecl` from a strawman `team Eng { ceiling { … } }` source.
    - `200k tokens` resolves to 200_000.
    - Missing `ceiling` raises VossParseError mentioning the team name; duplicate `ceiling` raises mentioning duplicate.
    - All existing parser tests still pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Acceptance test suite for OTEAM-01 / OTEAM-04 / OTEAM-08</name>
  <files>tests/parser/test_team_grammar.py, tests/parser/examples/team_strawman.voss</files>
  <behavior>
    - Strawman fixture (committed): a self-contained `.voss` source equivalent to ORCHESTRATION-PLAN.md §5 lines 84–108, using quoted-glob form per OQ-01-A. Parses end-to-end without error.
    - Tests below cover OTEAM-01 (parse), OTEAM-04 (frozen-ness), OTEAM-08 (opaque board/ritual round-trip), and R1 ambiguity smoke (OQ-01-B).
    - Every test runs in &lt; 0.5s; no I/O beyond the fixture file.
  </behavior>
  <action>
    1. **Create `tests/parser/examples/team_strawman.voss`:** Write a Voss source file modelling ORCHESTRATION-PLAN.md §5 strawman. Use quoted globs for scope. Include: `team Engineering { ceiling { budget: 200k tokens, scope: "src/**", latency: 30m }, p: risk_tiered, agent em { model: "opus", mode: "auto", authority: "full", scope: "all", budget: "ceiling", tools: ["board","spawn","kill","timer"], judge: "tiered", checks: ["slop","errors","correctness","review_idea_alignment"], sees: ["artifact","acceptance","repo","original_idea"], derives: "verification" }, roster engineers { backend { model: "opus", scope: "src/api/**", tools: ["fs","test"] }, frontend { model: "opus", scope: "src/web/**", tools: ["fs","test"] }, ui { model: "opus", scope: "src/ui/**", tools: ["fs","test"] }, ai { model: "opus", scope: "src/ml/**", tools: ["fs","test","net"] } }, board { columns: ["Backlog","Planned","InProgress","InReview","Blocked","Done"], wip: [3,2,1], p: 0.85, retry: 3, liveness: "30m", gate Done(code) { tests: pass, reviewer_a: pass, reviewer_b: pass } }, ritual ContextDigest { every: "1h", gather: "session_tree" } }`. Note: `gather: …` is a keyword `gather`, so use string for now to keep the strawman grammar-compatible. Where strawman uses function-call form (`gather(session_tree)`), record that as a deviation in the test docstring and surface as a follow-up open question if a future researcher revisits.

    2. **Create `tests/parser/test_team_grammar.py`** with these tests (using `parse_source` fixture from `tests/parser/conftest.py`):

       a. `test_minimal_team_parses` — `team Eng { ceiling { budget: 1000 tokens, scope: "src/**" } }` produces a `Program` whose body contains a `TeamDecl(name="Eng")` with `ceiling.budget == 1000` and `ceiling.scope == ("src/**",)`.

       b. `test_full_strawman_parses` — load `tests/parser/examples/team_strawman.voss`, parse it, assert the resulting `Program` contains exactly one `TeamDecl(name="Engineering")` with: 1 `TeamAgentDecl(name="em")`, 1 `RosterDecl(name="engineers")` with 4 roles (`backend`/`frontend`/`ui`/`ai`), a non-None `BoardDecl`, and 1 `RitualDecl(name="ContextDigest")`.

       c. `test_unknown_ceiling_key_rejects` — `team Eng { ceiling { foo: 1 } }` raises `VossParseError` (Lark terminal rejection — `foo` is not in `CEILING_KEY`). Assert error message references the source location (line/col).

       d. `test_unknown_role_kv_key_rejects` — `team Eng { ceiling { budget: 100 tokens }, roster e { backend { foo: 1 } } }` raises `VossParseError`.

       e. `test_team_agent_no_paren_collision` (R1 smoke) — assert both: (i) `team E { ceiling { budget: 100 tokens }, agent em { model: "opus" } }` parses successfully and produces a `TeamAgentDecl`; (ii) the source `agent em(x) { x }\n` at top-level still parses successfully and produces an `AgentDecl` (existing behaviour). If (i) fails with an Earley/transformer error, the test should `pytest.fail` with a directive to surface OQ-01-B to the user and switch the inner keyword to `role`.

       f. `test_duplicate_ceiling_rejects` — two `ceiling { … }` blocks inside one team_body raise `VossParseError` mentioning "duplicate" and the team name.

       g. `test_missing_ceiling_rejects` — `team Eng { agent em { model: "opus" } }` (no ceiling) raises `VossParseError` mentioning "missing required block: ceiling" and the team name.

       h. `test_team_decl_is_frozen` — construct a `TeamDecl`, assert assignment raises `FrozenInstanceError`.

       i. `test_team_ceiling_value_object_is_frozen` — `voss.harness.team.TeamCeiling(budget_tokens=1, scope=TeamRoleScope(("src/**",)), latency_seconds=None)`; `tc.budget_tokens = 2` raises `FrozenInstanceError`. (OTEAM-04 structural-cage gate.)

       j. `test_team_policy_value_object_is_frozen` — `TeamPolicy(p=0.85)`; mutation raises.

       k. `test_board_block_round_trips_opaquely` (OTEAM-08) — strawman fixture: assert `td.board.items` is a non-empty tuple including at least one gate node (something whose repr contains `"Done"`); assert NO interpretation of `gate`/`wip`/`liveness` semantics (the test just checks shape preservation, not validation).

       l. `test_ritual_block_round_trips_opaquely` (OTEAM-08) — `td.rituals[0].name == "ContextDigest"`; `td.rituals[0].kvs` includes a `("every", …)` entry.

    3. Add `tests/parser/test_team_grammar.py` to the path coverage by ensuring it's picked up by `pytest` automatically (it will be — `tests/parser/__init__.py` already exists, no config change needed).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && test -f tests/parser/examples/team_strawman.voss</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/parser/test_team_grammar.py -v</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -cE 'def test_' tests/parser/test_team_grammar.py | awk '$1 < 12 {exit 1} {print "tests:", $1}'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/parser/ -x -q</automated>
  </verify>
  <done>
    - At least 12 tests in `tests/parser/test_team_grammar.py`, all pass.
    - Strawman fixture parses without error.
    - Ambiguity smoke test passes (or, if it fails, OQ-01-B is escalated as a `checkpoint:decision` before continuing — see open question above).
    - All other `tests/parser/` tests still pass (regression gate).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.voss` source → Voss parser | User-authored grammar input becomes AST. The cage starts here — malformed input must fail loudly. |
| AST `TeamDecl` → downstream consumers (O2-02 compile, O3+) | Frozen AST is the contract handed off. Mutation here would be silent-corruption of the cage. |

## STRIDE Threat Register (O2-01 scope only)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O2-01-01 | Tampering | TeamCeiling / TeamPolicy / TeamConfig mutation post-construction | mitigate | All value-object dataclasses declared `frozen=True, slots=True`. Test `test_team_ceiling_value_object_is_frozen` is the structural gate. |
| T-O2-01-02 | Tampering | A subsequent author mutates `*Decl` types in `ast_nodes.py` to `frozen=False` | mitigate | Regression test `test_team_decl_is_frozen` asserts FrozenInstanceError; CI prevents the flip. |
| T-O2-01-03 | Spoofing | A malformed `team{}` block (e.g. with `agent em(x) { x }` style) might parse as `agent_decl` instead of `team_agent`, silently misrouting | mitigate | `test_team_agent_no_paren_collision` smoke test verifies disambiguation. If it fails, OQ-01-B fallback (`role` keyword) is documented and gated by `checkpoint:decision`. |
| T-O2-01-04 | Denial of Service | Pathological deeply-nested `team{}` parses cheaply enough to be a DoS surface for any tooling that parses untrusted `.voss` | accept | Parser is offline-only; threat model is single-user developer machine. Lark's Earley parser is not known to be vulnerable to exponential blowup on these productions. |
| T-O2-01-05 | Information Disclosure | Source spans inside `VossParseError` could leak filesystem paths | accept | Already the project-wide convention for VossParseError (see `voss/parser.py:861`); not a new exposure. |
| T-O2-01-06 | Repudiation / Audit | Board/ritual blocks accepted but not interpreted (OTEAM-08) — risk of "looks accepted, silently dropped" | mitigate | Test `test_board_block_round_trips_opaquely` and `test_ritual_block_round_trips_opaquely` assert tuple-shape preservation; downstream consumers in O3 see the data. |

(Package legitimacy gate: no new package installs in this plan. No `[ASSUMED]`/`[SUS]` checkpoints required.)
</threat_model>

<verification>
1. **Grammar wires up cleanly** — Lark rebuild on import succeeds; `_PARSER` round-trip of minimal `team Eng { ceiling { budget: 1000 tokens, scope: "src/**" } }` produces a parse tree.
2. **AST + value-objects exist, frozen** — All 7 `*Decl` types in `ast_nodes.py`, 6 value-objects + 1 exception in `voss/harness/team.py`; all are `frozen=True`. Six `frozen=True` markers in `voss/harness/team.py`.
3. **Strawman parses end-to-end** — `tests/parser/examples/team_strawman.voss` resolves to a `Program` whose body contains a `TeamDecl(name="Engineering")` with non-empty `agents`, `rosters`, `board`, `rituals`.
4. **Malformed input rejected with location** — unknown keys, duplicate ceiling, missing ceiling all raise `VossParseError`.
5. **No regression** — full `tests/parser/` suite green.
6. **Cage immutability is structural** — `tc.budget_tokens = 2` raises `FrozenInstanceError`; no setter exists on any value-object.
</verification>

<success_criteria>
- [ ] `voss/grammar.lark` includes `team_decl` and all sub-productions per O2-RESEARCH.md §2.1.
- [ ] `voss/ast_nodes.py` defines `TeamDecl`, `CeilingDecl`, `TeamAgentDecl`, `RosterDecl`, `RosterRoleDecl`, `BoardDecl`, `RitualDecl` (all `frozen=True, slots=True`).
- [ ] `voss/harness/team.py` exists and defines `TeamConfig`, `TeamCeiling`, `TeamPolicy`, `TeamRoleScope`, `BoardSpec`, `RitualSpec`, `VossTeamConfigError`.
- [ ] `voss/parser.py` `_Transformer` has methods for every new production; `parse()` returns `TeamDecl`-bearing programs.
- [ ] `tests/parser/examples/team_strawman.voss` parses without error.
- [ ] `tests/parser/test_team_grammar.py` has ≥ 12 tests, all pass.
- [ ] Full `tests/parser/` suite passes (no regression).
- [ ] Open questions OQ-01-A and OQ-01-B explicitly resolved in the implementation (or escalated to user) — note resolution in the SUMMARY.
- [ ] No edits to `voss/harness/subagents.py`, `voss/harness/permissions.py`, `voss/harness/skill/scope.py`, or `voss/harness/tools.py` — those are O2-02 / O2-03 surface.
</success_criteria>

<output>
Create `.planning/phases/O2-voss-team-spec-roster/O2-01-SUMMARY.md` when done, recording:
- Each task's outcome, with the four `<verify>` automated command results.
- The resolution of OQ-01-A (scope-literal form) and OQ-01-B (team_agent vs agent_decl ambiguity) — what was chosen, and the smoke-test evidence.
- The exact strawman `.voss` source committed (for cross-reference in O2-02).
- Any new transformer helper additions (e.g. `_resolve_token_budget`) so O2-02 can find them.
</output>

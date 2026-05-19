# Phase O2: `.voss team{}` Spec + Specialist Roster — Research

**Researched:** 2026-05-19
**Domain:** `.voss` grammar extension (Lark) + harness data-model enrichment (`SubagentSpec` / `SubagentRegistry`) + cage compilation (per-role `PermissionGate` / scope / tool profile)
**Confidence:** HIGH on existing code surface (read directly); MEDIUM on derived requirement boundaries (no O2-SPEC.md yet — synthesized from ORCHESTRATION-PLAN.md §5/§8 and O2-CONTEXT.md only)

---

<user_constraints>
## User Constraints (from O2-CONTEXT.md)

### Locked Decisions
- **Orchestrator lives in the harness, leverages `.voss`** (decision #1). `.voss` declares the team; harness executes.
- **EM selects from a declared roster; cannot invent agents** (decision #3 constraint). Arbitrary agent creation = unbounded, breaks the pre-declared scope/budget cage.
- **`ceiling`/`p` are EM-immutable** (invariant #3, decision #11). The cage is syntax — the EM can read but never rewrite them.
- **Specialization tightens scope for free**: per-role scope shrinks the global-union ceiling (decision #19).

### Claude's Discretion
- `team{}` grammar integration point in the existing `.voss` parser/grammar.
- Roster extensibility mechanism (fixed set vs. user-declared roles).
- How per-role `tools` maps onto existing permission/tool profiles.

### Deferred Ideas (OUT OF SCOPE)
- Board state machine execution → O3.
- Reviewer A/B wiring → O4.
- EM dispatch logic (selection, routing_rationale, kill/re-scope lineage) → O5.
- Audit surfacing, calibration telemetry, sign-off → O6.

The parser produces config + an enriched registry as DATA; O3+ consume it.
</user_constraints>

---

## Summary

O2 is the **declarative cage layer**: `.voss` gains a `team{}` block whose parser output is (a) an enriched `SubagentRegistry` where each `SubagentSpec` carries `model`/`mode`/`scope`/`budget`/`tools` (today it carries only `id`/`description`/`role_prompt` — `voss/harness/subagents.py:28-32`) and (b) a `TeamConfig` value object that records `ceiling`, `p`, board/wip declarations, and rituals as *frozen* data that the runtime EM cannot mutate. The compile target is **data, not behavior** — O3/O4/O5 consume the registry+config; O2 must not implement the board state machine, reviewer wiring, or EM dispatch.

Three load-bearing existing patterns make this tractable:
1. **`SubagentRegistry` already exists** as the central dispatch table (`voss/harness/subagents.py:35-49`), with 5 call sites in `cli.py` and 1 in `multiagent.py` that look up by id. Extending the spec is additive; the registry shape stays the same.
2. **`scope.py` in `voss/harness/skill/` already maps a declared scope (read-only/mutating/all + net) to a `PermissionGate` via `scoped_gate`** (`voss/harness/skill/scope.py:82-95`). This is the *exact* analog for per-role compilation — `team{}` per-role `mode`/`tools`/`net` should compile through the same shape, not a new mechanism.
3. **The grammar already has a precedent for declaration blocks** (`fn_decl`, `agent_decl`, `prompt_decl`, `class_decl` — `voss/grammar.lark:154-172`). `team{}` slots cleanly into `top_decl` (`voss/grammar.lark:13`) alongside them; the transformer pattern in `voss/parser.py:707-728` is the template to copy.

**Primary recommendation:** Add `team_decl` to the `top_decl` alternation; introduce a `TeamConfig` + `TeamCeiling` + `TeamPolicy` value-object trio in `voss/ast_nodes.py`; extend `SubagentSpec` with five `Optional` fields (back-compat by defaulting to `None`), defining a constructor helper `subagent_spec_from_role(role_node, ceiling)` that validates `role.scope ⊆ ceiling.scope` *at parse time*. The compile target is a `TeamConfig` value object that holds (immutable) `ceiling` + `p` + board + rituals **plus** an enriched `SubagentRegistry`. Per-role `PermissionGate` derivation reuses `voss/harness/skill/scope.py:scoped_gate` shape — do NOT hand-roll a parallel gate compiler.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| `team{}` token recognition + parse-tree | `.voss` grammar (`voss/grammar.lark`) | — | New productions; declaration sibling of `agent_decl`. |
| Parse-tree → AST nodes | `voss/parser.py` `_Transformer` | `voss/ast_nodes.py` | Mirror `agent_decl` transformer (`parser.py:707-728`). |
| AST → enriched `SubagentRegistry` + `TeamConfig` | `voss/harness/subagents.py` (extended) + new compiler helper | `voss/harness/skill/scope.py` (reuse `scoped_gate` shape) | Registry is the existing dispatch surface; scope compilation has an existing analog. |
| Compile-time cage enforcement (role.scope ⊆ ceiling.scope; unknown role rejection; EM cannot rewrite ceiling/p) | Compiler helper (new) | `voss/parser.py` | Reject at compile, not runtime — invariants become unrepresentable. |
| Runtime per-role `PermissionGate` (mode/net/tools filter) | Reuse `voss/harness/permissions.py:PermissionGate` (no new class) | `voss/harness/tools.py:make_toolset` (filter) | Same shape `skill/scope.py:scoped_gate` already produces. |
| Board execution, EM dispatch, reviewer | — (OUT OF SCOPE) | O3 / O4 / O5 | O2 only emits config data. |

---

## Phase Requirements

No `O2-SPEC.md` exists yet. The following `OTEAM-NN` set is **proposed** from ORCHESTRATION-PLAN.md §5 (strawman) and §8 (decision log) plus O2-CONTEXT.md. The planner / discuss-phase MUST confirm or refine these before locking.

| ID | Statement | Status | Refs |
|----|-----------|--------|------|
| OTEAM-01 | The `.voss` parser accepts a top-level `team <NAME> { … }` declaration containing `ceiling`, `p`, `agent`, `roster`, `board`, and `ritual` sub-blocks per ORCHESTRATION-PLAN.md §5 strawman; mismatched / malformed blocks raise `VossParseError` with a useful location. | **Locked** (strawman shape) | OPLAN §5; CTX `<domain>` |
| OTEAM-02 | `SubagentSpec` is extended with `model: Optional[str]`, `mode: Optional[Mode]`, `scope: Optional[ScopeSpec\|TeamRoleScope]`, `budget: Optional[int]` (token limit), `tools: Optional[frozenset[str]]`. Existing callers (`default_subagent_registry`, `agent_task`, `run_subagent` — all in `voss/harness/subagents.py`) keep working with defaults `None`. | **Locked** (decision #19, §5 strawman) | OPLAN §8 #19 |
| OTEAM-03 | A default specialist **roster** (`backend`, `frontend`, `ui`, `ai`) is declarable inside `roster engineers { … }`. Each role declares `{ model, scope, tools }`. AI role MUST be able to declare `net` in `tools`; other roles MUST NOT default to `net`. | **Locked** (§5 strawman) | OPLAN §5 lines 84-89 |
| OTEAM-04 | `ceiling { budget, scope, latency }` and `p:` (the threshold policy) are parsed into **frozen** `TeamCeiling` / `TeamPolicy` value objects on `TeamConfig`. No method on `TeamConfig` accepts a mutation of these — the EM cannot rewrite them at runtime *because no API exists to do so*. | **Locked** (invariant #3, decision #11) | OPLAN §4 inv #3; §8 #11 |
| OTEAM-05 | Compile-time validation enforces `role.scope ⊆ ceiling.scope` for every declared role; violation raises a compile-time error with both globs cited (location of role + location of ceiling). The union invariant `⋃ role.scope ⊆ ceiling.scope` is verified as a corollary (since each role is individually contained). | **Locked** (decision #19) | OPLAN §8 #19; §4 inv #2 |
| OTEAM-06 | The dispatch path (today: `run_subagent` in `voss/harness/subagents.py:82`) refuses an `agent_id` not in the declared roster — returns the existing `<error: unknown subagent {id!r}>` envelope (already implemented at `subagents.py:97-98`). O2 verifies this invariant holds for the enriched registry; "EM invents an agent" is structurally impossible because the registry is the lookup. | **Locked** (decision #3 constraint) | OPLAN §8 #3 |
| OTEAM-07 | A helper `gate_for_role(role: SubagentSpec, base_gate: PermissionGate) -> PermissionGate` returns a `PermissionGate` whose `mode` is capped by the role's declared `mode` and whose `auto_yes=True` (subagents must not prompt). MUST reuse the existing `voss/harness/skill/scope.py:scoped_gate` shape — the `_min_mode` helper is already there. Per-role tool *filter* is applied at `make_toolset` consumption, not by mutating `PermissionGate`. | **Locked** (CTX discretion) | `skill/scope.py:82-95` |
| OTEAM-08 | `board { columns, wip, p, retry, liveness, gate … }` and `ritual <NAME> { … }` blocks parse to opaque `BoardSpec` and `RitualSpec` data on `TeamConfig`. **O2 does not execute them** — they are recorded as data and surfaced for O3+ consumption. Parsing must accept the strawman syntax (§5 lines 96-108) but the *semantics* of `gate`/`wip`/`retry`/`liveness` are O3's contract; O2 must NOT silently drop them. | **Locked** (CTX boundary) | CTX `<domain>` |

**TBD (left for SPEC):**
- Roster extensibility — does `roster engineers { … }` allow user-declared role names beyond `backend/frontend/ui/ai`, or is the set closed? ORCHESTRATION-PLAN.md §5 marks the four as the strawman; §2 says "extensible". Resolve at SPEC.
- Scope grammar — is `scope: src/api/**` a string literal, a glob token, or a list-of-globs? Strawman is silent. The simplest answer (string literal containing glob) keeps grammar small; the safer answer (list of globs) future-proofs. Resolve at SPEC.
- `budget` syntax inside roster — strawman shows `ceiling { budget: 200k tokens, … }` but no per-role `budget`. Decision #19 (scope tightening) is the only per-role invariant called out; O3 owns per-card budget *policy* (O1-SPEC.md "Out of scope" line 60: "Budget allocation policy … O3 owns"). So `budget` on a role probably means a per-role *cap* not a per-card allocation. Resolve at SPEC.

---

## 1. Existing Code Surface

### 1.1 `.voss` grammar entry points

`voss/grammar.lark` — relevant productions for the integration point:

- `program: _NL* (top_stmt (_NL+ top_stmt)*)? _NL*` — `voss/grammar.lark:8`
- `top_stmt: top_decl | stmt` — `voss/grammar.lark:12`
- `top_decl: decorated_decl | fn_decl | agent_decl | prompt_decl | class_decl | use_stmt` — `voss/grammar.lark:13`
- Existing block-declaration siblings (precedent for `team_decl`):
  - `agent_decl: "agent" IDENT "(" … ")" … "{" agent_body "}"` — `voss/grammar.lark:161`
  - `agent_body: _NL* (agent_option (_NL+ agent_option)*)? _NL* (stmt …)? _NL*` — `voss/grammar.lark:162`
  - `agent_option: AGENT_OPTION_KEY ":" expr` — `voss/grammar.lark:163`
  - `AGENT_OPTION_KEY: "system" | "tools" | "model" | "retries" | "memory"` — `voss/grammar.lark:164` *(the literal-alternation terminal pattern is the template for `TEAM_OPTION_KEY`)*
  - `prompt_decl`, `class_decl` — `voss/grammar.lark:166-172` (single-purpose block declarations)
- Budget terminals already exist and are reusable inside `ceiling`:
  - `TOKEN_BUDGET: /\d+[ \t]+tokens\b/` — `voss/grammar.lark:191`
  - `DURATION_S: /\d+s\b/`, `DURATION_MS: /\d+ms\b/` — `voss/grammar.lark:193-194`
  - `budget_literal: TOKEN_BUDGET | DURATION_MS | DURATION_S | COST_USD | TURNS` — `voss/grammar.lark:85`
- Newline strategy is **explicit `_NL` in statement lists** (Strategy A, D-02) — `voss/grammar.lark:1-4`. Any new block rule MUST follow the same `_NL*` interior pattern or break the parse.

**Integration point (recommendation):** add `team_decl` to the `top_decl` alternation at `voss/grammar.lark:13` so a `team` block is a sibling of `fn`/`agent`/`prompt`/`class`.

### 1.2 `SubagentSpec` shape + call sites

`voss/harness/subagents.py:28-32`:

```python
@dataclass(frozen=True)
class SubagentSpec:
    id: str
    description: str
    role_prompt: str
```

Every reader:

| Call site | What it reads | Implication for extension |
|-----------|---------------|----------------------------|
| `subagents.py:42-49` — `SubagentRegistry.get/ids/entries` | the dataclass as opaque value | adding `Optional` fields is back-compat |
| `subagents.py:78` — `agent_task(spec, task)` reads only `spec.role_prompt` | role_prompt | unaffected |
| `subagents.py:96-156` — `run_subagent` reads `spec` once via `registry.get(agent_id)`; otherwise just calls `agent_task(spec, task)`. **No reader of `model`/`scope`/`tools` today** | id only (for lookup) | extension fields are uninspected by this call site — O3+ adds the consumption |
| `multiagent.py:240-334` — imports `SubagentRegistry, agent_task`; `_resolve_task(agent, task)` calls `agent_task(spec, task)` when `spec` resolves | role_prompt | unaffected |
| `cli.py:45-48` — imports `SubagentRegistry, attach_subagent_tool, default_subagent_registry, run_subagent` | constructors | unaffected |
| `cli.py:1145` — `/agent spawn` REPL slash-command calls `run_subagent` | runtime caller | unaffected |
| `cli.py:1362, 1659, 2540` — three `attach_subagent_tool(tools, registry=default_subagent_registry(), …)` sites (do / chat / extension contexts) | constructor | unaffected — extension only changes what `default_subagent_registry()` *populates*, not its signature |
| `cli.py:2650-2671` — `subagent` standalone CLI command, calls `run_subagent` directly | runtime caller | unaffected |

**Key takeaway:** every existing reader looks up by `id` and uses `role_prompt`. Adding `Optional` fields with `None` defaults is **fully backward-compatible**; no existing call site has to change in O2.

### 1.3 `SubagentRegistry` shape

`voss/harness/subagents.py:35-49`:

```python
class SubagentRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, SubagentSpec] = {}

    def register(self, spec: SubagentSpec) -> None:
        self._entries[spec.id] = spec

    def get(self, agent_id: str) -> SubagentSpec | None:
        return self._entries.get(agent_id)

    def ids(self) -> list[str]:
        return sorted(self._entries)

    def entries(self) -> list[SubagentSpec]:
        return [self._entries[k] for k in self.ids()]
```

Mutation surface: only `register()`. The dispatch refusal that enforces "EM cannot invent agents" (OTEAM-06) is already implemented at `voss/harness/subagents.py:96-98`:

```python
spec = registry.get(agent_id)
if spec is None:
    return f"<error: unknown subagent {agent_id!r}>"
```

So the cage invariant "EM cannot invent agents" is **already true today by construction** — O2 just inherits it for the enriched registry. O2 does NOT need to add new enforcement; it needs to ensure the `team{}` compiler is the *only* path that populates the registry in a production team-config run (so the EM has no `registry.register(...)` call seam).

### 1.4 `PermissionGate` / `Mode` / project policy

`voss/harness/permissions.py`:

- `Mode = Literal["plan", "edit", "auto"]` — `permissions.py:42`
- `READ_ONLY = {fs_read, fs_glob, fs_grep, git_status, git_diff, voss_check}` — `permissions.py:44`
- `WRITE = {fs_write, fs_edit}` — `permissions.py:45`
- `SHELL = {shell_run, shell_run_background, shell_monitor, shell_signal}` — `permissions.py:46`
- `mode_allows(mode, tool_name, is_mutating)` — `permissions.py:49-65`. Plan denies mutating; edit denies shell_run/_background/_signal; auto allows all (downstream allowlist still enforces).
- `PermissionGate(mode, store, auto_yes, prompt_fn, edit_scope, scope_prompt_fn, project_policy)` — `permissions.py:145-153`. Constructor takes optional `project_policy: PermissionsConfig` (`.voss/permissions.yml`).
- Network gate: `is_network=True` + runtime `allow_net=False` denies BEFORE mode-tier — `permissions.py:226-233`. Per-role `net` capability flows through `is_network` on `ToolEntry`, not through `Mode`. **The AI role getting `net` means: AI role's gate gets a flag that flips `voss_runtime._config.get_config().allow_net` true for that subagent's run** (or, more cleanly, a per-role override that mirrors `--allow-net`).
- Project-policy deny ALWAYS wins; allow does NOT expand — `permissions.py:222-224` and module docstring lines 17-26. Per-role gate compilation MUST preserve `project_policy` (the skill `scoped_gate` does — `skill/scope.py:90-95`).

### 1.5 Existing scope analog — `voss/harness/skill/scope.py`

The closest existing pattern to "declared role scope → `PermissionGate`":

```python
# voss/harness/skill/scope.py:22-28
@dataclass(frozen=True)
class ScopeSpec:
    tools: str = "read-only"  # "read-only" | "mutating" | "all"
    fs: str = "cwd"          # "cwd" | "none"
    net: bool = False
```

```python
# voss/harness/skill/scope.py:56-71
def scope_to_mode(tools_value: str) -> Mode:
    if val == "read-only": return "plan"
    if val == "mutating":  return "edit"
    if val == "all":       return "auto"
    return "plan"  # default-deny

# voss/harness/skill/scope.py:74-79
def _min_mode(m1, m2) -> Mode:
    order = {"plan": 0, "edit": 1, "auto": 2}
    return m1 if order[m1] <= order[m2] else m2

# voss/harness/skill/scope.py:82-95
def scoped_gate(spec, base_gate) -> PermissionGate:
    effective_mode = _min_mode(base_gate.mode, scope_to_mode(spec.tools))
    return PermissionGate(
        mode=effective_mode,
        auto_yes=True,
        store=None,
        project_policy=base_gate.project_policy,
    )
```

**This is the exact template** O2 must reuse for per-role gate compilation (OTEAM-07). The skill scope is essentially "one anonymous role's compiled cage"; the team roster is "N named roles, each with a compiled cage". The `_min_mode` cap-not-expand rule is precisely what OTEAM-04 needs (role mode is min of session mode and declared mode — a role can never expand the harness session's authority).

### 1.6 Tool registration

`voss/harness/tools.py:24-38`:

```python
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    is_network: bool = False
```

`make_toolset(cwd, *, renderer, net, session_id)` — `voss/harness/tools.py:78-625`. Returns `dict[str, ToolEntry]`. Per-role tool *filter* (OTEAM-07) means returning a subset of this dict based on the role's `tools` set, NOT mutating any tool's `is_mutating`/`is_network` flag.

Net example to anchor net handling: `web_fetch` is `ToolEntry(descriptor=web_fetch, is_mutating=False, is_network=True)` — `voss/harness/tools.py:577-579`. The fact that `web_fetch` is read-only yet network-gated proves the two axes (mutate vs net) are independent — see `tools.py:31-33` docstring. A role declaring `tools: [fs, test]` simply gets the subset without `web_fetch`; a role declaring `tools: [fs, test, net]` gets `web_fetch` included AND its `PermissionGate` MUST be constructed against a config with `allow_net=True` (or equivalent override).

### 1.7 Session-tree + budget substrate (O1 — already shipped)

`voss/harness/session_tree.py`:

- `SessionTreeNode` schema — `session_tree.py:47-58`: `{id, root_id, parent_run_id, envelope{limit,spent}, terminal_state, created_at, ended_at, rejected_raises}`
- `BudgetAllocationError`, `BudgetCapRaiseError` — `session_tree.py:30-44`
- `SessionTreeManager.allocate_child(limit)` enforces `sum(child envelopes) + reserve ≤ parent envelope` — `session_tree.py:151-178`
- `finalize_node(node, exit_reason, final, cwd)` — `session_tree.py:100-118` (single-write D-03 close)
- `mutate_envelope(node, delta, cwd)` rejects upward deltas — `session_tree.py:121-136`

**O2 implication:** the `budget` field on `SubagentSpec` (OTEAM-02) is the *declared per-role cap that O3 will pass to `SessionTreeManager.allocate_child(limit=spec.budget)`*. O2 only parses + stores it; O3 calls the allocator. The O1 substrate is **strictly upstream** of O2 — no schema change to `SessionTreeNode` is required for O2.

---

## 2. Grammar Integration Plan

### 2.1 Proposed Lark productions

Add to `voss/grammar.lark`. Slot in `top_decl` (line 13):

```
top_decl: decorated_decl | fn_decl | agent_decl | prompt_decl | class_decl | use_stmt | team_decl

// ---- Team declaration (O2) ----

team_decl:   "team" IDENT "{" team_body "}"
team_body:   _NL* (team_item (_NL+ team_item)*)? _NL*

team_item:   ceiling_block | policy_kv | team_agent | roster_block | board_block | ritual_block

// `ceiling { k: v, k: v }` — every kv is required to be either a budget_literal
// or a string literal (scope glob). Order-free; transformer validates required keys.
ceiling_block: "ceiling" "{" _NL* ceiling_kv (_NL* "," _NL* ceiling_kv)* _NL* ","? _NL* "}"
ceiling_kv:    CEILING_KEY ":" ceiling_value
CEILING_KEY:   "budget" | "scope" | "latency"
ceiling_value: budget_literal | STRING | list_lit

// `p: <expr>` and similar top-level team-config kvs (`p`, `retry`, etc. that
// the board strawman shows at the team level). Stored as opaque expr on
// TeamConfig.policy.
policy_kv:    TEAM_POLICY_KEY ":" expr
TEAM_POLICY_KEY: "p"

// A single named agent (`agent em { ... }`). Distinct from the existing
// `agent_decl` (top-level callable agent). team_agent's body is a kv list,
// not a statement block — no `param_list`, no `block`.
team_agent:   "agent" IDENT "{" _NL* team_agent_kv (_NL* "," _NL* team_agent_kv)* _NL* ","? _NL* "}"
team_agent_kv: TEAM_AGENT_KEY ":" team_agent_value
TEAM_AGENT_KEY: "model" | "mode" | "scope" | "budget" | "tools" | "authority"
              | "judge" | "tiered" | "checks" | "sees" | "derives"
team_agent_value: budget_literal | expr   // expr covers ident, list, string

// `roster <NAME> { role { k: v, ... } role { ... } }`
roster_block: "roster" IDENT "{" _NL* roster_role (_NL+ roster_role)* _NL* "}"
roster_role:  IDENT "{" _NL* role_kv (_NL* "," _NL* role_kv)* _NL* ","? _NL* "}"
role_kv:      ROLE_KEY ":" role_value
ROLE_KEY:     "model" | "mode" | "scope" | "budget" | "tools"
role_value:   budget_literal | expr

// `board { ... }` — strawman shape parsed as a sequence of opaque kv items
// and `gate` declarations. O2 stores as BoardSpec; O3 interprets.
board_block:  "board" "{" _NL* board_item (_NL+ board_item)* _NL* "}"
board_item:   board_kv | gate_decl
board_kv:     BOARD_KEY ":" expr
BOARD_KEY:    "columns" | "wip" | "p" | "retry" | "liveness"
gate_decl:    "gate" IDENT "->" gate_target "{" _NL* gate_predicate (_NL* "," _NL* gate_predicate)* _NL* "}"
gate_target:  IDENT ("(" IDENT ")")?                // `Done(code)`
gate_predicate: expr

// `ritual <NAME> { every: 1h, gather(...) -> semantic.memory }`
ritual_block: "ritual" IDENT "{" _NL* ritual_kv (_NL+ ritual_kv)* _NL* "}"
ritual_kv:    RITUAL_KEY ":" expr
RITUAL_KEY:   "every" | "gather"
```

### 2.2 Token vocabulary

- New literal keywords (consumed by the alternation rules above, NOT new terminals — Lark's anonymous string literals handle them): `team`, `agent` (already a keyword in `agent_decl`), `roster`, `ceiling`, `board`, `ritual`, `gate`.
- New named terminals (string-set literals; same pattern as `AGENT_OPTION_KEY` at `grammar.lark:164`): `CEILING_KEY`, `ROLE_KEY`, `BOARD_KEY`, `RITUAL_KEY`, `TEAM_AGENT_KEY`, `TEAM_POLICY_KEY`. Using named terminals — instead of inline string alternations — makes the transformer code clean (`str(child)` on the key) and produces good error messages on misspelling.
- Token reuse: `IDENT` (existing — `grammar.lark:210`), `STRING` (line 201), `expr` (line 25), `budget_literal` (line 85), `list_lit` (line 62).

### 2.3 Conflict / ambiguity analysis

- **`team_agent` vs `agent_decl` collision** — `agent_decl` requires `"agent" IDENT "(" param_list? ")" … "{" agent_body "}"` (parens around params are non-optional in the grammar at line 161). `team_agent` has `"agent" IDENT "{"` with no parens. Earley + dynamic lexer should pick `agent_decl` only when parens follow, `team_agent` only inside a `team_body`. **Verify with a parser smoke test** in O2 Wave 0: `agent em { model: opus }` inside `team { … }` must parse as `team_agent`; `agent em() { … }` at top level must still parse as `agent_decl`. Risk: MEDIUM — needs a test, not a redesign.
- **Roster role names are bare `IDENT`** — `backend`, `frontend`, `ui`, `ai` are all valid `IDENT`s (line 210). No keyword collision (none of them appear in the IDENT exclusion at line 210, which only excludes `similar` and `_`).
- **`board` inside `team_body` vs no top-level `board`** — `board_block` is only reachable from `team_body`; never reachable from `program` directly. No ambiguity.
- **`gate` keyword** — appears nowhere else in the grammar (verified by `grep -n '"gate"' voss/grammar.lark` returns nothing). Safe to introduce.
- **`scope: src/api/**` literal form** — `src/api/**` is not valid Voss expression syntax. Strawman shows it bare. Two options: (a) require quoting → `scope: "src/api/**"` (cleanest, no grammar change beyond `STRING`); (b) introduce a `glob_literal` terminal. Recommendation (TBD for SPEC): **require quoting**, because the grammar already accepts strings everywhere and the strawman's bare form is shorthand-prose, not a grammar contract.

### 2.4 Transformer (`voss/parser.py`)

Mirror the `agent_decl` transformer at `voss/parser.py:707-728`. New methods:

- `team_decl(meta, children)` → return new `TeamDecl` AST node (or call into compiler that returns `TeamConfig` directly — design choice, recommend `TeamDecl` for grammar/codegen symmetry, then a separate compiler).
- `team_body`, `team_item`, `ceiling_block`, `ceiling_kv`, `team_agent`, `roster_block`, `roster_role`, `board_block`, `gate_decl`, `ritual_block` — each builds the corresponding value object.

Hook into `top_decl` at `parser.py:814-815` — already returns `children[0]`, so a new `TeamDecl` flowing through `top_decl` reaches the `Program.body` tuple unchanged.

### 2.5 Malformed-block error reporting

Compile-time rejections (raise `VossParseError` or a new `VossTeamConfigError` with location):

| Malformed input | Expected rejection |
|-----------------|---------------------|
| Unknown role inside `roster engineers { foobar { … } }` | If roster is **closed** (TBD): `unknown role 'foobar' (expected: backend, frontend, ui, ai)` with role span. If open: accept. |
| Unknown `mode` literal (e.g. `mode: yolo`) | `unknown mode 'yolo' (expected: plan, edit, auto)` |
| Role scope outside ceiling scope (`ceiling { scope: "src/**" }` + `backend { scope: "etc/**" }`) | `role 'backend' scope 'etc/**' is not contained in ceiling scope 'src/**'` with both spans |
| Missing `ceiling` block | `team 'Eng' missing required block: ceiling` |
| Two `ceiling` blocks | `team 'Eng' has duplicate 'ceiling' block at <span2>` |
| `p:` mutation attempt — N/A at parse time (parse can only declare it once; runtime EM has no API path) | enforced structurally |
| `team{}` declared at non-top level (inside `fn { }` or `agent { }`) | Already rejected — `team_decl` is only in `top_decl`, not in `stmt`. |
| `agent` block with both `(params)` and `{kv}` body — same as the conflict in §2.3 | Earley/transformer error; surface as `unexpected '(' after 'agent <ID>' inside team{} — team-agent blocks take no parameters` |

---

## 3. `SubagentSpec` / `TeamConfig` Extension Shape

### 3.1 Proposed dataclasses

Add to `voss/harness/subagents.py` (or a new `voss/harness/team.py` if the planner prefers smaller modules):

```python
# voss/harness/team.py (NEW) — value objects, all frozen

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Tuple, Any
from .permissions import Mode  # Literal["plan", "edit", "auto"]


@dataclass(frozen=True)
class TeamRoleScope:
    """Per-role write scope; a list of glob patterns rooted at project cwd."""
    globs: Tuple[str, ...]

    def is_contained_in(self, other: "TeamRoleScope") -> bool:
        """Compile-time: every self.glob must be a subpath/subglob of some other.glob."""
        # implementation: for each self glob, verify ∃ outer glob whose prefix
        # (up to the first wildcard) contains it. Heuristic but adequate for
        # ceiling vs role compile-time check — formally verified by the
        # corresponding test (see §6).


@dataclass(frozen=True)
class TeamCeiling:
    """Immutable global ceiling. NO setter, NO with_ helper."""
    budget_tokens: int            # parsed from `200k tokens` -> 200_000
    scope: TeamRoleScope
    latency_seconds: Optional[int]  # parsed from `30m` -> 1800


@dataclass(frozen=True)
class TeamPolicy:
    """Immutable threshold policy (`p`). EM cannot rewrite."""
    p: str | float    # "risk_tiered" or 0.85 — opaque expr from grammar


@dataclass(frozen=True)
class BoardSpec:
    """Opaque board declaration; consumed by O3. O2 parses, does not execute."""
    raw_items: Tuple[Any, ...]    # list of board_kv / gate_decl AST shrapnel


@dataclass(frozen=True)
class RitualSpec:
    name: str
    raw_kvs: Tuple[Tuple[str, Any], ...]


@dataclass(frozen=True)
class TeamConfig:
    """The compile target of a `team { … }` block. Immutable.
    Held alongside the enriched SubagentRegistry; consumed by O3+."""
    name: str
    ceiling: TeamCeiling
    policy: TeamPolicy
    em_agent_id: str              # which roster id is the EM
    roster_ids: FrozenSet[str]    # the declared roster (closed set for dispatch)
    board: Optional[BoardSpec]
    rituals: Tuple[RitualSpec, ...]
```

Extend `SubagentSpec` in `voss/harness/subagents.py:28-32` (backward-compatible — every new field defaults to `None`):

```python
@dataclass(frozen=True)
class SubagentSpec:
    id: str
    description: str
    role_prompt: str
    # --- O2 additions (all Optional for back-compat) ---
    model: Optional[str] = None
    mode: Optional[Mode] = None             # session-mode tier
    scope: Optional[TeamRoleScope] = None   # per-role write scope
    budget: Optional[int] = None            # per-role token cap (consumed by O3 allocator)
    tools: Optional[FrozenSet[str]] = None  # subset of make_toolset() keys; None = unfiltered
    net: bool = False                       # explicit; if True, role gets is_network tools
```

### 3.2 Constructor helper (compiler)

```python
# voss/harness/team.py (NEW)

def subagent_spec_from_role(
    role_name: str,
    role_kvs: dict,
    ceiling: TeamCeiling,
) -> SubagentSpec:
    """Compile a roster role into an enriched SubagentSpec. Validates scope ⊆ ceiling."""
    scope = _parse_role_scope(role_kvs.get("scope"))
    if scope is not None and not scope.is_contained_in(ceiling.scope):
        raise VossTeamConfigError(
            f"role {role_name!r} scope {scope.globs!r} not contained "
            f"in ceiling scope {ceiling.scope.globs!r}",
            role_span=...,
            ceiling_span=...,
        )
    tools = frozenset(role_kvs.get("tools", []))
    return SubagentSpec(
        id=role_name,
        description=_default_description_for(role_name),  # or take from kv
        role_prompt=_default_prompt_for(role_name),
        model=role_kvs.get("model"),
        mode=role_kvs.get("mode") or "edit",  # default tier for engineer roles
        scope=scope,
        budget=_parse_budget(role_kvs.get("budget")),
        tools=tools or None,
        net=("net" in tools),
    )
```

### 3.3 Back-compat plan

- `voss/harness/subagents.py:52-75` `default_subagent_registry()` continues to construct the three legacy specs (`explorer`, `worker`, `reviewer`) with only `id`/`description`/`role_prompt` — every new field defaults to `None`. No call site change.
- `voss/harness/subagents.py:78` `agent_task(spec, task)` is unchanged — reads only `spec.role_prompt`.
- `voss/harness/subagents.py:82-156` `run_subagent` is unchanged in O2 — O3 will gate on `spec.budget`/`spec.scope`/`spec.tools` to actually shape the child's gate and toolset.
- `voss/harness/cli.py:1362, 1659, 2540` `attach_subagent_tool(…, registry=default_subagent_registry(), …)` keeps working unchanged. The team-compiled registry is a *separate* construction path activated only when a `team{}` block is loaded; the legacy registry remains the default for `voss chat`/`voss do` until O5 wires the EM.

---

## 4. Cage Invariants — Enforcement Strategy

| Invariant (OPLAN §4) | Where enforced | How |
|----------------------|----------------|------|
| Inv #2: scope has global ceiling; union of role scopes ⊆ ceiling | **Compile time** in `subagent_spec_from_role` (§3.2) | Per-role `is_contained_in` check during parse. Union holds by induction: each role ⊆ ceiling → ⋃ roles ⊆ ceiling. No runtime check needed. |
| Inv #3: confidence threshold `p` is human-set, EM-immutable | **Compile time + structural** | `TeamPolicy` is `frozen=True` and has no setter. `TeamConfig` is `frozen=True`. The EM at runtime holds a *reference* to `TeamConfig` but has no API to mutate it — invariant is unrepresentable in the type system. |
| Inv (decision #3): EM cannot invent agents | **Runtime, by existing `registry.get()` returning None** — `voss/harness/subagents.py:96-98` already returns `<error: unknown subagent {id!r}>`. | O2 inherits this for the enriched registry. The only additional requirement: the team compiler must be the *sole* path that populates the production registry; we MUST NOT expose a `registry.register(...)` seam to the EM at runtime. |
| Cage decl: ceiling/p declared *above* the EM | **Grammar shape** | `team_body` order is unconstrained but `em_agent_id` is just one `team_agent`; `ceiling`/`policy_kv` are siblings, not children of any agent. The "above" relationship is the *declaration model*: ceiling/p are properties of the TeamConfig, not properties any agent owns. |

### Threat model: adversarial EM

| Attack vector | What an adversarial EM might try | How the cage blocks it |
|---------------|----------------------------------|------------------------|
| Mutate `ceiling.budget_tokens` to extend total budget | call `team_config.ceiling.budget_tokens = X` | `TeamCeiling(frozen=True)` → `FrozenInstanceError`. No setter exists. |
| Mutate `p` to lower the threshold | call `team_config.policy.p = 0.1` | `TeamPolicy(frozen=True)` → `FrozenInstanceError`. |
| Spawn a sub-agent with role id not in roster | call `run_subagent(agent_id="freelancer", …)` | `voss/harness/subagents.py:97-98` — `registry.get` returns `None`, dispatch returns error envelope; **no execution**. |
| Register a new agent at runtime | call `registry.register(SubagentSpec(...))` | The team-compiled registry is local to the team loader and not exposed in the EM's tool set. Mitigation: do NOT pass the `SubagentRegistry` instance into the EM's tool surface — only the *agent-id list* (`registry.ids()`) and the `subagent_run` tool (which closes over the registry). |
| Widen role scope by re-emitting a card with broader edit_scope | call into a tool that bypasses the role's compiled `PermissionGate` | Per-role `PermissionGate` is constructed by `gate_for_role` (§3, OTEAM-07) at dispatch time and bound to the child's `run_subagent` call. The EM cannot construct a different gate because it has no `PermissionGate(...)` constructor in its tool surface. |
| Set `is_network=True` on a non-AI role's tool | not in the EM's surface — `ToolEntry` construction happens in `make_toolset` outside the team loop | The per-role tool filter at OTEAM-07 is a *subset* operation, not a re-classification. The AI role gets `net` because its declared `tools` includes `net`; other roles don't get `net` because their `tools` doesn't include it. The EM can't change the declaration — it's parsed at load. |

**Residual (acknowledged by OPLAN §7):** misroute risk #4 — EM can route a card to the wrong role (e.g., an editing card to the AI role to get `net`). OPLAN's mitigation is `routing_rationale` per card, audited in O6. O2 cannot close this in its layer.

---

## 5. Test Surface

### 5.1 Parser (unit, `tests/voss/test_team_grammar.py` — new)

| Test | Asserts |
|------|---------|
| `test_minimal_team_parses` | `team Eng { ceiling { budget: 1000 tokens } }` → `TeamDecl(name="Eng", …)` |
| `test_full_strawman_parses` | The §5 strawman parses end-to-end without errors |
| `test_unknown_ceiling_key_rejects` | `ceiling { foo: 1 }` raises `VossParseError` mentioning expected keys |
| `test_unknown_role_key_rejects` | `roster e { backend { foo: 1 } }` raises with `foo` location |
| `test_team_agent_no_paren_collision` | `team E { agent em { model: opus } }` parses as `team_agent`; `agent em() { … }` at top-level still parses as `agent_decl` |
| `test_duplicate_ceiling_rejects` | two `ceiling` blocks raise |
| `test_missing_ceiling_rejects` | `team Eng { agent em { … } }` raises "missing required block" |
| `test_bare_glob_requires_quoting` *(if SPEC chooses quoted globs)* | `scope: src/**` raises; `scope: "src/**"` succeeds |

### 5.2 `SubagentSpec` extension defaults (unit, `tests/harness/test_subagent_spec_extensions.py` — new)

| Test | Asserts |
|------|---------|
| `test_legacy_spec_construction_unchanged` | `SubagentSpec("x", "d", "rp")` succeeds; all new fields are `None`/`False` |
| `test_default_registry_unchanged` | `default_subagent_registry()` still returns exactly `{explorer, worker, reviewer}` (`subagents.py:52-75`) |
| `test_agent_task_uses_role_prompt_only` | `agent_task(spec, "do X")` reads `role_prompt` regardless of new fields |
| `test_dispatch_refuses_unknown_id` | `run_subagent(agent_id="ghost", …)` returns `<error: unknown subagent 'ghost'>` (current behaviour at `subagents.py:97-98` preserved) |

### 5.3 Compile-time scope ⊆ ceiling (unit, `tests/voss/test_team_scope_invariant.py` — new)

| Test | Asserts |
|------|---------|
| `test_role_scope_contained_compiles` | `ceiling { scope: "src/**" }` + `backend { scope: "src/api/**" }` compiles |
| `test_role_scope_outside_rejects` | `ceiling { scope: "src/**" }` + `backend { scope: "etc/**" }` raises `VossTeamConfigError` mentioning both globs |
| `test_role_with_no_scope_inherits_ceiling` | A role omitting `scope` gets `ceiling.scope` (or `None` — TBD at SPEC) |
| **Property test (OTEAM-05 corollary)** | For any compiled `TeamConfig` with roles `r1..rn`, `union(r.scope for r in roles) ⊆ ceiling.scope` holds. (Trivially true by per-role check; the property test ensures the helper isn't accidentally non-transitive.) |

### 5.4 Cage immutability (unit, `tests/voss/test_team_immutability.py` — new)

| Test | Asserts |
|------|---------|
| `test_team_ceiling_is_frozen` | `TeamCeiling(...)` → setting `.budget_tokens = X` raises `FrozenInstanceError` |
| `test_team_policy_is_frozen` | same for `TeamPolicy.p` |
| `test_team_config_is_frozen` | `TeamConfig.ceiling = …` raises |
| `test_subagent_spec_is_frozen` | already true (existing `frozen=True`) — regression guard against accidental unfreeze |

### 5.5 Per-role gate compilation (unit, `tests/harness/test_team_gate_compile.py` — new)

| Test | Asserts |
|------|---------|
| `test_gate_for_role_caps_mode` | `gate_for_role(spec(mode="plan"), base_gate(mode="edit"))` → `PermissionGate(mode="plan")` |
| `test_gate_for_role_never_expands` | `gate_for_role(spec(mode="auto"), base_gate(mode="edit"))` → `PermissionGate(mode="edit")` (cap-not-expand, mirroring `skill/scope.py:_min_mode`) |
| `test_gate_for_role_preserves_project_policy` | If `base_gate.project_policy` set, derived gate inherits it (mirrors `skill/scope.py:90-95`) |
| `test_gate_for_role_subagent_does_not_prompt` | `auto_yes=True` always (subagents non-interactive) |
| `test_ai_role_gets_net_tools` | `make_filtered_toolset(spec(tools={"fs","test","net"}), …)` includes `web_fetch`; without `"net"`, excludes it |

### 5.6 Integration (`tests/voss/test_team_compile_end_to_end.py` — new)

| Test | Asserts |
|------|---------|
| `test_strawman_compiles_to_expected_registry` | Compile §5 strawman → `TeamConfig` whose `roster_ids == {"em","backend","frontend","ui","ai","reviewer_a","reviewer_b"}`, ceiling `200_000` tokens, scope `"src/**"`, latency `1800`s |
| `test_compiled_registry_dispatch_refuses_unknown` | Compiled registry's `subagent_run("freelancer", …)` returns the `<error: unknown subagent>` envelope |
| `test_compiled_registry_back_compat_with_attach` | `attach_subagent_tool(tools, registry=compiled_registry, …)` succeeds; legacy callers don't break |

---

## 6. Risks + Open Questions

### Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | `team_agent` vs `agent_decl` grammar ambiguity (the `agent IDENT { …` overlap, §2.3) | **MEDIUM** | Add the smoke test in §5.1 `test_team_agent_no_paren_collision` as a Wave 0 acceptance gate. If ambiguity surfaces, rename the inner keyword (`role em { … }` instead of `agent em { … }`) — strawman uses `agent` but it's not a hard requirement. |
| R2 | Glob containment `is_contained_in` heuristic gets fancy globs wrong (e.g. `src/api/**` vs `src/**/api/**`) | **MEDIUM** | Start with a simple "prefix up to first `*`" comparison + explicit test cases for the known patterns (`src/**`, `src/api/**`, `tests/api/**`); document the heuristic; defer formal glob algebra to a follow-up if abuse patterns emerge. |
| R3 | Net handling — granting AI role `net` requires per-subagent override of `voss_runtime._config.allow_net`. Today `allow_net` is a process-level toggle (`permissions.py:226-233`). | **MEDIUM** | Two options: (a) extend `PermissionGate` to carry a per-gate `allow_net` override (small surface change, but touches the gate); (b) construct the AI role's runtime context with a fork that sets `allow_net=True`. Recommend (a); it stays inside the gate boundary and avoids cross-cutting config mutation. Confirm at SPEC. |
| R4 | Adding fields to a `frozen=True` dataclass is backward compatible with **positional** call sites today (3 in `default_subagent_registry`, none elsewhere), but **NOT** with any callsite that constructs `SubagentSpec(...)` with positional args beyond `role_prompt` — there are zero such callsites in repo (grep verified) | **LOW** | Defaulted-Optional fields keep the existing 3-positional-arg sites valid; regression test in §5.2 confirms. |
| R5 | `board_block` parsing accepts the strawman shape but stores it opaquely — risk of "looks-accepted, silently broken in O3" because semantics aren't validated | **LOW–MEDIUM** | O2 emits a `BoardSpec` whose contents are recorded faithfully; O3 owns validation. Add a Wave 0 doc note in `O2-RESEARCH.md` (this section) flagging that O3 must validate `board { gate … }` predicates against the `TeamConfig` it receives. |
| R6 | The `agent_decl` transformer at `parser.py:707-728` uses `_dc_replace` on `AgentOptions` per known key. The team transformer should follow the same idiom (key → dataclass field) to stay consistent. | **LOW** | Style choice; planner picks the structural shape. |
| R7 | Closed-roster vs open-roster (`backend/frontend/ui/ai` only, or any IDENT?) — unresolved in OPLAN | **LOW** (deferral risk, not technical) | Mark as TBD for SPEC; document both shapes; recommend **open** roster with the four as defaults registered automatically — preserves §2 "extensible" claim, satisfies §5 strawman. |

### Open Questions (resolve at SPEC or discuss-phase)

1. **Roster closed vs open** — `roster engineers { … }` accepts arbitrary role IDENTs, or only `backend/frontend/ui/ai`? OPLAN §2 says "extensible"; §5 strawman shows only the four. Recommend **open**, four-as-defaults.
2. **Scope grammar** — quoted strings (`scope: "src/api/**"`), bare globs (`scope: src/api/**`, requires new terminal), or list-of-globs (`scope: ["src/api/**", "tests/api/**"]`)? Recommend **quoted strings, list allowed**.
3. **`budget` per role semantics** — per-role cap (a ceiling) vs per-card allocation (O3's domain). Recommend **per-role cap**, with the cap MUST be ≤ `ceiling.budget_tokens` (compile-time check).
4. **`net` declaration form** — string `"net"` in `tools: [fs, test, net]` (per strawman) vs explicit boolean `net: true`. Strawman uses the string form; recommend keeping it (consistent with `skill/scope.py:ScopeSpec.net` semantic but expressed inside the `tools` set).
5. **Where does `TeamConfig` live in memory** — a session global, attached to the EM's session record, or held by a new `TeamRunContext` value? O2 produces it; O3 stores it. Recommend defining a new `TeamRunContext(team_config, registry, base_gate)` value object as the explicit O2→O3 hand-off shape — eliminates parameter-list creep in `run_subagent` later.
6. **`gate` predicate language** — `confidence_gate` already exists (`grammar.lark:73` `confidence_gate: expr "@" "p" cmp_op number_literal`). Can the existing rule be re-used inside `gate_decl`? Likely yes (it's a sub-rule of `expr`); confirm at SPEC.

---

## 7. Canonical References

The planner / discuss-phase / implementer MUST read these. Relative to repo root.

**Phase planning context (required):**
- `.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md` — phase boundary + locked decisions
- `.planning/ORCHESTRATION-PLAN.md` — §2 roles, §4 cage invariants, §5 strawman `.voss team{}` block, §6 build reality, §8 decision log, §9 phase decomposition
- `.planning/ROADMAP.md` — Phase O2 entry (lines 49, 1446-1452) and dependency chain
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md` — upstream contract O2 composes with (session-tree + budget fan-out)
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md` — node id scheme, persistence layout, idiomatic patterns to reuse

**Code surface (required for grammar + transformer):**
- `voss/grammar.lark` — top_decl alternation (line 13), agent_decl precedent (lines 161-164), budget literals (lines 85, 191-195), `confidence_gate` (line 73)
- `voss/parser.py:707-728` — `agent_decl` transformer template
- `voss/parser.py:814-825` — `top_decl` / `top_stmt` / `program` / `start` plumbing
- `voss/ast_nodes.py:271-287` — `AgentDecl` + `AgentOptions` template for `TeamDecl` / `TeamConfig`

**Code surface (required for cage compilation):**
- `voss/harness/subagents.py` — `SubagentSpec` (28-32), `SubagentRegistry` (35-49), `default_subagent_registry` (52-75), `agent_task` (78), `run_subagent` (82-156), `attach_subagent_tool` (159-188). The "unknown subagent" envelope at 96-98 is the cage's structural enforcement of "EM cannot invent agents".
- `voss/harness/skill/scope.py` — `ScopeSpec` (22-28), `scope_to_mode` (56-71), `_min_mode` (74-79), `scoped_gate` (82-95). **This is the template for `gate_for_role` (OTEAM-07).**
- `voss/harness/permissions.py` — `Mode` (42), `READ_ONLY`/`WRITE`/`SHELL` (44-46), `mode_allows` (49-65), `PermissionGate` (145-260), project-policy precedence docstring (1-26)
- `voss/harness/tools.py` — `ToolEntry` shape (24-57), `make_toolset` (78-625), `web_fetch` as net-tool exemplar (511-524, 577-579)

**Code surface (referenced for upstream substrate O1):**
- `voss/harness/session_tree.py` — `SessionTreeNode` (47-58), `SessionTreeManager.allocate_child` (151-178), `finalize_node` (100-118), `mutate_envelope` (121-136), error classes (30-44)
- `voss/harness/multiagent.py:140-340` — non-blocking fan-out (M13) context for how the registry is consumed in the multi-agent world; informs but does not block O2

**Call sites to leave untouched in O2 (back-compat anchors):**
- `voss/harness/cli.py:45-48` — subagent imports
- `voss/harness/cli.py:1145-1158` — `/agent spawn` REPL
- `voss/harness/cli.py:1362, 1659, 2540` — three `attach_subagent_tool` sites
- `voss/harness/cli.py:2640-2671` — `subagent` standalone CLI command

---

## Assumptions Log

All claims about *what the cage MUST do* trace to ORCHESTRATION-PLAN.md §4 / §8 (cited inline). All claims about *what the existing code does* are cited file:line and verified by direct read. Items below are `[ASSUMED]` and need user confirmation at SPEC or discuss-phase.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Roster is **open** (any IDENT, four defaults). | Open Q #1 | Wrong closed/open choice forces a grammar redesign mid-implementation. |
| A2 | Scope literals are **quoted strings** (`"src/api/**"`). | §2.1 / Open Q #2 | Wrong form forces grammar terminal addition late. |
| A3 | Per-role `budget` is a **cap** (compile-time check `≤ ceiling.budget_tokens`), not a per-card allocation. | Open Q #3 | Wrong semantics conflict with O3 allocator contract. |
| A4 | `net` is expressed as the string `"net"` inside `tools: […]`. | Open Q #4 | Cosmetic; easy to adjust. |
| A5 | `TeamConfig` and inner value objects are all `frozen=True` dataclasses. | §3.1 | If mutable shape is needed (e.g., for serde round-trip), need a separate frozen/mutable split. |
| A6 | The `agent IDENT { kv }` vs `agent IDENT(params) { stmts }` disambiguation works in Earley with the existing grammar shape. | §2.3 / R1 | If ambiguity surfaces, rename inner keyword to `role`. Strawman's `agent em` becomes `role em`. |
| A7 | Glob containment can be implemented as a heuristic prefix check, not full glob algebra. | R2 | Edge-case false-negatives (compiles a role that O3 then rejects) or false-positives (rejects a legitimate role). Confined to the helper. |
| A8 | The AI role's `net` capability is delivered by extending `PermissionGate` with a per-gate `allow_net` override, not by mutating process-level `allow_net`. | R3 | Wrong choice cross-cuts `voss_runtime._config`. |

---

## Confidence Breakdown

| Area | Level | Reason |
|------|-------|--------|
| Existing code surface (grammar, subagents, permissions, scope analog) | **HIGH** | Every claim cites file:line, directly read |
| Grammar integration plan (productions, transformer shape) | **HIGH–MEDIUM** | Pattern is verbatim from `agent_decl`; ambiguity risk R1 needs a smoke test (MEDIUM until proven) |
| `SubagentSpec` / `TeamConfig` shape | **HIGH** | Direct extension; back-compat verified by grep of all call sites |
| Cage enforcement strategy | **HIGH** | "EM cannot invent agents" already implemented; `frozen=True` makes mutation unrepresentable |
| Per-role gate compilation | **HIGH** | Template (`skill/scope.py:scoped_gate`) is the exact analog; reuse is a one-helper change |
| Derived requirement set (OTEAM-01..08) | **MEDIUM** | Synthesized from OPLAN §5/§8 + CONTEXT only; no SPEC.md yet — discuss-phase or `/gsd-spec-phase O2` must lock |
| Open questions resolution | **LOW** | These are deferred to SPEC/discuss — recommendations are non-binding |

---

*Phase: O2-voss-team-spec-roster*
*Research date: 2026-05-19*
*Valid until: 2026-06-19 (codebase + OPLAN are stable; refresh if `subagents.py`, `permissions.py`, `skill/scope.py`, or `grammar.lark` change materially)*
*Next step: `/gsd-spec-phase O2` (lock OTEAM-01..08 + resolve Open Questions) → `/gsd-discuss-phase O2` → `/gsd-plan-phase O2`*

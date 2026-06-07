# Phase V10: Voss Language as Coordination Spec — Research

**Researched:** 2026-06-07
**Domain:** .voss grammar extension (Lark DSL) + compile-to-config + diagnostics
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Add `principles{}` block — parses standalone AND nested in `team{}`; compiles to the **same V2 `PrinciplesConfig`**; block + `.voss/principles.yml` merge per V2 additive/disable rules.
- Add standalone declarative `gate{}` block — `gate done { require tests_passed; require independent_review; require evidence_refs }` parses + compiles to a config mapping onto **existing** V5/V6 Done-gate predicates.
- Add `memory{}` block — `memory { decisions: "..."; sessions: "..."; semantic: "..." }` parses + compiles to a config carrying the three paths; omitted keys default to convention.
- All three blocks are **compile-to-config only** over shipped runtime. No new gate/memory/principle enforcement logic.
- Each scope/budget/tools/role/unknown-model/unknown-block error emits a diagnostic naming the offending **construct + `file:line` + a one-line fix hint**.
- Diagnostics asserted by a **message-shape test** per error class.
- `ast`/`check`/`compile`/`run` must work on files using new blocks; existing raw-Python parity tests stay green.
- Ship three org-loop examples + **one** end-to-end `team{}` `.voss` that passes `voss check` AND `voss run` drives as a team run on the stub provider.
- Frozen (zero field changes): `RunRecord`, `SessionRecord`, `BudgetScope`.
- No new third-party dependencies.
- Language stays coordination-focused; no general-programming parity.

### Claude's Discretion

- Exact block grammar shapes (lark rule structure, terminal naming) within the coordination-focused constraint.
- Diagnostic formatter implementation (how construct/file:line/fix-hint are assembled).
- Example set content/scenarios beyond the three named categories.
- Internal config object shapes for `gate{}`/`memory{}` (must map onto existing runtime).

### Deferred Ideas (OUT OF SCOPE)

- A separate `review{}` block — use `gate ... require independent_review`.
- New runtime enforcement for gates/memory/principles.
- General-programming language expansion.
- ADE / editor language tooling.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VLANG-01a | `principles{}` grammar block → V2 `PrinciplesConfig` | Grammar slot identified; `PrinciplesConfig` + merge rules fully mapped at `voss/harness/principles.py` |
| VLANG-01b | `gate{}` declarative block → config over V5/V6 gates | `gate_decl` in `board{}` is the analog; Done-gate predicates in `board/gates.py` are the compile target |
| VLANG-01c | `memory{}` grammar block → config over existing memory paths | Path conventions confirmed: `.voss/decisions`, `.voss/sessions`, `.voss-cache/` (codegen default). Config object shape is discretionary. |
| VLANG-02 | Diagnostics bar (construct + file:line + fix hint; message-shape test) | `VossTeamConfigError` already carries `role_span`/`ceiling_span`; `Span` has `file`/`line_start`. Need: construct name field + fix_hint field + test class. |
| (verify) | CLI verbs + raw-Python parity green | All 31 team compile tests GREEN; `voss check` passes on minimal team file; parity suite 7/7 GREEN. |
| VLANG-08 | Org-loop examples + one end-to-end `team{}` file | `voss team run` drives on stub provider; `samples/` is the existing example location; `DeterministicReviewerStub` + `DeterministicEMStub` are the stub stack. |

</phase_requirements>

---

## Summary

V10 is a **delta** on a mostly-shipped base. The grammar (`voss/grammar.lark`), parser transformer (`voss/parser.py`), AST nodes (`voss/ast_nodes.py`), compiler (`voss/harness/team.py`), and CLI verbs (`voss/cli.py`) are all live and green. The three new coordination blocks (`principles{}`, `gate{}` standalone, `memory{}`) follow an exact existing pattern: add a lark rule in `grammar.lark`, add a transformer method in `_Transformer`, add a frozen AST node in `ast_nodes.py`, add a compile branch in `team.py`/`compile_team`, and add a frozen config dataclass in the appropriate harness module.

The diagnostics work is additive: `VossTeamConfigError.__init__` already accepts `role_span`/`ceiling_span` (both are `Span` objects carrying `file` + `line_start`). The upgrade is to add a `construct` name field and a `fix_hint` string, then retrofit all raise sites in `team.py` to populate them, and assert the shape in a new message-shape test.

The end-to-end `voss run` requirement binds onto `voss team run` (not `voss run <file.voss>`): the spec says "drives a team run on the stub provider", and `voss team run` already composes `DeterministicReviewerStub + DeterministicEMStub` on `VOSS_HERMETIC=1`. The end-to-end `.voss` file just needs to survive `voss check` (i.e., parse + analyze without errors) and be loadable by `voss team run --cwd <dir>` where the file lives at `.voss/team.voss`.

**Primary recommendation:** Follow the ceiling/roster/board/ritual extension pattern exactly — grammar rule → transformer method → AST node → compile branch → config dataclass. Upgrade `VossTeamConfigError` with `construct` + `fix_hint` fields and retrofit raise sites. Ship three `samples/` example files + one `team.voss` fixture that passes `voss check` and is runnable via `voss team run` on the stub.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `principles{}` grammar parsing | Language/Grammar (`grammar.lark` + `parser.py`) | — | Same tier as `ceiling_block`/`roster_block`/`ritual_block` |
| `principles{}` compile → `PrinciplesConfig` | Compile layer (`harness/team.py`) | `harness/principles.py` (existing config) | `compile_team` owns all block→config dispatch |
| `gate{}` standalone grammar | Language/Grammar | — | Same tier as `gate_decl` inside `board{}` |
| `gate{}` compile → gate config | Compile layer (`harness/team.py`) | `harness/board/gates.py` (existing predicates) | Maps declared names onto shipped predicate classes |
| `memory{}` grammar | Language/Grammar | — | New block; same grammar slot as `ritual_block` |
| `memory{}` compile → path config | Compile layer (`harness/team.py`) | `harness/cognition.py` + `harness/session.py` (existing paths) | Compile-to-config only; no new memory engine |
| Diagnostics (construct + file:line + fix hint) | Compile layer (`harness/team.py`) | — | `VossTeamConfigError` is already the single error class |
| Example `.voss` files | Language examples (`samples/`) | — | Mirrors `samples/classify.voss` etc. |
| End-to-end team run | CLI (`harness/cli.py` `team run`) | `voss_runtime.providers.stub.StubProvider` | `voss team run` already drives stub stack |

---

## Grammar — Existing Shape and Extension Points

### `grammar.lark` team-block anatomy [VERIFIED: codebase]

Location: `voss/grammar.lark` lines 177-226.

```lark
// Current team_item rule (line 182):
team_item:   ceiling_block | policy_kv | team_agent | roster_block | board_block | ritual_block
```

**Extension point:** Add `principles_block | gate_block | memory_block` to `team_item`, and add parallel top-level rules so `principles{}` parses standalone (in `top_decl`) too:

```lark
// New top_decl extension:
top_decl: ... | principles_block | gate_block | memory_block

// New team_item extension:
team_item: ceiling_block | policy_kv | team_agent | roster_block | board_block | ritual_block
         | principles_block | gate_block | memory_block
```

### `gate_decl` current shape (inside `board{}`) [VERIFIED: codebase]

```lark
// grammar.lark:219
gate_decl:    "gate" IDENT "->" gate_target "{" _NL* gate_predicate (_NL* "," _NL* gate_predicate)* _NL* "}"
gate_target:  IDENT ("(" IDENT ")")?
gate_predicate: expr
```

The **standalone declarative** `gate done { require tests_passed; ... }` needs a distinct grammar rule — different surface from `gate_decl` (which uses `->` target syntax). The canonical form from SPEC is:

```voss
gate done {
  require tests_passed
  require independent_review
  require evidence_refs
}
```

Proposed grammar:

```lark
gate_block:     "gate" IDENT "{" _NL* gate_require (_NL+ gate_require)* _NL* "}"
gate_require:   "require" IDENT
```

This does NOT conflict with the existing `gate_decl` inside `board{}` because `gate_decl` uses `"->"` which is grammatically distinct.

### `ceiling_block` — template for the three new blocks [VERIFIED: codebase]

`ceiling_block` (line 186) is the best template: key/value pairs, closed-set keys validated in the transformer, values as string literals. The `principles{}` block is structurally similar (key: "string"), as is `memory{}`.

---

## AST Nodes — Existing Pattern and New Node Shapes

### Pattern [VERIFIED: codebase `voss/ast_nodes.py`]

All team/coordination nodes follow:

```python
@dataclass(frozen=True, slots=True)
class XyzDecl(Decl):
    field_a: type
    field_b: type
    # tuple fields for sequences; str | None for optionals
```

Key parent chain: `Node → Stmt → Decl`. New nodes must be `Decl` subclasses.

`TeamDecl` (line 337) currently carries:

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
```

**New fields to add to `TeamDecl`:**

```python
principles: "PrinciplesBlockDecl | None" = None
gates: tuple["GateBlockDecl", ...] = ()
memory: "MemoryBlockDecl | None" = None
```

(Default to `None`/`()` so existing files that omit the new blocks compile unchanged — back-compat invariant.)

### New node classes

```python
@dataclass(frozen=True, slots=True)
class PrinciplesBlockDecl(Decl):
    """principles { key: "text"; ... } — compiles to PrinciplesConfig."""
    items: tuple[tuple[str, str], ...]  # (key, text) pairs

@dataclass(frozen=True, slots=True)
class GateBlockDecl(Decl):
    """gate done { require tests_passed; ... } — standalone declarative form."""
    name: str                           # e.g. "done"
    requires: tuple[str, ...]           # e.g. ("tests_passed", "independent_review", "evidence_refs")

@dataclass(frozen=True, slots=True)
class MemoryBlockDecl(Decl):
    """memory { decisions: "..."; sessions: "..."; semantic: "..." }"""
    decisions: str | None = None
    sessions: str | None = None
    semantic: str | None = None
```

---

## Compile Layer — `voss/harness/team.py`

### `compile_team` function (line 644) [VERIFIED: codebase]

The existing dispatch:

```python
def compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]:
    # ceiling -> TeamCeiling
    # agents -> SubagentSpec (registry)
    # rosters -> SubagentSpec (registry)
    # board -> BoardSpec
    # rituals -> RitualSpec
    return config, registry
```

**Extension:** Add compile branches for the three new fields:

```python
# principles block → PrinciplesConfig
principles_config: PrinciplesConfig | None = None
if decl.principles is not None:
    # Merge block items with .voss/principles.yml per V2 rules
    block_layer = _ProjectLayer(decl.principles.items, ())
    principles_config = merge_principles(DEFAULT_PRINCIPLES, block_layer)

# gate blocks → GateConfig (new frozen dataclass)
gate_configs = tuple(_compile_gate(g) for g in decl.gates)

# memory block → MemoryConfig (new frozen dataclass)
memory_config = _compile_memory(decl.memory)
```

`TeamConfig` gets three new fields (all defaulted for back-compat):

```python
@dataclass(frozen=True, slots=True)
class TeamConfig:
    # ... existing fields ...
    principles: PrinciplesConfig | None = None      # NEW
    gate_configs: tuple["GateConfig", ...] = ()     # NEW
    memory: "MemoryConfig | None" = None            # NEW
```

### V2 `PrinciplesConfig` merge path [VERIFIED: codebase `voss/harness/principles.py`]

The existing `merge_principles(defaults, layer)` at line 154 is exactly the function needed. The `_ProjectLayer` dataclass at line 59 accepts `items: tuple[tuple[str, str | None], ...]` and `disable: tuple[str, ...]`. A `principles{}` block compiles to a `_ProjectLayer` (items from block kvs, disable empty) and merges against `DEFAULT_PRINCIPLES`.

**Key insight:** The caller at runtime must decide whether to also load `.voss/principles.yml` and stack both layers, or treat the block as the project layer itself. The spec says "block + `.voss/principles.yml` merge per V2 additive/disable rules". The existing `load_principles(cwd)` returns a `_ProjectLayer` from the file. The block is also a `_ProjectLayer`. The natural composition: block items + file items merged as a two-layer stack, with block taking precedence.

---

## Done-Gate Predicates — Mapping for `gate{}` Config [VERIFIED: codebase]

`voss/harness/board/gates.py` lines 34-213 define 8 predicate classes. The three require names from SPEC map to:

| `.voss` `require` keyword | Shipped predicate class | `name` attribute | Location |
|--------------------------|-------------------------|------------------|----------|
| `tests_passed` | `tests_pass` | `"tests"` | `gates.py:137` |
| `independent_review` | `a_verification_passes` | `"reviewer_a"` | `gates.py:107` |
| `evidence_refs` | `b_passes` | `"reviewer_b"` | `gates.py:122` |

The full V6 Done gate uses `_CODE_DONE_PREDICATES = (scope_clean(), a_verification_passes(), b_passes(), tests_pass())` at line 185.

**Internal `GateConfig` shape** (discretionary — compile-to-config only):

```python
@dataclass(frozen=True, slots=True)
class GateConfig:
    name: str                       # "done"
    requires: frozenset[str]        # {"tests_passed", "independent_review", "evidence_refs"}
```

The config is stored on `TeamConfig.gate_configs`. No new enforcement — the shipped board uses `Gates.build_default()` directly; `GateConfig` is informational only.

---

## Memory Paths — V4/Cognition Conventions [VERIFIED: codebase]

Three path conventions in use:

| Key | Convention | Source |
|-----|-----------|--------|
| `decisions` | `<cwd>/.voss/decisions/` | `voss/harness/recorder.py:448` |
| `sessions` | `<cwd>/.voss/sessions/` | `voss/harness/session.py:57-58` via `_sessions_dir` |
| `semantic` | `<cwd>/.voss-cache/` (chromadb default: `"chroma"`) | `voss_runtime/memory/semantic.py:16` `persist_dir="chroma"` |

`voss/harness/cognition.py` defines:
- `voss_dir(cwd) -> cwd / ".voss"` (line 71)
- `cache_dir(cwd) -> cwd / ".voss-cache"` (line 75)

**Default values for `MemoryConfig`** (when key is omitted in block):

```python
@dataclass(frozen=True, slots=True)
class MemoryConfig:
    decisions: str = ".voss/decisions"
    sessions:  str = ".voss/sessions"
    semantic:  str = ".voss-cache/semantic"
```

---

## `VossTeamConfigError` — Diagnostics Upgrade [VERIFIED: codebase]

### Current shape (`voss/harness/team.py:33`) [VERIFIED]

```python
class VossTeamConfigError(Exception):
    def __init__(self, message: str, *, role_span: Span | None = None,
                 ceiling_span: Span | None = None) -> None:
        super().__init__(message)
        self.role_span = role_span
        self.ceiling_span = ceiling_span
```

`Span` is a frozen dataclass at `voss/ast_nodes.py:7`:

```python
@dataclass(frozen=True, slots=True)
class Span:
    file: str
    line_start: int
    col_start: int
    ...
```

**Live proof:** Raising `VossTeamConfigError` on a budget overage produces:
```
role_span: Span(file='test.voss', line_start=4, col_start=5, ...)
```
File and line are already available from `Span`. [VERIFIED: interactive test above]

### Target shape (VLANG-02)

```python
class VossTeamConfigError(Exception):
    def __init__(
        self,
        message: str,
        *,
        construct: str = "",           # NEW — "scope", "budget", "tools", "role", "model", "block"
        fix_hint: str = "",            # NEW — one-line actionable hint
        role_span: Span | None = None,
        ceiling_span: Span | None = None,
    ) -> None:
        super().__init__(message)
        self.construct = construct
        self.fix_hint = fix_hint
        self.role_span = role_span
        self.ceiling_span = ceiling_span
```

All existing callers that omit `construct`/`fix_hint` are backward-compatible (both default to `""`). The message-shape test asserts that each error class (scope, budget, tools, role, model, block) raises with `construct != ""` and `fix_hint != ""`.

### Raise sites to retrofit (in `team.py`) [VERIFIED: codebase]

There are 14 `raise VossTeamConfigError(...)` sites in `team.py`. Key categories:

| Line(s) | Error category | `construct` value | Fix hint example |
|---------|---------------|------------------|----|
| 395, 399 | scope list item | `"scope"` | `"scope list entries must be string literals"` |
| 413 | budget type | `"budget"` | `"use a token budget like: budget: 100 tokens"` |
| 428, 434 | tools type | `"tools"` | `"tools must be a string literal or list: tools: [\"fs\", \"test\"]"` |
| 445 | mode value | `"mode"` | `"mode must be one of: plan, edit, auto"` |
| 450 | mode type | `"mode"` | `"mode must be a string literal"` |
| 467 | model tier | `"model"` | `"configure the tier in [model_tiers]"` |
| 492 | model type | `"model"` | `"model must be a string literal or tier keyword"` |
| 525, 535 | scope overflow | `"scope"` | `"role scope must be within the ceiling scope globs"` |
| 606, 618 | agent scope/budget | `"scope"/"budget"` | same as roster |
| 648 | missing ceiling | `"ceiling"` | `"add a ceiling { budget: N tokens } block to team"` |

### `file:line` in formatted output

The planner must design a `format_diagnostic()` method or property on `VossTeamConfigError` that renders `"{file}:{line}"` from `role_span` (falling back to `ceiling_span`, falling back to `"<unknown>"`). The Lark parser already stores `line_start` on every `Span` via `propagate_positions=True` (confirmed at `parser.py:135` and `parser.py:145`).

---

## CLI Verbs — How New Blocks Surface [VERIFIED: codebase]

### `voss ast <file.voss>` (`voss/cli.py:430`)

Calls `_parse_file(source)` → `to_dict(program)`. The `ast_serializer.py` `to_dict` will need to handle the three new node classes (standard extension: add a new match arm in the serializer). The planner should include this in the AST serializer task.

### `voss check <file.voss>` (`voss/cli.py:341`)

Calls `parse` → `analyze`. The analyzer does NOT currently handle `TeamDecl` (confirmed: zero references to `TeamDecl` in `voss/analyzer.py`). This means `voss check` on a team file today just parses it without semantic analysis. After V10, `voss check` should surface `VossTeamConfigError`s from `compile_team`. The two options:

1. **Light option (preferred, coordination-focused):** In `voss/cli.py:check`, after `analyze`, if the file contains `TeamDecl` nodes, call `compile_team(team_decl)` and convert `VossTeamConfigError` to `Diagnostic` output — same path as `voss team check` but integrated into the standard `check` verb.
2. **Heavy option:** Wire `compile_team` into the `Analyzer` class. This is wider scope than V10 needs.

The `voss team check` command (`harness/cli.py:3888`) already does parse→compile_team and works correctly. The SPEC acceptance says "new blocks inspectable via `voss ast` and validated via `voss check`" — the simplest path is that `voss check` on a team file with new blocks exits 0 (parse succeeds, no analysis error), and `voss team check` handles semantic validation. The planner should clarify this but the safest V10 interpretation is: **`voss check` must not crash on files using new blocks** (parse must work), while `voss team check` is the semantic validation verb.

### `voss run <file.voss>` vs `voss team run` [VERIFIED: codebase]

`voss run` (`cli.py:293`) compiles the `.voss` to Python and executes the generated Python. It does NOT drive a team run — it runs the generated agent script via subprocess. The SPEC acceptance criterion for VLANG-08 ("voss run drives a team run on the stub provider") means `voss team run`, not `voss run`. Confirmed: `voss team run` loads `.voss/team.voss`, calls `compile_team`, builds the full stub stack, and runs the EM loop.

---

## Raw-Python Parity Tests (M3/M4) [VERIFIED: codebase]

### Location

- `tests/harness/test_voss_loop_parity.py` — M4 D-11 loop parity (same fixture, two backends, identical result)
- `tests/codegen/test_examples.py` — codegen examples including `samples/*.voss`
- `tests/parser/test_team_grammar.py` — team grammar parsing acceptance
- `tests/voss/test_team_compile.py` — `compile_team` acceptance
- `tests/voss/test_team_backcompat_regression.py` — V3 back-compat locks

### Current passing status

All of the above pass clean: 31/31 team tests, 7/7 parity suite, 36/36 principles+team_check tests. [VERIFIED: ran above]

### Regression invariant

V10 changes to `grammar.lark`, `ast_nodes.py`, `parser.py`, and `team.py` must leave these suites green. The back-compat rule: new `TeamDecl` fields must have Python defaults so existing parsed `TeamDecl` objects that omit the new blocks compile unchanged.

---

## Examples — Where They Live and How `voss run` Works [VERIFIED: codebase]

### Existing example locations

- `samples/classify.voss`, `samples/support.voss`, `samples/research.voss` — the three LANG-09 samples; they use the agent/prompt/fn language features, not team features.
- `tests/parser/examples/team_strawman.voss` — the parser grammar acceptance fixture; NOT a runnable example.

### Where org-loop examples should live

Follow the `samples/` pattern. New files: `samples/team-orchestration.voss`, `samples/reviewer-split.voss`, `samples/audit-gates.voss`.

The end-to-end runnable team file should live at `.voss/team.voss` in a fixture directory, OR the test should `tmp_path`-construct it. The `voss team run` command loads from `<cwd>/.voss/team.voss` by default (confirmed: `harness/cli.py:4046`).

### Stub provider entry point [VERIFIED: codebase]

- `voss_runtime.providers.stub.StubProvider` — deterministic in-memory provider at `voss_runtime/providers/stub.py:23`.
- Activated by: `VOSS_HERMETIC=1` env (sets stub in `voss_runtime/providers/__init__.py:21`).
- Also activated when `auth.resolve(preference="auto").source == "none"` (no creds detected).
- `voss team run` on a machine with no API creds auto-activates stub (confirmed: `harness/cli.py:3268` `--stub` flag, and fallback in `cli.py:317`).

The `DeterministicEMStub` and `DeterministicReviewerStub` are used within `voss team run` itself (from `harness/cli.py:4067-4071`).

---

## Common Pitfalls

### Pitfall 1: `TeamDecl` field addition breaks frozen back-compat

**What goes wrong:** Adding `principles`, `gates`, `memory` as required fields to `TeamDecl` breaks all existing tests that construct or parse `TeamDecl` without those fields.
**Why it happens:** `@dataclass(frozen=True, slots=True)` — required field after optional is a Python error.
**How to avoid:** All new `TeamDecl` fields MUST have defaults (`= None` or `= ()`). In Python dataclasses, defaulted fields must come after all non-defaulted fields — check current `TeamDecl` field order and insert new defaults AFTER the existing `decorators: tuple[Decorator, ...] = ()`.
**Warning signs:** `TypeError: non-default argument ... follows default argument` at import.

### Pitfall 2: `grammar.lark` keyword collision with `IDENT`

**What goes wrong:** `require`, `principles`, `memory`, `gate` (standalone) parse as `IDENT` instead of keywords, causing Earley grammar ambiguity.
**Why it happens:** Lark's dynamic lexer with Earley — new keywords that aren't excluded from `IDENT` become ambiguous (same issue as `similar`/`_` resolved in the existing grammar via `SIMILAR`/`UNDERSCORE` terminals).
**How to avoid:** For any new keyword used as a terminal in a rule where `IDENT` is also valid, either (a) use it inline as a quoted string literal `"require"` / `"principles"` / `"memory"` (Earley will prioritize the literal match), or (b) promote it to a priority terminal like `SIMILAR`. Since `require`, `principles`, `memory`, `gate` appear in dedicated non-overlapping grammar positions, inline string literals are safe.
**Warning signs:** `test_ambiguity` (the existing guard test) fails, or `parse("principles { ... }")` produces unexpected tokens.

### Pitfall 3: `ast_serializer.py` not updated for new nodes

**What goes wrong:** `voss ast <file>` crashes with `UnhandledType` or similar when the file contains new blocks.
**Why it happens:** `to_dict` in `voss/ast_serializer.py` dispatches on node type — if new `PrinciplesBlockDecl`/`GateBlockDecl`/`MemoryBlockDecl` are not handled, it falls through.
**How to avoid:** Add a match arm in `ast_serializer.py` for each new node class alongside the grammar/parser/AST changes (same wave).
**Warning signs:** `voss ast samples/team-orchestration.voss` crashes or silently omits new blocks from the JSON output.

### Pitfall 4: `compile_team` called without cwd for `principles{}` merge

**What goes wrong:** Merging `principles{}` block with `.voss/principles.yml` requires `cwd` to load the file, but `compile_team(decl)` currently takes only a `TeamDecl` (no `cwd`).
**Why it happens:** The compile step is designed to be pure/offline; file I/O lives in load steps.
**How to avoid:** Two options — (a) `compile_team` accepts optional `cwd: Path | None = None`; when present, loads and merges; when absent, block items only. (b) Pre-load the file layer and pass it as a separate argument. Option (a) is the simpler extension.
**Warning signs:** Principles merge tests fail because `load_principles(cwd)` is never called.

### Pitfall 5: Diagnostics `file:line` unavailable at error raise sites that don't have a `Span`

**What goes wrong:** Several `VossTeamConfigError` raise sites (e.g. `_parse_budget_value`, `_parse_tools_value`) are helper functions that don't receive a `Span` argument — they raise on value type errors with no position info.
**Why it happens:** Helper functions are called from the transformer which has the span, but the helpers themselves don't thread it.
**How to avoid:** Thread `Span | None = None` into the helper signatures; raise with `role_span=span` at each call site. Alternatively, only add `construct`/`fix_hint` for now (the span is already set at the outer raise sites that wrap the helpers).
**Warning signs:** Message-shape test fails because `role_span is None` and `file:line` cannot be formatted.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Principles merge logic | Custom key-merge code | `merge_principles(DEFAULT_PRINCIPLES, layer)` in `voss/harness/principles.py:154` | V2-tested merge with additive/disable rules; key-agnostic |
| Principles file loading | Custom YAML loader | `load_principles(cwd)` in `principles.py:70` | Handles missing file, invalid YAML, disable list, null values |
| Done-gate predicate lookup | Custom predicate registry | Import `tests_pass`, `a_verification_passes`, `b_passes` from `board/gates.py` | These are the shipped Done-gate predicates; don't alias |
| Memory path conventions | Hard-coding new path logic | `cognition.voss_dir(cwd)` → `.voss/`, `cognition.cache_dir(cwd)` → `.voss-cache/` | Single source of truth |
| Span extraction from parser | Custom line-number tracking | `propagate_positions=True` is already set; `_span(meta, file)` gives `Span` with `line_start` | Already works — just thread `Span` into error raise sites |

---

## Code Examples

### Pattern: Adding a transformer method (analog: `ceiling_block`)

```python
# voss/parser.py — in class _Transformer
def principles_block(self, meta, children):
    # children: list of (key, value) tuples from principles_kv
    items: list[tuple[str, str]] = []
    seen: set[str] = set()
    for c in children:
        if not (isinstance(c, tuple) and len(c) == 2):
            continue
        key, val = c
        if key in seen:
            raise VossParseError(
                file=self.file,
                line=meta.line,
                col=meta.column,
                expected=[f"unique key in principles block"],
                got=f"duplicate key {key!r}",
            )
        seen.add(key)
        if not isinstance(val, StringLit):
            raise VossParseError(
                file=self.file,
                line=meta.line,
                col=meta.column,
                expected=["string literal for principle text"],
                got=type(val).__name__,
            )
        items.append((key, val.value))
    return PrinciplesBlockDecl(span=_span(meta, self.file), items=tuple(items))

def principles_kv(self, meta, children):
    key = str(children[0])  # IDENT
    val = children[1]       # string_lit
    return (key, val)
```

### Pattern: `VossTeamConfigError` with construct + fix_hint

```python
# voss/harness/team.py
raise VossTeamConfigError(
    f"role {role_name!r} budget {budget} exceeds ceiling budget_tokens {ceiling.budget_tokens}",
    construct="budget",
    fix_hint=f"lower budget to ≤ {ceiling.budget_tokens} tokens, or raise the ceiling",
    role_span=role_decl_span,
    ceiling_span=ceiling_ast.span if ceiling_ast else None,
)
```

### Pattern: `compile_team` branch for `principles{}`

```python
# voss/harness/team.py — inside compile_team()
principles_config: PrinciplesConfig | None = None
if decl.principles is not None:
    from .principles import DEFAULT_PRINCIPLES, _ProjectLayer, merge_principles
    block_layer = _ProjectLayer(decl.principles.items, ())
    if cwd is not None:
        file_layer = load_principles(cwd)
        # Merge: defaults + file layer + block layer. Block takes precedence.
        # Simplest approach: merge defaults+file first, then treat block as override layer.
        base = merge_principles(DEFAULT_PRINCIPLES, file_layer)
        # Second merge: treat base as new defaults, block as new project layer.
        principles_config = merge_principles(base.principles, block_layer)
    else:
        principles_config = merge_principles(DEFAULT_PRINCIPLES, block_layer)
```

### End-to-end team file skeleton

```voss
# .voss/team.voss — V10 end-to-end example
team Engineering {
  ceiling {
    budget: 200k tokens
    scope: "src/**"
    latency: 3600s
  }

  principles {
    diff: "Make the smallest diff that solves the task."
    evidence: "No factual claim without evidence."
  }

  gate done {
    require tests_passed
    require independent_review
    require evidence_refs
  }

  memory {
    decisions: ".voss/decisions"
    sessions: ".voss/sessions"
    semantic: ".voss-cache/semantic"
  }

  roster engineers {
    backend {
      model: "cheap"
      scope: "src/**"
      tools: ["fs", "test"]
    }
    reviewer {
      model: "strong"
      scope: "src/**"
      tools: ["fs", "git"]
    }
  }
}
```

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed: `.venv/bin/python -m pytest`) |
| Config file | `pyproject.toml` (pytest settings) |
| Quick run command | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/test_team_compile.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/parser/ tests/voss/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| VLANG-01a | `principles{}` standalone parses → `PrinciplesBlockDecl` | unit/parser | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py::test_principles_block_parses -x` | ❌ Wave 0 |
| VLANG-01a | `principles{}` nested in `team{}` parses | unit/parser | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py::test_team_with_principles_block -x` | ❌ Wave 0 |
| VLANG-01a | `principles{}` block + `.voss/principles.yml` merge | unit/compile | `.venv/bin/python -m pytest tests/voss/test_team_principles_block.py -x` | ❌ Wave 0 |
| VLANG-01b | `gate done { require ... }` parses → `GateBlockDecl` | unit/parser | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py::test_gate_block_parses -x` | ❌ Wave 0 |
| VLANG-01b | `gate done {...}` compiles to `GateConfig` | unit/compile | `.venv/bin/python -m pytest tests/voss/test_team_gate_block.py -x` | ❌ Wave 0 |
| VLANG-01c | `memory{}` parses → `MemoryBlockDecl` | unit/parser | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py::test_memory_block_parses -x` | ❌ Wave 0 |
| VLANG-01c | `memory{}` defaults when keys omitted | unit/compile | `.venv/bin/python -m pytest tests/voss/test_team_memory_block.py -x` | ❌ Wave 0 |
| VLANG-02 | Each error class has construct + file:line + fix_hint | unit/compile | `.venv/bin/python -m pytest tests/voss/test_team_diagnostic_shape.py -x` | ❌ Wave 0 |
| verify | Existing parity tests pass after grammar changes | regression | `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py -x -q` | ✅ |
| VLANG-08 | Examples `voss check` clean | smoke | `.venv/bin/python -m pytest tests/voss/test_org_loop_examples.py -x` | ❌ Wave 0 |
| VLANG-08 | End-to-end team file passes `voss team check` | integration | `.venv/bin/python -m pytest tests/harness/test_e2e_team_run.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/parser/ tests/voss/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py tests/harness/test_voss_loop_parity.py -q`
- **Phase gate:** Full suite above green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/parser/test_team_grammar.py` — add cases: `test_principles_block_parses`, `test_team_with_principles_block`, `test_gate_block_parses`, `test_memory_block_parses`
- [ ] `tests/voss/test_team_principles_block.py` — compile + merge tests
- [ ] `tests/voss/test_team_gate_block.py` — `GateConfig` compile tests
- [ ] `tests/voss/test_team_memory_block.py` — `MemoryConfig` compile + defaults tests
- [ ] `tests/voss/test_team_diagnostic_shape.py` — message-shape tests (VLANG-02)
- [ ] `tests/voss/test_org_loop_examples.py` — `voss check` on all three org-loop examples
- [ ] `tests/harness/test_e2e_team_run.py` — `voss team run` on end-to-end team file (stub)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv/bin/python` | All tests | ✓ | 3.13 | — |
| `lark` | grammar.lark parsing | ✓ | confirmed (parser.py imports it) | — |
| `voss_runtime.providers.stub.StubProvider` | VLANG-08 end-to-end | ✓ | confirmed in codebase | — |
| `pyyaml` | principles.yml loading | ✓ | confirmed (principles.py imports yaml) | — |

No missing dependencies that block execution.

---

## Security Domain

The new blocks are compilation/config only. No new network calls, no new file writes beyond what `voss team run` already does. The `memory{}` block introduces declared paths but does NOT write to them — config only.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `VossParseError` + `VossTeamConfigError` on malformed block values |
| V4 Access Control | no | No new access control surface |
| V2 Authentication | no | — |
| V6 Cryptography | no | — |

### Threat pattern for `memory{}` path values

The `decisions`/`sessions`/`semantic` values are user-declared strings compiled into `MemoryConfig`. They are stored as config fields, not used for file I/O by V10. Future consumers should apply path-traversal guards before using these values to open files (consistent with `board/cli_view.py:85` which guards `..` / `/` traversal).

---

## Open Questions

1. **`voss check` semantic integration for team files**
   - What we know: `voss check` today calls `analyze()` which ignores `TeamDecl`; `voss team check` does semantic validation via `compile_team`.
   - What's unclear: Should V10 integrate `compile_team` into `voss check` so `voss check my-team.voss` catches config errors, or is `voss team check` the semantic path?
   - Recommendation: Keep them separate for V10 (lowest risk); `voss check` validates parse/analysis only; `voss team check` validates compile. The SPEC says "validated via `voss check`" but the simplest reading is that the file must not crash `voss check` (parse succeeds) — the planner should lock this interpretation.

2. **`principles{}` merge order when both block and `.voss/principles.yml` exist**
   - What we know: V2 merge is additive/disable from a project layer onto defaults; `merge_principles(defaults, layer)` is the function.
   - What's unclear: Is the block the project layer (replacing the file), or do both stack? The SPEC says "merge per V2 additive/disable rules" which implies both sources are active.
   - Recommendation: Treat block items as one layer and file items as another; compose them: `merge(merge(DEFAULT_PRINCIPLES, file_layer), block_layer)`. Block overrides file which overrides defaults.

3. **`TeamDecl.gates` as a tuple vs single optional**
   - What we know: SPEC mentions `gate done { ... }` — a single gate. But having a tuple allows multiple gate declarations (e.g., `gate review { ... }` in the future).
   - Recommendation: Use `gates: tuple[GateBlockDecl, ...] = ()` for forward-compatibility; the single-gate case is just a length-1 tuple.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `voss run <file.voss>` VLANG-08 acceptance criterion means `voss team run`, not the codegen-based `voss run` | CLI Verbs section | If wrong, the end-to-end example would need to be a codegen-compiled `.voss` program that calls team machinery — significantly more complex |
| A2 | The `samples/` directory is the correct location for org-loop examples | Examples section | If wrong, examples might go in `tests/parser/examples/` or a new `examples/` dir |
| A3 | `voss check` does not need to call `compile_team` for VLANG-08 acceptance — parse-only is sufficient | CLI Verbs section | If wrong, `voss/cli.py:check` needs a new team-compile branch |

---

## Sources

### Primary (HIGH confidence)
- `voss/grammar.lark` — full grammar, team block rules
- `voss/ast_nodes.py` — all AST node shapes
- `voss/parser.py` — Lark transformer and span propagation
- `voss/harness/team.py` — `compile_team`, `VossTeamConfigError`, config dataclasses
- `voss/harness/principles.py` — `PrinciplesConfig`, `merge_principles`, `load_principles`, `_ProjectLayer`
- `voss/harness/board/gates.py` — Done-gate predicates: `tests_pass`, `a_verification_passes`, `b_passes`
- `voss/harness/cognition.py` — `voss_dir`, `cache_dir` path conventions
- `voss/harness/recorder.py:448` — `.voss/decisions/` path
- `voss/harness/session.py:57` — `.voss/sessions/` path
- `voss_runtime/providers/stub.py` — `StubProvider` entry point
- `voss/cli.py` — `compile`, `run`, `check`, `ast` wiring
- `voss/harness/cli.py:3888,4021` — `team check`, `team run` wiring

### Secondary (MEDIUM confidence)
- `tests/parser/test_team_grammar.py` — grammar acceptance fixture, extension model
- `tests/voss/test_team_compile.py` — compile acceptance, informs test scaffold pattern
- `tests/harness/test_principles_config.py` — principles test pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all extension points verified against live codebase
- Architecture: HIGH — grammar/AST/compile pipeline fully mapped with line numbers
- Pitfalls: HIGH — identified from direct code inspection + live test run

**Research date:** 2026-06-07
**Valid until:** 2026-07-07 (stable codebase; grammar/AST patterns unlikely to change)

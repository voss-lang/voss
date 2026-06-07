# Phase V10: Voss Language as Coordination Spec — Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/grammar.lark` | config | transform | self (extend `team_item`, `ceiling_block`) | exact |
| `voss/ast_nodes.py` | model | transform | self (`CeilingDecl`, `RosterDecl`, `RitualDecl`) | exact |
| `voss/parser.py` | transformer | transform | self (`ceiling_block`, `ritual_block` methods) | exact |
| `voss/harness/team.py` | service | CRUD | self (`compile_team`, existing `VossTeamConfigError`) | exact |
| `tests/parser/test_team_grammar.py` | test | request-response | self (extend existing test file) | exact |
| `tests/voss/test_team_principles_block.py` | test | request-response | `tests/harness/test_principles_config.py` | role-match |
| `tests/voss/test_team_gate_block.py` | test | request-response | `tests/voss/test_team_compile.py` | role-match |
| `tests/voss/test_team_memory_block.py` | test | request-response | `tests/voss/test_team_compile.py` | role-match |
| `tests/voss/test_team_diagnostic_shape.py` | test | request-response | `tests/voss/test_team_backcompat_regression.py` | role-match |
| `tests/voss/test_org_loop_examples.py` | test | request-response | `tests/voss/test_team_compile.py` | role-match |
| `tests/harness/test_e2e_team_run.py` | test | event-driven | `voss/harness/cli.py:4021` (`team_run_cmd`) | role-match |
| `samples/team-orchestration.voss` + `reviewer-split.voss` + `audit-gates.voss` | config | transform | `samples/classify.voss`, `tests/parser/examples/team_strawman.voss` | role-match |

---

## Pattern Assignments

### `voss/grammar.lark` — extend `team_item` + add three block rules

**Analog:** `voss/grammar.lark` lines 177–226 (existing team block rules)

**Extension point — `team_item` rule** (line 182):
```lark
// CURRENT (line 182):
team_item:   ceiling_block | policy_kv | team_agent | roster_block | board_block | ritual_block

// V10 TARGET — append three new alternatives:
team_item:   ceiling_block | policy_kv | team_agent | roster_block | board_block | ritual_block
           | principles_block | gate_block | memory_block

// Also extend top_decl (wherever it lists team_decl) to allow standalone:
// top_decl: ... | principles_block | gate_block | memory_block
```

**Template: `ceiling_block`** (lines 186–189) — key/value, closed-set keys, string/literal values:
```lark
ceiling_block: "ceiling" "{" _NL* ceiling_kv ((_NL* "," _NL* | _NL+) ceiling_kv)* _NL* ","? _NL* "}"
ceiling_kv:    CEILING_KEY ":" ceiling_value
CEILING_KEY:   "budget" | "scope" | "latency"
ceiling_value: budget_literal | STRING | list_lit
```

**New `principles_block`** — follow `ceiling_block` shape exactly (key: STRING pairs):
```lark
principles_block: "principles" "{" _NL* principles_kv ((_NL* "," _NL* | _NL+) principles_kv)* _NL* ","? _NL* "}"
principles_kv:   IDENT ":" STRING
```

**New `gate_block`** — standalone declarative form (distinct from `gate_decl` which uses `"->"` inside `board{}`):
```lark
gate_block:    "gate" IDENT "{" _NL* gate_require (_NL+ gate_require)* _NL* "}"
gate_require:  "require" IDENT
```

**New `memory_block`** — follow `ceiling_block` shape (closed-set keys, string values):
```lark
memory_block:  "memory" "{" _NL* memory_kv ((_NL* "," _NL* | _NL+) memory_kv)* _NL* ","? _NL* "}"
memory_kv:     MEMORY_KEY ":" STRING
MEMORY_KEY:    "decisions" | "sessions" | "semantic"
```

**Keyword collision guard:** Use quoted string literals `"principles"`, `"gate"`, `"memory"`, `"require"` inline — Earley prioritizes literals over IDENT in non-overlapping positions. Do NOT create new IDENT-conflicts.

---

### `voss/ast_nodes.py` — three new node classes + `TeamDecl` field additions

**Analog:** `voss/ast_nodes.py` lines 291–334 (`CeilingDecl`, `RosterDecl`, `RitualDecl`)

**Node class pattern** (lines 291–313):
```python
# Every team/coordination node: @dataclass(frozen=True, slots=True), Decl subclass,
# tuple for sequences, str | None for optionals, span: Span first (inherited).
@dataclass(frozen=True, slots=True)
class CeilingDecl(Decl):
    budget: int | None
    scope: tuple[str, ...]
    latency_seconds: int | None

@dataclass(frozen=True, slots=True)
class RitualDecl(Decl):
    name: str
    kvs: tuple[tuple[str, object], ...]
```

**`TeamDecl` current shape** (lines 337–345) — new fields MUST come after `decorators` (last defaulted field):
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
    # V10 — append AFTER decorators (back-compat: all defaulted):
    # principles: "PrinciplesBlockDecl | None" = None
    # gates: "tuple[GateBlockDecl, ...]" = ()
    # memory: "MemoryBlockDecl | None" = None
```

**New node classes to add after `TeamDecl`:**
```python
@dataclass(frozen=True, slots=True)
class PrinciplesBlockDecl(Decl):
    """principles { key: "text"; ... } — compiles to PrinciplesConfig."""
    items: tuple[tuple[str, str], ...]   # (key, text) pairs

@dataclass(frozen=True, slots=True)
class GateBlockDecl(Decl):
    """gate done { require tests_passed; ... } — standalone declarative form."""
    name: str                            # e.g. "done"
    requires: tuple[str, ...]            # e.g. ("tests_passed", "independent_review")

@dataclass(frozen=True, slots=True)
class MemoryBlockDecl(Decl):
    """memory { decisions: "..."; sessions: "..."; semantic: "..." }"""
    decisions: str | None = None
    sessions: str | None = None
    semantic: str | None = None
```

**Back-compat invariant:** All three new `TeamDecl` fields must have Python defaults (`= None` or `= ()`). Python dataclasses require defaulted fields to follow non-defaulted ones. Insert after `decorators: tuple[Decorator, ...] = ()`.

**AST serializer note:** `voss/ast_serializer.py:to_dict` (lines 9–42) is fully generic — it dispatches via `isinstance(node, Node)` + `fields(node)`. No new match arm needed; new node classes are handled automatically.

---

### `voss/parser.py` — three new transformer methods + `team_decl` extension

**Analog:** `voss/parser.py` lines 877–1157 (ceiling/roster/gate/ritual block methods)

**`_span` helper** (lines 142–147) — use for every new node:
```python
def _span(meta, file: str) -> Span:
    return Span(
        file=file,
        line_start=meta.line, col_start=meta.column,
        line_end=meta.end_line, col_end=meta.end_column,
    )
```

**`ceiling_block` transformer pattern** (lines 877–942) — key/value dedup + type validation + node construction:
```python
def ceiling_block(self, meta, children):
    seen: dict[str, object] = {}
    for c in children:
        if not (isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], str)):
            continue
        key, val = c
        if key in seen:
            raise VossParseError(
                file=self.file, line=meta.line, col=meta.column,
                expected=[f"unique `{key}` key in `ceiling` block"],
                got=f"duplicate `{key}` in ceiling block",
            )
        seen[key] = val
    # ... validate types per key ...
    return CeilingDecl(span=_span(meta, self.file), budget=budget, scope=scope, latency_seconds=latency_seconds)

def ceiling_kv(self, meta, children):
    key = str(children[0])
    val = children[1]
    if key not in ("budget", "scope", "latency"):
        raise VossParseError(...)
    return (key, val)
```

**`ritual_block` pattern** (lines 1124–1145) — closest to `memory_block`/`principles_block` (name + kv list, duplicate detection):
```python
def ritual_block(self, meta, children):
    ritu_name = str(children[0])
    seen: set[str] = set()
    kvs: list[tuple[str, object]] = []
    for c in children[1:]:
        if isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], str):
            k, v = c
            if k in seen:
                raise VossParseError(
                    file=self.file, line=meta.line, col=meta.column,
                    expected=[f"unique `{k}` in ritual block"],
                    got="duplicate key",
                )
            seen.add(k)
            kvs.append((k, v))
    return RitualDecl(span=_span(meta, self.file), name=ritu_name, kvs=tuple(kvs))
```

**`team_decl` dispatch extension** (lines 800–869) — add new isinstance branches:
```python
# Current dispatch (lines 812–848):
for item in items:
    if isinstance(item, CeilingDecl):
        ceiling = item
    elif isinstance(item, tuple) and item and item[0] == "_team_policy":
        policy_obj = item[1]
    elif isinstance(item, TeamAgentDecl):
        agents.append(item)
    elif isinstance(item, RosterDecl):
        rosters.append(item)
    elif isinstance(item, BoardDecl):
        board = item
    elif isinstance(item, RitualDecl):
        rituals.append(item)
# V10: add three more elif branches before the closing block:
#   elif isinstance(item, PrinciplesBlockDecl): principles = item
#   elif isinstance(item, GateBlockDecl):       gates.append(item)
#   elif isinstance(item, MemoryBlockDecl):     memory = item

# Return site (lines 859–869):
return TeamDecl(
    span=_span(meta, self.file),
    name=name,
    ceiling=ceiling,
    policy=policy_obj,
    agents=tuple(agents),
    rosters=tuple(rosters),
    board=board,
    rituals=tuple(rituals),
    decorators=(),
    # V10 additions:
    # principles=principles,
    # gates=tuple(gates),
    # memory=memory,
)
```

---

### `voss/harness/team.py` — `VossTeamConfigError` upgrade + `compile_team` extension

**Analog:** `voss/harness/team.py` lines 33–45 (`VossTeamConfigError`), lines 644–719 (`compile_team`)

**Current `VossTeamConfigError`** (lines 33–45):
```python
class VossTeamConfigError(Exception):
    """Raised when team configuration is invalid or inconsistent (compile phase)."""

    def __init__(
        self,
        message: str,
        *,
        role_span: Span | None = None,
        ceiling_span: Span | None = None,
    ) -> None:
        super().__init__(message)
        self.role_span = role_span
        self.ceiling_span = ceiling_span
```

**Target shape (VLANG-02) — add `construct` + `fix_hint` kwargs with defaults (backward-compatible):**
```python
class VossTeamConfigError(Exception):
    def __init__(
        self,
        message: str,
        *,
        construct: str = "",      # NEW: "scope"|"budget"|"tools"|"role"|"model"|"block"|"ceiling"
        fix_hint: str = "",       # NEW: one-line actionable hint
        role_span: Span | None = None,
        ceiling_span: Span | None = None,
    ) -> None:
        super().__init__(message)
        self.construct = construct
        self.fix_hint = fix_hint
        self.role_span = role_span
        self.ceiling_span = ceiling_span

    def format_diagnostic(self) -> str:
        span = self.role_span or self.ceiling_span
        location = f"{span.file}:{span.line_start}" if span else "<unknown>"
        hint = f"  hint: {self.fix_hint}" if self.fix_hint else ""
        return f"[{self.construct}] {self} at {location}{hint}"
```

**14 raise sites to retrofit** (categories from RESEARCH.md §Raise sites):

| Lines | Construct | Fix hint example |
|-------|-----------|-----------------|
| 395, 399 | `"scope"` | `"scope list entries must be string literals"` |
| 413 | `"budget"` | `"use a token budget like: budget: 100 tokens"` |
| 428, 434 | `"tools"` | `'tools must be a string literal or list: tools: ["fs", "test"]'` |
| 445 | `"mode"` | `"mode must be one of: plan, edit, auto"` |
| 450 | `"mode"` | `"mode must be a string literal"` |
| 467 | `"model"` | `"configure the tier in [model_tiers]"` |
| 492 | `"model"` | `"model must be a string literal or tier keyword"` |
| 525, 535 | `"scope"` | `"role scope must be within the ceiling scope globs"` |
| 606, 618 | `"scope"` / `"budget"` | same as roster |
| 648 | `"ceiling"` | `"add a ceiling { budget: N tokens } block to team"` |

**`compile_team` current structure** (lines 644–719):
```python
def compile_team(decl: TeamDecl) -> tuple[TeamConfig, SubagentRegistry]:
    if decl.ceiling is None:
        raise VossTeamConfigError(f"team {decl.name!r} missing ceiling at compile")
    # ... ceiling, agents, rosters, board, rituals ...
    config = TeamConfig(
        name=decl.name,
        ceiling=ceiling_vo,
        policy=TeamPolicy(p=decl.policy),
        em_agent_id=em_agent_id,
        roster_ids=frozenset(roster_id_set),
        board=board_spec,
        rituals=rituals,
    )
    return config, registry
```

**V10 extension — add compile branches before `config = TeamConfig(...)` construction:**
```python
# --- principles block → PrinciplesConfig (VLANG-01a) ---
principles_config: PrinciplesConfig | None = None
if decl.principles is not None:
    from .principles import DEFAULT_PRINCIPLES, _ProjectLayer, merge_principles, load_principles
    block_layer = _ProjectLayer(decl.principles.items, ())
    if cwd is not None:
        file_layer = load_principles(cwd)
        base = merge_principles(DEFAULT_PRINCIPLES, file_layer)
        principles_config = merge_principles(base.principles, block_layer)
    else:
        principles_config = merge_principles(DEFAULT_PRINCIPLES, block_layer)

# --- gate blocks → GateConfig (VLANG-01b) ---
gate_configs = tuple(_compile_gate(g) for g in decl.gates)

# --- memory block → MemoryConfig (VLANG-01c) ---
memory_config = _compile_memory(decl.memory)
```

**New frozen config dataclasses to add in `team.py`** (follow `@dataclass(frozen=True, slots=True)` pattern from line 66):
```python
@dataclass(frozen=True, slots=True)
class GateConfig:
    name: str                        # "done"
    requires: frozenset[str]         # {"tests_passed", "independent_review", "evidence_refs"}

@dataclass(frozen=True, slots=True)
class MemoryConfig:
    decisions: str = ".voss/decisions"
    sessions:  str = ".voss/sessions"
    semantic:  str = ".voss-cache/semantic"
```

**`TeamConfig` additions** (defaulted for back-compat — check current `TeamConfig` field order, place new fields last):
```python
# Add to TeamConfig (all defaulted):
principles: PrinciplesConfig | None = None
gate_configs: tuple[GateConfig, ...] = ()
memory: MemoryConfig | None = None
```

**`compile_team` signature change** — accepts optional `cwd` for principles file merge:
```python
def compile_team(
    decl: TeamDecl,
    *,
    cwd: Path | None = None,          # NEW — optional; existing callers unaffected
) -> tuple[TeamConfig, SubagentRegistry]:
```

---

### `voss/harness/principles.py` — compile target for `principles{}`

**Read-only reference** (no changes to this file). Key functions:

**`_ProjectLayer`** (lines 58–67) — what a `principles{}` block compiles to:
```python
@dataclass(frozen=True, slots=True)
class _ProjectLayer:
    items: tuple[tuple[str, str | None], ...]
    disable: tuple[str, ...]
```

**`merge_principles`** (lines 154–159) — the merge function to call:
```python
def merge_principles(
    defaults: tuple[tuple[str, str], ...],
    layer: _ProjectLayer,
) -> PrinciplesConfig:
    """Active PrinciplesConfig from defaults + project layer (D-04)."""
    return PrinciplesConfig(tuple((k, t) for k, t, _ in _resolve(defaults, layer)))
```

**`load_principles`** (lines 70–117) — loads `.voss/principles.yml` when `cwd` is available:
```python
def load_principles(cwd: Path) -> _ProjectLayer:
    path = cwd / ".voss" / "principles.yml"
    if not path.exists():
        return _ProjectLayer((), ())
    # ... yaml.safe_load → _ProjectLayer ...
```

---

### `voss/harness/board/gates.py` — compile target for `gate{}`

**Read-only reference** (no changes). Predicate name → shipped class mapping:

```python
# gates.py lines 107–141
class a_verification_passes:
    name = "reviewer_a"         # maps from: require independent_review

class b_passes:
    name = "reviewer_b"         # maps from: require evidence_refs

class tests_pass:
    name = "tests"              # maps from: require tests_passed
```

**Pre-built Done gate** (line 185):
```python
_CODE_DONE_PREDICATES = (scope_clean(), a_verification_passes(), b_passes(), tests_pass())
```

---

### Test files — five new test modules

**Pattern source 1: `tests/parser/test_team_grammar.py`** (extend existing file)

Fixture pattern (lines 28–80):
```python
def test_minimal_team_parses(parse_source):
    prog = parse_source(
        """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
}
"""
    )
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    td = teams[0]
    assert td.name == "Eng"
```

New test cases to add (Wave 0 gaps from RESEARCH.md):
- `test_principles_block_parses` — standalone `principles{}` + in `team{}`
- `test_team_with_principles_block` — `team{}` with `principles` field populated
- `test_gate_block_parses` — `gate done { require tests_passed; ... }` → `GateBlockDecl`
- `test_memory_block_parses` — `memory{}` with defaults when keys omitted

**Pattern source 2: `tests/voss/test_team_compile.py`** (new test modules follow same shape)

```python
# Boilerplate for all new voss/ compile tests:
from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.team import VossTeamConfigError, compile_team

def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)

def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]
```

**Pattern source 3: `tests/harness/test_principles_config.py`** (for `test_team_principles_block.py`)

```python
# Uses tmp_path for file I/O, writes .voss/principles.yml:
def _write(cwd: Path, text: str) -> None:
    (cwd / ".voss").mkdir(parents=True, exist_ok=True)
    (cwd / ".voss" / "principles.yml").write_text(text, encoding="utf-8")
```

**Pattern source 4: `tests/voss/test_team_backcompat_regression.py`** (for diagnostic shape test)

```python
# Error assertion pattern (lines 24–29):
def _only_team(src: str) -> TeamDecl:
    prog = parse(src if src.endswith("\n") else src + "\n", "<test>")
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]

# Typical VossTeamConfigError assertion:
with pytest.raises(VossTeamConfigError) as ei:
    compile_team(_only_team(src))
err = ei.value
# V10 message-shape assertions:
assert err.construct != ""
assert err.fix_hint != ""
```

---

### `samples/team-orchestration.voss`, `samples/reviewer-split.voss`, `samples/audit-gates.voss`

**Analog:** `samples/classify.voss` (structure), `tests/parser/examples/team_strawman.voss` (team shape)

`classify.voss` shows the minimal `.voss` file header comment convention:
```voss
# classify.voss
# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.
```

The three org-loop examples should use `team{}` blocks with the new V10 grammar. The RESEARCH.md provides the canonical `team Engineering {}` skeleton (lines 574–614) — use that as the base for all three, varying the roster and gate config.

**End-to-end team file location:** `.voss/team.voss` within a pytest `tmp_path` fixture directory (or a dedicated fixture at `tests/fixtures/team.voss`). `voss team run` reads from `<cwd>/.voss/team.voss` (confirmed: `harness/cli.py:4046`).

---

### `tests/harness/test_e2e_team_run.py`

**Analog:** `voss/harness/cli.py:4021–4100` (`team_run_cmd`)

The `team_run_cmd` logic is the definitive pattern for what the e2e test must replicate or invoke:

```python
# From harness/cli.py:4035-4100 — stub stack used by team run:
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.em.stub import DeterministicEMStub
from voss.harness.em.schema import CreateTicketOp, EMPlanResponse, NoopOp

reviewer_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
reviewer_b = DeterministicReviewerStub(conf=0.99, verdict="pass", source="B", tier="strong")
# board, em_loop, handle composition follows...
```

The test can either:
1. Use `click.testing.CliRunner` to invoke `team_run_cmd` with a `--cwd` pointing to a `tmp_path` containing `.voss/team.voss`, or
2. Import and call the inner async `_run()` pattern directly.

---

## Shared Patterns

### Frozen dataclass node construction

**Source:** `voss/ast_nodes.py` lines 7–35 (Span, Node, Decl hierarchy)
**Apply to:** All new AST node classes (`PrinciplesBlockDecl`, `GateBlockDecl`, `MemoryBlockDecl`)

```python
@dataclass(frozen=True, slots=True)
class Span:
    file: str
    line_start: int
    col_start: int
    line_end: int
    col_end: int
    synthetic: bool = False

@dataclass(frozen=True, slots=True)
class Decl(Stmt): ...  # parent chain: Node → Stmt → Decl
```

Every new node: `@dataclass(frozen=True, slots=True)`, inherits `span: Span` from `Node`, uses tuples (not lists) for sequences.

### `VossParseError` raise pattern

**Source:** `voss/parser.py` lines 884–890, 1036–1043 (ceiling_block, roster_role)
**Apply to:** All new transformer methods

```python
raise VossParseError(
    file=self.file,
    line=meta.line,
    col=meta.column,
    expected=[f"unique `{key}` key in `ceiling` block"],
    got=f"duplicate `{key}` in ceiling block",
)
```

### Duplicate-key guard in transformer methods

**Source:** `voss/parser.py` lines 878–891 (ceiling_block), lines 1031–1044 (roster_role)
**Apply to:** `principles_block`, `memory_block` transformer methods

```python
seen: dict[str, object] = {}
for c in children:
    if not (isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], str)):
        continue
    key, val = c
    if key in seen:
        raise VossParseError(...)
    seen[key] = val
```

### Test fixture pattern — `parse_source` conftest

**Source:** `tests/parser/conftest.py`
**Apply to:** All parser test additions

```python
# conftest.py — provides parse_source fixture:
@pytest.fixture
def parse_source():
    def _impl(src: str, file: str = "<test>"):
        if not src.endswith("\n"):
            src = src + "\n"
        return _parse(src, file)
    return _impl
```

### Test compile helper pattern

**Source:** `tests/voss/test_team_compile.py` lines 18–25
**Apply to:** All `tests/voss/test_team_*.py` new files

```python
def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)

def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]
```

### `voss team check` CLI pattern

**Source:** `voss/harness/cli.py` lines 3888–3941
**Apply to:** `test_e2e_team_run.py` (use CliRunner or direct import)

```python
# team_check_cmd loads .voss/team.voss, calls compile_team, emits JSON:
p = Path(path)
src = p.read_text(encoding="utf-8")
program = parse(src if src.endswith("\n") else src + "\n", str(p))
team_decl = next((d for d in program.body if isinstance(d, TeamDecl)), None)
try:
    config, _registry = compile_team(team_decl)
except VossTeamConfigError as e:
    _fail(str(e))
```

---

## No Analog Found

All files have analogs. No entry needed here.

---

## Metadata

**Analog search scope:** `voss/grammar.lark`, `voss/ast_nodes.py`, `voss/parser.py`, `voss/harness/team.py`, `voss/harness/principles.py`, `voss/harness/board/gates.py`, `voss/cli.py`, `voss/harness/cli.py`, `voss/ast_serializer.py`, `tests/parser/test_team_grammar.py`, `tests/voss/test_team_compile.py`, `tests/voss/test_team_backcompat_regression.py`, `tests/harness/test_principles_config.py`, `samples/classify.voss`
**Files scanned:** 14 source files + directory listings
**Pattern extraction date:** 2026-06-07

---
phase: V10-voss-language-as-coordination-spec
plan: 02
type: execute
wave: 2
depends_on:
  - V10-01
files_modified:
  - voss/grammar.lark
  - voss/ast_nodes.py
  - voss/parser.py
autonomous: true
requirements:
  - VLANG-01a
  - VLANG-01b
  - VLANG-01c
  - VLANG-GUARD

must_haves:
  truths:
    - "principles{} parses standalone AND nested in team{}"
    - "gate done { require ... } parses standalone into a GateBlockDecl"
    - "memory{} parses with per-key defaulting (omitted keys → None on the node)"
    - "Existing team grammar (ceiling/roster/board/ritual) still parses unchanged"
    - "voss ast on a file with the new blocks does not crash"
  artifacts:
    - path: "voss/grammar.lark"
      provides: "principles_block, gate_block, memory_block rules + team_item/top_decl extensions"
      contains: "principles_block"
    - path: "voss/ast_nodes.py"
      provides: "PrinciplesBlockDecl, GateBlockDecl, MemoryBlockDecl + 3 defaulted TeamDecl fields"
      contains: "class PrinciplesBlockDecl"
    - path: "voss/parser.py"
      provides: "transformer methods for the three blocks + team_decl dispatch branches"
      contains: "def principles_block"
  key_links:
    - from: "voss/grammar.lark"
      to: "voss/parser.py"
      via: "_Transformer methods named after grammar rules"
      pattern: "def (principles_block|gate_block|memory_block)"
    - from: "voss/parser.py"
      to: "voss/ast_nodes.py"
      via: "constructs PrinciplesBlockDecl/GateBlockDecl/MemoryBlockDecl"
      pattern: "(PrinciplesBlockDecl|GateBlockDecl|MemoryBlockDecl)\\("
    - from: "voss/parser.py team_decl"
      to: "TeamDecl.principles/gates/memory"
      via: "isinstance dispatch + TeamDecl construction"
      pattern: "TeamDecl\\("
---

<objective>
Add the three coordination grammar blocks — `principles{}`, standalone `gate{}`, `memory{}` — to the Voss language at the grammar + AST + parser layers. This is a pure delta on the shipped team-block machinery: one new lark rule per block, one frozen AST node per block, one transformer method per block, plus dispatch wiring in `team_decl` and standalone entry via `top_decl`. After this wave the new blocks PARSE and serialize via `voss ast`; compilation to config happens in V10-03.

Purpose: Close VLANG-01a/01b/01c at the grammar/parse tier. The coordination-focus guard (VLANG-GUARD) is satisfied here by adding ONLY these three coordination blocks — no general-purpose language features.
Output: `voss/grammar.lark`, `voss/ast_nodes.py`, `voss/parser.py` extended; V10-01 parse tests (Task 1) go GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md

<interfaces>
<!-- Grammar extension points, verified against the live codebase. -->

voss/grammar.lark:
  line 12:  top_decl: decorated_decl | fn_decl | agent_decl | prompt_decl | class_decl | use_stmt | team_decl
  line 179: team_decl: "team" IDENT "{" team_body "}"
  line 180: team_body: _NL* (team_item (_NL+ team_item)*)? _NL*
  line 182: team_item: ceiling_block | policy_kv | team_agent | roster_block | board_block | ritual_block
  line 186: ceiling_block: "ceiling" "{" _NL* ceiling_kv ((_NL* "," _NL* | _NL+) ceiling_kv)* _NL* ","? _NL* "}"
  line 219: gate_decl: "gate" IDENT "->" gate_target "{" ... }  (EXISTING, inside board{} — DO NOT touch; "->" keeps it distinct)

voss/ast_nodes.py (parent chain Node → Stmt → Decl; Span at line 7):
  TeamDecl (line 337): name, ceiling, policy, agents, rosters, board, rituals, decorators=()  (decorators is the LAST defaulted field)
  CeilingDecl / RosterDecl / RitualDecl are the structural analogs.

voss/parser.py (class _Transformer):
  _span(meta, file) helper (lines 142-147) — use for every new node.
  ceiling_block / ceiling_kv methods (lines 877-942) — key/value dedup + type-validate template.
  ritual_block method (lines 1124-1145) — name + kv-list template (closest to principles/memory).
  team_decl method (lines 800-869) — isinstance dispatch over items, then TeamDecl(...) construction.
  voss/ast_serializer.py to_dict is GENERIC (isinstance(node, Node) + fields()) — no new arm needed (PATTERNS.md line 139).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add three grammar rules + wire team_item and top_decl</name>
  <read_first>
    - voss/grammar.lark (lines 12, 179-226 — the team block rules + top_decl; the existing gate_decl at 219 to confirm "->" keeps the standalone gate_block distinct)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (grammar rule shapes lines 47-74 — principles_block/gate_block/memory_block; keyword-collision guard line 74)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (Pitfall 2 keyword/IDENT collision lines 459-464)
  </read_first>
  <action>
    In voss/grammar.lark add three new rules following the `ceiling_block` template (PATTERNS.md lines 55-72):
    - `principles_block` — `"principles" "{" ... principles_kv ... "}"`; `principles_kv: IDENT ":" STRING`.
    - `gate_block` — `"gate" IDENT "{" ... gate_require (...)* "}"`; `gate_require: "require" IDENT`. This is DISTINCT from the existing `gate_decl` (line 219) because `gate_decl` uses the `"->"` target arrow; the standalone form has `{` directly after the IDENT. Confirm no ambiguity by keeping `"gate" IDENT "{"` vs `"gate" IDENT "->"`.
    - `memory_block` — `"memory" "{" ... memory_kv ... "}"`; `memory_kv: MEMORY_KEY ":" STRING`; `MEMORY_KEY: "decisions" | "sessions" | "semantic"` (closed-set keys, mirrors `CEILING_KEY`).
    Then extend two existing rules:
    - `team_item` (line 182): append `| principles_block | gate_block | memory_block`.
    - `top_decl` (line 12): append `| principles_block | gate_block | memory_block` so the blocks parse standalone.
    Use quoted string literals (`"principles"`, `"gate"`, `"memory"`, `"require"`) inline rather than promoting to named terminals — Earley prioritizes literals over IDENT in these non-overlapping positions (RESEARCH Pitfall 2). Do NOT modify the existing `gate_decl`/`gate_target`/`gate_predicate` rules.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss import parse; parse('principles { diff: \"x\" }\n', '<t>'); parse('gate done {\n  require tests_passed\n  require independent_review\n}\n', '<t>'); parse('memory { decisions: \"d\" }\n', '<t>'); print('PARSE_OK')"</automated>
  </verify>
  <acceptance_criteria>
    - voss/grammar.lark contains a `principles_block` rule, a `gate_block` rule, and a `memory_block` rule
    - `team_item` and `top_decl` each list the three new block alternatives: `grep -c "principles_block" voss/grammar.lark` >= 3
    - The existing `gate_decl` rule (with `"->"`) is unchanged: `grep -c '"->"' voss/grammar.lark` is unchanged from baseline
    - The existing ambiguity guard test passes: `.venv/bin/python -m pytest tests/parser/ -k ambiguity -q` exits 0
    - All three new block forms parse without error (the inline -c command above prints PARSE_OK)
  </acceptance_criteria>
  <done>Three grammar rules added; team_item + top_decl wired; existing grammar (incl. gate_decl) unchanged; ambiguity guard green.</done>
</task>

<task type="auto">
  <name>Task 2: Add three frozen AST node classes + three defaulted TeamDecl fields</name>
  <read_first>
    - voss/ast_nodes.py (Span/Node/Decl hierarchy lines 7-35; CeilingDecl/RosterDecl/RitualDecl lines 291-334; TeamDecl lines 337-345)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (new node class shapes lines 116-135; back-compat invariant lines 137)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (Pitfall 1 — defaulted fields must follow non-defaulted, lines 452-457)
  </read_first>
  <action>
    In voss/ast_nodes.py add three frozen dataclasses (all `@dataclass(frozen=True, slots=True)`, subclassing `Decl`, inheriting `span: Span`):
    - `PrinciplesBlockDecl` with `items: tuple[tuple[str, str], ...]`.
    - `GateBlockDecl` with `name: str` and `requires: tuple[str, ...]`.
    - `MemoryBlockDecl` with `decisions: str | None = None`, `sessions: str | None = None`, `semantic: str | None = None`.
    Then add three fields to `TeamDecl`, placed AFTER the existing last field `decorators: tuple[Decorator, ...] = ()` (Pitfall 1 — all new fields defaulted so existing constructions stay valid):
    - `principles: "PrinciplesBlockDecl | None" = None`
    - `gates: "tuple[GateBlockDecl, ...]" = ()`
    - `memory: "MemoryBlockDecl | None" = None`
    Use forward-reference string annotations if the new classes are defined after TeamDecl; otherwise define the three node classes before TeamDecl. Do NOT change the order or types of any existing TeamDecl field.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.ast_nodes import PrinciplesBlockDecl, GateBlockDecl, MemoryBlockDecl, TeamDecl; import dataclasses; fns=[f.name for f in dataclasses.fields(TeamDecl)]; assert fns[-3:]==['principles','gates','memory'], fns; m=MemoryBlockDecl.__dataclass_fields__; assert m['semantic'].default is None; print('NODES_OK')"</automated>
  </verify>
  <acceptance_criteria>
    - voss/ast_nodes.py contains `class PrinciplesBlockDecl`, `class GateBlockDecl`, `class MemoryBlockDecl`, each `@dataclass(frozen=True, slots=True)` and subclassing `Decl`
    - `TeamDecl`'s last three dataclass fields are `principles`, `gates`, `memory` in that order, all with defaults
    - Module imports without `TypeError: non-default argument ... follows default argument`
    - `MemoryBlockDecl` fields default to None; `GateBlockDecl.requires` is a tuple field
    - The inline -c verify above prints NODES_OK
  </acceptance_criteria>
  <done>Three node classes added; TeamDecl gains three defaulted fields after decorators; no import-time dataclass error.</done>
</task>

<task type="auto">
  <name>Task 3: Add three transformer methods + wire team_decl dispatch</name>
  <read_first>
    - voss/parser.py (_span helper lines 142-147; ceiling_block/ceiling_kv lines 877-942; ritual_block lines 1124-1145; team_decl dispatch + return lines 800-869)
    - voss/ast_nodes.py (the three new node classes from Task 2 — confirm exact field names)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (transformer patterns lines 157-240; duplicate-key guard lines 582-596; VossParseError pattern lines 567-580)
  </read_first>
  <action>
    In voss/parser.py class `_Transformer` add three methods mirroring the `ceiling_block`/`ritual_block` analogs:
    - `principles_kv(self, meta, children)` → returns `(str(children[0]), <STRING value>)`. `principles_block(self, meta, children)` → dedup keys (raise `VossParseError` on duplicate, using the file/line/col + expected/got pattern from ceiling_block), build `items` tuple, return `PrinciplesBlockDecl(span=_span(meta, self.file), items=tuple(items))`.
    - `gate_require(self, meta, children)` → returns the require-name string `str(children[0])`. `gate_block(self, meta, children)` → first child is the gate IDENT (name), remaining children are require strings; return `GateBlockDecl(span=_span(meta, self.file), name=<name>, requires=tuple(reqs))`.
    - `memory_kv(self, meta, children)` → returns `(MEMORY_KEY, STRING value)`. `memory_block(self, meta, children)` → dedup keys, map each declared key onto the matching MemoryBlockDecl field, leave omitted keys as None; return `MemoryBlockDecl(span=_span(meta, self.file), decisions=..., sessions=..., semantic=...)`.
    Extract the string value from a STRING/`StringLit` consistently with how ceiling_kv reads string values (check the existing code for whether children arrive as `StringLit` nodes or raw tokens, and match it).
    Then extend the `team_decl` method's isinstance dispatch (lines 812-848): add `elif isinstance(item, PrinciplesBlockDecl): principles = item`, `elif isinstance(item, GateBlockDecl): gates.append(item)`, `elif isinstance(item, MemoryBlockDecl): memory = item`. Initialize `principles=None`, `gates=[]`, `memory=None` before the loop. In the `return TeamDecl(...)` call (lines 859-869) pass `principles=principles, gates=tuple(gates), memory=memory`. Import the three node classes at the top of parser.py alongside the existing ast_nodes imports.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/parser/test_team_grammar.py -k "principles_block_parses or team_with_principles_block or gate_block_parses or memory_block_parses" -q</automated>
  </verify>
  <acceptance_criteria>
    - voss/parser.py defines methods `principles_block`, `principles_kv`, `gate_block`, `gate_require`, `memory_block`, `memory_kv`
    - `team_decl` constructs `TeamDecl(..., principles=..., gates=..., memory=...)`
    - The four V10-01 Task-1 parse tests now PASS (RED→GREEN): the pytest -k command above exits 0
    - `voss ast` does not crash on a file using the new blocks: `.venv/bin/python -m voss ast /dev/stdin <<< 'team E { ceiling { budget: 100 tokens } principles { diff: "x" } }' ` exits 0 OR (if /dev/stdin unsupported) a tmp-file equivalent exits 0
    - Existing parser tests stay green: `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -q` exits 0
  </acceptance_criteria>
  <done>Three transformer methods + team_decl dispatch wired; the four parse scaffolds are GREEN; voss ast does not crash on new blocks; existing parser suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.voss` source text → Lark parser | Untrusted `.voss` input is tokenized/parsed; malformed input must raise a clean VossParseError, not an unhandled exception or runaway recursion |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V10-02-01 | DoS | Lark Earley parser on deeply-nested/large `.voss` input | accept | Lark's Earley parser is the shipped, already-trusted parser for all `.voss` files; the three new rules add no recursion beyond the existing block grammar (flat key/value lists, no self-recursion). No new unbounded construct introduced. |
| T-V10-02-02 | Tampering | duplicate/garbage keys in new blocks | mitigate | `principles_block` and `memory_block` transformers raise `VossParseError` on duplicate keys (mirrors ceiling_block); `memory_kv` is constrained to the closed `MEMORY_KEY` terminal set so unknown keys fail at parse |
| T-V10-02-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs; uses already-installed `lark`. No new third-party dependency (SPEC constraint). |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -q` — all green (4 new + existing).
- Per-wave merge run: `.venv/bin/python -m pytest tests/parser/ tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py -q` — existing parser + team-compile + back-compat still green (compile-layer scaffolds from V10-01 remain RED — expected until V10-03).
- `voss ast` on a new-block file does not crash.
</verification>

<success_criteria>
- The three coordination blocks parse standalone and team-nested.
- TeamDecl carries the three new defaulted fields without breaking back-compat.
- VLANG-GUARD: the grammar diff adds ONLY principles/gate/memory blocks — no general-purpose language constructs.
- V10-01 Task-1 parse tests are GREEN.
</success_criteria>

<output>
Create `.planning/phases/V10-voss-language-as-coordination-spec/V10-02-SUMMARY.md` when done.
</output>

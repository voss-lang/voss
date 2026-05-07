# Phase 2: Parser & Grammar - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the front end of the Voss compiler: a Lark grammar (`grammar.lark`), a typed AST (Python dataclasses), and a transformer that converts Lark parse trees into Voss AST nodes. The parser must accept the full PRD §3 surface syntax — `probable<T>`, `ctx`, `within/fallback`, `match similar(...)`, agent definitions with options, `spawn`, `gather`, memory type declarations, `@tool`, `prompt` classes with inheritance, `try/catch`, and `use foo::bar` — and produce a clean AST for every PRD §7 example program (§7.1 classify, §7.2 support, §7.3 research; §7.4 assistant is v2 but should still parse).

**In scope (GRAM-01..05):**
- `grammar.lark` covering PRD §3 in full
- `ast_nodes.py` — frozen dataclass node hierarchy with span tracking
- `transformer.py` — Lark tree → Voss AST conversion
- `parser.py` — Lark setup + curated `VossParseError` wrapper
- Lexer rules (composite unit-suffix tokens, comment handling, newline semantics)
- Parser test suite — golden-AST snapshot equality for every PRD §7 example + per-construct unit tests

**Out of scope:**
- Type checking / unguarded-`probable` warnings (Phase 3 — analyzer)
- Token budget estimation, embedding index emission (Phase 3)
- Module resolution for `use foo::bar` — parser produces `Import` AST node only; resolution is Phase 4 codegen
- Pretty-printer / `voss fmt` (deferred; round-trip uses AST snapshot equality, not source round-trip)
- Multi-error recovery (single-error-stop in v1)
- Codegen, CLI, runtime work (later phases)

</domain>

<decisions>
## Implementation Decisions

### Parser Algorithm + Statement Separation
- **D-01:** **Lark Earley parser**, not LALR. Earley handles the small ambiguities Voss introduces (notably `memory.episodic(capacity: 20 turns)` looking like a call expression in a type position) without grammar contortions. Perf overhead acceptable for v1; LALR migration is an option later if compile time becomes a concern.
- **D-02:** **Newline is the in-block statement terminator.** Inside `{ ... }` bodies, statements end at NEWLINE. Blank lines and `# ...` comments are skipped. Statements can span multiple lines if they are clearly continued (open brackets, binary operator at end of line). PRD §7 examples use no semicolons — grammar matches.
- **D-03:** Comments are `#` to end-of-line only. No block comments in v1.

### AST Design
- **D-04:** AST nodes are **`@dataclass(frozen=True, slots=True)`**. Immutable trees prevent mid-walk mutation bugs in Phase 3 (analyzer) and Phase 4 (codegen).
- **D-05:** Every node carries a **`Span(file: str, line_start: int, col_start: int, line_end: int, col_end: int)`** field. Required for Phase 3 analyzer warnings ("Unguarded probable use — confidence not checked at line N") and Phase 5 `voss check` line/col reporting. Synthesized nodes use `Span.synthetic()` with a parent reference.
- **D-06:** **Typed base hierarchy:** `Node` → `Expr`, `Stmt`, `Decl`, `TypeExpr`. Pattern matching in transformer/analyzer becomes structural (`match node: case BinOp(...)`) rather than `isinstance`. Improves readability and catches missing cases at type-check time when tooling lands.

### Lexing — Unit-Suffix Literals
- **D-07:** **Composite tokens at lex time** for budget/duration/cost literals. Lexer emits dedicated tokens:
  - `TOKEN_BUDGET` for `4000 tokens` (and `2000 tokens`, etc.)
  - `DURATION_MS` for `500ms`
  - `DURATION_S` for `30s`, `60s`, `10s`
  - `COST_USD` for `$0.02`
  - `TURNS` for `20 turns`
  AST stores normalized numeric value plus a unit enum (`TokenUnit`, `DurationUnit`, `CostUnit`). Grammar reads cleanly: `budget_arg: "tokens" ":" TOKEN_BUDGET`. Unknown suffixes (`4000 banana`) fail at lex time with a clear "unknown unit" error rather than mysterious downstream confusion.

### Type Expressions
- **D-08:** **Separate `type_expr` grammar rule** in type positions only (after `:` in `let`/parameter, after `->` in fn/agent return, inside generic `<...>`). Distinct AST node `TypeExpr` (not unified with `Expr`).
- **D-09:** `type_expr` shape: `IDENT (\".\" IDENT)* (\"<\" type_expr (\",\" type_expr)* \">\")? (\"(\" type_kwargs \")\")?`. This covers `string`, `list<string>`, `dict<string, int>`, `probable<T>`, `memory.episodic(capacity: 20 turns)`, `memory.semantic(source: "./docs/", model: "...")`. `type_kwargs` accepts only literals + unit-suffix tokens — no arbitrary expressions in type slots.
- **D-10:** Phase 3 (analyzer) is responsible for resolving type names against a built-in registry (`probable`, `list`, `dict`, `memory.episodic`, etc.). Parser only validates surface shape.

### `@` Disambiguation
- **D-11:** **Position-based grammar productions**, two separate rules:
  - **Decorator:** `@` at start of statement/declaration, immediately followed by IDENT and optional `(args)`. Examples: `@tool`, `@match_threshold(0.80)`. Produced as `Decorator(name, args)` attached to the next decl/stmt.
  - **Confidence gate:** appears only inside `if` condition position, in form `expr "@" "p" comparison_op number`. Produced as `ConfidenceGate(target_expr, op, threshold)`.
  No token-level conflict; `@` lexes as one token and disambiguates by grammar context.

### Error Reporting
- **D-12:** **Curated `VossParseError` wrapper, single-error-stop in v1.** Catch Lark's `UnexpectedToken` / `UnexpectedCharacters` / `UnexpectedInput` and re-raise as:
  ```python
  VossParseError(
      file: str, line: int, col: int,
      expected: list[str],         # human-friendly token names
      got: str,                    # actual token / char
      hint: str | None,            # optional "did you mean ...?"
      source_excerpt: str          # 3-line window with caret
  )
  ```
  Stop at first error. Multi-error collection (Lark `on_error` recovery) deferred — risk of cascade noise outweighs benefit for author + early adopters.
- **D-13:** Token-name humanization table maintained alongside grammar (e.g. `LBRACE` → `"{"`, `TOKEN_BUDGET` → `"a token budget like 4000 tokens"`).

### Test Strategy (GRAM-05 Round-Trip)
- **D-14:** **AST snapshot equality** is the round-trip strategy. For each PRD §7 example program, check in a golden AST repr (deterministic JSON serialization of the frozen dataclass tree, with `Span` line/col stripped or normalized to make tests robust to whitespace edits). Test parses source → asserts equality with golden.
- **D-15:** Per-construct unit tests for every grammar production (one or more focused `.voss` snippets exercising each PRD §3 construct in isolation). Faster failure localization than full-program tests alone.
- **D-16:** Pretty-printer / source round-trip is **deferred** to a later phase (likely Phase 5 `voss fmt` or v2). Phase 2 ships parse-only.

### Claude's Discretion
- Internal split between `lexer.py` and `grammar.lark` (Lark allows both inline and external token defs) — pick whichever yields the cleanest grammar file.
- Exact JSON shape for golden AST snapshots (field order, span normalization rules) — document in test README.
- Internal helper names in `transformer.py` (e.g. one method per rule vs grouped helpers) — match Lark idioms.
- Whether to emit `Decorator` as an attached field on the decorated node or as a sibling node consumed by the decl — pick whichever simplifies analyzer (Phase 3) consumption.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `PRD.md` §3 — Full language specification; every construct the grammar must accept (`probable<T>`, `ctx`, `within/fallback`, `match similar`, agent primitives, memory primitives, `@tool`, `prompt`, `try/catch`, `use`, operator summary §3.10)
- `PRD.md` §4.1 — Compiler pipeline (parser sits between lexer and AST transformer)
- `PRD.md` §4.2 — Technology choices (Lark, dataclasses)
- `PRD.md` §4.3 — Directory structure (`voss/grammar.lark`, `voss/parser.py`, `voss/ast_nodes.py`, `voss/transformer.py`, `voss/lexer.py`)
- `PRD.md` §7 — Three example programs that must parse without error (§7.1 classify, §7.2 support, §7.3 research). §7.4 assistant should also parse (memory-augmented; targets v2 runtime but parser must accept it).
- `.planning/PROJECT.md` — Constraints (Python 3.11+, Lark, asyncio)
- `.planning/REQUIREMENTS.md` — GRAM-01..05 acceptance criteria
- `.planning/ROADMAP.md` Phase 2 — Goal and four success criteria
- `.planning/phases/01-runtime-library/01-CONTEXT.md` — Phase 1 runtime decisions; AST node shapes for `class Foo { ... }` will codegen to Pydantic in Phase 4 (D-11 in Phase 1), so `ClassDecl` AST nodes need fields sufficient to support that

### Library Documentation (fetch via context7 during planning/research)
- Lark — Earley parser configuration, `lark.Tree` → custom transformer, `Token` types, `UnexpectedToken`/`UnexpectedCharacters` exceptions, `parser="earley"` options, `propagate_positions=True` for span tracking, contextual lexer
- Python `dataclasses` — `frozen=True`, `slots=True`, `field(default_factory=...)` patterns
- pytest — parametrize for per-construct unit tests; snapshot/golden-file patterns (e.g. via syrupy or hand-rolled assert)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
None — Phase 2 is greenfield front-end work. Phase 1 (runtime) is still pending and lives in a sibling package (`voss_runtime/`); the parser does not import from it.

### Established Patterns
None pre-existing. Phase 2 establishes:
- Frozen dataclass + `Span` AST node shape (Phase 3 analyzer + Phase 4 codegen will walk this)
- `VossParseError` shape — likely template for `VossAnalyzeError` and other compiler error types
- Composite unit-suffix lex tokens — sets the precedent for any future literal types

### Integration Points
- **Phase 3 (analyzer)** consumes the AST produced here. Span tracking (D-05) is its load-bearing contract. Type-expr nodes (D-08..10) feed the type checker.
- **Phase 4 (codegen)** also consumes the AST. `ClassDecl`, `AgentDecl`, `PromptDecl`, `TryCatch`, `Use` nodes need codegen-friendly fields (decorators attached, body sequenced, parameters typed).
- **Phase 5 (CLI `voss ast`)** prints this AST. Implies `__repr__` or a serializer that produces readable structured output. Reuse the golden-snapshot serializer from D-14.

</code_context>

<specifics>
## Specific Ideas

- Lark `propagate_positions=True` is the path to spans on every node without manual plumbing in the transformer.
- Lark contextual lexer recommended — helps disambiguate `@` decorator vs confidence-gate context cleanly.
- Golden snapshots live under `tests/parser/golden/` mirroring `examples/` / PRD §7 names (`classify.ast.json`, `support.ast.json`, `research.ast.json`, `assistant.ast.json`).
- `voss ast` CLI command (Phase 5) should reuse the same JSON serializer used for golden snapshots — single source of truth for AST repr.
- Token-name humanization table belongs near the grammar so it stays in sync when productions evolve.

</specifics>

<deferred>
## Deferred Ideas

- **Pretty-printer / `voss fmt`** — Source round-trip (parse → print → reparse) is a stronger guarantee than AST snapshot equality but requires a full pretty-printer. Defer to Phase 5 or v2.
- **Multi-error recovery** — Collect-all-errors via Lark `on_error`. Real upside for editor / LSP scenarios; v1 author + early-adopter audience tolerates single-error-stop.
- **Block comments** — Only `# ...` line comments in v1. Add `/* ... */` (or similar) later if a real need surfaces.
- **String interpolation** — PRD §7 examples use `"text " + expr` concatenation. Interpolated strings (`f"..."`) are a quality-of-life win but not required by GRAM-01.
- **LALR migration** — Earley is the v1 choice. Revisit if compile times on real programs become a problem.
- **Tree-sitter grammar** — Listed in PRD §4.2 as "later" for editor support. v2 (EDIT-01).

</deferred>

---

*Phase: 2-Parser & Grammar*
*Context gathered: 2026-05-07*

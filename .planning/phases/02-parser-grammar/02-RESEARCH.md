# Phase 2: Parser & Grammar — Research

**Date:** 2026-05-07
**Phase:** 02-parser-grammar

## Context Summary

Phase 2 builds the front end: `grammar.lark`, `ast_nodes.py`, `transformer.py`, `parser.py`. Locked decisions (CONTEXT.md D-01..D-16) settle the big architectural questions: Earley parser, contextual lexer, frozen+slots dataclasses, Span on every node, separate `type_expr` rule, position-based `@` disambiguation, composite unit-suffix tokens, single-error-stop with curated `VossParseError`, AST snapshot equality for round-trip tests, no pretty-printer this phase. What's still open: exact AST node fields, transformer idiom (Transformer vs Interpreter), grammar fragment ordering, golden-snapshot serialization shape, and a handful of grammar-shape calls (agent-options vs statements, wildcard pattern node type, decorator attachment).

This research fills those gaps so the planner can size and order plans.

---

## Lark Earley Specifics

### `propagate_positions=True`
- When set, every `Tree` node gets a `meta` with `line`, `column`, `end_line`, `end_column`, `start_pos`, `end_pos`. Lark fills these from the first/last token of the matched span.
- Inside a `Transformer`, the corresponding methods receive the children list. To get `meta`, decorate the method with `@v_args(meta=True)` (or `inline=True, meta=True`) — then signature is `def rule(self, meta, children)` (or `def rule(self, meta, child1, child2, ...)`).
- Lark only attaches `meta` to **tree nodes**, not tokens. For pure-token rules (e.g. `IDENT`), use the token's `.line`/`.column`/`.end_line`/`.end_column` directly.
- **Synthesized nodes** (constructed by the transformer with no source backing — e.g. an implicit "block" wrapper) should use `Span.synthetic(parent_span)` per D-05. Recommend a class method `Span.synthetic(parent: Span | None) -> Span` that copies the parent's range and flags `synthetic=True`, OR uses sentinels (`-1`/`-1`) plus `file=parent.file`. Pick sentinels — simpler, works with JSON snapshot equality.
- **Empty productions** (e.g. an empty body `{ }`) get a meta whose `line`/`end_line` are the brace tokens; check `meta.empty` flag (`True` when the rule matched zero tokens) and fall back to surrounding token positions if needed.

### Contextual lexer
- `lexer="contextual"` (default for Earley in modern Lark) chooses terminal sets based on the parser state, not just the raw text. This means a token like `IDENT` matching `"p"` won't conflict with a literal keyword `"p"` in a confidence-gate position so long as the grammar slot accepts only one.
- For the `@` disambiguation: with the contextual lexer, **a single `AT` terminal is fine**. Decorator vs confidence-gate distinction lives entirely in grammar productions (D-11). At decl/stmt-start positions only the decorator rule accepts `AT`; inside an `if`-condition expression slot only the confidence-gate rule does. Earley + contextual lexer resolves it cleanly with no token-level pre-analysis.
- Caveat: contextual lexer requires terminals to be statically distinguishable across states. For composite-unit tokens (TOKEN_BUDGET = `INT WS+ "tokens"`) we likely cannot fold the unit into the same lexer pass cleanly because `INT` followed by `tokens` could appear elsewhere. Two viable strategies:
  1. **Lex-time composite via terminal regex:** define `TOKEN_BUDGET: /\d+\s+tokens\b/` directly. Earley + contextual lexer then prefers it in slots that accept it. Simple but `\s+` is sticky — must coordinate with the global `%ignore /[\t ]+/` rule (Lark allows terminals to consume their own whitespace; whitespace inside a terminal is **not** subject to `%ignore`).
  2. **Two-token grammar production:** keep `INT` and a unit IDENT (`"tokens"`) separate, build the composite in the transformer. Cleaner lexer, slightly more transformer code.
- **Recommendation: strategy 1.** D-07 explicitly says "Composite tokens at lex time"; honor it with terminal regex. Errors like `4000 banana` will surface as a parse error at the budget slot ("expected a token budget like 4000 tokens, got 4000 banana"). The humanization table (D-13) maps `TOKEN_BUDGET` to that phrase.

### Earley + ambiguity
- Lark's Earley returns the **first** parse tree by default; ambiguous parses can be exposed with `ambiguity="explicit"` (which yields `_ambig` tree nodes). For Voss v1, **leave default behavior**: any genuine ambiguity in the grammar is a bug, not a feature.
- Detection strategy: during development run the parser test suite once with `ambiguity="explicit"` and assert no `_ambig` nodes appear. Either keep that as a CI guard or run it as a one-shot lint during phase 2 wrap-up. Recommend the one-shot lint — runtime overhead of explicit ambiguity tracking is non-trivial and not worth paying on every parse.
- Likely ambiguity hotspots:
  - **Call vs type-instantiation:** `Foo(x: 1)` could be a call expression or a type-expr-with-kwargs. Resolved by D-08 (separate `type_expr` rule, only used in type positions). The expression grammar never reaches `type_expr`, so no ambiguity.
  - **Lambda `t => spawn ...` vs grouping:** `(t) => expr` could be a parenthesized expression followed by `=>`. Resolved by `lambda` having a fixed shape `IDENT "=>" expr` (or `"(" param_list ")" "=>" expr`) at a higher precedence than grouping. With Earley this should "just work" but watch for it during testing.
  - **`@` decorator vs confidence gate:** addressed by D-11 — decorator only at stmt/decl start, gate only inside if-condition expressions. No grammar conflict.
  - **`spawn Researcher(t)`:** `spawn` is a keyword prefix; `spawn` followed by a call expression. Make `spawn_expr: "spawn" call_expr` to avoid expr-precedence weirdness.
  - **`gather(handles, timeout: 30s)`:** mixed positional + named args. Recommend a single `arg_list` rule allowing both `expr` and `IDENT ":" expr` items; transformer separates them.

### Performance
- Earley on Lark for ~100 LOC programs (PRD §7 examples are 20-50 lines) parses in single-digit milliseconds in informal benchmarks. Grammar size matters more than input size at this scale; keep terminals reasonable (~50 terminals, ~80 rules expected for Voss v1) and runtime is fine. **Not a perf-critical phase.** Caching the parser instance (Lark builds tables once on `Lark(...)`) matters across many parses but not for v1.

### Error reporting shapes
- `lark.exceptions.UnexpectedToken`: fields `.token` (the actual `Token` with `.line`, `.column`, `.end_line`, `.end_column`, `.value`, `.type`), `.expected` (set of terminal names Lark expected), `.considered_rules`, `.state`, `.token_history`, `.line`, `.column`, `.pos_in_stream`. Has method `.match_examples(parser, examples)` for "did you mean..." style hints.
- `lark.exceptions.UnexpectedCharacters`: fields `.line`, `.column`, `.pos_in_stream`, `.allowed` (set of terminal names that could have started here), `.char`, `.token_history`. No `.token` because lexing failed.
- `lark.exceptions.UnexpectedInput`: base class. Has `get_context(text, span=40)` which returns a multi-line excerpt with a caret pointing at the offending position — directly usable for `VossParseError.source_excerpt`.
- **`accepts` / `expected` set:** for `UnexpectedToken`, `.expected` is a `set[str]` of terminal names. Pass each through the humanization table (D-13) to produce the "expected one of: `{`, a token budget like 4000 tokens, ..." message. For `UnexpectedCharacters` the equivalent is `.allowed`.
- **Recommendation:** centralize error wrapping in `parser.py`'s top-level `parse(source, file)` function. Catch the three exception types, build `VossParseError` from token/line/col + humanized expected list + `get_context()` excerpt, raise. No try/except scattered through transformer.

---

## Grammar Shape

### Token list (terminals)

**Literals:**
- `INT: /\d+/`
- `FLOAT: /\d+\.\d+/`
- `STRING: /"([^"\\]|\\.)*"/` plus `TRIPLE_STRING: /"""(.|\n)*?"""/` for `prompt` class bodies (D-08 deferred ideas note multi-line)
- `IDENT: /[a-zA-Z_][a-zA-Z0-9_]*/`

**Composite unit-suffix (D-07):**
- `TOKEN_BUDGET: /\d+\s+tokens\b/`
- `DURATION_MS: /\d+ms\b/`
- `DURATION_S: /\d+s\b/`
- `COST_USD: /\$\d+(\.\d+)?/`
- `TURNS: /\d+\s+turns\b/`

**Punctuation:** `LBRACE "{"`, `RBRACE "}"`, `LPAREN "("`, `RPAREN ")"`, `LBRACK "["`, `RBRACK "]"`, `LANGLE "<"`, `RANGLE ">"`, `COMMA ","`, `COLON ":"`, `SEMI` (unused but reserved), `DOT "."`, `DCOLON "::"`, `AT "@"`, `ARROW "->"`, `FATARROW "=>"`, `EQUALS "="`, `PLUS "+"`, `MINUS "-"`, `STAR "*"`, `SLASH "/"`, `EQ "=="`, `NEQ "!="`, `LE "<="`, `GE ">="`, `AND "and"`, `OR "or"`, `NOT "not"`, `UNDERSCORE "_"` (wildcard).

**Keywords (reserved IDENTs):** `fn`, `agent`, `prompt`, `class`, `let`, `if`, `else`, `match`, `case`, `ctx`, `within`, `fallback`, `try`, `catch`, `return`, `yield`, `include`, `spawn`, `gather`, `similar`, `use`, `extends`, `true`, `false`, `null`, `p` (used only in confidence-gate position; with contextual lexer it doesn't need full reservation but simplest to reserve).

**Whitespace + structure:**
- `NEWLINE: /\r?\n/+` — significant statement terminator (D-02)
- `%ignore /[\t ]+/` — horizontal whitespace
- `COMMENT: /#[^\n]*/` then `%ignore COMMENT` (D-03)
- Continuation: lines ending with an open bracket `(`, `[`, `{`, or with a binary operator, transparently continue. Easiest implementation: NEWLINE is only emitted at "statement boundaries" — i.e. let the grammar accept NEWLINE-or-not at brace/bracket interiors. Concretely: `%ignore NEWLINE` **inside parenthesized expressions** is not directly expressible in Lark; instead use `_NL: NEWLINE` rules where statement-significant and just `NEWLINE*` filler everywhere else. (See "Risks" section.)

### Top-level entry rule

```
start: program
program: (top_decl _NL)* top_decl? 
top_decl: fn_decl | agent_decl | prompt_decl | class_decl | let_stmt | use_stmt | decorated
```

`_NL` is the newline-eating filler (suppressed in the tree via underscore prefix).

### Statement categories

- `expr_stmt: expr` — bare expression as statement (e.g. `print(x)`, `history.add(msg)`)
- `let_stmt: "let" IDENT (":" type_expr)? ("=" expr)?` — declaration with optional type, optional initializer (PRD §3.7 has `let history: memory.episodic(capacity: 20 turns)` with no initializer)
- `if_stmt: "if" condition "{" block "}" ("else" "{" block "}")?` where `condition` is `expr` OR `confidence_gate` (D-11)
- `match_stmt: "match" expr "{" (_NL)? match_case+ "}"` 
- `match_case: "case" pattern "=>" (expr_stmt | "{" block "}") _NL`
- `pattern: similar_pattern | wildcard | expr` — wildcard is `_`
- `similar_pattern: "similar" "(" STRING ")"`
- `ctx_stmt: "ctx" "(" budget_arg ")" "{" block "}"`
- `within_stmt: "within" "budget" "(" budget_arg_list ")" "{" block "}" ("fallback" "{" block "}")?`
- `try_stmt: "try" "{" block "}" "catch" IDENT? "{" block "}"`
- `return_stmt: "return" expr?`
- `yield_stmt: "yield" expr?`
- `include_stmt: "include" expr` (PRD §3.7)
- `block: (stmt _NL)* stmt?`
- `stmt: let_stmt | if_stmt | match_stmt | ctx_stmt | within_stmt | try_stmt | return_stmt | yield_stmt | include_stmt | expr_stmt | decorated`

### Expression precedence ladder

From lowest to highest:

```
expr:           lambda_expr | spawn_expr | or_expr
lambda_expr:    IDENT "=>" expr            // single-arg lambda (PRD: t => spawn ...)
              | "(" param_list ")" "=>" expr
spawn_expr:     "spawn" call_expr
or_expr:        and_expr ("or" and_expr)*
and_expr:       not_expr ("and" not_expr)*
not_expr:       "not" not_expr | comparison
comparison:     additive (cmp_op additive)*
cmp_op:         "==" | "!=" | "<" | "<=" | ">" | ">="
additive:       multiplicative (("+" | "-") multiplicative)*
multiplicative: unary (("*" | "/") unary)*
unary:          "-" unary | postfix
postfix:        primary (call_suffix | member_suffix | index_suffix)*
call_suffix:    "(" arg_list? ")"
member_suffix:  "." IDENT
index_suffix:   "[" expr "]"
primary:        literal | IDENT | "(" expr ")" | list_lit | dict_lit | similar_call | gather_call
literal:        INT | FLOAT | STRING | TRIPLE_STRING | "true" | "false" | "null"
list_lit:       "[" (expr ("," expr)* ","?)? "]"
dict_lit:       "{" (kv ("," kv)* ","?)? "}"   // distinct from block — see ambiguity note
kv:             (STRING | IDENT) ":" expr
arg_list:       arg ("," arg)*
arg:            expr | IDENT ":" expr        // positional or named
```

**Confidence gate** lives only in `if_stmt` condition slot, not in the general expr ladder:

```
condition:        confidence_gate | expr
confidence_gate:  expr "@" "p" cmp_op (FLOAT | INT)
```

### Type expressions

Per D-09:

```
type_expr:    qual_name type_generics? type_kwargs?
qual_name:    IDENT ("." IDENT)*
type_generics: "<" type_expr ("," type_expr)* ">"
type_kwargs:  "(" type_kwarg ("," type_kwarg)* ")"
type_kwarg:   IDENT ":" type_arg_value
type_arg_value: STRING | INT | FLOAT | "true" | "false" | "null"
              | TOKEN_BUDGET | DURATION_MS | DURATION_S | COST_USD | TURNS
              | qual_name   // for memory references like `episodic` as an enum-ish value
```

Reaches `let foo: list<dict<string, int>> = ...` cleanly. Reaches `memory.episodic(capacity: 20 turns)` cleanly (qual_name = `memory.episodic`, kwargs = `capacity: TURNS`).

### Notes on ambiguity-prone productions

1. **`{ ... }` block vs dict literal.** The transformer must know context. Solution: dict literals only appear in *expression* slots; `{...}` after `if`/`else`/`ctx`/`within`/`fallback`/`fn`/`agent`/`prompt`/`class`/`try`/`catch` is always a block (separate rule, not via `expr`). With Earley + contextual lexer this disambiguates fine.
2. **Lambda single-IDENT vs IDENT expr.** `t => spawn x` parses as lambda; bare `t` as an expression statement parses as expr. The `=>` lookahead resolves it. Earley handles.
3. **Call args vs named args.** Both `gather(handles, 30s)` and `gather(handles, timeout: 30s)` must work. Single `arg` rule with two alternatives; transformer disambiguates.
4. **`spawn` precedence.** `spawn Foo(x).result` — does `.result` attach to the spawn or to Foo(x)? Per common-sense: the spawn returns an AgentHandle; `.result` belongs to it. Make `spawn_expr` parse `"spawn" call_expr` then allow postfix on the *whole* spawn_expr OR don't. PRD examples never chain on spawn, so simplest: `spawn_expr` is terminal at its level, no postfix chaining.
5. **`agent` body — options vs statements.** PRD §3.6 shows agent body containing named option fields (`system: "..."`, `tools: [...]`) interleaved with regular statements (`let findings = ...`, `return ...`). Solution: dedicated `agent_body` rule:
   ```
   agent_body: agent_option* stmt*
   agent_option: ("system" | "tools" | "model" | "retries" | "memory") ":" expr
   ```
   The option keywords are a closed set. They lex as IDENTs and only become "options" at the agent_body's leading position. With Earley + contextual lexer this works because once the first non-option statement appears, the option section ends. Note: this requires options to be *all* up front, which matches PRD examples. Document this constraint.
6. **`prompt` class body — bare strings.** `prompt SupportAgent { "You are ..." }`. The body is a sequence of (concatenable?) string literals. Recommend:
   ```
   prompt_decl: "prompt" IDENT ("extends" qual_name)? "{" prompt_body "}"
   prompt_body: (STRING | TRIPLE_STRING) (_NL (STRING | TRIPLE_STRING))*
   ```
   Multi-line content via TRIPLE_STRING; multiple string literals concatenated by the transformer.
7. **`include x` and `yield x`.** Treat as statement keywords (D-stated as PRD operator-summary keywords). Grammar production: `include_stmt: "include" expr`. Not a function call.
8. **Wildcard `_` in match.** Recommend explicit `wildcard_pattern: "_"` AST node `WildcardPattern(span)` rather than treating as `Identifier("_")`. Cleaner to match in transformer/codegen, no risk of conflating with a user-named variable `_`.

---

## AST Node Taxonomy

All nodes inherit from `Node` (abstract) which carries `span: Span`. Sub-bases: `Expr`, `Stmt`, `Decl`, `TypeExpr`, `Pattern`. All concrete classes are `@dataclass(frozen=True, slots=True)`.

### Base classes

```
Node       (abstract; span: Span)
  ├─ Expr        (abstract)
  ├─ Stmt        (abstract)
  ├─ Decl        (abstract; subclass of Stmt — decls are valid at top level AND in blocks)
  ├─ TypeExpr    (abstract)
  └─ Pattern     (abstract; only inside match cases)
```

`Decl` extends `Stmt` so a `block` can hold either. Top-level `program` accepts `Stmt` (which covers `Decl`).

### Expr nodes

| Node | Fields | Purpose |
|---|---|---|
| `IntLit` | `value: int` | Integer literal |
| `FloatLit` | `value: float` | Float literal |
| `StringLit` | `value: str`, `triple: bool` | String literal; `triple` flags multi-line for codegen pretty-printing |
| `BoolLit` | `value: bool` | `true` / `false` |
| `NullLit` | — | `null` |
| `Identifier` | `name: str` | Variable / name reference |
| `BinOp` | `op: str`, `left: Expr`, `right: Expr` | Arithmetic, comparison, logical |
| `UnaryOp` | `op: str`, `operand: Expr` | `-x`, `not x` |
| `Call` | `callee: Expr`, `args: list[Arg]` | Function/method call |
| `Arg` | `name: str \| None`, `value: Expr` | Positional (`name=None`) or named |
| `Member` | `obj: Expr`, `attr: str` | `x.y` |
| `Index` | `obj: Expr`, `index: Expr` | `x[y]` |
| `ListLit` | `items: list[Expr]` | `[a, b, c]` |
| `DictLit` | `items: list[tuple[Expr, Expr]]` | `{k: v}` |
| `Lambda` | `params: list[Param]`, `body: Expr` | `t => expr` |
| `SpawnExpr` | `agent: Call` | `spawn Researcher(t)` — agent is always a Call |
| `GatherExpr` | `handles: Expr`, `timeout: BudgetArg \| None` | `gather(handles, timeout: 30s)` (special-cased so analyzer/codegen can find timeout cleanly; alternatively keep as `Call`) |
| `SimilarPredicate` | `text: str` | `similar("...")` — captured as Pattern not Expr; see Pattern section |
| `ConfidenceGate` | `target: Expr`, `op: str`, `threshold: float` | `expr @ p >= 0.85` — only in `if` condition |

**Recommendation on `GatherExpr`:** keep as a regular `Call` node. The analyzer/codegen identify `gather(...)` by callee name. Simpler grammar, no special expr type. Same logic for `spawn` — but `spawn` *is* a syntactic prefix keyword, not a function, so it deserves its own node.

### Stmt nodes

| Node | Fields | Purpose |
|---|---|---|
| `ExprStmt` | `expr: Expr` | Bare expression as statement |
| `LetStmt` | `name: str`, `type_annot: TypeExpr \| None`, `value: Expr \| None` | `let x: T = e` |
| `IfStmt` | `condition: Expr \| ConfidenceGate`, `then_body: list[Stmt]`, `else_body: list[Stmt] \| None` | `if ... { ... } else { ... }` |
| `MatchStmt` | `scrutinee: Expr`, `cases: list[MatchCase]`, `threshold: float \| None` | Threshold set by `@match_threshold` decorator |
| `MatchCase` | `pattern: Pattern`, `body: list[Stmt]` | One arm |
| `CtxBlock` | `budget: BudgetArg`, `body: list[Stmt]` | `ctx(budget: 4000 tokens) { ... }` |
| `WithinFallback` | `budget_args: list[BudgetArg]`, `primary: list[Stmt]`, `fallback: list[Stmt] \| None` | `within budget(...) { ... } fallback { ... }` |
| `TryCatch` | `try_body: list[Stmt]`, `exc_name: str \| None`, `catch_body: list[Stmt]` | `try { ... } catch [name] { ... }` |
| `ReturnStmt` | `value: Expr \| None` | `return [expr]` |
| `YieldStmt` | `value: Expr \| None` | `yield [expr]` (only legal inside ctx; analyzer enforces) |
| `IncludeStmt` | `value: Expr` | `include x` (only inside ctx) |
| `BudgetArg` | `unit: str`, `value: int \| float`, `raw_unit: str` | Reused across ctx and within. `unit` ∈ `{"tokens", "ms", "s", "usd", "turns"}`, normalized. |

### Decl nodes

| Node | Fields | Purpose |
|---|---|---|
| `FnDecl` | `name: str`, `params: list[Param]`, `return_type: TypeExpr \| None`, `body: list[Stmt]`, `decorators: list[Decorator]` | `fn name(params) -> T { ... }` |
| `Param` | `name: str`, `type_annot: TypeExpr \| None`, `default: Expr \| None` | One parameter |
| `AgentDecl` | `name: str`, `params: list[Param]`, `return_type: TypeExpr \| None`, `options: AgentOptions`, `body: list[Stmt]`, `decorators: list[Decorator]` | `agent Foo(...) -> T { options...; stmts... }` |
| `AgentOptions` | `system: str \| None`, `tools: list[Identifier] \| None`, `model: str \| None`, `retries: int \| None`, `memory: Identifier \| None` | Captured option block |
| `PromptDecl` | `name: str`, `extends: QualName \| None`, `body: list[StringLit]`, `decorators: list[Decorator]` | `prompt Foo extends Bar { "..." }` |
| `ClassDecl` | `name: str`, `fields: list[ClassField]`, `decorators: list[Decorator]` | Pydantic-target. `class Report { content: string }` |
| `ClassField` | `name: str`, `type_annot: TypeExpr`, `default: Expr \| None` | Field of a class |
| `UseStmt` | `path: list[str]`, `alias: str \| None` | `use foo::bar` → path=["foo","bar"]; alias for future `as` syntax (not in PRD §3 but cheap to reserve) |
| `Decorator` | `name: str`, `args: list[Arg]` | `@tool`, `@match_threshold(0.80)` |

**Decorator attachment recommendation:** attached as a field on the decorated `Decl` (and `MatchStmt`, since `@match_threshold` decorates a match), not as a sibling node. Reasoning:
- Phase 3 analyzer needs to know "is this fn a tool?" — answered by a single field check on `FnDecl`.
- Phase 4 codegen for `@tool` emits a `_register_tool(fn)` call after the function definition; needs the decorator+function bundled.
- Sibling nodes would require analyzer/codegen to walk a list and pair them up — more code, more bugs.

`@match_threshold(0.80)` is a special case: it decorates a `MatchStmt` (a Stmt, not a Decl). Two options: (a) make `MatchStmt` accept decorators too — minor pollution but symmetric; (b) lift the threshold value into `MatchStmt.threshold` directly during transformation, dropping the Decorator node. **Recommend (b)** — single source of truth for the analyzer; the surface decorator is a parsing convenience, the AST captures the semantic meaning.

### TypeExpr nodes

| Node | Fields | Purpose |
|---|---|---|
| `TypeRef` | `name: QualName`, `generics: list[TypeExpr]`, `kwargs: list[TypeKwarg]` | `string`, `list<T>`, `memory.episodic(capacity: 20 turns)` |
| `QualName` | `parts: list[str]` | Dotted name, reused outside TypeExpr if needed |
| `TypeKwarg` | `name: str`, `value: TypeArgValue` | `capacity: 20 turns` |
| `TypeArgValue` | union: `IntLit \| FloatLit \| StringLit \| BoolLit \| NullLit \| BudgetArg \| QualName` | Limited to literals + qual names per D-09 |

A single `TypeRef` covers everything: `string` (no generics, no kwargs), `list<T>` (generics only), `memory.episodic(capacity: 20 turns)` (qualname + kwargs).

### Pattern nodes

| Node | Fields | Purpose |
|---|---|---|
| `SimilarPattern` | `text: str` | `similar("user wants a refund")` — text captured for compile-time embedding (Phase 3 reads this) |
| `WildcardPattern` | — | `_` |
| `ExprPattern` | `expr: Expr` | Fallback for any other expression-as-pattern (literal match) |

---

## Transformer Patterns

### Recommended idiom: `lark.Transformer` subclass with `@v_args(inline=True, meta=True)`

```python
from lark import Transformer, v_args

@v_args(inline=True, meta=True)
class VossTransformer(Transformer):
    def __init__(self, file: str):
        super().__init__()
        self.file = file

    def let_stmt(self, meta, name_token, type_expr, value_expr):
        return LetStmt(
            name=str(name_token),
            type_annot=type_expr,
            value=value_expr,
            span=self._span(meta),
        )
    
    def _span(self, meta) -> Span:
        return Span(
            file=self.file,
            line_start=meta.line, col_start=meta.column,
            line_end=meta.end_line, col_end=meta.end_column,
        )
```

**Why Transformer (not Interpreter):**
- Transformer is bottom-up: children are already AST nodes by the time the parent method runs. Pure functional construction, easier to reason about with frozen dataclasses.
- Interpreter is top-down: useful for context-dependent traversal (e.g. when the parent decides what to do with raw subtrees). Voss doesn't need that — every node's construction is local.

**Why `@v_args(inline=True, meta=True)`:**
- `inline=True` unpacks children as positional args (signature reads like the grammar).
- `meta=True` injects the `meta` object as first arg.
- Combined: methods read like dataclass constructors with span as a free parameter.

**Caveat:** with `inline=True`, optional rules (e.g. `("=" expr)?` in `let_stmt`) yield `None` for the missing slot. Method signatures need defaults or careful unpacking. Lark's behavior here is well-documented; expect to write helpers for "either-or" rules.

### Producing frozen dataclasses

Direct construction: `LetStmt(name=..., span=..., ...)`. Frozen dataclasses don't prevent construction, only post-construction mutation. Safe.

For optional fields: declare as `field(default=None)` on the dataclass; transformer passes `None` when grammar slot is empty.

### Error wrapping inside transformer methods

Most domain errors should be impossible if the grammar is correct (e.g. unknown unit can't appear because lexer rejects it). For belt-and-suspenders cases (e.g. parsing a `BudgetArg` value):

```python
def budget_arg(self, meta, name_token, value_token):
    name = str(name_token)
    try:
        return BudgetArg(unit=name, value=self._parse_unit(value_token), ...)
    except ValueError as e:
        raise VossParseError(
            file=self.file, line=meta.line, col=meta.column,
            expected=["a token budget like 4000 tokens"],
            got=str(value_token),
            hint=str(e),
            source_excerpt=...,
        ) from e
```

In practice, expect zero of these — the lexer already rejects unknown units.

### Span construction

`Span(file=..., line_start=meta.line, col_start=meta.column, line_end=meta.end_line, col_end=meta.end_column)`. For tokens (not subtrees), use `token.line`, `token.column`, `token.end_line`, `token.end_column`. For synthesized nodes (only the AgentOptions-merged dataclass might be synthetic), use parent's span or `Span.synthetic(parent)`.

---

## Test Strategy Details

### Golden snapshot serializer

**Recommendation:** hand-rolled `to_dict(node) -> dict` with deterministic field order, used by both tests and (eventually) `voss ast` CLI. Reasons:
- `dataclasses.asdict` works but recurses into all fields including `Span` — needs custom encoder for span normalization. About the same code volume as a hand-rolled serializer.
- Hand-rolled gives full control over span normalization, key order, and how `None`/empty-list fields are emitted (drop or keep).

Shape proposed:
```json
{
  "_node": "LetStmt",
  "span": {"file": "classify.voss", "lines": [3, 3], "cols": [4, 42]},
  "name": "intent",
  "type_annot": {
    "_node": "TypeRef",
    "span": {"file": "classify.voss", "lines": [3, 3], "cols": [16, 30]},
    "name": ["probable"],
    "generics": [{"_node": "TypeRef", "name": ["string"], "generics": [], "kwargs": []}],
    "kwargs": []
  },
  "value": {...}
}
```

Span normalization: keep `file` and `lines`/`cols` for round-trip; **but** in golden snapshots, replace `lines`/`cols` with `[0, 0]` / `[0, 0]` (or omit entirely). Tests then assert structural equality; whitespace edits to source don't break golden files.

Two-tier strategy:
1. **Structure-only goldens** (`*.ast.json`): spans zeroed. Robust to formatting tweaks.
2. **Span sanity checks** (per-construct unit tests): a handful of focused tests that *do* assert span ranges for specific nodes, ensuring `propagate_positions` is wired correctly. Don't need to cover every node — sample the tree.

### Span normalization rule

Concrete rule for goldens: `to_dict(node, normalize_spans=True)` zeros out `lines` and `cols` (`[0, 0]`) and keeps `file` as the source filename basename only (not full path — paths differ between dev machines and CI). Document in `tests/parser/golden/README.md`.

### Per-construct test layout

```
tests/parser/
├── conftest.py                  # parse(src, file) helper, golden-load helper, asdict helper
├── golden/
│   ├── README.md                # snapshot format + normalization rules
│   ├── classify.ast.json        # PRD §7.1 golden
│   ├── support.ast.json         # PRD §7.2 golden
│   ├── research.ast.json        # PRD §7.3 golden
│   └── assistant.ast.json       # PRD §7.4 golden (parser-only; doesn't run yet)
├── test_examples.py             # parametrized snapshot equality test for all four
├── test_literals.py             # int/float/string/bool/null
├── test_expressions.py          # binop, unary, call, member, index, list/dict literals
├── test_lambdas.py              # `t => expr`, multi-arg lambdas
├── test_type_expr.py            # qual names, generics, kwargs (incl. memory.episodic)
├── test_let_and_assign.py       # let with/without type, with/without init
├── test_if_and_match.py         # if, if/else, confidence gate, match (similar/_/expr), threshold
├── test_ctx_and_within.py       # ctx, within, fallback, nested ctx, all budget unit types
├── test_agent.py                # agent decl, options ordering, body interleave, spawn, gather
├── test_prompt_and_class.py     # prompt with extends, multi-line strings, class fields
├── test_decorators.py           # @tool, @match_threshold, on fn vs on match
├── test_use_and_include.py      # use foo::bar, include x
├── test_try_catch.py            # try/catch with and without exc binding
├── test_errors.py               # syntax errors → VossParseError shape; unknown units; bad nesting
└── test_spans.py                # sample-based span correctness checks
```

### Edge cases checklist

- Empty body: `fn foo() { }` — block has zero statements
- Empty agent body (no options, no statements) — should parse; analyzer flags missing system prompt later
- Nested ctx-in-ctx — legal grammar-wise, analyzer may warn
- Decorator on class vs fn vs match — all three paths
- Agent options in any order (system→tools→model vs model→system→tools), missing options — `AgentOptions` has all-`Optional` fields
- Match with no wildcard — legal; analyzer may warn
- Match with multiple wildcards — grammar allows; analyzer should error
- `gather` with no timeout: `gather(handles)`
- `gather` with positional timeout: `gather(handles, 30s)` — should this be allowed? PRD §3.6 shows named only. Recommend grammar-level: only named `timeout:` is accepted by `arg_list` semantics in `gather` — actually no, keep grammar permissive (general `arg_list`); analyzer enforces shape if needed
- Multi-line string in `prompt` body — `TRIPLE_STRING` terminal
- Single-line string in `prompt` body — `STRING` terminal
- `TypeExpr` with no kwargs: `string`, `list<T>`
- `TypeExpr` with kwargs: `memory.episodic(capacity: 20 turns)`
- `TypeExpr` with both generics and kwargs: hypothetical `Cache<T>(size: 100)` — grammar allows; analyzer rejects if no such type exists
- `if` with confidence gate: `if intent @ p >= 0.80 { ... }`
- `if` with regular condition: `if x > 5 { ... }`
- `let` with no initializer: `let history: memory.episodic(capacity: 20 turns)` (PRD §3.7)
- Trailing comma in list/dict/arg lists — recommend grammar accepts it (Python convention)
- Nested generics: `dict<string, list<probable<int>>>`
- Comments at end of line, on their own line, between block statements
- Comment immediately before `}` — must not break newline handling
- Continuation across newline inside `(`, `[`, `<` — needs newline tolerance in those contexts

---

## Risks and Gotchas

1. **Newline-significant grammar in Lark.** Lark's `%ignore /[\t ]+/` handles horizontal whitespace, but newlines as statement separators while *also* being insignificant inside parens/brackets is tricky. Two strategies:
   - **A (recommended):** Don't `%ignore` NEWLINE globally. Instead, define `_NL: NEWLINE+` and emit it explicitly in statement-list rules (`block: (stmt _NL)* stmt?`, etc.). Inside parenthesized expression rules, allow optional NEWLINE between tokens via `expr: NEWLINE* base_expr NEWLINE*`-style filler at the right places. Verbose but explicit.
   - **B:** Use Lark's `%declare` + a custom postlexer that swallows NEWLINEs inside paren depth > 0. More magic, easier to get wrong. Skip.
   - **Mitigation:** decide upfront and document in grammar comments. Build a small newline-handling test suite early (`test_newlines.py` — separate from the per-construct tests) that exercises continuation rules.
2. **Comments adjacent to NEWLINE.** `# comment\n` should produce a single statement-terminating NEWLINE. With `%ignore COMMENT` (where `COMMENT: /#[^\n]*/`), Lark consumes the comment but leaves the `\n` for NEWLINE. Verify this in a test; the order of `%ignore` directives matters.
3. **Agent body interleaving.** The grammar must allow `option* stmt*` in that order specifically. If a user writes `let x = 1` *then* `system: "..."`, the system line must lex+parse as a `let_stmt` or fail cleanly. The cleanest grammar is "options must come before any statement"; document this in the grammar comment and in the user-facing error when it happens. Analyzer may surface a "agent options must come before statements" hint; for v1 a generic parse error is acceptable.
4. **Triple-quoted strings.** `TRIPLE_STRING: /"""(.|\n)*?"""/` is greedy-shy and *can* match across NEWLINEs without confusion; just make sure the regex precedes the regular `STRING` regex in the lexer ordering (Lark prefers earlier-defined / more-specific terminals; explicit priority via `STRING.2` if needed).
5. **`probable<T>` parsing.** `<` and `>` are also comparison operators. With `type_expr` only used in type positions and the contextual lexer, this should disambiguate, but watch out for `if x < 5` accidentally parsing as a type-expr. Confidence gate test cases must include `if x < 5 { ... }`. Recommend explicit test.
6. **`use foo::bar` vs `foo.bar`.** Per PRD §3 example "use foo::bar". `::` is a separate terminal from `.`; grammar has `DCOLON` for it. `use` paths use `::`, member access uses `.`. Don't conflate.
7. **`let foo: probable<list<int>> = ...`.** Nested generics test required.
8. **`p` keyword.** `p` appears only in `expr "@" "p" cmp_op number`. With contextual lexer, `p` lexes as IDENT outside that slot and as keyword inside. With non-contextual lexer it would conflict. CONTEXT.md mandates contextual lexer (D-implicit via Lark earley default + explicit "contextual lexer recommended" in specifics) — confirmed safe.
9. **`null` keyword vs Python `None`.** PRD §3 uses `null` (per PRD §3.10 implied by `gather` semantics returning `null`). Grammar uses `null`; transformer maps to `NullLit` AST node; codegen (Phase 4) emits `None`. Keep keyword as `null`.
10. **`true`/`false`/`null` reservation.** They lex as keywords; not as identifiers. Tests should confirm a user can't write `let true = 5`.
11. **`gather` and `spawn` reservation.** `gather` is a builtin function call (looks like any other call); reserving as a keyword is unnecessary and would break the call-grammar uniformity. Keep `gather` as IDENT, special-case in codegen. `spawn` IS a keyword (syntactic prefix).
12. **Analyzer leak.** Be disciplined: Phase 2 grammar/AST should not encode any analyzer rules (e.g. "yield must be inside ctx"). Those are Phase 3. Surface error: a `yield` outside ctx parses cleanly into a `YieldStmt` and Phase 3 rejects it.
13. **Round-trip definition.** D-14 calls round-trip "AST snapshot equality". This is **not** source round-trip (parse → print → reparse). It is parse → assert AST equals golden. Tests that try to assert source-byte equality will fail because of formatting variance. Document this carefully in `tests/parser/golden/README.md`.

---

## Suggested Implementation Order

Each step is independently testable with its own grammar fragment + AST nodes + transformer methods + per-construct test file. Land in this order:

1. **Skeleton + literals + identifiers.** Grammar entry point, NEWLINE handling baseline, `INT/FLOAT/STRING/TRIPLE_STRING/BoolLit/NullLit/Identifier`, `expr_stmt` accepting only literals/idents. Tests: `test_literals.py`. Establishes the transformer + Span pattern.
2. **Composite unit-suffix tokens.** `TOKEN_BUDGET`, `DURATION_MS`, `DURATION_S`, `COST_USD`, `TURNS` terminals + `BudgetArg` AST node. Tests: parametrized parsing of each unit literal. (Not used yet but available for ctx/within.)
3. **Type expressions.** `type_expr`, `TypeRef`, `QualName`, `TypeKwarg`. Tests: `test_type_expr.py` covering string, list<T>, dict<K,V>, probable<T>, memory.episodic(capacity: 20 turns), nested generics.
4. **Expressions: precedence ladder.** Binary/unary ops, calls, member, index, list/dict literals. Tests: `test_expressions.py` — operator precedence, associativity, postfix chaining.
5. **Lambdas.** `t => expr` and `(x, y) => expr`. Tests: `test_lambdas.py`.
6. **Simple statements.** `let_stmt` (with/without type, with/without init), `expr_stmt`, `return_stmt`, `yield_stmt`, `include_stmt`. Tests: `test_let_and_assign.py`. Block rule + newline handling now exercised.
7. **`if/match`.** `if_stmt` with regular and confidence-gate conditions; `match_stmt` with `similar`, wildcard, expression patterns; `@match_threshold` decorator. Tests: `test_if_and_match.py`. Confidence gate AST + grammar.
8. **`ctx` and `within/fallback`.** `ctx_stmt`, `within_stmt`. Re-uses `BudgetArg` from step 2. Tests: `test_ctx_and_within.py`.
9. **`try/catch`.** `try_stmt`. Tests: `test_try_catch.py`.
10. **Function declarations.** `fn_decl` + `Param` + `@tool` decorator. Tests: `test_decorators.py` (tool only at this point) + start `test_fn.py`.
11. **Agent declarations.** `agent_decl` + `agent_option*` + body. `spawn_expr` + `gather` (just a Call). Tests: `test_agent.py`.
12. **Prompt + class declarations.** `prompt_decl` (with `extends`), `class_decl` + `ClassField`. Tests: `test_prompt_and_class.py`.
13. **`use` statement.** `use_stmt` with `::` separator. Tests: `test_use_and_include.py` (already started in step 6 for include; finish here).
14. **Error wrapping.** Implement `VossParseError`, humanization table, top-level `parse(source, file)`. Tests: `test_errors.py`. Convert all the per-construct tests to also verify error paths for malformed inputs.
15. **PRD §7 example snapshots.** Generate goldens (`classify.ast.json`, `support.ast.json`, `research.ast.json`, `assistant.ast.json`) using the implemented parser+serializer; commit. Tests: `test_examples.py` parametrized over the four files.
16. **Span sanity tests.** `test_spans.py` — pick representative nodes and assert correct line/col ranges.
17. **Ambiguity sweep.** One-shot run with `ambiguity="explicit"` against every test file; assert no `_ambig` nodes. Add as a CI smoke check.

This ordering is bottom-up (literals → atomic exprs → compound exprs → simple stmts → control flow → declarations) so each step's tests build on stable foundations. Steps 1-9 produce a meaningful subset of Voss; steps 10-13 close out declarations; steps 14-17 finalize quality.

---

## Validation Architecture

Phase 2 satisfies Nyquist Dimension 8 (multi-perspective validation) via four orthogonal test types:

1. **Round-trip / golden snapshot tests** (`test_examples.py`): full PRD §7 programs parse and produce a stable AST shape. Catches whole-program integration regressions.
2. **Per-construct unit tests** (`test_literals.py` … `test_use_and_include.py`): each grammar production tested in isolation with multiple inputs (including negatives). Catches localized grammar/transformer bugs.
3. **Error-message tests** (`test_errors.py`): asserts `VossParseError` shape — line/col, expected list, got, hint, source_excerpt — for representative malformed inputs (bad unit, missing brace, decorator misplacement, agent option after stmt, etc.). Catches error-path regressions.
4. **AST shape assertions** (`test_spans.py`): targeted assertions on span ranges and synthetic-node detection, ensuring `propagate_positions` plumbing stays correct as grammar evolves.

Plus the one-shot ambiguity sweep (step 17) as a meta-check over the test corpus.

---

## Open Questions for Planner

1. **Continuation-line rule scope.** Recommend brackets/parens only (`(`, `[`, `<` — when in type position — and `{`). Does `let x =\n expr` (newline after `=`) need to work? PRD §7 examples don't require it. Recommend: no — keep newlines significant except inside brackets. Planner should confirm.
2. **`@match_threshold` AST shape.** Recommended: lift threshold into `MatchStmt.threshold`, drop the Decorator node entirely. Alternative: keep Decorator on MatchStmt for symmetry. Pick one before plan-phase to fix the AST contract for Phase 3.
3. **`gather` AST node.** Recommended: keep as `Call` (no special node). Alternative: dedicated `GatherExpr` for analyzer convenience. Negligible cost either way; resolve to lock the AST.
4. **`use foo::bar` AST.** Recommend `UseStmt(path=["foo","bar"], alias=None)`. Should we also accept `use foo::bar as baz` now? PRD doesn't mention it; recommend defer.
5. **Trailing commas.** Recommend allowed in list/dict/arg/param lists. Trivial grammar addition; reduces user friction. Confirm.
6. **Newline handling strategy.** Recommend strategy A (explicit `_NL` in stmt-list rules; no global `%ignore NEWLINE`). Confirm before grammar work starts — flips the entire grammar file's shape.
7. **`assistant.voss` (PRD §7.4) golden.** PRD §7.4 is v2 runtime but should parse in v1. Should the golden be committed in Phase 2 or deferred? Recommend committing — proves parser handles memory primitives even if runtime support lags.

## RESEARCH COMPLETE

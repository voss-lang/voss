# Phase 2: Parser & Grammar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 2-parser-grammar
**Areas discussed:** Parser algorithm + statement separation, AST node design, Unit-suffix literals, Type-expr vs call-expr, `@` disambiguation, Error reporting, GRAM-05 round-trip strategy

User direction: "use all of your recommended selection." All seven gray areas presented; user accepted the recommended option for each.

---

## Parser Algorithm + Statement Separation

| Option | Description | Selected |
|--------|-------------|----------|
| Earley + newline-terminator (Recommended) | Earley handles ambiguity (type-expr vs call-expr). Newline ends stmt inside `{}`; blank lines & comments ignored. Matches PRD examples (no `;`). Slight perf cost vs LALR but fine for v1. | ✓ |
| LALR + newline-terminator | Faster parse. May force grammar contortions to resolve `memory.episodic(...)` in type pos. Risk: hand-rolling lookahead hacks. | |
| Earley + explicit `;` terminator | Simpler grammar. Breaks PRD example syntax — every example would need rewrite. | |

**User's choice:** Earley + newline-terminator
**Notes:** Earley chosen for ambiguity tolerance (type-expr vs call-expr). LALR migration left as a future option if compile time becomes a problem.

---

## AST Node Design

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen + pos-on-every-node + typed unions (Recommended) | `@dataclass(frozen=True, slots=True)`. Span on every node. Base classes: `Node`, `Expr`, `Stmt`, `Decl`, `TypeExpr`. Analyzer needs spans for warnings; immutability prevents mid-walk mutation bugs. | ✓ |
| Mutable + pos-on-leaves only | Easier to build during transform. Loses span on synthesized nodes. Worse Phase 3 error msgs. | |
| Frozen + flat single Node base | Less type discrimination. Pattern-matching becomes runtime isinstance instead of structural. | |

**User's choice:** Frozen + pos-on-every-node + typed unions
**Notes:** Spans are load-bearing for Phase 3 analyzer warnings (line numbers in success criteria) and Phase 5 `voss check`. `Span.synthetic()` reserved for transformer-generated nodes.

---

## Unit-Suffix Literals

| Option | Description | Selected |
|--------|-------------|----------|
| Composite tokens at lex time (Recommended) | Lexer emits `TOKEN_BUDGET`, `DURATION_MS`, `DURATION_S`, `COST_USD`, `TURNS`. Grammar reads clean. AST stores normalized numeric + unit enum. | ✓ |
| Number + bare identifier, parsed syntactically | Looser — `4000 banana` parses then fails in analyzer. More flexible if future units appear. | |
| Treat suffix as macro / call | Wrap as `tokens(4000)`. Drifts from PRD surface syntax. | |

**User's choice:** Composite tokens at lex time
**Notes:** Unknown unit fails at lex time with clear "unknown unit" error. Cleaner grammar, fewer downstream surprises.

---

## Type-Expr vs Call-Expr Disambiguation

| Option | Description | Selected |
|--------|-------------|----------|
| Separate `type_expr` rule in type positions (Recommended) | Distinct `TypeExpr` AST node. Type positions: after `:`, after `->`, inside `<...>`. No ambiguity with call expressions. | ✓ |
| Unified expr; tag at semantic phase | Simpler grammar but pushes errors to Phase 3 + makes parse-only tools (`voss ast`) fuzzy. | |

**User's choice:** Separate `type_expr` rule in type positions
**Notes:** `type_kwargs` accepts only literals + unit-suffix tokens — no arbitrary expressions in type slots. Phase 3 owns name resolution against built-in registry.

---

## `@` Disambiguation

| Option | Description | Selected |
|--------|-------------|----------|
| Position-based grammar (Recommended) | Decorator: `@` at start of stmt/decl + IDENT. Confidence gate: only inside `if` condition, form `expr "@" "p" cmp number`. Two distinct grammar productions; no token-level conflict. | ✓ |
| Different tokens | Lex `@` followed by `p` as `AT_P`. Brittle — breaks if grammar evolves. | |
| Method-call sugar instead | Rewrite `intent @ p >= 0.85` to `intent.confidence_gte(0.85)` at parse time. Drifts from PRD surface. | |

**User's choice:** Position-based grammar
**Notes:** Lark contextual lexer expected to make this clean.

---

## Error Reporting Fidelity

| Option | Description | Selected |
|--------|-------------|----------|
| Curated wrapper, single-error-stop (Recommended) | Wrap Lark errors into `VossParseError(file, line, col, expected, got, hint)`. Stop at first error. `voss check` gets clean structured output. Multi-error deferred. | ✓ |
| Vanilla Lark errors | Pass through Lark messages. Fast to ship, ugly UX. Slows dogfooding. | |
| Curated + collect-all | Use Lark `on_error` recovery. Higher complexity; cascade noise risk. Overkill for v1. | |

**User's choice:** Curated wrapper, single-error-stop
**Notes:** Token-name humanization table maintained alongside grammar.

---

## GRAM-05 Round-Trip Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| AST snapshot equality (Recommended) | Each PRD §7 example has a checked-in golden AST repr. Test parses source, asserts equal to golden. No pretty-printer needed in Phase 2. | ✓ |
| Parse → pretty-print → reparse → AST equality | Stronger guarantee but requires pretty-printer in Phase 2. Useful for `voss fmt` later but extra scope now. | |
| Smoke parse only (no error) | Weakest — can't catch silent transformer bugs. | |

**User's choice:** AST snapshot equality
**Notes:** Snapshots live under `tests/parser/golden/` mirroring example names. Same JSON serializer powers `voss ast` CLI command in Phase 5.

---

## Claude's Discretion

- Internal split between `lexer.py` and `grammar.lark` (Lark allows both inline and external token defs)
- Exact JSON shape for golden AST snapshots (field order, span normalization rules)
- Internal helper organization in `transformer.py`
- Whether `Decorator` attaches as a field on the decorated node or as a sibling consumed by the decl

## Deferred Ideas

- Pretty-printer / `voss fmt` — likely Phase 5 or v2
- Multi-error recovery (Lark `on_error`) — useful for future editor/LSP work
- Block comments — `#` only in v1
- String interpolation (`f"..."`) — concatenation suffices for PRD §7
- LALR migration — revisit if compile times become a problem
- Tree-sitter grammar — v2 (EDIT-01)

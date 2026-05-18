# Voss AST JSON contract

This document describes the JSON produced by [`voss.ast_serializer.to_dict`](../../voss/ast_serializer.py) and consumed by tooling, golden tests, and the optional Haskell front end.

## Conventions

- **Discriminator**: Every AST node (subclass of `Node`) includes `"_node": "<PythonClassName>"` matching the class name in [`voss/ast_nodes.py`](../../voss/ast_nodes.py).
- **Spans**: `Span` values are **not** `Node`s and have **no** `_node` field. Shape:
  - **Full spans** (`normalize_spans=False`):  
    `{"file": str, "lines": [line_start, line_end], "cols": [col_start, col_end], "synthetic": bool}`
  - **Normalized** (`normalize_spans=True`):  
    `file` is basename only (except synthetic `"<synthetic>"`), `lines` and `cols` are `[0, 0]`.
- **Lists**: `tuple` fields serialize as JSON arrays.
- **Primitives**: `str`, `int`, `float`, `bool`, JSON `null` for Python `None`.
- **Optional fields**: Omitted or `null` per `dataclasses.fields`; serializers emit all fields for `Node` instances via `fields()`.

## Node kinds (alphabetic by class name)

| `_node` | Notes |
|--------|--------|
| `AgentDecl` | `name`, `params`, `return_type`, `options`, `body`, `decorators` |
| `AgentOptions` | `system`, `tools`, `model`, `retries`, `memory` (optional) |
| `Arg` | `name` (`null` for positional), `value` |
| `BinOp` | `op`, `left`, `right` |
| `BoolLit` | `value` |
| `BudgetArg` | `name`, `unit`, `value`, `raw` |
| `Call` | `callee`, `args` |
| `ClassDecl` | `name`, `fields`, `decorators` |
| `ClassField` | `name`, `type_annot`, `default` |
| `ConfidenceGate` | `target`, `op`, `threshold` |
| `CtxBlock` | `budget`, `body` |
| `Decorator` | `name`, `args` |
| `DictLit` | `items` — array of `[key, value]` pairs |
| `ExprPattern` | `expr` |
| `ExprStmt` | `expr` |
| `FloatLit` | `value` |
| `FnDecl` | `name`, `params`, `return_type`, `body`, `decorators` |
| `Identifier` | `name` |
| `IfStmt` | `condition`, `then_body`, `else_body` |
| `IncludeStmt` | `value` |
| `Index` | `obj`, `index` |
| `IntLit` | `value` |
| `Lambda` | `params`, `body` |
| `LetStmt` | `name`, `type_annot`, `value` |
| `ListLit` | `items` |
| `MatchCase` | `pattern`, `body` |
| `MatchStmt` | `scrutinee`, `cases`, `threshold` |
| `Member` | `obj`, `attr` |
| `NullLit` | (no extra fields beyond `span`) |
| `Param` | `name`, `type_annot`, `default` |
| `Program` | `body` — top-level statements |
| `PromptDecl` | `name`, `extends`, `body` (string literals), `decorators` |
| `QualName` | `parts` |
| `ReturnStmt` | `value` |
| `SimilarPattern` | `text` |
| `SpawnExpr` | `agent` (always a `Call` in the concrete grammar) |
| `StringLit` | `value`, `triple` |
| `TryCatch` | `try_body`, `exc_name`, `catch_body` |
| `TypeKwarg` | `name`, `value` |
| `TypeRef` | `name`, `generics`, `kwargs` |
| `UnaryOp` | `op`, `operand` |
| `UseStmt` | `path`, `alias` |
| `WildcardPattern` | (no extra fields) |
| `WithinFallback` | `budget_args`, `primary`, `fallback` |
| `YieldStmt` | `value` |

## Golden tests

Normalized AST goldens live under [`tests/parser/golden/*.ast.json`](../../tests/parser/golden/) and are compared to `to_dict(program, normalize_spans=True)` in [`tests/parser/test_examples.py`](../../tests/parser/test_examples.py).

## Deserialization

[`voss.ast_deserializer.program_from_dict`](../../voss/ast_deserializer.py) reconstructs Python dataclass AST nodes from this JSON for the Haskell subprocess path and round-trip tests.

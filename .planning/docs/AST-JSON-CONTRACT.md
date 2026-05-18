# Voss AST JSON contract

This document describes the JSON produced by [`voss.ast_serializer.to_dict`](../../voss/ast_serializer.py) and consumed by tooling, golden tests, and the Haskell front end.

## How `to_dict` walks the tree

- **`Span`**: Mapped to the object shapes below (never includes `_node`).
- **Subclasses of `Node`**: One object per node: `{"_node": <class name>, "span": <span object>, ...}` with **every** dataclass field listed in declaration order (from `dataclasses.fields`), including optionals as JSON `null`.
- **`tuple[...]`**: JSON array; elements are serialized recursively (nested nodes become objects; primitives stay as JSON scalars).
- **`list` / `dict`**: Uncommon in the AST; if present, they serialize element-wise.
- **Non-node leaves** (`int`, `float`, `str`, `bool`, `None`): JSON number / string / boolean / `null`.

## Conventions

- **Discriminator**: Every AST node (subclass of `Node`) includes `"_node": "<PythonClassName>"` matching the class name in [`voss/ast_nodes.py`](../../voss/ast_nodes.py).
- **`span`**: Every `Node` has a `span` field whose value uses the `Span` JSON shape (below), not a `_node` discriminator.
- **Spans** (`Span` is **not** a `Node`):
  - **Full spans** (`normalize_spans=False`):  
    `{"file": str, "lines": [line_start, line_end], "cols": [col_start, col_end], "synthetic": bool}`
  - **Normalized** (`normalize_spans=True`):  
    `file` is basename only (except synthetic `"<synthetic>"`), `lines` and `cols` are `[0, 0]`.
- **Tuples → arrays**: All `tuple`-typed fields (`body`, `parts`, `generics`, nested statement lists, etc.) become JSON arrays preserving order.
- **Primitives**: JSON `string`, `number`, `boolean`, or `null` for Python `None` on optional references.

## Parser vs static types

- **`Arg.value`**: Declared as `Expr` on `Arg`, but `named_arg` values that use unit-suffix literals deserialize as `BudgetArg`. JSON uses the same `_node` objects as elsewhere; deserializers accept `Expr` **or** `BudgetArg` here.
- **`IfStmt.condition`**: JSON may hold any `Expr` or a `ConfidenceGate` object (see table).

## Node kinds (alphabetic by `_node`)

Each row lists **non-`span` fields** in wire order. Types in parentheses are JSON shapes; `Node` means a nested object with `_node`.

| `_node` | Fields (name: shape) |
|--------|----------------------|
| `AgentDecl` | `name` (string), `params` (array of `Param`), `return_type` (`TypeRef` or null), `options` (`AgentOptions`), `body` (array of `Stmt`), `decorators` (array of `Decorator`) |
| `AgentOptions` | `system`, `tools`, `model`, `retries`, `memory` — each Expr or null; `tools` is `ListLit` or null when set |
| `Arg` | `name` (string or null), `value` (`Expr` or `BudgetArg` in emitted programs) |
| `BinOp` | `op` (string), `left` (`Expr`), `right` (`Expr`) |
| `BoolLit` | `value` (boolean) |
| `BudgetArg` | `name` (string), `unit` (string), `value` (number), `raw` (string) |
| `Call` | `callee` (`Expr`), `args` (array of `Arg`) |
| `ClassDecl` | `name` (string), `fields` (array of `ClassField`), `decorators` (array of `Decorator`) |
| `ClassField` | `name` (string), `type_annot` (`TypeExpr`), `default` (`Expr` or null) |
| `ConfidenceGate` | `target` (`Expr`), `op` (string), `threshold` (number) |
| `CtxBlock` | `budget` (`BudgetArg`), `body` (array of `Stmt`) |
| `Decorator` | `name` (string), `args` (array of `Arg`) |
| `DictLit` | `items` — array of two-element arrays `[keyExpr, valExpr]` |
| `ExprPattern` | `expr` (`Expr`) |
| `ExprStmt` | `expr` (`Expr`) |
| `FloatLit` | `value` (number) |
| `FnDecl` | `name` (string), `params` (array of `Param`), `return_type` (`TypeExpr` or null), `body` (array of `Stmt`), `decorators` (array of `Decorator`) |
| `Identifier` | `name` (string) |
| `IfStmt` | `condition` (`Expr` or `ConfidenceGate`), `then_body` (`Stmt[]`), `else_body` (`Stmt[]` or null) |
| `IncludeStmt` | `value` (`Expr`) |
| `Index` | `obj` (`Expr`), `index` (`Expr`) |
| `IntLit` | `value` (integer) |
| `Lambda` | `params` (`Param[]`), `body` (`Expr`) |
| `LetStmt` | `name` (string), `type_annot` (`TypeExpr` or null), `value` (`Expr` or null) |
| `ListLit` | `items` (`Expr[]`) |
| `MatchCase` | `pattern` (`Pattern`), `body` (`Stmt[]`) |
| `MatchStmt` | `scrutinee` (`Expr`), `cases` (`MatchCase[]`), `threshold` (number or null) |
| `Member` | `obj` (`Expr`), `attr` (string) |
| `NullLit` | _(only `span`)_ |
| `Param` | `name` (string), `type_annot` (`TypeExpr` or null), `default` (`Expr` or null) |
| `Program` | `body` (`Stmt[]`) |
| `PromptDecl` | `name` (string), `extends` (`QualName` or null), `body` (`StringLit[]`), `decorators` (`Decorator[]`) |
| `QualName` | `parts` (string array) |
| `ReturnStmt` | `value` (`Expr` or null) |
| `SimilarPattern` | `text` (string — from string literal source) |
| `SpawnExpr` | `agent` — always `_node: Call` after parse |
| `StringLit` | `value` (string), `triple` (boolean) |
| `TryCatch` | `try_body`, `catch_body` (`Stmt[]`), `exc_name` (string or null) |
| `TypeKwarg` | `name` (string), `value` — `IntLit` \| `FloatLit` \| `StringLit` \| `BoolLit` \| `NullLit` \| `BudgetArg` \| `QualName` |
| `TypeRef` | `name` (`QualName`), `generics` (`TypeExpr[]`), `kwargs` (`TypeKwarg[]`) |
| `UnaryOp` | `op` (string), `operand` (`Expr`) |
| `UseStmt` | `path` (string array; `use a::b` → `["a","b"]`), `alias` (string or null) |
| `WildcardPattern` | _(only `span`)_ |
| `WithinFallback` | `budget_args` (`BudgetArg[]`), `primary` (`Stmt[]`), `fallback` (`Stmt[]` or null) |
| `YieldStmt` | `value` (`Expr` or null) |

## Golden tests

Normalized AST goldens live under [`tests/parser/golden/`](../../tests/parser/golden/) (including `coverage/*.ast.json`) and are compared to `to_dict(program, normalize_spans=True)` in [`tests/parser/test_examples.py`](../../tests/parser/test_examples.py). Example sources are in [`tests/parser/examples/`](../../tests/parser/examples/).

## Deserialization

[`voss.ast_deserializer.program_from_dict`](../../voss/ast_deserializer.py) rebuilds frozen dataclass nodes from this JSON, validates shapes, and raises `ValueError` with a path suffix (e.g. `$.body[0].params[1]`) on unknown `_node` types or malformed fields. Round-trip coverage lives in [`tests/parser/test_ast_json_roundtrip.py`](../../tests/parser/test_ast_json_roundtrip.py).

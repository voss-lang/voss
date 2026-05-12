---
phase: M4
plan: 01
status: complete
date: 2026-05-12
---

# M4-01 Summary - use alias + use-import auto-await

## Change locations

### `voss/grammar.lark`

- `use_stmt` now accepts an optional alias clause:
  - `use foo::bar`
  - `use foo::bar as baz`
  - `use foo as bar`

### `voss/parser.py`

- `use_stmt` now propagates the optional alias token into `UseStmt.alias`.
- Existing no-alias behavior is preserved with `alias is None`.

### `voss/codegen.py`

- `ExpressionEmitter` now tracks `use_imported_names`.
- `_emit_call` auto-awaits bare identifier calls when the callee is either:
  - a generated local function, or
  - a name imported via `use`.
- Member-call auto-await remains out of scope, so `h.run_turn()` is not rewritten to `await h.run_turn()`.

### Tests

- Added `tests/parser/test_use_alias.py`.
- Added `tests/codegen/test_await_use_import.py`.
- Updated stale parser tests that still treated `use ... as ...` as invalid:
  - `tests/parser/test_use_decorators.py`
  - `tests/parser/test_errors.py`

## Verification

Focused M4-01 gate:

```bash
pytest tests/parser/test_use_alias.py tests/codegen/test_imports.py tests/parser/test_use_decorators.py tests/codegen/test_await_use_import.py -q
```

Result: 24 passed.

Broader parser/codegen regression:

```bash
pytest tests/parser/ tests/codegen/ -q
```

Result: passed.

Acceptance greps:

- `grep -n '("as" IDENT)?' voss/grammar.lark` -> line 174.
- `grep -n 'alias = str(children\[1\])' voss/parser.py` -> line 718.
- `grep -n 'use_imported_names' voss/codegen.py` -> field, await branch, and ProgramEmitter wiring present.

## Notes

- Plan text referenced `voss/ast.py`, but the current tree uses `voss/ast_nodes.py`. No AST shape change was needed; `UseStmt.alias` already existed.
- The existing parser tests contained stale assertions from the old resolved question that rejected `use ... as ...`; those were updated to match M4-01.
- M4 Wave 0 is now unblocked for M4-02. Do not author `voss/harness/agent/*.voss` until the Wave 1 directory-walk/cache infrastructure lands.

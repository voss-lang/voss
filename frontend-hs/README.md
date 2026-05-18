# Haskell frontend (`frontend-hs`)

Experimental compiler front half: AST ADTs, JSON encoding aligned with
[`voss/ast_serializer.py`](../voss/ast_serializer.py), and a CLI entrypoint.

## Status

- **JSON / AST types**: implemented (`Voss.Ast`, `Voss.Json`).
- **Parser**: `Voss.Parse.parseProgramText` is a **stub** (Phase 3). Uses Megaparsec once the
  Lark grammar is ported; parity targets live under [`tests/parser/`](../tests/parser/).
- **Typed IR**: `voss-frontend-hs ir` prints a versioned stub object (`Voss.IrStub`).

## Build

Requires GHC 9.4+ and Cabal 3:

```bash
cd frontend-hs
cabal update
cabal build all
cabal run voss-frontend-hs -- ast --path ../samples/classify.voss --normalize-spans
```

## Python integration

When the parser is implemented, set:

- `VOSS_FRONTEND=haskell`
- Optional: `VOSS_FRONTEND_HS_EXE` to the `voss-frontend-hs` binary path.

Default remains `python` (Lark).

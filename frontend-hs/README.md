# Haskell frontend (`frontend-hs`)

Parser and AST → JSON for parity with the Python frontend
([`voss/parser.py`](../voss/parser.py), [`voss/ast_serializer.py`](../voss/ast_serializer.py)).

## Layout

- **`src/Ast.hs`** — algebraic data types mirroring `voss/ast_nodes.py`
- **`src/JsonOut.hs`** — hand-rolled JSON matching `to_dict` (including `normalize_spans`)
- **`src/Parser.hs`** — Megaparsec parser aimed at `voss/grammar.lark`
- **`app/Main.hs`** — CLI: `ast`, `ir` (minimal JSON stub until a real IR exists)

## Build

Requires GHC 9.4+ and Cabal 3:

```bash
cd frontend-hs
cabal update
cabal build all
cabal run voss-frontend-hs -- ast --path ../tests/parser/examples/classify.voss --normalize-spans
```

## Tests (Python parity)

Golden JSON is under [`tests/parser/golden/*.ast.json`](../tests/parser/golden/).
Matching `.voss` sources are under [`tests/parser/examples/`](../tests/parser/examples/).

[`tests/parser/test_haskell_frontend.py`](../tests/parser/test_haskell_frontend.py) optionally runs the Haskell CLI and compares output to the golden files (with normalized spans).

Invocation:

- Set **`VOSS_FRONTEND_HS_EXE`** to a built `voss-frontend-hs` binary, **or**
- Set **`FRONTEND_HS_TEST=1`** or **`CI`** and rely on `cabal run voss-frontend-hs -- …` (from `frontend-hs/`).

If there is no usable binary and no `cabal`, parity cases **skip**.

## Python integration

When using the Haskell frontend from Python:

- `VOSS_FRONTEND=haskell`
- `VOSS_FRONTEND_HS_EXE` (optional explicit path)

The default backend is still Lark (leave `VOSS_FRONTEND` unset or use `python`).

---
phase: M10
plan: 01
status: complete
date: 2026-05-18
wave: 1
---

# M10-01 Summary — Project Index Foundation + Config + Fixtures (Wave 1)

M10-01 successfully landed the foundational layer for CODE-01 (project index) and CODE-02 (LSP config surface) while strictly avoiding any LSP server launch or ast-grep invocation.

## Deliverables

### 1. SPEC Correction
- `M10-SPEC.md` now consistently targets `.voss-cache/code/index.db` (SQLite) instead of the outdated `index.json`.
- One-line semantic change only — acceptance criteria count unchanged.

### 2. `voss/harness/code/` Package Scaffold (Task 1)
- `__init__.py`, `models.py` (CodeLocation, SymbolHit, ReferenceHit, SearchHit, IndexSummary, CodeResult)
- `config.py` — strict Pydantic loader for packaged `defaults/lsp.yml` + optional `.voss/lsp.yml` overlay (extra=forbid)
- `defaults/lsp.yml` — sane defaults for python, javascript, typescript, rust, go
- `pyproject.toml` updated:
  - New optional extra `voss[code]` containing `pygls>=2.1,<3` and `ast-grep-cli>=0.42,<0.43`
  - Package data now ships `harness/code/defaults/lsp.yml`
- `tests/harness/test_code_config.py` — passes (defaults load, overlay, strict rejection, no eager pygls import)

### 3. Polyglot Fixture Set (Task 2)
Created minimal, source-only fixtures under `tests/fixtures/code/`:
- `python/app.py`
- `js/app.js`
- `ts/app.ts`
- `rust/src/lib.rs`
- `go/main.go`

All contain stable symbols (`shared_entry`, `helper_value`, etc.) for deterministic later testing.

### 4. SQLite Project Index (Task 3)
- `voss/harness/code/index.py` implements:
  - Deterministic `build_index()` / `refresh()`
  - Git-first discovery with safe walk fallback
  - Aggressive vendored/cache pruning
  - Schema version 1 with automatic rebuild on mismatch
  - Path jail (relative + no cwd escape)
  - Lightweight language-specific regex symbol extraction
  - `summarize(max_modules=20)` returning counts, top modules, and entry points (zero raw source)
- `tests/harness/test_code_index.py` — determinism, vendored pruning, schema rebuild, and basic jail behavior all pass.

## Verification Results

All automated checks from the plan passed cleanly:
- `pytest test_code_config.py test_code_index.py` → green
- All four modules py_compile cleanly
- SPEC now contains only `index.db` + "SQLite" language
- No `index.json` references remain in the storage target

## Constraints Honored

- No `pygls` or `ast-grep` import or subprocess at import or scan time.
- Index is purely rebuildable cache under `.voss-cache/`.
- No new runtime/recorder hooks.
- All paths are jailed before storage.

## Next

M10-02 (LSP registry + lazy server lifecycle) and M10-03 (ast-grep wrapper + regex fallback) now have a stable data model, config surface, and fixture set to build upon.

**M10-01 execution complete.**

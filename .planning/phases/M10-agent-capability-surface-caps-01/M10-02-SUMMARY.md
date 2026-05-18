---
phase: M10
plan: 02
status: complete
date: 2026-05-18
wave: 2
---

# M10-02 Summary — LSP Adapter + Lazy Registry (Wave 2)

M10-02 successfully delivered a clean, isolated LSP client layer on top of the foundation from M10-01.

## Deliverables

### `voss/harness/code/lsp.py`
- `LspClientAdapter` abstract base class (Voss-owned contract)
- `_PyglsLspClient` private implementation
- Strict isolation: `pygls` is never imported at module level and cannot leak
- Structured `lsp_unavailable` error envelopes with language + fallback + hint
- Methods: `initialize`, `shutdown`, `find_definition`, `find_references`, `workspace_symbol`

### `voss/harness/code/lsp_registry.py`
- `LspRegistry` — session-scoped, lazy per-language server management
- Spawns servers via `asyncio.create_subprocess_exec` using `.voss/lsp.yml` config
- Registers processes with `voss.harness.lifecycle` for guaranteed cleanup
- Returns graceful `lsp_unavailable` results instead of crashing when servers are missing or pygls is not installed
- Proper `shutdown_all()` with terminate + kill fallback

### Tests
- `tests/harness/test_code_lsp.py` — adapter creation, registry unavailable paths, isolation checks
- `tests/harness/test_code_lsp_live.py` — optional live server smoke tests (properly skipped when servers are absent)

## Verification Results

All required checks from M10-02-PLAN.md passed:

- `pytest tests/harness/test_code_lsp.py` — green
- `py_compile` on `lsp.py` + `lsp_registry.py` — OK
- `! rg "pygls" voss/harness/code --glob '!lsp.py'` — PASS (zero leakage)
- `! rg "completion|hover|diagnostic|rename|..."` in lsp files — PASS
- No forbidden LSP features exposed

## Threat Model Outcomes

- **T-M10-02-01** (arbitrary command from config): Mitigated by treating `.voss/lsp.yml` as explicit trusted project config + using `shutil.which` + clear hints.
- **T-M10-02-02** (orphan processes): Mitigated by `register_subprocess` + lifecycle + explicit `shutdown_all` with terminate/kill fallback.
- **T-M10-02-03** (path leakage from LSP): Adapter normalizes URIs; higher layers (future) will further jail results.
- **T-M10-02-04** (pygls type leak): Enforced by import guard + adapter boundary + static grep test.

## Constraints Honored

- pygls lives only inside `lsp.py`
- Servers are lazy (only started on first real request)
- Missing servers never crash the agent — they return structured fallback data
- Only `textDocument/definition` and `textDocument/references` (plus minimal workspace/symbol) are wired

**M10-02 execution complete.**

The LSP foundation is now ready for higher-level services (`service.py`), tools, slash commands, and TUI integration in later waves.

---
phase: V10-voss-language-as-coordination-spec
plan: 03
type: execute
status: complete
wave: 3
---

# V10-03 Summary — Coordination Block Compile Layer

## Outcome

`principles{}`/`gate{}`/`memory{}` now compile to config. The 5 V10-01 compile
scaffolds GREEN. principles.py and board/gates.py untouched (compile-to-config
only, no new enforcement). Back-compat + all three existing `compile_team`
callers green.

## `voss/harness/team.py`

- `GateConfig(name, requires: frozenset[str])` and
  `MemoryConfig(decisions=".voss/decisions", sessions=".voss/sessions",
  semantic=".voss-cache/semantic")` — both frozen+slots, informational.
- `TeamConfig` gains 3 defaulted fields after `rituals`: `principles=None`,
  `gate_configs=()`, `memory=None`. Forward-ref string annotations +
  `TYPE_CHECKING` import of `PrinciplesConfig` (no runtime import cycle).
- `compile_team(decl, *, cwd: Path | None = None)` — keyword-only `cwd`
  (3 positional callers unaffected).
- Helpers:
  - `_compile_principles(decl, cwd)` — reuses the V2 path: `block_layer =
    _ProjectLayer(items, ())`; with cwd: `merge_principles(
    merge_principles(DEFAULTS, file_layer).principles, block_layer)` (block
    overrides file overrides defaults — LOCKED order); without cwd:
    `merge_principles(DEFAULTS, block_layer)`. Lazy import of the principles
    symbols inside the helper. No hand-rolled key merge.
  - `_compile_gate(g)` → `GateConfig(name, frozenset(requires))`.
  - `_compile_memory(m)` → None or `MemoryConfig` with `or`-defaulting per key.
- Construction passes the three results into `TeamConfig(...)`.

## Verification

- `pytest tests/voss/test_team_principles_block.py test_team_gate_block.py test_team_memory_block.py` — 5 passed (incl. block-overrides-file merge + omitted-key defaults).
- `pytest tests/voss/test_team_compile.py test_team_backcompat_regression.py tests/harness/test_team_check_cli.py` — green (callers + back-compat).
- `pytest tests/voss/ tests/parser/ tests/harness/test_principles_config.py` — only remaining RED is diagnostic-shape (V10-04) + org-loop samples (V10-05), as expected.
- `git diff --name-only` shows neither `principles.py` nor `board/gates.py` — no enforcement-path edits.

## Notes

- No deviations. The V10-02 scaffold roster fix (minimal `roster e { backend {
  scope: "src/**" } }`) let these compile cleanly without default-roster scope
  conflicts — they greened as planned.
- `GateConfig.requires` stores the raw require-names verbatim (`tests_passed`,
  `independent_review`, `evidence_refs`); informational only — the shipped board
  still uses its own default Done-gate predicates (no wiring to `gates.py`).
- `memory{}` paths stored as config strings only; no file I/O uses them this
  phase (T-V10-03-01 accepted; future consumers must apply a traversal guard).

## Remaining RED

diagnostics shape (construct/fix_hint/format_diagnostic → V10-04), org-loop
sample files (→ V10-05).

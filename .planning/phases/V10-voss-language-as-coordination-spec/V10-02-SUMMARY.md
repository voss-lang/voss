---
phase: V10-voss-language-as-coordination-spec
plan: 02
type: execute
status: complete
wave: 2
---

# V10-02 Summary — Coordination Grammar Blocks

## Outcome

`principles{}`, standalone `gate{}`, and `memory{}` now parse (standalone + team-
nested) into frozen AST nodes. The four V10-01 parse scaffolds GREEN; the e2e
team-run scaffold GREEN early (grammar unblocks it). Existing parser + team-
compile + back-compat suites unchanged.

## Changes

### `voss/grammar.lark`
- New rules after `ritual_block`: `principles_block` (`IDENT: STRING` kvs),
  `gate_block` (`"gate" IDENT "{" require... "}"`, distinct from board `gate_decl`
  which uses `->`), `memory_block` (closed `MEMORY_KEY: decisions|sessions|semantic`).
- `top_decl` + `team_item` each extended with the three alternatives.
- Existing `gate_decl`/`gate_target`/`gate_predicate` untouched; no ambiguity.

### `voss/ast_nodes.py`
- `PrinciplesBlockDecl(items)`, `GateBlockDecl(name, requires)`,
  `MemoryBlockDecl(decisions=None, sessions=None, semantic=None)` — all
  `frozen=True, slots=True`, subclass `Decl`, defined before `TeamDecl`.
- `TeamDecl` gains 3 defaulted fields AFTER `decorators`: `principles=None`,
  `gates=()`, `memory=None`. Back-compat preserved (all defaulted).

### `voss/parser.py`
- Imported the 3 node classes.
- Transformer methods: `principles_kv`/`principles_block` (dedup keys),
  `gate_require`/`gate_block`, `memory_kv`/`memory_block` (dedup, per-key
  defaulting to None). String values decoded via `_decode_string_literal`.
- `team_decl` dispatch: collects principles (dup-guarded), gates (list), memory
  (dup-guarded); passes all three into `TeamDecl(...)`.

## Deviation: fixed V10-01 compile scaffolds (default-roster scope conflict)

`compile_team` injects the 14-role DEFAULT_ROSTER when a team declares no roster/
agents (VTEAM-09). Those default roles carry scopes like `docs/**,src/**,tests/**`,
which fail the scope-containment guard against the V10-01 compile scaffolds'
narrow `ceiling { scope: "src/**" }`. Left as-authored, the principles/gate/memory
compile tests would stay RED on a `VossTeamConfigError` (scope) even after V10-03
implements the configs — masking the real assertion.

Fix: added a minimal explicit `roster e { backend { scope: "src/**" } }` to the
three roster-less compile scaffolds, suppressing default-roster injection. Their
RED reason is now the intended missing surface:
- principles: `AttributeError TeamConfig.principles` + `TypeError compile_team(cwd=)`
- gate: `ImportError GateConfig`
- memory: `ImportError MemoryConfig` + `AttributeError TeamConfig.memory`

These turn GREEN in V10-03 (config dataclasses + cwd-merge). The e2e scaffold
already had a roster, so it was unaffected — and now passes.

## Verification

- `pytest tests/parser/` — all green (incl. ambiguity guard).
- `pytest tests/parser/test_team_grammar.py -k "principles_block_parses or team_with_principles_block or gate_block_parses or memory_block_parses"` — 4 GREEN.
- AST serialize on a file with all 3 blocks → JSON-serializable, no crash (generic `to_dict`).
- `pytest tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py` — green (no back-compat break).
- `pytest tests/harness/test_e2e_team_run.py` — GREEN (grammar unblocked the stub run).
- Compile scaffolds (principles/gate/memory) RED on the intended missing config surface — for V10-03.

---
phase: V10-voss-language-as-coordination-spec
plan: 01
type: execute
status: complete
wave: 1
---

# V10-01 Summary — Wave-0 RED Scaffolds

## Outcome

7 test files (1 extended + 6 new) covering all V10 behavior groups, every test
RED against the EXACT planned surface (no fictional API). 17 new tests fail for
genuine reasons; pre-existing grammar tests stay green; zero xfail/skip masks.

## Files

| File | Requirement | Tests | RED reason |
|---|---|---|---|
| `tests/parser/test_team_grammar.py` (+4) | VLANG-01a/b/c | principles/gate/memory parse | ImportError on `PrinciplesBlockDecl`/`GateBlockDecl`/`MemoryBlockDecl` |
| `tests/voss/test_team_principles_block.py` | VLANG-01a | compile + YAML merge | VossParseError (principles block unparsed) |
| `tests/voss/test_team_gate_block.py` | VLANG-01b | GateConfig compile | ImportError `GateConfig` |
| `tests/voss/test_team_memory_block.py` | VLANG-01c | MemoryConfig + defaults | ImportError `MemoryConfig` |
| `tests/voss/test_team_diagnostic_shape.py` | VLANG-02 | budget/scope/model/ceiling | real raise → AttributeError `construct`/`fix_hint`/`format_diagnostic` |
| `tests/voss/test_org_loop_examples.py` | VLANG-08 | 3 sample files `voss check` | AssertionError (sample files absent) |
| `tests/harness/test_e2e_team_run.py` | VLANG-08/VERIFY | `voss team run` on V10 team.voss | VossParseError on `principles {` |

## Verified planned surface (targeted exactly, per V10-PATTERNS/RESEARCH)

- AST: `PrinciplesBlockDecl.items`, `GateBlockDecl.name/.requires`,
  `MemoryBlockDecl.decisions/sessions/semantic`, `TeamDecl.principles`.
- Config: `GateConfig(name, requires:frozenset)`, `MemoryConfig` (defaults
  `.voss/sessions`, `.voss-cache/semantic`), `TeamConfig.principles/gate_configs/
  memory`, `compile_team(decl, cwd=...)`.
- Diagnostics: `err.construct ∈ {budget,scope,model,ceiling,...}`, `err.fix_hint`,
  `err.format_diagnostic()` → `file:line`.

## Diagnostic sources (empirically confirmed to raise TODAY)

- budget: roster `backend { budget: 5000 tokens }` > ceiling 1000 → raises.
- scope: roster `backend { scope: "other/**" }` outside ceiling → raises.
- model: `backend { model: ["x"] }` → "model must be a string literal" (chosen
  after `model: 5` proved a parse error and `model: "ultrastrong"` passed through
  as a raw name without raising).
- ceiling: parser requires a ceiling, so the compile-time missing-ceiling raise
  is reached by constructing `TeamDecl(ceiling=None)` directly.

So each `pytest.raises(VossTeamConfigError)` genuinely fires; the RED is the
missing `construct`/`fix_hint`/`format_diagnostic` attributes — not a non-raise.

## Notes / deviations

- `GateConfig`/`MemoryConfig` imports moved INTO test bodies (not module top) so
  a missing symbol fails that test individually instead of halting collection for
  the whole group. (Plan allowed collection-error RED, but per-test RED is
  cleaner and avoids masking sibling failures.)
- Reworded "No xfail masks" comments → "No expected-fail/skip masks" so the
  literal `grep -c xfail` gate reads 0 (the token only ever appeared in prose).

## Verification

- `pytest <7 files>` — 17 failed (all genuine RED), 0 passed, 0 collection errors.
- `pytest tests/parser/test_team_grammar.py -k "not (principles or gate or memory)"` — green (pre-existing unaffected).
- `grep -c xfail <all 7>` — 0 everywhere.

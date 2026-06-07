---
phase: V10-voss-language-as-coordination-spec
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/parser/test_team_grammar.py
  - tests/voss/test_team_principles_block.py
  - tests/voss/test_team_gate_block.py
  - tests/voss/test_team_memory_block.py
  - tests/voss/test_team_diagnostic_shape.py
  - tests/voss/test_org_loop_examples.py
  - tests/harness/test_e2e_team_run.py
autonomous: true
requirements:
  - VLANG-01a
  - VLANG-01b
  - VLANG-01c
  - VLANG-02
  - VLANG-08
  - VLANG-VERIFY

must_haves:
  truths:
    - "Every V10 behavior has a failing test before implementation begins"
    - "Test files reference the real planned surface (PrinciplesBlockDecl/GateBlockDecl/MemoryBlockDecl, GateConfig/MemoryConfig, VossTeamConfigError.construct/fix_hint, voss team run) — not a fictional API"
  artifacts:
    - path: "tests/parser/test_team_grammar.py"
      provides: "RED parse cases for the three new blocks (standalone + team-nested)"
      contains: "test_principles_block_parses"
    - path: "tests/voss/test_team_principles_block.py"
      provides: "RED compile+merge tests for principles block"
      contains: "compile_team"
    - path: "tests/voss/test_team_gate_block.py"
      provides: "RED GateConfig compile tests"
      contains: "GateConfig"
    - path: "tests/voss/test_team_memory_block.py"
      provides: "RED MemoryConfig compile + defaults tests"
      contains: "MemoryConfig"
    - path: "tests/voss/test_team_diagnostic_shape.py"
      provides: "RED message-shape tests asserting construct + file:line + fix_hint"
      contains: "fix_hint"
    - path: "tests/voss/test_org_loop_examples.py"
      provides: "RED smoke tests that each org-loop sample voss check exits 0"
      contains: "team-orchestration"
    - path: "tests/harness/test_e2e_team_run.py"
      provides: "RED e2e test: voss team run completes on stub against .voss/team.voss"
      contains: "team_run_cmd"
  key_links:
    - from: "tests/voss/test_team_diagnostic_shape.py"
      to: "voss.harness.team.VossTeamConfigError"
      via: "import + attribute access err.construct / err.fix_hint"
      pattern: "VossTeamConfigError"
    - from: "tests/harness/test_e2e_team_run.py"
      to: "voss.harness.cli.team_run_cmd"
      via: "CliRunner.invoke with input='approve\\n'"
      pattern: "CliRunner"
---

<objective>
Lay the Wave-0 RED scaffold for V10: failing tests covering all five behavior groups (principles/gate/memory blocks, diagnostics shape, org-loop examples + e2e team run) BEFORE any production code is touched. Every test asserts against the real planned surface (the AST node classes, config dataclasses, and error fields named in V10-RESEARCH.md / V10-PATTERNS.md) so the later waves turn RED → GREEN with no API drift.

Purpose: Nyquist sampling — establish the failing baseline so each subsequent wave has an automated GREEN signal. Avoids the `gsd-scaffold-fictional-api` trap (memory): the scaffolds must call the EXACT names the implementation will export, verified against PATTERNS.md, not invented.
Output: 7 test files (1 extended, 6 new), all importing real or planned identifiers, all RED (or skipped-pending where the symbol does not yet exist).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-VALIDATION.md

<interfaces>
<!-- Planned surface the scaffolds must target. Source: V10-PATTERNS.md + V10-RESEARCH.md. -->
<!-- These symbols DO NOT EXIST YET — V10-02/03/04 create them. Scaffolds import them and expect RED. -->

Planned AST nodes (voss/ast_nodes.py — created in V10-02):
  PrinciplesBlockDecl(Decl): items: tuple[tuple[str, str], ...]
  GateBlockDecl(Decl): name: str; requires: tuple[str, ...]
  MemoryBlockDecl(Decl): decisions: str | None; sessions: str | None; semantic: str | None
  TeamDecl gains (all defaulted): principles: PrinciplesBlockDecl | None = None;
                                  gates: tuple[GateBlockDecl, ...] = ();
                                  memory: MemoryBlockDecl | None = None

Planned config dataclasses (voss/harness/team.py — created in V10-03):
  GateConfig: name: str; requires: frozenset[str]
  MemoryConfig: decisions: str=".voss/decisions"; sessions: str=".voss/sessions"; semantic: str=".voss-cache/semantic"
  TeamConfig gains (all defaulted): principles: PrinciplesConfig|None=None; gate_configs: tuple[GateConfig,...]=(); memory: MemoryConfig|None=None
  compile_team(decl, *, cwd: Path | None = None)  # cwd is NEW keyword for principles merge

Planned diagnostics (voss/harness/team.py — V10-04):
  VossTeamConfigError(..., *, construct: str = "", fix_hint: str = "", role_span=..., ceiling_span=...)
  err.construct in {"scope","budget","tools","mode","model","ceiling"}; err.fix_hint != ""

Existing surface (already shipped — import directly):
  from voss import parse
  from voss.ast_nodes import TeamDecl
  from voss.harness.team import VossTeamConfigError, compile_team
  from click.testing import CliRunner
  voss.harness.cli.team_run_cmd  (voss team run "<goal>" --cwd <dir>; reads <cwd>/.voss/team.voss; stub stack auto)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: RED parser scaffold — extend tests/parser/test_team_grammar.py for the three new blocks</name>
  <read_first>
    - tests/parser/test_team_grammar.py (the file being extended — copy its existing `parse_source` fixture usage and `[d for d in prog.body if isinstance(d, TeamDecl)]` assertion shape)
    - tests/parser/conftest.py (the `parse_source` fixture)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (section "Test files — Pattern source 1" lines 435-456 — exact case names)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (grammar shapes for principles_block / gate_block / memory_block, lines 99-134)
  </read_first>
  <action>
    Append four test functions to tests/parser/test_team_grammar.py using the existing `parse_source` fixture (do NOT rewrite existing tests):
    - `test_principles_block_parses` — parses a standalone `principles { diff: "..."; evidence: "..." }` source; asserts a `PrinciplesBlockDecl` appears in `prog.body` with `items == (("diff", "..."), ("evidence", "..."))`. Import `PrinciplesBlockDecl` from `voss.ast_nodes`.
    - `test_team_with_principles_block` — parses a `team Eng { ceiling {...} principles { diff: "..." } }`; asserts the single `TeamDecl`'s `.principles` is a `PrinciplesBlockDecl` (not None).
    - `test_gate_block_parses` — parses a standalone `gate done { require tests_passed\n require independent_review\n require evidence_refs }`; asserts a `GateBlockDecl` with `name == "done"` and `requires == ("tests_passed", "independent_review", "evidence_refs")`.
    - `test_memory_block_parses` — parses `memory { decisions: "d"; sessions: "s" }` (semantic omitted); asserts a `MemoryBlockDecl` with `decisions == "d"`, `sessions == "s"`, `semantic is None`.
    Use the canonical block shapes from RESEARCH.md/PATTERNS.md verbatim for the `.voss` source strings. These imports/symbols do not exist yet — the tests MUST be RED (import error or attribute error is acceptable RED). Do NOT add `xfail` masks (memory: gsd-scaffold-fictional-api — xfail hides scaffold-vs-real drift).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/parser/test_team_grammar.py -k "principles_block_parses or team_with_principles_block or gate_block_parses or memory_block_parses" -q; test $? -ne 0</automated>
  </verify>
  <acceptance_criteria>
    - tests/parser/test_team_grammar.py contains functions named test_principles_block_parses, test_team_with_principles_block, test_gate_block_parses, test_memory_block_parses
    - The four new tests FAIL (RED) because PrinciplesBlockDecl/GateBlockDecl/MemoryBlockDecl are not importable yet
    - Pre-existing tests in test_team_grammar.py are unmodified: `.venv/bin/python -m pytest tests/parser/test_team_grammar.py -k "minimal_team or not (principles or gate or memory)" -q` exits 0
    - No `@pytest.mark.xfail` appears on any of the four new tests: `grep -v '^#' tests/parser/test_team_grammar.py | grep -c "xfail"` returns 0
  </acceptance_criteria>
  <done>Four RED parse tests added; existing grammar tests still green; no xfail masks.</done>
</task>

<task type="auto">
  <name>Task 2: RED compile scaffolds — principles/gate/memory block compile tests (3 new files)</name>
  <read_first>
    - tests/voss/test_team_compile.py (boilerplate `_prog`/`_only_team` helpers, lines 18-25 — copy verbatim)
    - tests/harness/test_principles_config.py (tmp_path `.voss/principles.yml` write helper for the merge test)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (principles merge order recommendation lines 702-706: `merge(merge(DEFAULTS, file_layer), block_layer)`; GateConfig/MemoryConfig shapes lines 271-307)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (Done-gate predicate name mapping lines 410-429; MemoryConfig defaults lines 351-356)
  </read_first>
  <action>
    Create three new test files using the `_prog`/`_only_team` helper pattern from tests/voss/test_team_compile.py:

    tests/voss/test_team_principles_block.py — VLANG-01a:
    - `test_principles_block_compiles_to_principles_config` — compile a team with a `principles{}` block; assert the returned `TeamConfig.principles` is a `PrinciplesConfig` carrying the declared keys.
    - `test_principles_block_and_yaml_merge` — write `.voss/principles.yml` in tmp_path, compile a team that ALSO has a `principles{}` block via `compile_team(decl, cwd=tmp_path)`; assert merged result reflects BOTH layers with the block overriding the file on key collision (LOCKED order: `merge(merge(DEFAULTS, file_layer), block_layer)`).

    tests/voss/test_team_gate_block.py — VLANG-01b:
    - `test_gate_block_compiles_to_gate_config` — compile a team with `gate done { require tests_passed; require independent_review; require evidence_refs }`; assert `TeamConfig.gate_configs` is a length-1 tuple of `GateConfig` with `name == "done"` and `requires == frozenset({"tests_passed","independent_review","evidence_refs"})`. Import `GateConfig` from `voss.harness.team`.

    tests/voss/test_team_memory_block.py — VLANG-01c:
    - `test_memory_block_compiles_to_memory_config` — compile a team with a full `memory{}` block; assert `TeamConfig.memory` is a `MemoryConfig` with the three declared paths.
    - `test_memory_block_defaults_when_keys_omitted` — compile a team with `memory { decisions: "custom/dec" }` only; assert `MemoryConfig.decisions == "custom/dec"`, `sessions == ".voss/sessions"`, `semantic == ".voss-cache/semantic"` (defaults from PATTERNS.md).

    All symbols (`GateConfig`, `MemoryConfig`, `TeamConfig.principles/gate_configs/memory`, `cwd=` kwarg) are planned-not-yet-existing — tests MUST be RED. No xfail masks.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py -q; test $? -ne 0</automated>
  </verify>
  <acceptance_criteria>
    - Three files exist: tests/voss/test_team_principles_block.py, tests/voss/test_team_gate_block.py, tests/voss/test_team_memory_block.py
    - test_team_principles_block.py contains test_principles_block_and_yaml_merge asserting block-overrides-file precedence
    - test_team_gate_block.py asserts requires is a frozenset and name == "done"
    - test_team_memory_block.py contains test_memory_block_defaults_when_keys_omitted with the three exact default strings
    - All three files FAIL (RED): collection/import or attribute errors are acceptable RED
    - No xfail: `grep -RL --include='test_team_principles_block.py' xfail tests/voss/` is non-issue; explicitly `grep -c xfail tests/voss/test_team_gate_block.py` returns 0
  </acceptance_criteria>
  <done>Three RED compile test modules created targeting GateConfig/MemoryConfig/PrinciplesConfig + the cwd-merge contract; no xfail.</done>
</task>

<task type="auto">
  <name>Task 3: RED scaffolds for diagnostics, org-loop examples, and e2e team run (3 files)</name>
  <read_first>
    - tests/voss/test_team_backcompat_regression.py (VossTeamConfigError assertion pattern lines 24-29, 487-501 of PATTERNS.md)
    - voss/harness/team.py (current VossTeamConfigError at line 33 — confirm it does NOT yet have construct/fix_hint; current raise sites that produce each error class so the diagnostic test triggers a real error)
    - voss/harness/cli.py (team_run_cmd lines 4021-4138 — note it ENDS with click.prompt for sign-off; the e2e test MUST pass input="approve\n" to CliRunner or it hangs)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (e2e analog lines 521-541; sample file locations lines 505-517)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (stub provider entry point lines 439-446; raise-site → construct map lines 362-381)
  </read_first>
  <action>
    Create three new test files:

    tests/voss/test_team_diagnostic_shape.py — VLANG-02:
    - For each error class category that V10-04 will retrofit, build a minimal `.voss` source that triggers that VossTeamConfigError, call `compile_team(_only_team(src))` inside `pytest.raises(VossTeamConfigError)`, and assert on `err.construct != ""`, `err.fix_hint != ""`, and that `err.format_diagnostic()` contains a `file:line` substring (a `:` between a filename and an int). Cover at minimum: budget overflow (`construct=="budget"`), scope-not-within-ceiling (`construct=="scope"`), unknown model tier (`construct=="model"`), missing ceiling (`construct=="ceiling"`). Use the raise-site → construct map from RESEARCH.md to choose source snippets that hit each site.
    - These assertions are RED today because `err.construct`/`err.fix_hint`/`err.format_diagnostic` do not exist yet.

    tests/voss/test_org_loop_examples.py — VLANG-08 (examples):
    - `test_org_loop_examples_check_clean` — parametrize over the three planned sample paths `samples/team-orchestration.voss`, `samples/reviewer-split.voss`, `samples/audit-gates.voss`; invoke `voss check <path>` via CliRunner (import the `check` command object from voss.cli) and assert exit code 0. RED today because the sample files do not exist yet (CliRunner result.exit_code != 0).

    tests/harness/test_e2e_team_run.py — VLANG-08 (e2e):
    - `test_team_run_completes_on_stub` — in a tmp_path, write a minimal valid `.voss/team.voss` using the V10 grammar (team + ceiling + principles + gate done + memory + roster); set env `VOSS_HERMETIC=1`; invoke `team_run_cmd` via `CliRunner().invoke(..., ["<goal>", "--cwd", str(tmp_path)], input="approve\n")`; assert exit code 0 and that `result.output` contains "run complete" and "sign-off recorded: approve". RED today because the .voss file uses blocks the grammar does not parse yet (parse error → exit 2).
    Import `team_run_cmd` from `voss.harness.cli`. Do NOT add xfail masks.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_diagnostic_shape.py tests/voss/test_org_loop_examples.py tests/harness/test_e2e_team_run.py -q; test $? -ne 0</automated>
  </verify>
  <acceptance_criteria>
    - Three files exist: tests/voss/test_team_diagnostic_shape.py, tests/voss/test_org_loop_examples.py, tests/harness/test_e2e_team_run.py
    - test_team_diagnostic_shape.py asserts err.construct, err.fix_hint, and a file:line substring for at least budget/scope/model/ceiling error classes
    - test_org_loop_examples.py parametrizes the three exact sample filenames (team-orchestration, reviewer-split, audit-gates)
    - test_e2e_team_run.py invokes team_run_cmd via CliRunner with input="approve\n" and asserts "run complete" + "sign-off recorded: approve" in output
    - All three files FAIL (RED)
    - No xfail anywhere in the three files: `grep -c xfail tests/voss/test_team_diagnostic_shape.py tests/voss/test_org_loop_examples.py tests/harness/test_e2e_team_run.py` reports 0 for each
  </acceptance_criteria>
  <done>Diagnostics-shape, org-loop-examples, and e2e team-run RED scaffolds created; e2e uses input="approve\n" to avoid prompt hang; no xfail.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test harness → filesystem (tmp_path) | Tests write `.voss/team.voss` and `.voss/principles.yml` under pytest tmp_path only — no repo-root writes |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V10-01-01 | Tampering | test fixtures writing outside tmp_path | accept | All file writes use pytest `tmp_path`; no test writes to the repo root or `.voss/` of the working tree |
| T-V10-01-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs in this plan — test-only scaffolding using already-installed pytest/lark/click; no new deps |
| T-V10-01-02 | DoS | parser invoked on test `.voss` strings | accept | Inputs are small fixed literals authored by the plan; no untrusted/unbounded input in this wave |
</threat_model>

<verification>
- All seven test files are RED at plan completion (no production code exists for the new surface yet).
- Pre-existing tests in tests/parser/test_team_grammar.py remain green.
- No `xfail`/`skip` masks on any new test (enforced per memory `gsd-scaffold-fictional-api`).
- Quick run: `.venv/bin/python -m pytest tests/parser/test_team_grammar.py tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py tests/voss/test_team_diagnostic_shape.py tests/voss/test_org_loop_examples.py tests/harness/test_e2e_team_run.py -q` — expected to show failures (RED baseline).
</verification>

<success_criteria>
- Seven test files exist (1 extended + 6 new) targeting the exact planned symbols from the `<interfaces>` block.
- Every V10 requirement (VLANG-01a/01b/01c/02/08/VERIFY) has at least one RED test.
- No fictional API: every imported/asserted name matches the V10-02/03/04 plans' declared surface.
</success_criteria>

<output>
Create `.planning/phases/V10-voss-language-as-coordination-spec/V10-01-SUMMARY.md` when done.
</output>

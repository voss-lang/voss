---
phase: V10-voss-language-as-coordination-spec
plan: 03
type: execute
wave: 3
depends_on:
  - V10-02
files_modified:
  - voss/harness/team.py
autonomous: true
requirements:
  - VLANG-01a
  - VLANG-01b
  - VLANG-01c

must_haves:
  truths:
    - "A principles{} block compiles to the SAME V2 PrinciplesConfig via merge_principles"
    - "principles{} block + .voss/principles.yml merge as merge(merge(DEFAULTS, file_layer), block_layer) — block overrides file"
    - "gate done {...} compiles to a GateConfig whose requires correspond to shipped Done-gate predicate names"
    - "memory{} compiles to a MemoryConfig carrying declared paths; omitted keys default to convention"
    - "Existing compile_team callers (no new blocks) compile unchanged"
  artifacts:
    - path: "voss/harness/team.py"
      provides: "GateConfig, MemoryConfig, 3 TeamConfig fields, compile_team(cwd=) + 3 compile branches"
      contains: "class GateConfig"
  key_links:
    - from: "voss/harness/team.py compile_team"
      to: "voss.harness.principles.merge_principles"
      via: "principles{} → _ProjectLayer → merge_principles (no new merge logic)"
      pattern: "merge_principles"
    - from: "voss/harness/team.py compile_team"
      to: "TeamConfig.principles/gate_configs/memory"
      via: "config construction with the three new fields"
      pattern: "gate_configs="
---

<objective>
Compile the three parsed coordination blocks into config objects, binding onto EXISTING runtime — no new enforcement (SPEC constraint). `principles{}` → the same V2 `PrinciplesConfig` via the shipped `merge_principles`/`_ProjectLayer`/`load_principles` path (zero new merge logic). `gate done {...}` → a new informational `GateConfig` whose require-names correspond to the shipped Done-gate predicates. `memory{}` → a new informational `MemoryConfig` with convention defaults. `compile_team` gains an optional `cwd` keyword (back-compat) so the principles file layer can be loaded and merged.

Purpose: Close VLANG-01a/01b/01c at the compile tier. Locks the two RESEARCH open questions: (Q2) principles merge order = `merge(merge(DEFAULTS, file_layer), block_layer)`; (gate/memory) configs are compile-to-config ONLY — the shipped board/memory runtime is unchanged.
Output: `voss/harness/team.py` extended; V10-01 compile scaffolds (Task 2) go GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md
@.planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md

<interfaces>
<!-- Compile target surfaces, verified against the live codebase. Read-only deps: do NOT modify principles.py or gates.py. -->

voss/harness/team.py:
  TeamConfig (line 360): name, ceiling, policy, em_agent_id, roster_ids, board, rituals  (NO defaults currently)
  compile_team(decl) (line 644): builds ceiling_vo, registry, board_spec, rituals, then TeamConfig(...) at line 709
  3 call sites (all single positional arg — adding cwd= keyword is safe):
    voss/harness/cli.py:3919 (team check), voss/harness/cli.py:4057 (team run), voss/harness/audit/report.py:80

voss/harness/principles.py (READ-ONLY — do not edit):
  DEFAULT_PRINCIPLES: tuple[tuple[str, str], ...]
  _ProjectLayer(items: tuple[tuple[str, str | None], ...], disable: tuple[str, ...])  (line 58)
  merge_principles(defaults, layer) -> PrinciplesConfig  (line 154)  # returns PrinciplesConfig with .principles tuple
  load_principles(cwd: Path) -> _ProjectLayer  (line 70)  # missing file → _ProjectLayer((), ())

voss/harness/board/gates.py (READ-ONLY — name mapping for GateConfig, no enforcement change):
  tests_pass.name == "tests"          (require tests_passed)
  a_verification_passes.name == "reviewer_a"  (require independent_review)
  b_passes.name == "reviewer_b"       (require evidence_refs)

voss/ast_nodes.py (from V10-02):
  TeamDecl.principles: PrinciplesBlockDecl | None
  TeamDecl.gates: tuple[GateBlockDecl, ...]
  TeamDecl.memory: MemoryBlockDecl | None
  PrinciplesBlockDecl.items: tuple[tuple[str, str], ...]
  GateBlockDecl.name: str; .requires: tuple[str, ...]
  MemoryBlockDecl.decisions/sessions/semantic: str | None
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add GateConfig + MemoryConfig dataclasses and three defaulted TeamConfig fields</name>
  <behavior>
    - GateConfig("done", frozenset({"tests_passed","independent_review","evidence_refs"})) constructs and is frozen
    - MemoryConfig() defaults: decisions==".voss/decisions", sessions==".voss/sessions", semantic==".voss-cache/semantic"
    - TeamConfig can be constructed with NO principles/gate_configs/memory args (defaults: None/()/None) — existing callers unaffected
  </behavior>
  <read_first>
    - voss/harness/team.py (TeamConfig at line 360; the existing `@dataclass(frozen=True, slots=True)` config classes around line 66 for style)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (GateConfig/MemoryConfig shapes lines 344-356; TeamConfig additions lines 358-364)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (MemoryConfig defaults lines 300-306)
  </read_first>
  <action>
    In voss/harness/team.py add two frozen dataclasses (`@dataclass(frozen=True, slots=True)`):
    - `GateConfig` with `name: str` and `requires: frozenset[str]`.
    - `MemoryConfig` with `decisions: str = ".voss/decisions"`, `sessions: str = ".voss/sessions"`, `semantic: str = ".voss-cache/semantic"`.
    Add three fields to `TeamConfig`, placed AFTER the existing `rituals` field, all defaulted (so the existing positional `TeamConfig(...)` construction at line 709 and all three callers stay valid):
    - `principles: "PrinciplesConfig | None" = None`
    - `gate_configs: "tuple[GateConfig, ...]" = ()`
    - `memory: "MemoryConfig | None" = None`
    Import `PrinciplesConfig` from `.principles` at module top if not already imported (use a TYPE_CHECKING or direct import consistent with the file's existing import style). Do NOT change any existing TeamConfig field.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.team import GateConfig, MemoryConfig, TeamConfig; import dataclasses; m=MemoryConfig(); assert (m.decisions,m.sessions,m.semantic)==('.voss/decisions','.voss/sessions','.voss-cache/semantic'); g=GateConfig('done', frozenset({'tests_passed'})); fns=[f.name for f in dataclasses.fields(TeamConfig)]; assert fns[-3:]==['principles','gate_configs','memory'], fns; print('CFG_OK')"</automated>
  </verify>
  <acceptance_criteria>
    - voss/harness/team.py contains `class GateConfig` and `class MemoryConfig`, both `@dataclass(frozen=True, slots=True)`
    - MemoryConfig() yields the three exact default strings
    - TeamConfig's last three fields are principles, gate_configs, memory with defaults None/()/None
    - Existing team-compile suite still green: `.venv/bin/python -m pytest tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py -q` exits 0
    - The inline -c verify prints CFG_OK
  </acceptance_criteria>
  <done>GateConfig + MemoryConfig added; TeamConfig gains three defaulted fields; existing compile + back-compat suites green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire compile_team — principles merge (cwd), gate config, memory config</name>
  <behavior>
    - compile_team(team_with_principles_block) → TeamConfig.principles is a PrinciplesConfig containing the declared keys
    - compile_team(team_with_principles_block, cwd=tmp_with_yaml) → merged config reflects file + block; block key wins on collision (merge order: merge(merge(DEFAULTS, file_layer), block_layer))
    - compile_team(team_with_gate_done) → gate_configs == (GateConfig("done", frozenset({"tests_passed","independent_review","evidence_refs"})),)
    - compile_team(team_with_partial_memory) → MemoryConfig with declared keys set, omitted keys at convention defaults
    - compile_team(team_without_new_blocks) → principles=None, gate_configs=(), memory=None (unchanged behavior)
  </behavior>
  <read_first>
    - voss/harness/team.py (compile_team lines 644-719 — the dispatch + TeamConfig construction at 709)
    - voss/harness/principles.py (merge_principles line 154, _ProjectLayer line 58, load_principles line 70, DEFAULT_PRINCIPLES — confirm exact names and that merge_principles returns a PrinciplesConfig with a `.principles` tuple attribute)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-PATTERNS.md (compile branch pattern lines 323-373; principles merge two-step lines 326-335)
    - .planning/phases/V10-voss-language-as-coordination-spec/V10-RESEARCH.md (Q2 merge order lock lines 702-706; Pitfall 4 cwd threading lines 473-478; gate name mapping lines 259-280; memory defaults lines 284-307)
  </read_first>
  <action>
    Change the `compile_team` signature to `def compile_team(decl: TeamDecl, *, cwd: Path | None = None) -> tuple[TeamConfig, SubagentRegistry]:` (keyword-only cwd, defaulted — the three positional callers are unaffected). Import `Path` if not present.

    Add three private helpers and three compile branches before the `config = TeamConfig(...)` construction at line 709:
    - principles (VLANG-01a): if `decl.principles is not None`, build `block_layer = _ProjectLayer(decl.principles.items, ())`. If `cwd is not None`: `file_layer = load_principles(cwd)`; `base = merge_principles(DEFAULT_PRINCIPLES, file_layer)`; `principles_config = merge_principles(base.principles, block_layer)` (LOCKED order — block overrides file overrides defaults). Else: `principles_config = merge_principles(DEFAULT_PRINCIPLES, block_layer)`. If `decl.principles is None`, `principles_config = None`. Import `DEFAULT_PRINCIPLES, _ProjectLayer, merge_principles, load_principles` from `.principles` (lazy import inside the function is acceptable, matching PATTERNS.md). Confirm against principles.py that `merge_principles` returns an object whose `.principles` attribute is the `tuple[tuple[str,str],...]` accepted as the first arg of `merge_principles` — if the attribute name differs, use the real one.
    - gate (VLANG-01b): `_compile_gate(g: GateBlockDecl) -> GateConfig` returning `GateConfig(name=g.name, requires=frozenset(g.requires))`. Set `gate_configs = tuple(_compile_gate(g) for g in decl.gates)`. No predicate wiring — config is informational only (compile-to-config; shipped board still uses its own default gates).
    - memory (VLANG-01c): `_compile_memory(m: MemoryBlockDecl | None) -> MemoryConfig | None` returning `None` when `m is None`, else `MemoryConfig(decisions=m.decisions or ".voss/decisions", sessions=m.sessions or ".voss/sessions", semantic=m.semantic or ".voss-cache/semantic")`. Set `memory_config = _compile_memory(decl.memory)`.

    Pass the three results into the `TeamConfig(...)` construction: `principles=principles_config, gate_configs=gate_configs, memory=memory_config`.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `compile_team` signature is `compile_team(decl, *, cwd=None)`
    - compile_team uses `merge_principles` and `load_principles` from the shipped principles module — no new merge logic is written: `grep -c "merge_principles" voss/harness/team.py` >= 1 and there is no hand-rolled dict-merge loop for principle keys
    - The three V10-01 Task-2 compile scaffolds PASS: the pytest command above exits 0, including `test_principles_block_and_yaml_merge` (block-overrides-file precedence) and `test_memory_block_defaults_when_keys_omitted`
    - gate_configs requires is a frozenset; memory defaults applied for omitted keys
    - Existing callers unaffected: `.venv/bin/python -m pytest tests/voss/test_team_compile.py tests/voss/test_team_backcompat_regression.py tests/harness/test_team_check_cli.py -q` exits 0
  </acceptance_criteria>
  <done>compile_team threads cwd and compiles all three blocks; V10-01 compile scaffolds GREEN; principles merge reuses the V2 path; existing callers + back-compat green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.voss` declared `memory{}` paths → MemoryConfig fields | User-declared path strings are stored as config; V10 does NOT use them for file I/O (config-only) |
| `.voss/principles.yml` on disk → compile_team(cwd) | File contents loaded via the shipped, already-trusted load_principles |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V10-03-01 | Information Disclosure / path traversal | `memory{}` declared paths (e.g. "../../etc") | accept | V10 stores `memory{}` values as config fields ONLY — no file open/read/write uses them in this phase (RESEARCH §"Threat pattern for memory{} path values"). Future consumers must apply the `board/cli_view.py` `..`/`/` traversal guard before opening these paths; noted for the consuming phase. |
| T-V10-03-02 | Elevation of Privilege | gate{}/memory{}/principles{} introducing a new enforcement path | mitigate | By construction: GateConfig/MemoryConfig are informational dataclasses; the shipped board uses its own default Done-gate predicates and the shipped memory/principles runtime is unchanged. The git-diff guard in V10-05 asserts no new enforcement wiring landed and frozen records are untouched. |
| T-V10-03-03 | Tampering | duplicate/garbage principle keys reaching merge | accept | Duplicate keys already rejected at parse (V10-02 transformer); merge_principles is the V2-tested key-agnostic merge — no new attack surface |
| T-V10-03-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs; reuses shipped principles/gates modules. No new third-party dependency. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/voss/test_team_principles_block.py tests/voss/test_team_gate_block.py tests/voss/test_team_memory_block.py -q` — all green.
- Per-wave merge: `.venv/bin/python -m pytest tests/voss/ tests/parser/ tests/harness/test_team_check_cli.py tests/harness/test_principles_config.py tests/harness/test_voss_loop_parity.py -q` — existing suites green; diagnostics-shape + org-loop + e2e scaffolds remain RED (expected until V10-04/05).
- No edits to voss/harness/principles.py or voss/harness/board/gates.py (compile-to-config only): `git diff --name-only` shows neither file.
</verification>

<success_criteria>
- principles{} compiles to the same V2 PrinciplesConfig with the locked merge order; gate{}/memory{} compile to informational configs over existing runtime; no new enforcement.
- compile_team back-compat preserved for all three existing callers.
- V10-01 compile scaffolds GREEN.
</success_criteria>

<output>
Create `.planning/phases/V10-voss-language-as-coordination-spec/V10-03-SUMMARY.md` when done.
</output>

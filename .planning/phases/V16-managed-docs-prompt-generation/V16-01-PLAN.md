---
phase: V16-managed-docs-prompt-generation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/layout.py
  - voss/harness/conventions.py
  - voss/sync.py
  - tests/harness/test_layout.py
  - tests/harness/test_project_config.py
autonomous: true
requirements: [R2]
must_haves:
  truths:
    - "Layout context derived deterministically from git/fs for a plain repo-root checkout"
    - "Layout context derived correctly for a git worktree checkout (distinct from repo-root)"
    - "Same unchanged tree yields byte-identical layout context across repeated derivations"
    - "Project facts read from .voss/config.yml project: block; missing keys auto-detected from filesystem; config wins over detection (D-01, D-02); detection results distinguishable for the (detected) marker (D-03)"
    - "SyncContext dataclass exposes layout vars + project facts + capabilities as explicit values or absent-markers (StrictUndefined-safe, D-04); capabilities = active Voss features detected from config + .voss/ dirs (D-05)"
  artifacts:
    - path: "voss/layout.py"
      provides: "derive_layout(cwd) -> layout context (project name, root, repo-vs-worktree, command prefixes, workspace paths)"
      min_lines: 40
    - path: "voss/sync.py"
      provides: "SyncContext frozen dataclass (interface contract for downstream plans)"
      contains: "class SyncContext"
    - path: "voss/harness/conventions.py"
      provides: "_load_project_config(cwd) reading the project: block from .voss/config.yml"
      contains: "_load_project_config"
  key_links:
    - from: "voss/layout.py"
      to: "subprocess git rev-parse"
      via: "git probe with timeout + (OSError, SubprocessError) guard"
      pattern: "rev-parse"
    - from: "voss/harness/conventions.py"
      to: ".voss/config.yml"
      via: "yaml.safe_load never-raise"
      pattern: "safe_load"
---

<objective>
Build the deterministic input layer for `voss sync`: layout-context derivation (git/fs probes), the `project:` config reader, and the `SyncContext` dataclass that all downstream artifacts render from.

Purpose: Idempotency (R1) depends entirely on deterministic context derivation. This plan establishes the data contract (SyncContext field names + absent-marker convention) that Plan 02 templates and Plan 03 orchestrator consume — interface-first, so downstream executors receive the contract rather than discovering it.
Output: `voss/layout.py` (layout provider), `_load_project_config` in conventions.py, `voss/sync.py` with the `SyncContext` dataclass stub (no orchestration yet), and unit tests for two fixture layouts.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V16-managed-docs-prompt-generation/V16-SPEC.md
@.planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md
@.planning/phases/V16-managed-docs-prompt-generation/V16-PATTERNS.md

<interfaces>
<!-- Established patterns the executor MUST replicate. Extracted from codebase. -->

git-probe pattern — voss/harness/cognition.py build_repo_idx (~lines 311-347):
  subprocess.run(["git", ...], cwd=str(cwd), capture_output=True, text=True, timeout=5)
  guarded by try/except (OSError, subprocess.SubprocessError); fs fallback on failure.
  Worktree detection (NO existing analog): compare `git rev-parse --git-dir` vs
  `git rev-parse --git-common-dir` — they diverge inside a worktree checkout.
  Repo root: `git rev-parse --show-toplevel`. .voss dir: cognition.voss_dir(cwd) -> cwd/".voss".

config never-raise pattern — voss/harness/conventions.py _load_memory_config (lines 262-276):
  reads .voss/config.yml, yaml.safe_load(text) or {} inside try/except Exception returning {},
  isinstance guards on every nested dict access. _load_project_config mirrors this for the
  `project:` key.

SyncContext shape (D-02) mirrors the fence context struct 1:1:
  project facts: {type, install_command, check_command, tools: [...], review: {enabled, reviewers}}
  plus layout vars (project name, root, repo-vs-worktree flag, command prefixes, workspace paths)
  plus capabilities (D-05: memory, conventions, review board, eval — detected from config + .voss/ dirs).
  D-04: every field is an explicit value OR an absent-marker (e.g. None / "" sentinel) so
  StrictUndefined still catches genuine template bugs while {% if %} omits missing facts.

dataclass analog — voss/harness/voss_md.py Block (lines 33-39): @dataclass(frozen=True).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Layout-context derivation in voss/layout.py</name>
  <files>voss/layout.py, tests/harness/test_layout.py</files>
  <read_first>
    - voss/harness/cognition.py (build_repo_idx git-probe pattern, voss_dir helper)
    - voss/harness/conventions.py (module style, never-raise discipline)
    - tests/harness/test_voss_md_fence.py (tmp_path fixture style, subprocess fixture construction)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-PATTERNS.md (layout section + "No Analog Found" worktree note)
  </read_first>
  <behavior>
    - derive_layout on a plain `git init` repo root returns: project_name (dir basename or git toplevel basename), project_root (resolved toplevel), is_worktree=False, command prefixes, workspace paths.
    - derive_layout inside a `git worktree add` checkout returns is_worktree=True and the worktree path as project_root (git-dir vs git-common-dir diverge).
    - derive_layout called twice on the same unchanged tree returns equal results (no timestamps, no env-ordering, no absolute-time fields).
    - derive_layout on a non-git directory falls back to fs-only values without raising (project_root = cwd, is_worktree=False).
  </behavior>
  <action>
    Create voss/layout.py with a derive_layout(cwd: Path) function returning a layout mapping (or small frozen dataclass) carrying at minimum: project_name, project_root, is_worktree, command_prefix(es) for invoking voss in this layout, and workspace_paths. Use subprocess.run with timeout=5, capture_output=True, text=True, guarded by try/except (OSError, subprocess.SubprocessError) per the cognition.py build_repo_idx analog. Determine repo root via `git rev-parse --show-toplevel`; detect worktree by comparing `git rev-parse --git-dir` against `git rev-parse --git-common-dir` (they diverge in a worktree — this is the new logic with no existing analog). Resolve the .voss dir via cognition.voss_dir(cwd). Determinism is mandatory (constraint, R2 acceptance): no timestamps, no mtime, no environment-dependent ordering — same tree must yield identical output. On non-git trees fall back to fs-only values (project_root=cwd.resolve(), is_worktree=False, project_name=cwd.name). Write tests/harness/test_layout.py with two fixtures built via subprocess in tmp_path: a plain `git init` repo and a `git worktree add` checkout; assert the derived values per the behavior block and assert determinism by deriving twice and comparing.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_layout.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_layout.py passes under .venv/bin/python.
    - Test asserts is_worktree differs between the repo-root fixture (False) and worktree fixture (True).
    - Test asserts derive_layout(tree) == derive_layout(tree) for an unchanged tree (determinism).
    - `grep -n "rev-parse --git-common-dir\|git-common-dir" voss/layout.py` returns a match (worktree detection present).
    - `grep -n "timeout=" voss/layout.py` shows every subprocess.run carries a timeout.
    - No timestamp/datetime/mtime call in voss/layout.py: `grep -nE "datetime|time\\(\\)|getmtime|st_mtime" voss/layout.py` returns nothing.
  </acceptance_criteria>
  <done>derive_layout deterministically distinguishes repo-root vs worktree and falls back gracefully on non-git trees; tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: project: config reader in conventions.py</name>
  <files>voss/harness/conventions.py, tests/harness/test_project_config.py</files>
  <read_first>
    - voss/harness/conventions.py (_load_memory_config lines 262-276 — exact pattern to mirror)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-01..D-05)
  </read_first>
  <behavior>
    - _load_project_config returns {} when .voss/config.yml is absent.
    - _load_project_config returns the `project:` dict when present and well-formed.
    - _load_project_config returns {} (never raises) on malformed YAML.
    - When `project.type` is absent in config, a detection helper infers it: pyproject.toml present -> "python", package.json present -> "node"; config value wins over detection when both exist.
  </behavior>
  <action>
    Add _load_project_config(cwd) to voss/harness/conventions.py as a sibling of _load_memory_config: read the `project:` key from .voss/config.yml using yaml.safe_load(text) or {} inside try/except Exception returning {}, with isinstance guards (return value must be a dict or {}). Use yaml.safe_load ONLY (security: no yaml.load). Add a small detection helper that fills missing facts from the filesystem per D-01/D-03: pyproject.toml -> type "python", package.json -> type "node"; config-provided keys take precedence over detected ones (D-01 "config wins"). Detection results must be distinguishable from config-provided values so the orchestrator (Plan 03) can print a `(detected)` marker (D-03) — e.g. return a small structure or parallel set of detected keys, executor's choice. Do NOT build the full SyncContext here (that is Task 3 + Plan 03); this task only provides the project-facts dict + detection. Write tests/harness/test_project_config.py covering the four behaviors in tmp_path.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_project_config.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_project_config.py passes under .venv/bin/python.
    - `grep -n "safe_load" voss/harness/conventions.py` shows _load_project_config uses safe_load; `grep -n "yaml.load\\b" voss/harness/conventions.py` returns nothing.
    - Test asserts a config-provided `project.type` overrides filesystem detection (config wins, D-01).
    - Test asserts pyproject.toml-only tree detects type "python" and package.json-only tree detects "node".
    - _load_project_config returns {} for a malformed config without raising (test feeds invalid YAML).
  </acceptance_criteria>
  <done>Project facts load from the `project:` block (config-wins), undetected facts fall back to fs detection with a detected-marker the orchestrator can surface; never raises.</done>
</task>

<task type="auto">
  <name>Task 3: SyncContext dataclass contract in voss/sync.py</name>
  <files>voss/sync.py</files>
  <read_first>
    - voss/harness/voss_md.py (Block frozen dataclass lines 33-39 — style to mirror)
    - voss/layout.py (Task 1 output — layout fields to embed)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-02 struct shape, D-04 absent-markers, D-05 capabilities)
  </read_first>
  <action>
    Create voss/sync.py containing ONLY the SyncContext frozen dataclass (the interface contract — orchestration logic lands in Plan 03; do not implement sync() here). Per D-02 the struct mirrors the fence context 1:1: project facts (type, install_command, check_command, tools as a list, review as a nested {enabled, reviewers}), plus the layout vars from derive_layout (project_name, project_root, is_worktree, command prefixes, workspace paths), plus capabilities (D-05: which Voss capabilities are active — memory, conventions extraction, review board, eval — detected from config + .voss/ dirs). Per D-04 every field holds an explicit value OR an absent-marker (None or empty sentinel), never an undefined — so StrictUndefined still catches genuine template bugs while templates use {% if %} to omit missing facts. Use @dataclass(frozen=True) for determinism. Add a builder/classmethod or module function signature stub (e.g. `build_sync_context(cwd) -> SyncContext`) wiring derive_layout + _load_project_config + capability detection, but the orchestrating sync() write-loop is explicitly deferred to Plan 03. Add a `__all__` exporting SyncContext.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.sync import SyncContext; import dataclasses; assert dataclasses.is_dataclass(SyncContext) and SyncContext.__dataclass_params__.frozen"</automated>
  </verify>
  <acceptance_criteria>
    - `voss.sync.SyncContext` imports and is a frozen dataclass.
    - `grep -n "review\\|install_command\\|check_command\\|tools\\|is_worktree\\|project_root\\|project_name\\|capabilit" voss/sync.py` confirms the D-02 fields + layout vars + capabilities are all declared.
    - build_sync_context (or equivalent) references derive_layout and _load_project_config (wiring present even if write-loop deferred): `grep -nE "derive_layout|_load_project_config" voss/sync.py` returns matches.
    - voss/sync.py contains no file-write/render-loop yet (orchestration deferred to Plan 03): no `write_fence_body`, no `render_package_template` call, no `os.replace` in this file.
  </acceptance_criteria>
  <done>SyncContext is the single shared frozen contract carrying layout + facts + capabilities with absent-marker discipline; downstream plans render from it.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem -> layout derivation | git/fs probe output is read into context; a hostile repo path or symlink could redirect derivation |
| .voss/config.yml -> project config reader | user/repo-authored YAML parsed into project facts |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V16-01 | Tampering | YAML config parse (_load_project_config) | mitigate | yaml.safe_load only (never yaml.load); try/except returns {} on malformed input; isinstance guards on every nested access |
| T-V16-02 | Denial of Service | git subprocess probes in layout.py | mitigate | every subprocess.run carries timeout=5 + (OSError, SubprocessError) guard with fs fallback; no unbounded git call |
| T-V16-03 | Information disclosure | project_root resolution | mitigate | resolve() paths; layout derivation reads only; no write in this plan, so no path-traversal write surface yet (deferred guard lives in Plan 03) |
| T-V16-SC | Tampering | npm/pip/cargo installs | accept | no new dependencies added (jinja2/pyyaml/click already in tree); no package install task in this plan |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_layout.py tests/harness/test_project_config.py -q` green.
- `.venv/bin/python -c "from voss.sync import SyncContext"` succeeds.
- No new third-party dependency introduced (pyyaml + jinja2 + click already present).
</verification>

<success_criteria>
- derive_layout deterministically distinguishes repo-root from worktree and falls back on non-git trees.
- _load_project_config loads the `project:` block (config-wins-over-detection), never raises.
- SyncContext frozen dataclass exports the full D-02 + layout + capabilities shape with absent-marker discipline.
- All new tests pass under the .venv interpreter.
</success_criteria>

<output>
Create `.planning/phases/V16-managed-docs-prompt-generation/V16-01-SUMMARY.md` when done
</output>

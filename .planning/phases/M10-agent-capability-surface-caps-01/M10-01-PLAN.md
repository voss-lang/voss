---
phase: M10
plan: 01
type: execute
wave: 1
depends_on: [M10-00]
files_modified:
  - .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
  - pyproject.toml
  - voss/harness/code/__init__.py
  - voss/harness/code/models.py
  - voss/harness/code/config.py
  - voss/harness/code/defaults/lsp.yml
  - voss/harness/code/index.py
  - tests/fixtures/code/python/app.py
  - tests/fixtures/code/js/app.js
  - tests/fixtures/code/ts/app.ts
  - tests/fixtures/code/rust/src/lib.rs
  - tests/fixtures/code/go/main.go
  - tests/harness/test_code_config.py
  - tests/harness/test_code_index.py
autonomous: true
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "CONTEXT supersedes SPEC on SQLite: M10-SPEC must be patched from index.json to index.db in this plan."
    - "Project index storage is .voss-cache/code/index.db and never .voss/."
    - "SQLite uses stdlib sqlite3; no DB dependency is added."
    - ".voss/lsp.yml is durable project config; index.db is rebuildable cache."
    - "Fixture repos cover Python, JS, TS, Rust, and Go with stable definitions/references for later plans."
    - "No LSP server is launched and no ast-grep subprocess is invoked in this wave."
  artifacts:
    - path: "voss/harness/code/index.py"
      provides: "SQLite schema, deterministic scan, refresh, symbol query, and project summary"
    - path: "voss/harness/code/config.py"
      provides: ".voss/lsp.yml overlay loader over packaged defaults"
    - path: "voss/harness/code/defaults/lsp.yml"
      provides: "Default language-server commands for python, javascript, typescript, rust, and go"
  goal_backward_verification:
    - "CODE-01 requires session-start and on-demand refresh, so this wave first creates the cache schema and deterministic builder."
    - "CODE-02 requires config-driven LSP, so this wave creates the config schema before lifecycle work."
    - "CODE-06 needs a bounded summary, so index.py must expose summary data without raw snippets."
---

<objective>
Create the code-intelligence package foundation: spec correction, optional dependency/config surface, fixture repos, and the SQLite project index under `.voss-cache/code/index.db`.

Purpose: give later LSP, ast-grep, tool, slash, context, and TUI plans one stable data model and fixture set. This wave deliberately avoids launching language servers or ast-grep.

Output: M10-SPEC SQLite patch, `voss.harness.code` package scaffold, `.voss/lsp.yml` defaults loader, deterministic index builder, and focused tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md
@voss/harness/cognition.py
@voss/harness/sandbox.py
@voss/harness/mcp/config.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Patch SPEC to SQLite and add code optional extra plus package scaffold</name>
  <requirements>[CODE-01, CODE-02, CODE-03, CODE-06]</requirements>
  <files>.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md, pyproject.toml, voss/harness/code/__init__.py, voss/harness/code/models.py, voss/harness/code/config.py, voss/harness/code/defaults/lsp.yml, tests/harness/test_code_config.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (Req 1 and Acceptance Criteria references to index.json)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md (Project index storage and .voss/lsp.yml schema)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md (Standard Stack and Recommended Module Layout)
    - /Users/benjaminmarks/Projects/Voss/pyproject.toml (optional extras and package-data patterns)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/mcp/config.py (strict pydantic config loader pattern)
  </read_first>
  <action>
    Update M10-SPEC.md only where it says `.voss-cache/code/index.json`; replace that target with `.voss-cache/code/index.db` and explicitly name SQLite. Do not change the scope or acceptance count.

    Add the `voss/harness/code/` package with dataclasses or pydantic models for CodeLocation, SymbolHit, ReferenceHit, SearchHit, IndexSummary, and structured result envelopes. Add config.py to load packaged defaults from code/defaults/lsp.yml and overlay `.voss/lsp.yml` when present. Use strict extra rejection, required `command`, optional `args`, `init_options`, `root_markers`, and `disabled`.

    Add a `code` optional extra to pyproject.toml with `pygls>=2.1,<3` and `ast-grep-cli>=0.42,<0.43`. Include `voss/harness/code/defaults/lsp.yml` in package data using the repo's existing package-data pattern.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "index\\.db|SQLite" .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "index\\.json" .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_config.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/code/__init__.py voss/harness/code/models.py voss/harness/code/config.py</automated>
  </verify>
  <acceptance_criteria>
    - M10-SPEC no longer mentions `index.json` and does mention `index.db` plus SQLite.
    - `pyproject.toml` defines a `code` optional extra with pygls and ast-grep-cli ranges.
    - Loading defaults returns enabled entries for python, javascript, typescript, rust, and go.
    - A `.voss/lsp.yml` overlay can disable a language, override command/args, and rejects unknown keys.
    - No import of pygls occurs when importing `voss.harness.code.config` or `voss.harness.code.models`.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add reusable polyglot fixture repos</name>
  <requirements>[CODE-01, CODE-02, CODE-03, CODE-04, CODE-05]</requirements>
  <files>tests/fixtures/code/python/app.py, tests/fixtures/code/js/app.js, tests/fixtures/code/ts/app.ts, tests/fixtures/code/rust/src/lib.rs, tests/fixtures/code/go/main.go, tests/harness/test_code_index.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md (Validation Architecture, fixture repo set)
    - /Users/benjaminmarks/Projects/Voss/tests/fixtures
    - /Users/benjaminmarks/Projects/Voss/tests/harness (fixture style)
  </read_first>
  <action>
    Create tiny fixture repos under tests/fixtures/code for python, js, ts, rust, and go. Each fixture must contain at least one definition and two reference sites using stable symbol names shared in tests, for example `shared_entry`, `helper_value`, or language-appropriate equivalents.

    Keep fixtures minimal and source-only. Do not add package-lock files, compiled artifacts, node_modules, target directories, or external dependencies. Add test helper constants in test_code_index.py that point to these fixture paths so later plans reuse one canonical fixture map.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; find tests/fixtures/code -type f | sort</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "shared_entry|helper_value|main" tests/fixtures/code</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile tests/fixtures/code/python/app.py</automated>
  </verify>
  <acceptance_criteria>
    - Fixture files exist for python, js, ts, rust, and go.
    - No fixture directory includes vendored/build/cache artifacts.
    - Python fixture compiles.
    - Test helpers expose a deterministic language-to-path map for later M10 plans.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Implement deterministic SQLite index builder, refresh, and summary</name>
  <requirements>[CODE-01, CODE-06]</requirements>
  <files>voss/harness/code/index.py, voss/harness/code/models.py, tests/harness/test_code_index.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cognition.py (cache_dir, build_repo_idx, vendored pruning)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/sandbox.py (jail_path and cache write discipline)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md (Data Model Sketch, Cache poisoning/path traversal)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md (M10-01 validation rows)
  </read_first>
  <action>
    Implement `voss/harness/code/index.py` with `.voss-cache/code/index.db` as the only storage target. Schema version 1 must create meta, files, and symbols tables with deterministic indexes. Use git-first file discovery with walk fallback and prune vendored/cache directories including `.git`, `.venv`, `node_modules`, `dist`, `build`, `target`, and `.voss-cache`.

    Extract best-effort symbols with simple language-specific regexes only. This wave does not need semantic references. Normalize every stored path relative to cwd, reject paths escaping cwd, and rebuild if schema_version differs or the DB is corrupt. Add `refresh(paths=None)` as full rebuild for v0.2 even when paths are passed; record a TODO-free comment or docstring that partial subtree refresh is deferred.

    Add `summarize(max_modules=20)` returning counts by language, top modules by symbol count, and entry-point candidates without raw code snippets.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_index.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/code/index.py voss/harness/code/models.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "index\\.db|schema_version|CREATE TABLE files|CREATE TABLE symbols" voss/harness/code/index.py</automated>
  </verify>
  <acceptance_criteria>
    - Session fixture scan creates `.voss-cache/code/index.db`.
    - Re-running scan on unchanged fixtures produces deterministic files/symbol rows.
    - Editing a fixture then calling refresh reflects the new symbol.
    - Schema-version mismatch rebuilds the DB instead of attempting migration.
    - Symlink/path traversal cases do not store paths outside cwd.
    - Summary contains counts/modules/entry points and no raw source snippets.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. High-severity cache traversal, arbitrary config execution during load, or source leakage in summaries blocks completion.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-01-01 | Tampering | index.db | User-edited DB could store paths outside cwd. | Jail every DB-loaded and scan-discovered path before reading. |
| T-M10-01-02 | Information disclosure | summary | Project Index summary could leak raw source. | Summary returns counts/modules/entry points only, no snippets. |
| T-M10-01-03 | DoS | scan | Vendored dirs could make scan unbounded. | Prune known vendored/cache dirs and use deterministic caps in tests. |
| T-M10-01-04 | Supply chain | optional extra | Binary ast-grep dependency could affect default install. | Put ast-grep-cli only in `voss[code]`; no eager import. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_code_config.py tests/harness/test_code_index.py -q`
- `python3 -m py_compile voss/harness/code/__init__.py voss/harness/code/models.py voss/harness/code/config.py voss/harness/code/index.py`
- `rg -n "index\\.db|SQLite" .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md`
- `! rg -n "index\\.json" .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md`
- `git diff --check -- .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md pyproject.toml voss/harness/code tests/fixtures/code tests/harness/test_code_config.py tests/harness/test_code_index.py`
</verification>

<success_criteria>
- The SPEC/CONTEXT mismatch is closed in favor of SQLite index.db.
- The code-intel package imports without pygls or ast-grep installed.
- The SQLite index is deterministic, jailed, rebuildable, and summary-safe.
- The polyglot fixture set exists for all later M10 acceptance tests.
</success_criteria>


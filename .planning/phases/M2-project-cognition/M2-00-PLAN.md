---
phase: M2
plan: 00
type: execute
wave: 0
depends_on: [M1]
files_modified:
  - tests/harness/conftest.py
  - tests/harness/test_cognition.py
  - tests/harness/test_cognition_schemas.py
  - tests/harness/test_recorder.py
  - tests/harness/test_repl_cognition.py
  - pyproject.toml
autonomous: true
requirements: []
tags:
  - harness
  - cognition
  - test-scaffold

must_haves:
  truths:
    - "Every Wave 0 test file enumerated in M2-VALIDATION.md exists with @pytest.mark.skip stubs for each named test."
    - "Shared git_repo fixture in conftest.py creates a tmp_path git repo with one commit and is reusable by every later wave."
    - "pyyaml is a declared first-party dependency in pyproject.toml so cognition YAML parsing has a guaranteed import."
    - "pytest collects the new files without import errors."
  artifacts:
    - path: "tests/harness/conftest.py"
      provides: "git_repo + isolated_state fixtures shared across harness tests"
      contains: "def git_repo"
    - path: "tests/harness/test_cognition.py"
      provides: "stubbed test functions named per M2-VALIDATION.md COG-01/02/04/06/07 rows"
      contains: "def test_analyze_writes_project_json"
    - path: "tests/harness/test_cognition_schemas.py"
      provides: "stubbed test functions for COG-03 schema validation"
      contains: "def test_constraints_extra_forbid"
    - path: "tests/harness/test_recorder.py"
      provides: "stubbed test functions for COG-08 mechanical capture"
      contains: "def test_inspect_captures_fs_read"
    - path: "tests/harness/test_repl_cognition.py"
      provides: "stubbed test functions for drift, status line, NDJSON event, overflow"
      contains: "def test_cognition_status_line_tty"
    - path: "pyproject.toml"
      provides: "pyyaml declared in [project] dependencies"
      contains: "pyyaml"
  key_links:
    - from: "tests/harness/test_cognition.py"
      to: "tests/harness/conftest.py::git_repo"
      via: "pytest fixture autodiscovery"
      pattern: "def test_.*\\(.*git_repo"
---

<objective>
Lay the test scaffold M2 will fill in across waves 1-4. Every test name from M2-VALIDATION.md exists as a skipped stub so later plans can flip skips into pass/fail signals without inventing file paths or function names. Also adds the missing `pyyaml` dependency.

Purpose: M2-VALIDATION.md enumerates 36 named tests across 4 new files plus a shared `git_repo` fixture. Wave 0 of the validation contract requires those test files to exist before later waves can reference them via `<verify>` commands. This plan ships the scaffold (skipped stubs + fixture + dep) so Wave 1+ plans can implement against named functions.

Output:
- `tests/harness/conftest.py` with `git_repo` + `isolated_state` fixtures.
- `tests/harness/test_cognition.py` with 14 stubs covering COG-01, COG-02, COG-04, COG-06, COG-07.
- `tests/harness/test_cognition_schemas.py` with 3 stubs covering COG-03.
- `tests/harness/test_recorder.py` with 6 stubs covering COG-08 mechanical.
- `tests/harness/test_repl_cognition.py` with 5 stubs covering drift, status line, NDJSON, overflow, malformed YAML.
- `pyproject.toml` lists `pyyaml>=6.0` in `[project] dependencies`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M2-project-cognition/M2-CONTEXT.md
@.planning/phases/M2-project-cognition/M2-VALIDATION.md
@.planning/phases/M2-project-cognition/M2-PATTERNS.md
@tests/harness/test_session.py
@tests/harness/test_session_redaction.py

<interfaces>
From tests/harness/test_session.py (analog pattern — class-based + isolated_state fixture):

```python
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path
```

From M2-PATTERNS.md (new conftest target):

```python
@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path
```

pytest discovery: tests/harness/ uses class-based grouping (test_session.py:17 TestSessionRoundtrip). Stubs in this plan use module-level functions named exactly as M2-VALIDATION.md rows so executors can find them by grep.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create conftest.py with shared fixtures + add pyyaml dep</name>
  <files>tests/harness/conftest.py, pyproject.toml</files>
  <read_first>
    - tests/harness/test_session.py (lines 1-30: existing autouse isolated_state pattern to promote)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§conftest.py NEW — fixture definitions)
    - pyproject.toml (current [project] dependencies block)
  </read_first>
  <action>
    1. Create tests/harness/conftest.py. Define two fixtures:
       - `isolated_state(tmp_path, monkeypatch)` — autouse=True; sets XDG_STATE_HOME to str(tmp_path); returns tmp_path. Mirrors the inline fixture currently in test_session.py.
       - `git_repo(tmp_path)` — non-autouse; subprocess runs `git init`, sets user.email and user.name to t@t / t, writes tmp_path/README.md, then `git add .` and `git commit -m init`. All subprocess.run calls use cwd=tmp_path, check=True, capture_output=True. Returns tmp_path.
    2. Add `import subprocess`, `import pytest`, `from pathlib import Path` at the top of conftest.py.
    3. Edit pyproject.toml: in `[project]` table's `dependencies` list, append `"pyyaml>=6.0"`. Keep existing entries unchanged; maintain TOML formatting.
    4. Do NOT remove the inline isolated_state fixture from test_session.py in this task — leave behavior identical until Wave 1+ plans confirm conftest discovery works. Conftest fixtures with the same name as inline fixtures cause pytest to prefer the inline definition; running `pytest tests/harness/ --collect-only` should report no fixture conflicts.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/ --collect-only -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def git_repo\\|^def isolated_state" tests/harness/conftest.py` returns 0 (they're decorated with @pytest.fixture so they are still `def` but the safer check follows).
    - `grep -c "@pytest.fixture" tests/harness/conftest.py` returns at least 2.
    - `grep -c "def git_repo" tests/harness/conftest.py` returns exactly 1.
    - `grep -c "def isolated_state" tests/harness/conftest.py` returns exactly 1.
    - `grep -c "pyyaml" pyproject.toml` returns at least 1.
    - `python -c "import yaml; print(yaml.__version__)"` succeeds and prints a 6.x version (already installed transitively; this confirms the declaration matches reality).
    - `pytest tests/harness/ --collect-only -q` exits 0 and reports no fixture-resolution errors.
  </acceptance_criteria>
  <done>conftest.py provides git_repo + isolated_state fixtures; pyyaml is declared; pytest collection is clean.</done>
</task>

<task type="auto">
  <name>Task 2: Stub the four new test files with skipped placeholders matching M2-VALIDATION.md names</name>
  <files>tests/harness/test_cognition.py, tests/harness/test_cognition_schemas.py, tests/harness/test_recorder.py, tests/harness/test_repl_cognition.py</files>
  <read_first>
    - .planning/phases/M2-project-cognition/M2-VALIDATION.md (every named test in the Per-Requirement Verification Map table — function names are the contract)
    - tests/harness/test_session.py (class-based test grouping pattern)
    - tests/harness/test_tools.py (unit-test layout for a single module's API)
  </read_first>
  <action>
    For each of the four new files, write a module-level skeleton: top-of-file docstring naming the requirement IDs covered, `import pytest`, and one `@pytest.mark.skip(reason="Wave N — pending plan M2-NN")` decorated `def test_NAME(...)` for every test named in M2-VALIDATION.md against that file.

    test_cognition.py — 14 stubs:
      test_analyze_writes_project_json (Wave 2, M2-04)
      test_architecture_md_frontmatter_well_formed (Wave 2, M2-04)
      test_load_parses_frontmatter (Wave 1, M2-01)
      test_drift_commits_threshold (Wave 1, M2-01)
      test_drift_file_count_threshold (Wave 1, M2-01)
      test_drift_days_threshold (Wave 1, M2-01)
      test_plan_filename_and_frontmatter (Wave 1, M2-01)
      test_reserve_filename_collision (Wave 1, M2-01)
      test_decision_frontmatter (Wave 2, M2-03)
      test_repo_idx_schema (Wave 1, M2-01)
      test_gitignore_idempotent (Wave 1, M2-01)
      test_voss_gitignore_autogenerated (Wave 2, M2-04)
      test_analyze_invokes_natural_language_route (Wave 2, M2-04)
      test_analyze_emits_project_root_gitignore_append (Wave 2, M2-04)

    test_cognition_schemas.py — 3 stubs:
      test_constraints_extra_forbid (Wave 1, M2-01)
      test_permissions_layered_with_gate (Wave 1, M2-01)
      test_validation_on_enum (Wave 1, M2-01)

    test_recorder.py — 6 stubs:
      test_inspect_captures_fs_read (Wave 1, M2-02)
      test_change_captures_fs_write (Wave 1, M2-02)
      test_validation_captures_exit_code (Wave 1, M2-02)
      test_failure_captures_tool_error (Wave 1, M2-02)
      test_diff_summary_from_git (Wave 1, M2-02)
      test_decisions_mirror_to_markdown (Wave 2, M2-03)

    test_repl_cognition.py — 5 stubs:
      test_cognition_overflow_truncates_constraints (Wave 3, M2-05)
      test_cognition_status_line_tty (Wave 3, M2-05)
      test_cognition_loaded_ndjson_event (Wave 3, M2-05)
      test_drift_hint_printed_non_blocking (Wave 4, M2-06)
      test_bad_yaml_loud_failure (Wave 1, M2-01)

    Each stub body is exactly:
      ```
      pass
      ```
    The `@pytest.mark.skip(reason="...")` decorator carries the wave + plan reference verbatim.

    These names map 1:1 to M2-VALIDATION.md rows. Renaming or omitting any name breaks the contract.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_cognition.py tests/harness/test_cognition_schemas.py tests/harness/test_recorder.py tests/harness/test_repl_cognition.py -v 2>&amp;1 | tail -40</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def test_" tests/harness/test_cognition.py` returns 14.
    - `grep -c "^def test_" tests/harness/test_cognition_schemas.py` returns 3.
    - `grep -c "^def test_" tests/harness/test_recorder.py` returns 6.
    - `grep -c "^def test_" tests/harness/test_repl_cognition.py` returns 5.
    - `pytest tests/harness/test_cognition.py tests/harness/test_cognition_schemas.py tests/harness/test_recorder.py tests/harness/test_repl_cognition.py -v` exits 0 with all 28 tests reported as skipped.
    - `grep -c "Wave 1\\|Wave 2\\|Wave 3\\|Wave 4" tests/harness/test_cognition.py` returns at least 14 (each skip reason references a wave).
    - Existing harness suite still green: `pytest tests/harness/ -x --ignore=tests/harness/test_cognition.py --ignore=tests/harness/test_cognition_schemas.py --ignore=tests/harness/test_recorder.py --ignore=tests/harness/test_repl_cognition.py` exits 0.
  </acceptance_criteria>
  <done>All 28 named test stubs exist and skip cleanly; existing tests unaffected.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/ -q` exits 0; the 28 new tests show as skipped, all other tests pass.
- `python -c "import yaml; assert yaml.__version__.startswith('6.')"` succeeds.
- `git ls-files tests/harness/conftest.py tests/harness/test_cognition.py tests/harness/test_cognition_schemas.py tests/harness/test_recorder.py tests/harness/test_repl_cognition.py` lists all 5 files as tracked (after staging).
</verification>

<success_criteria>
- Wave 0 of M2-VALIDATION.md is fully satisfied: every named test exists as a callable function and pytest can collect it.
- pyyaml is a declared dependency, not transitive.
- Shared `git_repo` fixture is available to drift and ls-files tests in later waves without per-file boilerplate.
- No existing test regresses.
</success_criteria>

<output>
After completion, create `.planning/phases/M2-project-cognition/M2-00-SUMMARY.md` documenting which test names belong to which wave (the wave-mapping table from this plan's Task 2 action), the conftest fixture surface, and the pyyaml dep addition.
</output>

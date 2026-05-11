---
phase: M2
plan: 01
type: execute
wave: 1
depends_on: [M1, M2-00]
files_modified:
  - voss/harness/cognition.py
  - voss/harness/cognition_schemas.py
  - tests/harness/test_cognition.py
  - tests/harness/test_cognition_schemas.py
  - tests/harness/test_repl_cognition.py
autonomous: true
requirements:
  - COG-01
  - COG-02
  - COG-03
  - COG-07
tags:
  - harness
  - cognition
  - schemas

must_haves:
  truths:
    - "cognition.load(cwd) returns a CognitionBundle for any cwd — initialized=False when .voss/ is empty, initialized=True with parsed fields when present."
    - "Strict pydantic schemas reject unknown YAML keys with a file:line error pointer collected into load_errors instead of raising."
    - "drift_check returns DriftStatus(is_stale=True) when HEAD diverges by 20+ commits, file count drifts ≥10%, or 7+ days have elapsed — and returns is_stale=False otherwise without raising on force-rebased SHAs."
    - "repo.idx is a JSON manifest with version/git_head/files[{path,size,mtime,sha}] and is built from git ls-files."
    - "append_gitignore_line_idempotent and reserve_filename helpers exist and behave per D-09 and D-08."
  artifacts:
    - path: "voss/harness/cognition.py"
      provides: "pure load(cwd) -> CognitionBundle + drift_check + helpers (slug, reserve_filename, append_gitignore_line_idempotent, build_repo_idx, render_constraints_bullets)"
      contains: "def load"
    - path: "voss/harness/cognition_schemas.py"
      provides: "strict pydantic v2 models: ProjectMeta, ConstraintsConfig, PermissionsConfig, ValidationConfig and their nested types"
      contains: "STRICT"
    - path: "tests/harness/test_cognition.py"
      provides: "10 unskipped tests covering load+drift+repo.idx+helpers"
      contains: "def test_load_parses_frontmatter"
    - path: "tests/harness/test_cognition_schemas.py"
      provides: "3 unskipped tests covering strict YAML schema validation"
      contains: "def test_constraints_extra_forbid"
    - path: "tests/harness/test_repl_cognition.py"
      provides: "test_bad_yaml_loud_failure unskipped — load_errors populated on malformed YAML, no raise"
      contains: "def test_bad_yaml_loud_failure"
  key_links:
    - from: "voss/harness/cognition.py::load"
      to: "voss/harness/cognition_schemas.py"
      via: "Model.model_validate against yaml.safe_load output"
      pattern: "model_validate"
    - from: "voss/harness/cognition.py::drift_check"
      to: "subprocess git rev-list --count"
      via: "subprocess.run wrapped in try/except — never raises"
      pattern: "git rev-list"
---

<objective>
Ship the pure-function cognition core: `cognition.load(cwd) -> CognitionBundle`, strict pydantic schemas for the three `*.yml` configs and `project.json`, drift detection against architecture.md frontmatter, the `repo.idx` JSON-manifest builder, and the small write helpers (`slug`, `reserve_filename`, `append_gitignore_line_idempotent`). Plus the 14 Wave-1 unit/integration tests these modules unlock.

Purpose: Every subsequent M2 plan needs `cognition.load(cwd)` (auto-injection in M2-05, drift hint and doctor rows in M2-06, /analyze post-step in M2-04) and the helpers (decisions/plans markdown writers in M2-03, repo.idx rebuild in M2-04). Centralizing this in two new modules with no dependencies on `agent.py` / `cli.py` keeps the rest of M2 a thin integration layer. Covers COG-01 (schema), COG-02 (frontmatter parse + drift), COG-03 (strict YAML schemas + loud fail), COG-07 (repo.idx + gitignore helpers).

Output:
- `voss/harness/cognition_schemas.py` — pydantic v2 strict models per D-07.
- `voss/harness/cognition.py` — pure `load(cwd) -> CognitionBundle`, `drift_check(cwd, frontmatter) -> DriftStatus`, `build_repo_idx(cwd) -> dict`, plus the 5 helpers.
- 14 tests flipped from skip to live across test_cognition.py / test_cognition_schemas.py / test_repl_cognition.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M2-project-cognition/M2-CONTEXT.md
@.planning/phases/M2-project-cognition/M2-RESEARCH.md
@.planning/phases/M2-project-cognition/M2-PATTERNS.md
@voss/harness/auth.py
@voss/harness/cli.py
@voss/harness/sandbox.py

<interfaces>
From voss/harness/auth.py (lines 279-329 — Resolution dataclass + resolve() pure-function pattern to mirror):

```python
@dataclass
class Resolution:
    source: str
    detail: str
    ...

def resolve(preference: str = "auto") -> Resolution:
    ...  # never raises; returns sentinel Resolution(source="none") on failure
```

From voss/harness/cli.py:80-99 (_git_status — subprocess wrap pattern to copy):

```python
def _git_status(cwd: Path) -> str:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=str(cwd),
                             capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return "not a git repo"
    if out.returncode != 0:
        return "not a git repo"
```

From voss/harness/sandbox.py — already implements jail_path(cwd, target).

From M2-RESEARCH.md §Pattern 1 — CognitionBundle dataclass shape (frozen, optional fields, load_errors: list[str]).
From M2-RESEARCH.md §Pattern 2 — pydantic strict model with `model_config = {"extra": "forbid"}` and the `_loc(loc)` helper.
From M2-RESEARCH.md "cognition.py skeleton" code block — full reference implementation incl. ANALYZER_VERSION=1, DRIFT_COMMITS=20, DRIFT_FILE_PCT=0.10, DRIFT_DAYS=7 constants.
From M2-RESEARCH.md "cognition_schemas.py" code block — every model definition incl. ProjectMeta, ConstraintRule, ConstraintsConfig, ToolPolicy, PathScope, PermissionsConfig, ValidationCommand, ValidationConfig.

litellm.token_counter signature (already used by voss_runtime/providers/litellm_provider.py):
    litellm.token_counter(model=str, text=str) -> int

repo.idx schema (D-05):
    {"version": 1, "git_head": "<sha>", "files": [{"path": str, "size": int, "mtime": float, "sha": str}, ...]}
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement cognition_schemas.py and unskip the 3 schema tests</name>
  <files>voss/harness/cognition_schemas.py, tests/harness/test_cognition_schemas.py</files>
  <read_first>
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§"cognition_schemas.py" code block — the verbatim reference; §Pattern 2 for the loc helper)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-07 — schema field requirements)
    - voss/harness/agent.py (lines 35-56 — pydantic v2 Field usage pattern in the existing Plan model)
    - tests/harness/test_cognition_schemas.py (existing skipped stubs from M2-00)
  </read_first>
  <behavior>
    - test_constraints_extra_forbid: `ConstraintsConfig.model_validate({"rules": [], "stray_key": 1})` raises pydantic.ValidationError.
    - test_permissions_layered_with_gate: `PermissionsConfig.model_validate({"tool_policy": {"allow": ["fs_read"], "deny": ["shell_run"]}, "path_scopes": [{"glob": "src/**", "modes": ["plan", "edit"]}]})` succeeds; `.tool_policy.deny == ["shell_run"]`; first `path_scopes[0].modes == ["plan", "edit"]`.
    - test_validation_on_enum: `ValidationConfig.model_validate({"commands": [{"name": "tests", "run": "pytest", "on": ["save", "post_run"]}]})` succeeds; `ValidationCommand.model_validate({"name": "x", "run": "y", "on": ["invalid"]})` raises ValidationError.
    - Additional invariants (existing stubs may need bodies): `ConstraintRule(max_file_size_lines=0)` raises (must be `gt=0`); `PathScope(glob="a", modes=["unknown"])` raises.
  </behavior>
  <action>
    1. Create voss/harness/cognition_schemas.py. Use the RESEARCH.md "cognition_schemas.py (pydantic v2 strict)" code block as the source of truth for model definitions. The module exports: STRICT (the model_config dict), ProjectMeta, ConstraintRule, ConstraintsConfig, ToolPolicy, PathScope, PermissionsConfig, ValidationCommand, ValidationConfig.
    2. Add module docstring naming D-07 as the source. Use `from __future__ import annotations`, `from typing import Literal`, `from pydantic import BaseModel, Field`.
    3. Every model defines `model_config = STRICT`. STRICT is `{"extra": "forbid"}`.
    4. ProjectMeta fields: name (str, required), type (str, default "library"), primary_language (str, required), entry_points (list[str], default_factory=list).
    5. ConstraintRule fields: forbid (list[str] | None = None), require_tests_for (list[str] | None = None), max_file_size_lines (int | None with Field(default=None, gt=0)), custom (str | None = None).
    6. ConstraintsConfig: rules (list[ConstraintRule], default_factory=list).
    7. ToolPolicy: allow (list[str], default_factory=list), deny (list[str], default_factory=list).
    8. PathScope: glob (str, required), modes (list[Literal["plan","edit","auto"]], required).
    9. PermissionsConfig: tool_policy (ToolPolicy, default_factory=ToolPolicy), path_scopes (list[PathScope], default_factory=list).
    10. ValidationCommand: name (str), run (str), on (list[Literal["save","pre_apply","post_run"]]).
    11. ValidationConfig: commands (list[ValidationCommand], default_factory=list).
    12. In tests/harness/test_cognition_schemas.py: remove the `@pytest.mark.skip` decorator from each of the 3 named tests and replace the `pass` body with the behavior above. Add `import pytest`, `from pydantic import ValidationError`, and `from voss.harness.cognition_schemas import (...)`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_cognition_schemas.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "model_config = STRICT" voss/harness/cognition_schemas.py` returns at least 8 (one per BaseModel).
    - `grep -c "from pydantic import BaseModel" voss/harness/cognition_schemas.py` returns 1.
    - `pytest tests/harness/test_cognition_schemas.py -v` reports 3 passed, 0 skipped.
    - `python -c "from voss.harness.cognition_schemas import ConstraintsConfig; ConstraintsConfig.model_validate({'rules':[],'x':1})"` exits non-zero (raises ValidationError).
    - `python -c "from voss.harness.cognition_schemas import PermissionsConfig; c=PermissionsConfig.model_validate({'tool_policy':{'deny':['shell_run']}}); assert 'shell_run' in c.tool_policy.deny"` exits 0.
  </acceptance_criteria>
  <done>Strict YAML schemas exist; 3 schema tests pass; unknown keys + invalid enums fail loud.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement cognition.py (load + drift_check + repo.idx + helpers) and unskip the cognition.py-side tests</name>
  <files>voss/harness/cognition.py, tests/harness/test_cognition.py, tests/harness/test_repl_cognition.py</files>
  <read_first>
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§"cognition.py skeleton" code block — verbatim reference; §Pitfall 4 force-rebase handling; §Pitfall 6 idempotent gitignore append)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-04 drift thresholds; §D-05 repo.idx schema; §D-08 slug + reserve_filename; §D-09 gitignore contents)
    - voss/harness/auth.py (lines 60-330 — never-raise resolution pattern)
    - voss/harness/cli.py (lines 80-99 — subprocess wrap)
    - tests/harness/test_cognition.py (skipped stubs from M2-00 — exact names this task unskips)
    - tests/harness/conftest.py (git_repo fixture this task consumes)
  </read_first>
  <behavior>
    - test_load_parses_frontmatter: write a synthetic `<git_repo>/.voss/architecture.md` whose body starts with a YAML frontmatter block (`---\ngit_head: abc\nanalyzed_at: 2026-05-10T00:00:00+00:00\nfile_count: 5\nanalyzer_version: 1\n---\n# Arch`). load(git_repo).architecture_frontmatter is an ArchitectureFrontmatter with those values; architecture_md is "# Arch" (no frontmatter); initialized=True.
    - test_drift_commits_threshold: git_repo fixture provides 1 commit. Write architecture.md with frontmatter pointing to an ancient sha that's unreachable. drift_check returns DriftStatus(is_stale=True) and reason contains "HEAD" or "commits".
    - test_drift_file_count_threshold: frontmatter file_count = 1; current file count (via `git ls-files | wc -l`) = 2 in git_repo after adding a second file → 100% delta → drift triggers. (Threshold is 10% so 1→2 is well over.)
    - test_drift_days_threshold: frontmatter analyzed_at is 10 days ago. drift_check returns is_stale=True with reason mentioning days.
    - test_plan_filename_and_frontmatter: `reserve_filename(tmp_path / "plans", slug("My Plan Title"))` returns a Path like `tmp_path/plans/YYYY-MM-DD-my-plan-title.md` (today's UTC date).
    - test_reserve_filename_collision: pre-create a same-day file with the slug; reserve_filename returns `...-2.md`; pre-create that too, returns `...-3.md`.
    - test_repo_idx_schema: `build_repo_idx(git_repo)` returns dict with `version: 1`, `git_head: <40-char sha>`, `files: list[dict]` where each entry has keys exactly `{"path", "size", "mtime", "sha"}` and `sha` is a 40-char hex string.
    - test_gitignore_idempotent: append_gitignore_line_idempotent(tmp_path/".gitignore", ".voss-cache/") returns True first time, writes the line; calling it again returns False; file contains exactly one `.voss-cache/` line.
    - test_bad_yaml_loud_failure (test_repl_cognition.py): write `<git_repo>/.voss/constraints.yml` with content `rules: [\n` (malformed). load(git_repo).load_errors is non-empty; first entry contains the path string `constraints.yml` and the YAML error. No exception raised.
  </behavior>
  <action>
    1. Create voss/harness/cognition.py. Use M2-RESEARCH.md "cognition.py skeleton" as the implementation source of truth. The module exports: ANALYZER_VERSION, DRIFT_COMMITS=20, DRIFT_FILE_PCT=0.10, DRIFT_DAYS=7, ArchitectureFrontmatter, CognitionBundle, DriftStatus, voss_dir(cwd), cache_dir(cwd), load(cwd, *, token_count=None), drift_check(cwd, fm), build_repo_idx(cwd), render_constraints_bullets(c), append_gitignore_line_idempotent(path, line), slug(title), reserve_filename(dir_, base, ext=".md").
    2. ArchitectureFrontmatter is `@dataclass(frozen=True)` with fields git_head (str), analyzed_at (str ISO timestamp), file_count (int), analyzer_version (int).
    3. CognitionBundle is `@dataclass(frozen=True)` with fields: initialized (bool), project (ProjectMeta | None = None), architecture_md (str | None = None), architecture_frontmatter (ArchitectureFrontmatter | None = None), constraints (ConstraintsConfig | None = None), permissions (PermissionsConfig | None = None), validation (ValidationConfig | None = None), architecture_tokens (int = 0), load_errors (list[str] = field(default_factory=list)).
    4. DriftStatus is `@dataclass` (not frozen) with is_stale (bool), head_diverged_by (int), file_count_delta (int), days_elapsed (int), reason (str = "").
    5. FRONTMATTER_RE = `re.compile(r"^---\\n(.*?)\\n---\\n(.*)$", re.DOTALL)`. Use to split `<frontmatter>` from `<body>` in architecture.md.
    6. load(cwd, *, token_count=None) -> CognitionBundle:
       - If `(cwd/".voss"/"architecture.md").exists()` is False → return CognitionBundle(initialized=False).
       - Else parse project.json (json.loads → ProjectMeta.model_validate), architecture.md (split frontmatter, yaml.safe_load it into dict, build ArchitectureFrontmatter), each *.yml via helper `_load_yaml(path, Model, errors)` that wraps yaml.safe_load + Model.model_validate in try/except and pushes "{path}: {detail}" strings to errors.
       - architecture_tokens = `token_count(arch_body)` if token_count and arch_body else 0.
       - Returns CognitionBundle with all fields populated.
    7. drift_check(cwd, fm) -> DriftStatus:
       - head_div = `_git_rev_list_count(cwd, fm.git_head)` — runs `git rev-list --count <sha>..HEAD`. On nonzero exit (unreachable sha, force-rebase) return a large number like `DRIFT_COMMITS` so drift triggers (per Pitfall 4).
       - cur_files = `_git_ls_files_count(cwd)` — runs `git ls-files | wc -l` equivalent (subprocess + len of splitlines). On failure returns fm.file_count (no delta).
       - file_delta = cur_files - fm.file_count.
       - days = `_days_since(fm.analyzed_at)` (parse ISO, compute (now-then).days).
       - triggers list: if head_div >= DRIFT_COMMITS, append f"HEAD +{head_div} commits"; if abs(file_delta)/max(fm.file_count,1) >= DRIFT_FILE_PCT, append f"{sign}{file_delta} files"; if days >= DRIFT_DAYS, append f"{days}d old".
       - Return DriftStatus(is_stale=bool(triggers), head_diverged_by=head_div, file_count_delta=file_delta, days_elapsed=days, reason=", ".join(triggers)).
    8. build_repo_idx(cwd) -> dict:
       - Run `git ls-files` (subprocess) inside cwd; on nonzero exit fall back to `[p for p in cwd.rglob("*") if p.is_file() and not _ignored(p, cwd)]` (simple walk, skip `.git/`).
       - For each path: compute size (stat.st_size), mtime (stat.st_mtime), sha (`hashlib.sha1(file_bytes).hexdigest()`).
       - Return `{"version": 1, "git_head": <subprocess git rev-parse HEAD or "">, "files": [{"path": rel_path, "size": ..., "mtime": ..., "sha": ...}, ...]}`.
    9. Helpers:
       - slug(title) → kebab-case via `re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]` or "untitled" if empty.
       - reserve_filename(dir_, base, ext=".md") → today_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d"). Start with `dir_/f"{today}-{base}{ext}"`. While exists, increment suffix `-2`, `-3`. dir_ is created via `dir_.mkdir(parents=True, exist_ok=True)` only if the caller is going to write — keep reserve_filename pure (no mkdir; the caller does it).
       - append_gitignore_line_idempotent(path, line) → if path exists, read lines, check `stripped(line) in {stripped(l) for l in existing}`. If present return False. Else append (ensure trailing newline). Return True.
       - render_constraints_bullets(c) → see RESEARCH skeleton.
    10. _load_yaml helper:
        ```
        def _load_yaml(path: Path, model, errors: list[str]):
            if not path.exists(): return None
            try:
                raw = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError as e:
                errors.append(f"{path}: invalid YAML: {e}")
                return None
            try:
                return model.model_validate(raw)
            except ValidationError as e:
                for err in e.errors():
                    loc = ".".join(str(x) for x in err["loc"]) or "<root>"
                    errors.append(f"{path}: {loc}: {err['msg']}")
                return None
        ```
    11. Every subprocess call uses try/except (OSError, subprocess.SubprocessError) returning a sentinel; never raises out.
    12. In tests/harness/test_cognition.py: remove `@pytest.mark.skip` from the 9 Wave-1 tests listed in this task's <behavior>. Implement each per behavior above. Use the `git_repo` fixture from conftest.py where git is needed.
    13. In tests/harness/test_repl_cognition.py: remove `@pytest.mark.skip` from `test_bad_yaml_loud_failure` and implement per behavior.
    14. Tests for COG-04 plan_filename/reserve_collision rely on helpers only — no git needed; use tmp_path directly.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_cognition.py tests/harness/test_repl_cognition.py::test_bad_yaml_loud_failure -v</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def load\\|^def drift_check\\|^def build_repo_idx\\|^def slug\\|^def reserve_filename\\|^def append_gitignore_line_idempotent\\|^def render_constraints_bullets" voss/harness/cognition.py` returns at least 7.
    - `grep -c "ANALYZER_VERSION\\|DRIFT_COMMITS\\|DRIFT_FILE_PCT\\|DRIFT_DAYS" voss/harness/cognition.py` returns at least 4.
    - `pytest tests/harness/test_cognition.py -v` reports the 9 Wave-1 tests passing (test_load_parses_frontmatter, test_drift_commits_threshold, test_drift_file_count_threshold, test_drift_days_threshold, test_plan_filename_and_frontmatter, test_reserve_filename_collision, test_repo_idx_schema, test_gitignore_idempotent — 8 by name + at least 1 skipped Wave-2 stub still skipped). Total pass count ≥ 8 in this file.
    - `pytest tests/harness/test_repl_cognition.py::test_bad_yaml_loud_failure -v` exits 0.
    - `python -c "from voss.harness.cognition import load; b=load(__import__('pathlib').Path('.')); print(b.initialized)"` runs without raising regardless of whether `.voss/` exists.
    - `python -c "import subprocess; from voss.harness.cognition import drift_check, ArchitectureFrontmatter; from pathlib import Path; drift_check(Path('.'), ArchitectureFrontmatter(git_head='deadbeef'*5, analyzed_at='2020-01-01T00:00:00+00:00', file_count=1, analyzer_version=1))"` runs without raising (force-rebase pitfall — unreachable sha must not crash).
  </acceptance_criteria>
  <done>cognition.py is the pure, never-raising loader + helper module M2 depends on; 9 cognition tests + 1 REPL test pass.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_cognition.py tests/harness/test_cognition_schemas.py tests/harness/test_repl_cognition.py::test_bad_yaml_loud_failure -v` exits 0 with 12 passing tests (8 cognition + 3 schemas + 1 repl).
- `pytest tests/harness/ -x` still exits 0 (no regression in M1 tests).
- `python -c "import voss.harness.cognition; import voss.harness.cognition_schemas"` succeeds.
</verification>

<success_criteria>
- COG-01 schema (ProjectMeta) and COG-02 frontmatter parsing + drift detection are testable in isolation.
- COG-03 strict YAML schemas reject typos at REPL boot time, not mid-turn (loud-fail).
- COG-07 repo.idx structure and gitignore-append idempotence are nailed down.
- No `agent.py` / `cli.py` modification — pure new module, ready to be wired by later plans.
- Force-rebase + missing-frontmatter never raises; populates load_errors instead (D-04, Pitfall 4).
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| disk → cognition.load | user/agent-written YAML and markdown crosses into a pydantic validator |
| disk → architecture.md | YAML frontmatter from prior /analyze (or hand-edited) is parsed |
| git subprocess → cognition | shell exit codes determine drift state |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M2-01 | Tampering | YAML deserialization gadget (`!!python/object`) in `.voss/*.yml` | mitigate | `yaml.safe_load` only; never `yaml.load`. Document at top of cognition.py. |
| T-M2-02 | Information Disclosure | symlink at `.voss/architecture.md` pointing outside cwd | mitigate | `path.resolve().relative_to(cwd)` check inside `load()` before reading any `.voss/` file; reuse sandbox.jail_path. |
| T-M2-03 | Denial of Service | malformed git rev-list (force-rebased SHA) raises uncaught exception at REPL boot | mitigate | Every subprocess call in cognition.py wrapped in try/except (OSError, SubprocessError); nonzero exit → sentinel value (per Pitfall 4). |
| T-M2-04 | Input Validation | unknown YAML key silently coerced into model (typo accepted) | mitigate | `model_config = {"extra": "forbid"}` on every BaseModel (D-07). |
</threat_model>

<output>
After completion, create `.planning/phases/M2-project-cognition/M2-01-SUMMARY.md` documenting: (1) the cognition.py public API (every exported name + signature), (2) the schema field map (model → field → type), (3) the drift threshold constants and what triggers each, (4) the repo.idx JSON shape, (5) the never-raise invariant + which subprocess sites enforce it.
</output>

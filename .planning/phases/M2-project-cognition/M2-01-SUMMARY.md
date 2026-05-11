---
phase: M2
plan: 01
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/cognition.py (new)
  - voss/harness/cognition_schemas.py (new)
  - tests/harness/test_cognition.py (8 stubs unskipped)
  - tests/harness/test_cognition_schemas.py (3 stubs unskipped)
  - tests/harness/test_repl_cognition.py (1 stub unskipped — test_bad_yaml_loud_failure)
tests_added: 12 passing (8+3+1)
tests_total: 179 passed + 16 skipped
---

# M2-01 Summary: Cognition Core (pure module + strict schemas)

Wave 1 ships the two pure modules every later M2 plan depends on. No
`agent.py` / `cli.py` touched.

## 1. `voss/harness/cognition.py` — public API

| Name                                     | Kind       | Signature |
|------------------------------------------|------------|-----------|
| `ANALYZER_VERSION`                       | constant   | `1` |
| `DRIFT_COMMITS`                          | constant   | `20` |
| `DRIFT_FILE_PCT`                         | constant   | `0.10` |
| `DRIFT_DAYS`                             | constant   | `7` |
| `FRONTMATTER_RE`                         | regex      | `^---\n(.*?)\n---\n(.*)$` (DOTALL) |
| `ArchitectureFrontmatter`                | frozen dc  | `git_head, analyzed_at, file_count, analyzer_version` |
| `CognitionBundle`                        | frozen dc  | `initialized, project, architecture_md, architecture_frontmatter, constraints, permissions, validation, architecture_tokens, load_errors` |
| `DriftStatus`                            | dc         | `is_stale, head_diverged_by, file_count_delta, days_elapsed, reason` |
| `voss_dir(cwd)`                          | helper     | `Path -> Path` (cwd/".voss") |
| `cache_dir(cwd)`                         | helper     | `Path -> Path` (cwd/".voss-cache") |
| `load(cwd, *, token_count=None)`         | loader     | `-> CognitionBundle`. Never raises. |
| `drift_check(cwd, fm)`                   | checker    | `-> DriftStatus`. Never raises. |
| `build_repo_idx(cwd)`                    | builder    | `-> dict` (D-05 schema) |
| `render_constraints_bullets(c)`          | renderer   | `-> str` |
| `append_gitignore_line_idempotent(path, line)` | helper | `-> bool` (True if appended). |
| `slug(title)`                            | helper     | kebab-case, ≤60 chars, "untitled" fallback |
| `reserve_filename(dir_, base, ext='.md')` | helper    | `YYYY-MM-DD-<base>(-N).md` collision-aware |

### `repo.idx` JSON shape (D-05)

```json
{
  "version": 1,
  "git_head": "<40-char sha or ''>",
  "files": [
    {"path": "relative/posix.py", "size": 123, "mtime": 1714000000.0, "sha": "<sha1 40 hex>"}
  ]
}
```

`build_repo_idx` prefers `git ls-files` for the file list; falls back to
`rglob('*')` filtered to files, skipping `.git/`, on subprocess failure.

### Drift thresholds + triggers

| Constant         | Value | Trigger if |
|------------------|-------|------------|
| `DRIFT_COMMITS`  | 20    | `git rev-list --count <fm.git_head>..HEAD` ≥ 20 (or subprocess fails → treated as 20+) |
| `DRIFT_FILE_PCT` | 0.10  | `abs(cur_files - fm.file_count) / max(fm.file_count, 1)` ≥ 0.10 |
| `DRIFT_DAYS`     | 7     | `(now - fm.analyzed_at).days` ≥ 7 |

Any trigger → `is_stale=True`; `reason` is the comma-joined trigger
descriptions (e.g. `"HEAD +25 commits, 12d old"`).

### Never-raise invariant

| Site                                         | Guard |
|----------------------------------------------|-------|
| `_git_rev_list_count` (drift HEAD compare)   | `try: subprocess.run(...) except (OSError, SubprocessError): return DRIFT_COMMITS` |
| `_git_ls_files_count`                        | same shape, returns `fm.file_count` (zero delta) on failure |
| `_load_yaml`                                 | `yaml.YAMLError` + `ValidationError` → push string into `errors`, return None |
| `_load_json` / `_load_arch`                  | same |
| `build_repo_idx` git rev-parse + ls-files    | both wrapped; fall back to `rglob` walk if ls-files fails |

Manual smoke: `load(Path('.'))` on a non-initialized repo → returns
`CognitionBundle(initialized=False)`. `drift_check(Path('.'), <unreachable sha>)`
→ `is_stale=True`, no exception (Pitfall 4 enforced).

YAML parsing is `yaml.safe_load` ONLY (T-M2-01) — verified by grep: 0 hits
for `yaml.load(`.

## 2. `voss/harness/cognition_schemas.py` — strict pydantic v2 models

`STRICT = {"extra": "forbid"}` applied to every BaseModel (count = 9).

| Model                  | Fields |
|------------------------|--------|
| `ProjectMeta`          | name (str, req), type (str, "library"), primary_language (str, req), entry_points (list[str], []) |
| `ConstraintRule`       | forbid (list[str] | None), require_tests_for (list[str] | None), max_file_size_lines (int | None, `gt=0`), custom (str | None) |
| `ConstraintsConfig`    | rules (list[ConstraintRule], []) |
| `ToolPolicy`           | allow (list[str], []), deny (list[str], []) |
| `PathScope`            | glob (str, req), modes (list[Literal["plan","edit","auto"]], req) |
| `PermissionsConfig`    | tool_policy (ToolPolicy), path_scopes (list[PathScope], []) |
| `ValidationCommand`    | name (str), run (str), on (list[Literal["save","pre_apply","post_run"]]) |
| `ValidationConfig`     | commands (list[ValidationCommand], []) |

Unknown keys at any level → `ValidationError`. T-M2-04 enforced.

## 3. Test status

| File                                  | Wave-1 passing | Still skipped |
|---------------------------------------|----------------|---------------|
| `tests/harness/test_cognition.py`     | 8              | 6 (Wave 2+ Wave 3) |
| `tests/harness/test_cognition_schemas.py` | 3          | 0 |
| `tests/harness/test_repl_cognition.py` | 1 (bad_yaml)  | 4 (Wave 3+4) |

Full harness suite: **179 passed + 16 skipped** (up from 167+28 in M2-00).

## 4. Threat-model dispositions

| Threat   | Status   |
|----------|----------|
| T-M2-01 (YAML gadget) | Mitigated: `yaml.safe_load` only; grep `yaml.load(` returns 0. |
| T-M2-02 (symlink in `.voss/`) | Partial — load() reads `.voss/<known files>` via direct Path; no glob/follow_symlinks. Full belt-and-braces (sandbox.jail_path on every read) deferred to integration plan. |
| T-M2-03 (force-rebase crash) | Mitigated: every subprocess wrapped; manual smoke confirms. |
| T-M2-04 (unknown YAML key)   | Mitigated: STRICT on every model; tested by `test_constraints_extra_forbid`. |

## 5. Handoff to later M2 plans

- **M2-02 recorder** consumes `voss_dir(cwd)` for run-record paths.
- **M2-03 plans/decisions writers** use `slug()` + `reserve_filename()`.
- **M2-04 /analyze** uses `build_repo_idx`, `append_gitignore_line_idempotent`, and the schema models to write `.voss/*.yml` initial scaffolds.
- **M2-05 REPL auto-injection** calls `load(cwd, token_count=litellm.token_counter)` then `render_constraints_bullets()`.
- **M2-06 doctor/drift hint** calls `drift_check(cwd, bundle.architecture_frontmatter)`.

No public API name changes expected for the rest of M2 — these signatures are the contract.

Subagents used (sonnet, parallel): one per task. Task 2 had implicit dependency on Task 1's schemas module; both completed cleanly with no race.

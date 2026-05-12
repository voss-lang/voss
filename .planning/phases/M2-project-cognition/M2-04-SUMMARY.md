---
phase: M2
plan: 04
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/cognition.py (7 new helpers: detect_primary_language, build_bootstrap_inventory, init_voss_stubs, bootstrap_prompt, write_voss_gitignore, write_plan_md, _render_steps_for_plan_md)
  - voss/harness/skills/__init__.py (new package marker)
  - voss/harness/skills/analyze.py (new — orchestrates hybrid bootstrap)
  - voss/harness/cli.py (_classify_intent, _handle_analyze, _handle_save_plan, /analyze + /save-plan slash branches, natural-language route, last_plan tracking, /help text)
  - tests/harness/test_cognition.py (12 new tests + stub provider helper)
  - tests/harness/test_cli.py (2 routing tests + Wave-4 placeholder)
tests_added: 14
tests_total: 210 passed + 8 skipped
agent_py_edited: false
---

# M2-04 Summary · `/analyze` Hybrid Bootstrap + `/save-plan`

## 1. Hybrid bootstrap shape

| File | Owner | Re-run semantics |
|------|-------|------------------|
| `.voss/project.json`     | harness (heuristic ProjectMeta) | preserve-if-exists |
| `.voss/constraints.yml`  | harness (default ConstraintsConfig)  | preserve-if-exists |
| `.voss/permissions.yml`  | harness (default PermissionsConfig)  | preserve-if-exists |
| `.voss/validation.yml`   | harness (default ValidationConfig)   | preserve-if-exists |
| `.voss/architecture.md`  | **LLM** (1 fs_write)                 | always overwritten + post-validated + rolled-back on schema failure |
| `.voss/.gitignore`       | harness                              | preserve-if-exists (`sessions/`) |
| `.voss-cache/repo.idx`   | harness (build_repo_idx)             | always rebuilt |
| project-root `.gitignore`| harness (append helper)              | idempotent append of `.voss-cache/` |

Result: 1 LLM tool call per `/analyze` (was 5-10 in plan-as-originally-drafted),
0 schema-violation risk on harness-owned files (each goes through pydantic STRICT
construction before serialization).

## 2. `build_bootstrap_inventory(cwd)` schema

```python
{
  "name": str,                   # cwd.name
  "git_head": str,               # `git rev-parse HEAD` or "UNKNOWN"
  "file_count": int,             # `git ls-files | wc -l` or rglob fallback
  "analyzed_at": str,            # UTC ISO seconds
  "primary_language": str,       # extension histogram → language map; "unknown"
  "dir_tree": list[(str, int)],  # top-level dirs ≤ 12, with file counts
  "manifest_path": str | None,   # first match of MANIFEST_CANDIDATES
  "manifest_head": str,          # ≤ 4096 chars
  "readme_head": str,            # ≤ 4096 chars
}
```

Manifest detection order: `pyproject.toml`, `package.json`, `Cargo.toml`,
`Package.swift`, `go.mod`, `Gemfile`.

## 3. Bootstrap prompt contract

Single instruction: emit **exactly one** `fs_write` to `.voss/architecture.md`.

Forbidden during this turn: `fs_glob`, `fs_read`, `shell_run`, `git_status`
(all inventory is in-context). Body sections enforced in order:

1. `# Project` (one-paragraph summary)
2. `## Primary language`
3. `## Entry points`
4. `## Module map`
5. `## Key dependencies`
6. `## Testing approach`

Frontmatter values dictated verbatim from inventory:

```
---
git_head: <inventory.git_head>
analyzed_at: <inventory.analyzed_at>
file_count: <inventory.file_count>
analyzer_version: 1
---
```

Total length ≤ 150 lines. Post-turn the harness re-validates via
`FRONTMATTER_RE`; on failure, rolls back to previous content (if any) or emits
stderr warning.

## 4. Post-step machine actions in order

```
inventory = build_bootstrap_inventory(cwd)
stubs    = init_voss_stubs(cwd, inventory=inventory)          # preserve-if-exists
            write_voss_gitignore(cwd)                          # preserve-if-exists
            append_gitignore_line_idempotent(cwd/.gitignore,
                                             ".voss-cache/")
backup   = arch_path.read_text() if exists else None
result   = run_turn(bootstrap_prompt(inventory), cognition=None, ...)
arch_ok  = FRONTMATTER_RE.match(arch_path.read_text())
if not arch_ok: rollback-or-warn
idx      = build_repo_idx(cwd)
write idx -> .voss-cache/repo.idx
echo "cognition initialized: ..."
```

## 5. Intent classifier (literal allowlist, no LLM)

```python
_INTENT_ALLOWLIST = {
    "analyze repo",
    "analyze this repo",
    "analyze this project",
    "update project memory",
    "refresh cognition",
    "rebuild cognition",
}
```

`_classify_intent(line)` returns `"analyze"` iff `line.lower().strip()` is in
the allowlist. Else `None`. Hooked into `_run_repl` just before the catch-all
`if line.startswith("/"):` unknown handler.

## 6. `write_plan_md` frontmatter shape + kwargs-style steps

Filename: `.voss/plans/YYYY-MM-DD-<slug>.md`, collision-suffixed via
`reserve_filename`.

```
---
id: <YYYY-MM-DD-slug>
status: open
related_session: <session_id>
model: <record.model>
confidence: <0..1 .2f>
created_at: <UTC ISO seconds>
---

# <title or "Plan">

## Rationale

<plan.rationale>

## Steps

- <tool_name>(<k>=<json.dumps(v)>, ...) — <why>
```

Step rendering example (compact JSON for values):

```
- fs_read(path="cli.py", limit=10) — locate symbol
```

## 7. Idempotence guarantees

| File                      | On re-run |
|---------------------------|-----------|
| `.voss/project.json`      | preserved if pre-existing |
| `.voss/{constraints,permissions,validation}.yml` | preserved if pre-existing |
| `.voss/.gitignore`        | preserved if pre-existing |
| `.voss/architecture.md`   | always overwritten (LLM-refreshed) — with schema-failure rollback to the previous version |
| `.voss-cache/repo.idx`    | always rebuilt |
| project-root `.gitignore` | `.voss-cache/` line appended only if absent |

## 8. OQ-2 resolution (manual `/save-plan` only)

No auto-persist anywhere. `/save-plan [title]` is the sole entry point. REPL
tracks `last_plan` (initialized `None`, assigned `result.plan` after each
user-turn dispatch). `_handle_save_plan`:

- `last_plan is None` → stderr `"no plan to save yet — run a turn first"`, no file written.
- Else → `cognition.write_plan_md(...)` → echo `plan saved: <relative path>`.

## 9. No `agent.py` edit

`TurnResult.plan: Plan` already exists at `agent.py:111` and is populated at
both return sites (clarify branch + happy path). `cli.py:_run_repl` reads
`result.plan` into `last_plan` after each turn — no schema change required.

```
$ git diff voss/harness/agent.py
$           # empty
```

## 10. Test additions

| File                          | Tests | Notes |
|-------------------------------|-------|-------|
| `tests/harness/test_cognition.py` | 12   | hybrid helpers + analyze e2e via `_StubAnalyzeProvider` + 4 `/save-plan` tests + render unit |
| `tests/harness/test_cli.py`       | 2    | `test_slash_analyze_routes`, `test_natural_analyze_routes` (driving `_run_repl` via monkeypatched `input()`) + 1 Wave-4 skip |

Suite: **210 passed + 8 skipped** (was 196 + 11 after M2-03).

## 11. Threat dispositions

| Threat   | Disposition |
|----------|-------------|
| T-M2-13 | Mitigated — literal allowlist, no substring matching, no LLM classifier. |
| T-M2-14 | Mitigated — prompt instructs single fs_write inside `.voss/`; post-validation + rollback on missing/malformed file. |
| T-M2-15 | Mitigated — `append_gitignore_line_idempotent` reads existing lines; only appends if absent. Test asserts single occurrence. |
| T-M2-16 | Mitigated — frontmatter values dictated verbatim in prompt; post-turn `FRONTMATTER_RE` re-validation; rollback path covers schema regression. |
| T-M2-17 | Accepted — README/manifest already public-intended; 4k cap limits leak surface. |
| T-M2-18 | Mitigated — `init_voss_stubs` preserve-if-exists; only `architecture.md` overwritten. |

## 12. Handoff to M2-05+

- M2-05 REPL cognition injection: passes loaded `CognitionBundle` into
  `run_turn(..., cognition=cog, ...)` for non-analyze turns. `analyze.run`
  passes `cognition=None` explicitly (no injection during bootstrap).
- M2-06 doctor cognition rows: placeholder `test_doctor_cognition_rows`
  already skipped with `reason="Wave 4 — pending plan M2-06"`.
- `cognition.write_plan_md` callable now exposed; M2-05/06 can extend with
  status mutations (`open` → `approved`/`rejected`) without schema churn.

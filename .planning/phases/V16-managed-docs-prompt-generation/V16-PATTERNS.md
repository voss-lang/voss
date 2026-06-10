# Phase V16: Managed Docs & Prompt Generation - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 13 (new/modified)
**Analogs found:** 12 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/sync.py` (new module) | service | transform / batch | `voss/cli.py` `_scaffold_target` (render-loop) + `voss/harness/voss_md.py` (fence writes) | role-match |
| `voss/sync.py` `SyncContext` dataclass | model | transform | `voss/harness/voss_md.py` `@dataclass Block` | role-match |
| `voss/layout.py` (layout-context derivation) | service/utility | transform (git/fs read) | `voss/harness/cognition.py` `build_repo_idx` (git rev-parse / ls-files probes) | role-match |
| `voss sync` CLI command | controller (CLI) | request-response | `voss/cli.py` `init` command + `_scaffold_target` | exact |
| Project-facts config reader (`project:` block) | config | file-I/O (read) | `voss/harness/conventions.py` `_load_memory_config` | exact |
| `.voss/sync-state.json` manifest writer | utility | file-I/O (write) | `voss/cli.py` `_write_text_atomic` + `json` (stdlib in cli.py) | role-match |
| VOSS.md workflow fence write | service | file-I/O (write) | `voss/harness/voss_md.py` `write_fence_body` (REUSE verbatim) | exact |
| `voss/templates/docs/cheatsheet.md.jinja` (new) | template | transform | `voss/templates/init/README.md.jinja` | role-match |
| `voss/templates/docs/commands.md.jinja` (new) | template | transform | `voss/templates/init/README.md.jinja` | role-match |
| `voss/templates/docs/review.md.jinja` (new) | template | transform | `voss/templates/init/README.md.jinja` | role-match |
| `voss/templates/docs/voss_md_fence.md.jinja` (new fence body) | template | transform | `voss/templates/agent/cognition_block.md.jinja` (rendered-to-string body) | role-match |
| Prompt-loader override (project copy + `${}` substitution) | utility/provider | transform | `voss/harness/agent.py` `_compose_loop_system` (str.replace placeholder fill) + the 3 render sites below | role-match |
| `tests/cli/test_sync.py` (+ unit tests) | test | — | `tests/cli/test_init.py` + `tests/harness/test_voss_md_fence.py` | exact |

## Pattern Assignments

### `voss/sync.py` — sync orchestrator (service, transform/batch)

**Analogs:** `voss/cli.py` `_scaffold_target` (lines 445-473) for the render→guard→write loop; `voss/harness/voss_md.py` `write_fence_body` for the fence write.

**Render loop pattern to mirror** (`voss/cli.py:458-473`): a template-name→resource map, render each via `render_package_template("voss", "templates/...", ctx)`, path-traversal guard (`dest.is_relative_to(target_resolved)`), then write. V16 sync extends this with a diff/skip stage (read existing → compare → apply per-artifact write policy → update manifest) instead of unconditional write.

```python
# _scaffold_target render loop (voss/cli.py:460-473) — copy structure, add diff/skip
for name in _INIT_TEMPLATE_NAMES:
    resource_name = _INIT_TEMPLATE_RESOURCES.get(name, name)
    template = template_root.joinpath(resource_name)
    if not template.is_file():
        raise click.ClickException(f"missing scaffold template: {resource_name}")
    dest = (target_resolved / name).resolve()
    if not dest.is_relative_to(target_resolved):
        raise click.ClickException(f"refused to write outside target: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        render_package_template("voss", f"templates/init/{resource_name}", template_context)
    )
```

**Rendering constraint (D-17):** ALL rendering goes through `render_package_template(package, resource, context)` (`voss/template_render.py:22-28`). Never construct a second `Environment` or ad-hoc `Template(...)`. The cached env already applies `StrictUndefined`, `trim_blocks`, `lstrip_blocks`, `keep_trailing_newline`.

**Atomic write pattern** (`voss/cli.py:99-115` `_write_text_atomic`): mkstemp in dest dir → write → `os.replace` → cleanup on failure. Use for `.voss/docs/*` and `.voss/sync-state.json`. (`write_fence_body` already does its own `.tmp` + `os.replace`.)

**Idempotency anchor (R1, D-14):** the diff pass must be byte-exact. `render_package_template` keeps trailing newlines, so rendered output is stable; compare rendered string against `dest.read_text()` before writing. `--dry-run` runs the same diff pass and reports without writing.

---

### `SyncContext` dataclass (model, transform)

**Analog:** `voss/harness/voss_md.py:33-39` `@dataclass(frozen=True) Block`.

```python
@dataclass(frozen=True)
class Block:
    kind: str
    id: str | None
    body: str
    recorded_hash: str | None
```

**Shape (D-02):** `SyncContext` carries layout vars (project name, root, repo-vs-worktree, command prefixes, workspace paths) + project facts (`type, install_command, check_command, tools, review:{enabled, reviewers}`) + capabilities. Per D-04 every field is an explicit value or an absent-marker so `StrictUndefined` still catches genuine template bugs while `{% if %}` blocks omit missing facts. Render each artifact from one shared `SyncContext` (D-17). Prefer `frozen=True` for determinism.

---

### `voss/layout.py` — layout-context derivation (service/utility, git/fs transform)

**Analog:** `voss/harness/cognition.py:311-347` `build_repo_idx` — the established git-probe pattern.

```python
# cognition.py:315-326 — git rev-parse probe with graceful fallback
try:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), capture_output=True, text=True, timeout=5,
    )
    if result.returncode == 0:
        git_head = result.stdout.strip()
except (OSError, subprocess.SubprocessError):
    pass
```

**Apply to layout derivation (R2):** use `git rev-parse --show-toplevel` (repo root), `git rev-parse --is-inside-work-tree` / `--git-dir` vs `--git-common-dir` divergence (worktree detection) — same `subprocess.run(..., timeout=N)` + `(OSError, subprocess.SubprocessError)` guard + fs fallback. **Determinism (constraint):** no timestamps, no env-dependent ordering; same tree → same context (R2 acceptance). `.voss` dir resolved via `cognition.voss_dir(cwd)` (`cognition.py:75-76`, returns `cwd / ".voss"`).

---

### `voss sync` CLI command (controller, request-response)

**Analog:** `voss/cli.py:476-488` `init` command + the `main` group at `voss/cli.py:200-206`.

```python
@main.command("init")
@click.argument("target", type=click.Path(path_type=Path))
@click.option("--force", is_flag=True, default=False)
@click.option("--name", "project_name", default=None, help="...")
def init(target: Path, force: bool, project_name: str | None) -> None:
    """Scaffold a new Voss project."""
    _scaffold_target(target, force=force, name=project_name)
    click.echo(f"initialized voss project at {target}")
```

**Registration:** add `@main.command("sync")` directly in `voss/cli.py` (the compiler-verb group at line 200), mirroring `init`. `--force` (D-16, prompts only) and `--dry-run` (D-14) as `is_flag` options. Use `click.echo(...)` for per-file status lines (D-13); `click.echo(..., err=True)` for warnings.

**Exit codes (D-15):** exit 0 for changed/no-changes/skipped-edited; nonzero only on real failures (`HashMismatch`, IO). Mirror existing `raise click.exceptions.Exit(code=1)` (`voss/cli.py:421`) and `raise click.ClickException(...)` (`voss/cli.py:451`) for errors. Warnings are NOT failures.

---

### Project-facts config reader (`project:` block) (config, file-I/O)

**Analog:** `voss/harness/conventions.py:262-276` `_load_memory_config` — the `.voss/config.yml` precedent.

```python
def _load_memory_config(cwd) -> dict:
    """Load the optional `.voss/config.yml` memory section; never raises."""
    config_path = Path(cwd) / ".voss" / "config.yml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:  # noqa: BLE001
        return {}
    memory = data.get("memory") if isinstance(data, dict) else None
    return memory if isinstance(memory, dict) else {}
```

**Apply (D-01/D-02):** add a sibling `_load_project_config(cwd)` reading the `project:` key from the same `.voss/config.yml`, never raising, same `yaml.safe_load(...) or {}` + isinstance guards. Config wins over fs detection (D-01); missing keys fall back to detection probes (pyproject→python, package.json→node) and sync reports detected values with a `(detected)` marker (D-03).

---

### `.voss/sync-state.json` manifest writer (utility, file-I/O)

**Analog:** `voss/cli.py:99-115` `_write_text_atomic` + `json` (already imported in cli.py:4).

**Shape (D-10/D-12):** `{ path → sha256 }` for synced prompts, plus doc/fence bookkeeping. Deterministic content (sync is idempotent) → committed to repo (D-12), survives clones. Write via the atomic helper. **Missing-manifest rule (D-11):** treat absence as "files edited" — skip + warn, never clobber without hash evidence; `--force` to re-adopt. Hash via `hashlib.sha256(body.encode()).hexdigest()` (same as `voss_md.py:232`).

---

### VOSS.md workflow fence (service, file-I/O) — REUSE, do not reimplement

**Analog / engine:** `voss/harness/voss_md.py:206-270` `write_fence_body` (REUSE verbatim — constraint forbids a parallel marker system).

```python
write_fence_body(voss_md_path, fence_id="workflow", body=rendered_body)
```

**Behavior already provided (R4):** inserts fence when absent (appends fully-formed fence at EOF, `write_fence_body:255-264`); regenerates in place when present; preserves all human content outside the fence (parse→replace→render, lines 231-266); refuses on hash drift via `HashMismatch` (lines 241-249) unless `adopt=True`. D-16: fence drift resolution stays in the existing `voss memory adopt` flow — sync does NOT pass `adopt=True`. Render the fence body string via `render_package_template` first, THEN hand to `write_fence_body` (D-17: Jinja never touches VOSS.md structure). Pick fence id (Claude's discretion, e.g. `id=workflow`).

---

### Doc + fence-body templates (template, transform)

**Analog (docs):** `voss/templates/init/README.md.jinja:1-8` — plain markdown + `{{ }}` interpolation.

```jinja
# {{ project_name }}

A new Voss project scaffolded by `voss init`.
```

**Analog (fence body rendered to string):** `voss/templates/agent/cognition_block.md.jinja`, rendered at `voss/harness/agent.py:101-110` with `{% if with_constraints %}`-style conditionals — mirror for D-04 graceful omission.

**Templates to create under `voss/templates/docs/`:**
- `cheatsheet.md.jinja` — agent operating guide (D-06): repo layout, where things live, active capabilities, do/don't. Terse imperative (D-09).
- `commands.md.jinja` — project-relevant voss command subset with layout-adjusted invocations (D-07).
- `review.md.jinja` — rendered only when `review.enabled` (D-08); fence omits its link when false.
- fence-body template (e.g. `voss_md_fence.md.jinja`) — rendered to string, passed to `write_fence_body`.

**Header constraint:** each generated doc carries a "generated — do not edit" header (R3, constraints). Use `{% if %}` blocks (StrictUndefined-safe) for absent facts (D-04). Templates resolve via `templates/docs/<name>.jinja` resource path through `render_package_template`.

---

### Prompt-loader override (utility/provider, transform)

**Render sites to wrap (the 3 synced prompts):**
- `voss/harness/board/reviewer_a.py:38-42` → `REVIEWER_A_ROLE_PROMPT` from `templates/prompts/reviewer_a_role.txt.jinja`
- `voss/harness/board/reviewer_b.py:45-48` → `REVIEWER_B_SYSTEM` from `templates/prompts/reviewer_b_system.txt.jinja`
- `voss/harness/em/llm.py:16-20` → `EM_SYSTEM` from `templates/prompts/em_system.txt.jinja`

All three are module-level `render_package_template("voss", "templates/prompts/<x>.txt.jinja", {})` constants (package-internal, no project override today).

**Runtime substitution analog:** `voss/harness/agent.py:358-360` `_compose_loop_system` — str.replace placeholder fill, NOT f-string/Jinja.

```python
def _compose_loop_system(max_iterations: int) -> str:
    """Fill the PLAN_LOOP_SYSTEM placeholder via str.replace (cache-stable)."""
    return PLAN_LOOP_SYSTEM.replace("{max_iterations}", str(max_iterations))
```

**Apply (R5/D-18):** loader prefers a project copy under `.voss/prompts/<name>.txt` (jinja suffix stripped) when present, else the package template (unchanged behavior, R5 acceptance). On the project copy, fill `${AGENT}` / `${PROJECT}` / `${WORKSPACE}` via plain `str.replace` (D-18 — distinct shell syntax avoids Jinja collision; constraint: NOT Jinja at runtime so StrictUndefined can't detonate on user edits). Module-level constants become lazy/load-time lookups so the project copy is checked at load. Sync writes the project copies via the sync render loop + hash-guard (R6).

---

## Shared Patterns

### Rendering — single Jinja entrypoint
**Source:** `voss/template_render.py:22-28`
**Apply to:** every doc, the fence body, and the synced prompt baking (D-17 / constraint)
```python
render_package_template("voss", "templates/docs/cheatsheet.md.jinja", ctx)
```
Cached `Environment` per package: `StrictUndefined`, `trim_blocks`, `lstrip_blocks`, `keep_trailing_newline`, `autoescape=False`. No second env, no ad-hoc `Template(...)`.

### Hashing — sha256 hexdigest
**Source:** `voss/harness/voss_md.py:232`
**Apply to:** manifest entries, prompt edit-detection (R6)
```python
new_hash = hashlib.sha256(body.encode()).hexdigest()
```

### Config loading — never-raise YAML
**Source:** `voss/harness/conventions.py:262-276`
**Apply to:** the new `project:` block reader (D-01)
`yaml.safe_load(...) or {}` inside `try/except Exception` returning `{}`; isinstance guards on every nested dict access.

### Atomic file write
**Source:** `voss/cli.py:99-115` (`_write_text_atomic`) and `voss/harness/voss_md.py:267-270` (`.tmp` + `os.replace`)
**Apply to:** `.voss/docs/*`, `.voss/sync-state.json`. (`write_fence_body` self-handles VOSS.md.)

### Machine-write-refuses-on-drift philosophy
**Source:** `voss/harness/voss_md.py:241-249` (`HashMismatch`)
**Apply to:** prompt hash-guard (D-11/R6) — extend the same "refuse without hash evidence" principle: missing manifest ⇒ treat prompt as edited ⇒ skip+warn. Generated docs are exempt (machine-owned, always regenerated, D-16/R3).

### CLI conventions
**Source:** `voss/cli.py:200-206` (`main` group), `voss/cli.py:476-488` (`init`)
**Apply to:** `voss sync` registration. `@main.command`, `click.option(... is_flag=True)`, `click.echo` (stdout status) / `click.echo(..., err=True)` (warnings), `raise click.exceptions.Exit(code=1)` / `raise click.ClickException(...)` for failures only.

### Test conventions
**Source:** `tests/cli/test_init.py:18-28` (CliRunner + `isolated_filesystem`), `tests/harness/test_voss_md_fence.py:17-67` (fence fixtures, `tmp_path`, `pytest.raises(HashMismatch)`)
**Apply to:** `tests/cli/test_sync.py` (idempotency: invoke sync twice, assert second run reports no changes / byte-identical), `tests/harness` unit tests for layout derivation (two fixtures: plain repo-root vs worktree, determinism) and fence insert/regenerate/drift.
```python
runner = CliRunner()
with runner.isolated_filesystem():
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0, result.output
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Worktree-layout detection branch | utility | git transform | `build_repo_idx` probes git HEAD/ls-files but no existing code distinguishes repo-root vs worktree checkout — new logic (use `git rev-parse --git-dir` vs `--git-common-dir` divergence). Test fixtures must construct an actual worktree. |

## Metadata

**Analog search scope:** `voss/` (cli.py, template_render.py, harness/voss_md.py, harness/conventions.py, harness/cognition.py, harness/agent.py, harness/board/*, harness/em/llm.py), `voss/templates/`, `tests/cli/`, `tests/harness/`
**Files scanned:** ~14 read in full or targeted ranges
**Pattern extraction date:** 2026-06-09

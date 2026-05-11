---
phase: M1-harness-happy-path
plan: 04
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/edit_scope.py (new)
  - voss/harness/cli.py (edit_cmd + _run_repl edit_scope thread)
  - voss/cli.py (help-string update)
  - voss/harness/permissions.py (diff preview + expand-scope prompt)
  - tests/harness/test_edit_scope.py (new)
  - tests/harness/test_edit_cmd.py (new)
tests_added: 18
tests_total_passing: 135
---

# M1-04 Summary: `voss edit` + Scope-Aware Gate + Diff Preview

## What shipped

### `voss/harness/edit_scope.py` (new)

`EditScope` dataclass with:

- `resolve(cwd, path)` — picks `<path>` plus sibling test mirror. Handles
  files (test_<name>.py, <name>_test.py, sibling-and-walked `tests/...`
  mirrors), directories (walks for `tests/<rel>/` mirror), and the common
  `src/`-prefix-strip case (so `src/foo/bar.py` maps to `tests/foo/test_bar.py`).
- `allows_write(target)` — returns True only if target is inside scope AND
  under cwd. Belt-and-braces cwd jail.
- `expand(target)` — adds target to in-memory scope. Never touches
  `PermissionStore` → "always" persistence is session-only (D-04).
- `summary()` — sorted relpath list for banner.

### `voss/harness/permissions.py` extensions

`PermissionGate` gained two optional fields:
- `edit_scope: EditScope | None` — set by `voss edit`; `None` for do/chat.
- `scope_prompt_fn: Callable | None` — test injection for the expand prompt.

New methods:
- `_render_diff_preview(tool_name, args)` — best-effort unified diff to
  stderr for `fs_write` and `fs_edit`. Failure swallowed (best-effort).
  Resolves against `edit_scope.cwd` if set, else `Path('.')`.
- `_prompt_expand(target)` — `[y]/[a]/[n]` prompt returning `("once" |
  "always" | "denied")`.

### `check()` flow (order matters)

```
1. mode_allows(...)                     # structural denial first
2. if WRITE:  _render_diff_preview(...) # CTRL-08, scope-independent
3. if edit_scope and WRITE and out-of-scope:
       _prompt_expand(target)           # AFTER diff (W4)
4. needs_prompt(...) / store.always / _prompt(...)
```

**The diff render is OUTSIDE the scope guard** — that's the W1 fix. Sample
grep confirms placement:

```
        if tool_name in WRITE:
            self._render_diff_preview(tool_name, args)
```

### `voss/harness/cli.py` additions

- `edit_cmd` (`@click.command("edit")`) — accepts `PATH` arg, optional
  `--cwd`, `--model`, `--json`, `--mode`, `--auth`. Defaults to
  `--mode=edit` (D-07). Constructs `EditScope.resolve(cwd, path)`, prints
  the resolved scope summary, and hands off to `_run_repl(edit_scope=scope)`.
- `_run_repl` now accepts `edit_scope` (default `None`) and threads it into
  `PermissionGate(edit_scope=...)`.
- `AGENT_COMMANDS` extended to include `edit_cmd`.
- `voss/cli.py` help-string updated to list `edit` among agent verbs.

## Verification

- `pytest tests/harness/test_edit_cmd.py tests/harness/test_edit_scope.py tests/harness/test_permissions_modes.py tests/harness/test_cli.py -x` — 37 passed.
- Full harness suite: `pytest tests/harness/` — 135 passed (up from 117).
- `python -m voss.cli edit --help` shows `PATH` arg + "scope" wording.
- `python -m voss.cli --help` lists `edit` under agent verbs.

## Key behaviors locked

- **D-01** REPL session — reuses `_run_repl` (Ctrl-D/EOF/`/exit`/`/quit` exit).
- **D-02** sibling-mirror resolution — covered by 5 tests (file + tests-dir
  mirror, file no sibling, dir + mirror, pytest-style sibling, top-level
  sibling).
- **D-03** reads stay under existing cwd jail — gate only intercepts writes.
- **D-04** `[y/once/always/n]` — `"always"` calls `scope.expand()`,
  `PermissionStore` untouched → session-only persistence.
- **CTRL-08** diff preview — fires for `fs_write` + `fs_edit`, with AND
  without `edit_scope`. Ordering test (W4) asserts diff renders before the
  expand prompt.
- **CLIH-04** `voss edit <path>` registered + help-documented.

## Handoff for downstream plans

### M2 (`voss do --mode=edit` + sessions move)

- W1 lift means `voss do`/`voss chat --mode=edit` ALREADY get diff previews
  via the same `PermissionGate._render_diff_preview` call site. M2 doesn't
  need to re-wire anything.
- `EditScope` state lives only on the gate instance. It is NEVER written to
  `PermissionStore`, so when M2 moves sessions to `.voss/sessions/`, no
  scope state leaks into the persisted record. Session save still serializes
  only the `SessionRecord` schema (M1-03 invariant holds).

### Plan 05 (`/mode` REPL command + `--confirm` for `/mode auto`)

The mode field on `PermissionGate` is the mutation target. Switching mode
mid-session via `/mode` already works (chat_cmd does
`gate.mode = new_mode`). Plan 05 adds the `--confirm` escalation guard.

### Plan 06+07 (e2e happy-path)

`voss edit <path>` should appear in the happy-path script alongside `voss
do "fix bug"` and `voss chat`. The diff preview rendered to stderr is what
the CTRL-08 verification step grabs.

## Requirements covered

CLIH-04, CTRL-08.

---
phase: M1-harness-happy-path
plan: 01
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/tools.py
  - voss/harness/permissions.py
  - voss/harness/agent.py
  - tests/harness/test_tools.py
  - tests/harness/test_permissions_modes.py
tests_added: 13
tests_total_passing: 86
---

# M1-01 Summary: Permission-Tier Foundation

## What shipped

### `ToolEntry` dataclass (voss/harness/tools.py)

Frozen dataclass pairing a `ToolDescriptor` with an explicit `is_mutating: bool`.
Proxies `name`, `description`, `parameters`, and `invoke(**kwargs)` to the
wrapped descriptor so callers (`run_turn`, `_format_tools`) keep working.

`make_toolset(cwd)` now returns `dict[str, ToolEntry]`. All 9 tools registered
with hardcoded classification at the registration site — **no name-pattern
inference** (D-06):

| Read-only (6)                                              | Mutating (3)                  |
|------------------------------------------------------------|-------------------------------|
| fs_read, fs_glob, fs_grep, git_status, git_diff, voss_check | fs_write, fs_edit, shell_run  |

### `mode_allows` predicate (voss/harness/permissions.py)

```python
def mode_allows(mode: Mode, tool_name: str, is_mutating: bool) -> tuple[bool, str]:
    # plan : deny any mutating tool        -> "denied by mode plan"
    # edit : deny shell_run (special-case)  -> "denied by mode edit"
    # auto : allow everything (downstream allowlist/timeouts still apply)
```

Strict tier semantics per D-05. `edit` allows fs_write/fs_edit by mode but the
in-mode prompt (`needs_prompt`) still fires unless `auto_yes=True` or the
signature is remembered — D-07 structural half preserved.

### `PermissionGate.check` integration

Signature: `check(tool_name, args, *, is_mutating: bool = False)`. Structural
denial via `mode_allows` fires **before** the prompt path. Default of `False`
preserves backward compatibility for any pre-existing callers (only `run_turn`
threads the real flag).

### Agent loop wiring (voss/harness/agent.py)

- Import switched from `ToolDescriptor` to `ToolEntry`.
- `run_turn` and `_format_tools` typed as `dict[str, ToolEntry]`.
- Tool dispatch threads `is_mutating=entry.is_mutating` into `gate.check`.

## Verification

- `pytest tests/harness/test_tools.py tests/harness/test_permissions_modes.py tests/harness/test_agent_integration.py -x` — 36 passed.
- Full harness suite: `pytest tests/harness/` — 86 passed.
- Manual: `make_toolset(Path('.'))` reports 6 read-only / 3 mutating split.
- Manual: `mode_allows('plan', 'fs_write', True)` → `(False, 'denied by mode plan')`.

## Integration points for downstream plans

### Plan 04 (edit-scope gate)

Plan 04 will add a per-path edit scope on top of mode-tier denial. Hook in
`PermissionGate.check` after the `mode_allows` block and before `needs_prompt`:

```python
allowed, why = mode_allows(self.mode, tool_name, is_mutating)
if not allowed:
    return False, why
# <-- Plan 04: edit-scope predicate here (denies fs_write/fs_edit
#     outside the declared scope even when mode=edit).
if not self.needs_prompt(tool_name): ...
```

The `is_mutating` flag is already threaded — Plan 04 just needs `args["path"]`.

### Plan 05 (`/mode` REPL escalation)

This plan exposes the structural predicate; Plan 05 owns the REPL command and
the `--confirm` escalation requirement for `/mode auto`. The mode field on
`PermissionGate` is the mutation target; tier semantics are now load-bearing
contract — switching mode is a real capability change, not a prompt-policy
change.

### Plan 02-03 (CLI surface, REPL bootstrap)

`make_toolset` return type changed (`dict[str, ToolDescriptor]` → `dict[str, ToolEntry]`).
Callers needing the raw descriptor use `entry.descriptor`; most code can use
`entry.invoke(...)` and the proxied properties unchanged.

## Decisions implemented

- **D-05** strict mode tiers — covered for all three modes.
- **D-06** data-driven mutation classification — hardcoded per-tool at registration.
- **D-07** structural half — prompt path preserved for in-mode mutating tools.

## Requirements covered

CTRL-01..07.

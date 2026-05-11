---
phase: M1-harness-happy-path
plan: 05
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/config.py (new)
  - voss/harness/cli.py (_resolve_default_model + _handle_login + new slash handlers)
  - tests/harness/test_harness_config.py (new)
  - tests/harness/test_repl_slash.py (new)
  - tests/harness/test_model_persistence.py (new)
tests_added: 18
tests_total_passing: 153
---

# M1-05 Summary: `/login` · `/model` · `/mode --confirm` + preferred_model resolution

## What shipped

### `voss/harness/config.py` (new)

Minimal TOML reader/writer scoped to `[harness]`. Public surface:

```python
config_path() -> Path                       # ~/.config/voss/config.toml (XDG-aware)
load_harness_config() -> dict[str, str]     # {} on missing file
set_preferred_model(name: str) -> Path      # chmod 600, preserves other sections
```

Regex-based parser is intentional: file has one section, one key in M1. No
`tomllib` write helper exists in stdlib; rolling a single-key writer is
cheaper than pulling in `tomli-w`. Preserves any unrelated `[other]` sections
already in the file (verified by test).

### REPL slash commands (`voss/harness/cli.py`)

| Slash command            | Behavior |
|--------------------------|----------|
| `/login`                 | Status for both Claude + Codex. |
| `/login anthropic`       | Existing fresh → OK + expiry. Existing expired → `refresh_anthropic`. Missing → "Run: claude /login". |
| `/login openai`/`/login codex` | Existing → status. Missing → "Run: codex login". |
| `/model` (no arg)        | Active model + provider availability matrix. |
| `/model <name>`          | `configure(default_model=name)` + `set_preferred_model(name)`. |
| `/mode` (no arg)         | Print current mode. |
| `/mode plan` / `/mode edit` | Switch instantly. |
| `/mode auto`             | **Refused** — `escalating to auto requires --confirm`. |
| `/mode auto --confirm`   | Switch to auto. |
| `/help`                  | Updated list reflects new commands + `--confirm` form. |

### D-08 narrowing (deliberate)

`/login` does NOT drive a bespoke OAuth flow. Plan Objective documents this
narrowing; `_handle_login` carries an in-code comment noting:

> M1 contract: D-10 forbids new credential stores, so re-auth must go
> through the upstream CLI. We refresh EXISTING tokens via
> `auth.refresh_anthropic` / `auth.refresh_codex`; for MISSING tokens we
> print the upstream command. Full OAuth flow drive is deferred.

### B3 fix: model resolution lives in commands, not `_run_repl`

`_resolve_default_model(user_explicit: str | None)` is the single source of
truth for D-09 resolution order:

```
1. user_explicit (--model flag)       wins outright
2. else ~/.config/voss/config.toml [harness] preferred_model
3. else leave get_config().default_model alone
```

Called from `do_cmd`, `chat_cmd`, `edit_cmd` BEFORE `SessionRecord.new(...)`,
so the persisted record carries the resolved model. The broken
`if persisted and not record.model:` guard from the prior draft is GONE
(verified: `grep -cE 'if persisted and not record\.model'` → 0).

## Verification

- `pytest tests/harness/test_harness_config.py tests/harness/test_repl_slash.py tests/harness/test_model_persistence.py tests/harness/test_cli.py -x` — 24 passed.
- Full harness suite: `pytest tests/harness/` — 153 passed (up from 135).
- `python -m voss.cli edit --help` still works.
- `_print_slash_help()` output verified to include `/login`, `/model`,
  `/mode`, `--confirm`.

## Decisions implemented

- **D-07 runtime half** — `/mode auto` mid-session refuses without `--confirm`.
- **D-08 (narrowed)** — `/login` and `/model` are first-class REPL commands.
  `/login` does status + refresh-existing (delegates upstream for missing).
- **D-09** — preferred_model resolution order enforced before
  `SessionRecord.new(...)` in every command entry point.
- **D-10** — no new credential stores; reads/writes go through existing
  `auth.py` paths.

## Requirements covered

CLIH-01, CLIH-02, CTRL-05.

## Handoff for downstream plans

### Plan 06+07 (e2e happy-path)

Happy-path script can now exercise:
1. `voss chat` → `/login` → see status line.
2. `voss chat` → `/model gpt-4o` → quit → relaunch → banner reflects gpt-4o
   AND `/save` produces a record with `model: "gpt-4o"`.
3. `voss chat` → `/mode auto` → refused → `/mode auto --confirm` → accepted.

### M2

`config.toml` will likely gain `[telemetry]`, `[context]`, etc. The
preserve-other-sections logic is already in place; future writers should
add their own regex block helper or upgrade to a real TOML library at that
point. Don't widen `set_preferred_model`'s contract — add a new
`set_xxx(value)` per key.

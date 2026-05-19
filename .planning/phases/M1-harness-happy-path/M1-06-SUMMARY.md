---
phase: M1-harness-happy-path
plan: 06
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/cli.py (tools_cmd + config_cmd + AGENT_COMMANDS)
  - voss/cli.py (help-string update)
  - tests/harness/test_tools_config_cmds.py (new)
tests_added: 6
tests_total_passing: 159
---

# M1-06 Summary: `voss tools` + `voss config`

## What shipped

### `voss tools`

Plain text table, three columns: `name | mut | description`. Sourced from
`make_toolset(cwd)` → `ToolEntry.is_mutating`. Output:

```
  name        mut    description
  ----------  -----  ----------------------------------------
  fs_edit     yes    Replace exact `old` text with `new` ...
  fs_glob     no     List files matching a glob pattern, ...
  fs_grep     no     Recursively search for a regex pattern...
  fs_read     no     Read a UTF-8 text file from the project...
  fs_write    yes    Write text to a file inside cwd...
  git_diff    no     Run `git diff`...
  git_status  no     Run `git status --porcelain`.
  shell_run   yes    Run a shell command from the allowlist...
  voss_check  no     Run `voss check`...
```

Sorted alphabetically. Description truncated to 60 chars with `…`. Plain
text chosen over a `rich` table because: (a) the renderer module isn't a
table library; (b) we want this scrape-friendly for shell-prompt
integration; (c) `mut` column doubles as a sort-grep hook
(`voss tools | grep ' yes '` → mutating-only list).

### `voss config`

- `voss config` — opens the file in `$EDITOR` (defaults to `vi`).
- `voss config --show` — prints the file to stdout. Empty file → `(empty)`.
- `voss config --config-path PATH` — testing-only override. Behind the same
  flag because rolling a separate ENV var for one private flag isn't worth
  the API surface.

If the file doesn't exist, it's created with a single `[harness]\n` header
and `chmod 600` before either editor or `--show` path runs.

### Wiring

Both commands appended to `AGENT_COMMANDS`, so the existing
`register(group)` call in `voss.cli` picks them up automatically. Help
blurb in `voss/cli.py` updated to list `tools` + `config` alongside the
other agent verbs.

## Verification

- `pytest tests/harness/test_tools_config_cmds.py tests/harness/test_cli.py -x` — 12 passed.
- Full harness suite: `pytest tests/harness/` — 159 passed (up from 153).
- Manual: `python -m voss.cli tools` prints all 9 rows with correct mut
  flags.
- Manual: `python -m voss.cli config --show --config-path /tmp/x.toml`
  creates `/tmp/x.toml`, prints contents (or `(empty)`).
- Manual: `python -m voss.cli --help` lists `tools` and `config` under
  agent verbs.

## Deferred (deliberate)

- Interactive provider-table UI inside `voss config` (e.g. `--add-key`,
  `--set-model` interactive prompt). Deferred until real usage signals
  demand. `/model <name>` already persists from the REPL (Plan 05).
- A `voss tools --json` flag for scriptable output. Not required by
  CLIH-07 happy path; revisit if a tool consumer asks.

## Requirements covered

CLIH-07, CLIH-09.

## Re-execution Check — 2026-05-18

Re-ran M1-06 against the current codebase after later phases expanded the
tool registry. The user-facing contract still holds:

- `voss tools` now lists every current registered tool dynamically instead
  of the original 9-tool M1 snapshot.
- The table header was restored to the full `mutating` label from the plan
  contract (`name | mutating | description`).
- `tests/harness/test_tools_config_cmds.py` now asserts against
  `make_toolset(tmp_path)` so future additive read-only tools do not stale
  the M1 happy-path check.

Verification:

- `python3 -m pytest -q tests/harness/test_tools_config_cmds.py tests/harness/test_cli.py -x` — 20 passed.
- `python3 -m voss.cli --help` lists `tools` and `config`.
- `python3 -m voss.cli tools` prints the current tool table with
  `mutating` values.
- `python3 -m voss.cli config --show --config-path <tmp>/config.toml`
  creates the file and exits 0.
- `EDITOR=true python3 -m voss.cli config --config-path <tmp>/config.toml`
  exits 0.

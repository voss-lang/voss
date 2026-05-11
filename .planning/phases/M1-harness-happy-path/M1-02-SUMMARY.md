---
phase: M1-harness-happy-path
plan: 02
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/diagnostics.py (new)
  - voss/harness/cli.py (doctor_cmd rewrite)
  - tests/harness/test_diagnostics.py (new)
  - tests/harness/test_cli.py (existing doctor tests updated)
tests_added: 26
tests_total_passing: 112
---

# M1-02 Summary: `voss doctor` Check Registry

## What shipped

### `voss/harness/diagnostics.py` (new module)

- `CheckResult` enum: `OK | WARN | FAIL` → ✓/⚠/✗.
- `Check` dataclass: `name`, `result`, `detail`, `fix` (optional shell suggestion).
- 7 pure check functions covering D-11 minimal-essentials:
  1. `check_python_version` (>=3.10, FAIL otherwise)
  2. `check_voss_import` (voss.cli + voss_runtime)
  3. `check_provider_auth` (Anthropic primary OK; expired Anthropic = WARN; Codex-only = WARN; nothing = FAIL; honors `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` env)
  4. `check_git_on_path` (shutil.which)
  5. `check_cwd_writable` (tempfile probe in cwd)
  6. `check_config_dirs_creatable` (XDG-honoring `~/.config/voss/`, `~/.local/state/voss/sessions/`)
  7. `check_project_dirs` (informational `.voss/`, `.voss-cache/` — WARN at worst, never FAIL)
- `run_all_checks(cwd)` returns the 7 checks in documented display order.
- `aggregate_exit_code(results)`: 0 if no FAIL; 1 if any FAIL.

**No `subprocess`, no `os.system`** — checks only probe via `shutil.which`, `tempfile`, and `Path.mkdir`. D-13 boundary preserved: doctor diagnoses, never fixes.

### `doctor_cmd` rewrite (voss/harness/cli.py)

New signature: `doctor_cmd(--cwd PATH)` (default ".") — `--cwd` improves testability and supports the FAIL-path manual verification (`--cwd=/nonexistent` → exit 1).

Renders a traffic-light table:
```
  ✓  python          3.13
  ⚠  provider auth   only codex (...)
     → claude /login
  ✗  cwd writable    [Errno 2] ...
     → chmod u+w /nonexistent
```

### D-14 exit-code semantics

| Result mix          | Exit code | Stderr summary                              |
|---------------------|-----------|---------------------------------------------|
| All OK              | 0         | (empty)                                     |
| OK + WARN (no FAIL) | 0         | `doctor: N warning(s) (<names>)`            |
| Any FAIL            | 1         | `failed checks. fix above and re-run.`      |

The WARN-only stderr summary is the W2 nuance: CI / shell prompts can grep
stderr to surface informational misses without failing the build.

## Verification

- `pytest tests/harness/test_diagnostics.py tests/harness/test_cli.py -x` — 32 passed.
- Full harness suite: `pytest tests/harness/` — 112 passed (up from 86).
- Manual all-OK: `python -m voss.cli doctor` → exit 0, empty stderr.
- Manual WARN-only (simulated via monkeypatch): exit 0, stderr `doctor: 1 warning (provider auth)`.
- Manual FAIL: `python -m voss.cli doctor --cwd=/nonexistent` → exit 1, stderr summary line.

## Integration points for downstream plans

### Plan 05 (`/login` slash + `claude /login` invocation)

When Plan 05 wires `/login` into the REPL and the standalone `claude /login`
proxy, the **same** auth surface drives the doctor `provider auth` check:

- After `/login` succeeds, a fresh call to `check_provider_auth()` will flip
  from FAIL → OK (or WARN → OK if upgrading from Codex-only).
- The `fix` string on the WARN/FAIL row already points users to
  `claude /login`, so Plan 05 only needs to make that command actually work;
  doctor messaging is already aligned.
- No new credential resolution path was introduced — D-10 boundary preserved.
  Doctor only calls `auth.load_anthropic_oauth()` and `auth.load_codex()`.

### Plan 03 (REPL `/doctor` slash)

If Plan 03 adds an in-REPL `/doctor` command, it can call
`diag.run_all_checks(cwd)` directly and render the same table via `Renderer`,
reusing the glyph map and exit-code logic without re-parsing CLI output.

### Plan 04 (edit-scope) — no interaction

Plan 04 doesn't touch doctor; the check registry is independent of permission
state.

## Decisions implemented

- **D-11** minimal-essentials check set + display order — 7 checks, ordered.
- **D-12** traffic-light glyphs — ✓/⚠/✗ with green/yellow/red.
- **D-13** diagnose-only — `subprocess` count is 0 in diagnostics.py; fixes are strings only.
- **D-14** exit codes + WARN-only stderr nuance — implemented + tested.

## Requirements covered

CLIH-08.

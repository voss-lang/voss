---
phase: M1-harness-happy-path
plan: 07
status: complete
date: 2026-05-11
files_modified:
  - voss/harness/cli.py (do_cmd / chat_cmd / standalone main defaults → plan)
  - voss/cli.py (bare main bare-invoke → plan)
  - tests/harness/test_run_not_overloaded.py (new)
  - tests/harness/test_happy_path_integration.py (new)
tests_added: 8
tests_total_passing: 167
---

# M1-07 Summary: Default Modes + Compiler-Verb Guard + Happy-Path Integration

## What shipped

### Per-command default mode matrix (D-07)

| Command          | Default mode | Source |
|------------------|--------------|--------|
| `voss do`        | `plan`       | `voss/harness/cli.py` do_cmd `default="plan"` |
| `voss chat`      | `plan`       | `voss/harness/cli.py` chat_cmd `default="plan"` |
| bare `voss`      | `plan`       | `voss/cli.py` + `voss/harness/cli.py` main fallback |
| `voss edit`      | `edit`       | unchanged from Plan 04 |
| `voss resume`    | `edit`       | unchanged (resuming continues edit work) |

Grep verification:
- `default="plan"` in `voss/harness/cli.py` → 2 (do_cmd + chat_cmd)
- `default="edit"` in `voss/harness/cli.py` → 2 (edit_cmd + resume_cmd)
- `mode="plan"` in `voss/cli.py` → 1 (bare-invoke)
- `mode="plan"` in `voss/harness/cli.py` → 1 (standalone main bare-invoke)

### `tests/harness/test_run_not_overloaded.py` (CLIH-10 guard)

4 tests lock the contract:
- `voss run --help` describes compiler semantics ("Compile and execute a Voss source file"). Test scans for `voss source` / `compile and execute` / `.voss`. Rejects `natural-language` and `agent task`.
- `voss run hello.voss` does NOT emit "no usable credentials" — i.e. the compile path never hits auth.
- `AGENT_COMMANDS` does NOT contain a "run" entry — proves the unified `voss` CLI keeps `run` as a compiler verb.
- `voss do --help` mentions "task"; `voss run --help` does NOT mention "natural" — proves the two verbs stay distinct.

### `tests/harness/test_happy_path_integration.py` (CLIH-01/02/03/05/06)

4 tests that compose Plans 01-06:

| Class                   | Test                                          | Composes |
|-------------------------|-----------------------------------------------|----------|
| `TestDoHappyPath`       | `test_voss_do_runs_in_plan_mode_without_crash` | Plans 01 (mode tiers), 03 (session), 06 (commands) |
| `TestSessionsLifecycle` | `test_save_list_and_load`                      | session save/list/load round-trip |
| `TestSessionsLifecycle` | `test_session_json_has_no_creds`               | M1-03 D-17 secret-pattern scan on integration-produced JSON |
| `TestSessionsCmd`       | `test_sessions_lists_saved`                    | `voss sessions` command output contains record id |

**Fixtures available for M2 reuse:**

- `isolated_env(monkeypatch, tmp_path)` — sandboxes `XDG_STATE_HOME`,
  `XDG_CONFIG_HOME`, and stubs `ANTHROPIC_API_KEY=sk-test-fake-...` so
  integration tests never touch real Keychain / real config / real network.
- `mock_provider(monkeypatch)` — patches `voss.harness.cli._resolve_auth_or_die`
  to return a MagicMock provider whose `.complete` returns a canned
  `ProviderResponse(model="claude-sonnet-4-20250514", ...)` carrying a
  predetermined `Plan`. Required fields explicit (text, model, prompt_tokens,
  completion_tokens, cost_usd) — B2 fix preserved.

### Provider response import fix (B1 + B2)

Tests import `ProviderResponse` from `voss_runtime.providers.base` (NOT the
non-existent `ModelResponse`). Construction passes the required `model`
field explicitly. Grep confirms: `ProviderResponse` appears 3 times,
`ModelResponse` 0 times.

## Verification

- `pytest tests/harness/test_run_not_overloaded.py -x` → 4 passed.
- `pytest tests/harness/test_happy_path_integration.py -x` → 4 passed.
- Full M1 harness suite: `pytest tests/harness/` → 167 passed (up from 159).
- Manual: `python -m voss.cli do --help` shows `--mode [plan|edit|auto]`.
- Manual: `python -m voss.cli edit --help` notes "(default edit per D-07)".
- Manual: `python -m voss.cli run --help` shows "Compile and execute a Voss
  source file" — no agent verbiage.

## Requirements covered

CLIH-01, CLIH-02, CLIH-03, CLIH-05, CLIH-06, CLIH-10.

## M1 phase status

All 7 plans land green:

| Plan  | Title                                          | Tests added |
|-------|------------------------------------------------|-------------|
| M1-01 | Permission-tier foundation (ToolEntry + mode_allows) | 12 |
| M1-02 | `voss doctor` check registry                   | 26 |
| M1-03 | Session redaction guarantee                    | 5 |
| M1-04 | `voss edit` + scope-aware gate + diff preview  | 18 |
| M1-05 | `/login` · `/model` · `/mode --confirm` + persistence | 18 |
| M1-06 | `voss tools` + `voss config`                   | 6 |
| M1-07 | Default modes + compiler guard + happy path    | 8 |
| **Total** | — | **93 new** |

Harness suite: 167 passing.

M1 is ready for verification phase.

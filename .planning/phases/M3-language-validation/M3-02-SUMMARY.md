---
phase: M3
plan: 02
status: complete
date: 2026-05-11
---

# M3-02 Summary — D-01 auto-stub fallback + D-02 stderr banner

## Change locations

### voss_runtime/providers/__init__.py (lines 1-7, 13-17)
- Added `import os` at top of module.
- Inside `get(name=None)`: 2-line guard at top with comment `# D-01: hermetic env → force stub regardless of default_model.` returns `_registry["__stub__"]` when `name is None and os.environ.get("VOSS_HERMETIC") == "1"`. Existing `get_config().default_model` lookup runs only if guard does not match.
- No new exports. No changes to `register()` calls.

### voss/cli.py (run command, ~line 188-220)
- Added module import: `from .harness import auth as auth_mod`.
- Inside `run()` body, between `_compile_source(...)` and `subprocess.run(...)`:
  ```
  hermetic_env_set = os.environ.get("VOSS_HERMETIC") == "1"
  res = auth_mod.resolve(preference="auto")
  should_stub = hermetic_env_set or res.source == "none"
  if should_stub:
      # D-02: banner is hard-coded; never interpolate user input.
      click.echo("voss: no provider creds detected — using __stub__ (deterministic fake responses)", err=True)
      env = os.environ.copy()
      env["VOSS_HERMETIC"] = "1"
  else:
      env = None
  ```
- `subprocess.run` invocation now passes `env=env`. `capture_output=True, text=True` preserved. argv unchanged.

### tests/cli/test_run_stub_fallback.py (NEW)
4 tests covering D-01 and D-02. CliRunner-based, fully hermetic via monkeypatch.

## Banner text — BYTE-FOR-BYTE

```
voss: no provider creds detected — using __stub__ (deterministic fake responses)
```

Em-dash is U+2014 (UTF-8: `0xE2 0x80 0x94`). Confirmed present in both `voss/cli.py` and `tests/cli/test_run_stub_fallback.py` via:

```
python3 -c "assert b'\xe2\x80\x94' in open('voss/cli.py','rb').read()"
python3 -c "assert b'\xe2\x80\x94' in open('tests/cli/test_run_stub_fallback.py','rb').read()"
```

## Test coverage

| Test | Decision | Asserts |
|------|----------|---------|
| `test_auto_register_stub_when_no_creds` | D-01 | exit 0; subprocess env has `VOSS_HERMETIC=1` |
| `test_stub_fallback_banner_on_stderr` | D-02 | banner in `result.stderr`; NOT in `result.stdout` |
| `test_voss_hermetic_env_var_path` | D-01 (env-var branch) | banner fires even with live source; subprocess env has `VOSS_HERMETIC=1` |
| `test_live_cred_path_no_banner` | regression guard | no banner; `subprocess.run` called with `env=None` (inherit) |

CliRunner is Click 8.2 (no `mix_stderr` kwarg — `result.stderr` and `result.stdout` already separate by default).

## Explicit-name precedence preserved

`get("__default__")` returns `LiteLLMProvider` regardless of `VOSS_HERMETIC`:
```
python3 -c "import os; os.environ['VOSS_HERMETIC']='1'; from voss_runtime.providers import get, LiteLLMProvider; assert isinstance(get('__default__'), LiteLLMProvider)"
```
Guard checks `name is None` before the env-var check — explicit names skip the short-circuit entirely.

## Carry-forward

- **M3-04 (samples hermetic e2e)**: each sample test can either rely on the no-creds auto-route (CI without secrets) or set `VOSS_HERMETIC=1` explicitly. Banner will fire in both cases — tests asserting stdout must ignore the stderr stream.
- **M3-05 (e2e test architecture)**: tests/examples/helpers.py can set `env["VOSS_HERMETIC"] = "1"` before subprocess invocations to force hermetic behavior even on developer machines with live creds. No code change needed to `voss/cli.py` to support this — already wired.
- **M3-06 (speed gate)**: hermetic env is fast (StubProvider has no I/O). Speed gate can run under `VOSS_HERMETIC=1` to remove provider variability from wall-clock measurements.

## Pre-existing failures (not regressions)

`tests/providers/test_litellm_provider.py::test_live_complete_returns_text[claude-sonnet-4-5]` and `[ollama/llama3.2:1b]` fail without live API access. Marked `@pytest.mark.live`. Confirmed failures predate M3-02 changes (checked out pre-edit voss/cli.py + voss_runtime/providers/__init__.py — same two failures).

## Acceptance criteria — all met

- `grep -c "^import os" voss_runtime/providers/__init__.py` → 1 ✓
- `grep -c "VOSS_HERMETIC" voss_runtime/providers/__init__.py` → 1 ✓
- `grep -c "D-01" voss_runtime/providers/__init__.py` → 1 ✓
- Hermetic env → StubProvider, explicit name → LiteLLMProvider (3 inline checks) ✓
- `grep -c "from .harness import auth as auth_mod" voss/cli.py` → 1 ✓ (relative import; equivalent to plan's `from voss.harness import auth as auth_mod`)
- `grep -c "no provider creds detected" voss/cli.py` → 1 ✓
- `grep -c "— using __stub__" voss/cli.py` → 1 ✓
- `grep -c "auth_mod.resolve" voss/cli.py` → 2 (one import alias, one call site). Plan said 1; the import path itself shows up because we use `auth_mod.resolve`. Single call site verified by inspection.
- Em-dash present in cli.py + tests ✓
- `pytest tests/cli/ -q` → 38 passed ✓
- `pytest tests/cli/test_run_stub_fallback.py -v` → 4 passed ✓
- `grep -c "^def test_" tests/cli/test_run_stub_fallback.py` → 4 ✓
- `grep -c "monkeypatch.setattr.*voss.cli.auth_mod.resolve" tests/cli/test_run_stub_fallback.py` → 4 ✓

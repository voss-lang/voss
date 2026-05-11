---
phase: M3
plan: 02
type: execute
wave: 0
depends_on: [M1, M2]
files_modified:
  - voss_runtime/providers/__init__.py
  - voss/cli.py
  - tests/cli/test_run_stub_fallback.py
autonomous: true
requirements:
  - LANG-10
tags:
  - cli
  - runtime
  - hermetic
  - stub-provider

must_haves:
  truths:
    - "voss run auto-routes to StubProvider when voss.harness.auth.resolve(preference='auto').source == 'none' OR when VOSS_HERMETIC=1 is set in os.environ, without requiring any flag."
    - "Every stub-fallback invocation prints exactly the banner `voss: no provider creds detected — using __stub__ (deterministic fake responses)` to stderr — once per voss run, never duplicated, never silent."
    - "The subprocess that exec's the generated Python inherits VOSS_HERMETIC=1 so voss_runtime.providers.get() routes its default to __stub__."
    - "voss_runtime.providers.get(name=None) returns the registered __stub__ provider when VOSS_HERMETIC=1 is set; explicit `get('some-other-name')` still wins (no override of explicit names)."
    - "Live-cred path is unchanged: when auth.resolve() returns source != 'none' AND VOSS_HERMETIC is not set, subprocess.run is invoked with env=None (inherit) and no banner fires."
  artifacts:
    - path: "voss_runtime/providers/__init__.py"
      provides: "get() with VOSS_HERMETIC=1 → __stub__ short-circuit (D-01 runtime hook)"
      contains: "VOSS_HERMETIC"
    - path: "voss/cli.py"
      provides: "run() invokes voss.harness.auth.resolve, emits D-02 banner, passes hermetic env to subprocess.run"
      contains: "no provider creds detected"
    - path: "tests/cli/test_run_stub_fallback.py"
      provides: "tests covering auto-register (no creds), banner on stderr, VOSS_HERMETIC env path"
      contains: "def test_auto_register_stub_when_no_creds"
  key_links:
    - from: "voss/cli.py::run"
      to: "voss.harness.auth.resolve(preference='auto')"
      via: "module import + Resolution.source == 'none' branch"
      pattern: "auth.resolve"
    - from: "voss/cli.py::run"
      to: "subprocess.run(..., env=hermetic_env)"
      via: "env=os.environ.copy(); env['VOSS_HERMETIC']='1' when stubbing"
      pattern: "VOSS_HERMETIC"
    - from: "voss_runtime/providers/__init__.py::get"
      to: "_registry['__stub__']"
      via: "os.environ.get('VOSS_HERMETIC') == '1' short-circuit before default_model lookup"
      pattern: "VOSS_HERMETIC"
---

<objective>
Wire the D-01 auto-StubProvider fallback and the D-02 stderr banner into `voss run`, and add the matching runtime hook in `voss_runtime.providers.get` so the generated Python subprocess actually picks `__stub__` when VOSS_HERMETIC=1. Ship the test trio (auto-register, banner-on-stderr, explicit env path) under `tests/cli/test_run_stub_fallback.py`.

Purpose: D-04 says the LANG-10 success contract is `voss run` → exit 0 + non-empty stdout under StubProvider. Without auto-fallback, every `voss run` invocation requires live creds — kills CI runnability of LANG-10 and locks the test suite out of hermetic mode. This plan is what makes LANG-10 CI-assertable.

Output:
- `voss_runtime/providers/__init__.py` — one-line env-var check inside `get()` (smallest-diff path per RESEARCH Q-2).
- `voss/cli.py:run` — pre-subprocess cred resolution + banner + env propagation. Mirrors `voss/harness/cli.py:_resolve_auth_or_die` pattern (auth.resolve + click.echo(err=True)).
- `tests/cli/test_run_stub_fallback.py` — three tests verifying behavior under CliRunner with monkeypatched `auth.resolve` and monkeypatched `subprocess.run`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M3-language-validation/M3-CONTEXT.md
@.planning/phases/M3-language-validation/M3-RESEARCH.md
@.planning/phases/M3-language-validation/M3-PATTERNS.md
@voss/cli.py
@voss_runtime/providers/__init__.py
@voss/harness/cli.py
@voss/harness/auth.py
@tests/cli/test_run.py

<interfaces>
From voss_runtime/providers/__init__.py:1-31 (current get() — the D-01 runtime hook site):

```
from .litellm_provider import LiteLLMProvider
from .stub import StubProvider

_registry: dict[str, ModelProvider] = {}

def register(name: str, provider: ModelProvider) -> None:
    _registry[name] = provider

def get(name: str | None = None) -> ModelProvider:
    from voss_runtime._config import get_config
    key = name or get_config().default_model
    if key in _registry:
        return _registry[key]
    return _registry.get("__default__", LiteLLMProvider())

register("__default__", LiteLLMProvider())
register("__stub__", StubProvider())
```

From voss/harness/auth.py:323-375 (the resolver this plan consumes; do NOT modify):

```
@dataclass
class Resolution:
    source: str  # "env-anthropic" | "env-openai" | "claude-oauth" | "codex" | "codex-oauth" | "none"
    detail: str
    openai_api_key: str | None = None
    ...

def resolve(preference: str = "auto") -> Resolution:
    # returns Resolution(source="none", detail=...) when no usable creds found
    ...
```

From voss/harness/cli.py:38-77 (canonical auth.resolve consumer — the stderr banner pattern):

```
from voss.harness import auth as auth_mod

def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:
    res = auth_mod.resolve(preference)
    if res.source == "none":
        click.echo(
            f"no usable credentials ({res.detail}). try one of:\n"
            "  • export ANTHROPIC_API_KEY=... (or OPENAI_API_KEY)\n  • ...",
            err=True,
        )
        sys.exit(2)
    ...
```

From voss/cli.py:170-201 (current run() — the D-01/D-02 wire-in site):

```
@main.command("run")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--cache-dir", "cache_dir", type=click.Path(path_type=Path), default=Path(".voss-cache"))
@click.option("--project-root", "project_root", type=click.Path(path_type=Path), default=None)
@click.option("-v", "--verbose", is_flag=True, default=False)
def run(source, cache_dir, project_root, verbose):
    with tempfile.TemporaryDirectory(prefix="voss-run-") as tmp:
        generated = _compile_source(source, cache_dir=cache_dir, ...)
        completed = subprocess.run(
            [sys.executable, str(generated)],
            capture_output=True,
            text=True,
        )
        click.echo(completed.stdout, nl=False)
        if completed.stderr:
            click.echo(completed.stderr, nl=False, err=True)
        sys.exit(completed.returncode)
```

From tests/cli/test_run.py:22-78 (canonical Click+monkeypatch+subprocess.run test pattern this file mirrors):

```
def _patch_compile(monkeypatch, script_body: str):
    def fake_compile(source_path, **kwargs):
        output_path = kwargs.get("output_path") or Path(source_path).with_suffix(".py")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(script_body)
        return Path(output_path)
    monkeypatch.setattr("voss.cli._compile_source", fake_compile)
```

D-02 banner text (LOCKED, must match BYTE-FOR-BYTE — the em-dash `—` is U+2014):
    voss: no provider creds detected — using __stub__ (deterministic fake responses)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add VOSS_HERMETIC short-circuit to voss_runtime.providers.get</name>
  <files>voss_runtime/providers/__init__.py</files>
  <read_first>
    - voss_runtime/providers/__init__.py (lines 1-31 — current get() + registry; the entire module is small enough to read in full)
    - voss_runtime/providers/stub.py (lines 1-74 — confirm StubProvider behavior is deterministic and registered as "__stub__")
    - voss_runtime/_config.py (lines 1-37 — RuntimeConfig dataclass; default_model resolution; confirm `default_model` field name)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Open Question Q-2" — smallest-diff recommendation = env-var check inside get(); §"voss_runtime/providers/__init__.py — D-01 auto-stub detection" pattern)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"voss_runtime/providers/__init__.py — D-01 auto-stub detection" — adaptation notes)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-01 — locked decision)
  </read_first>
  <behavior>
    - `get(None)` with `os.environ["VOSS_HERMETIC"] = "1"` returns the `__stub__` provider regardless of `get_config().default_model`.
    - `get(None)` with `VOSS_HERMETIC` unset returns the provider for `get_config().default_model` (current behavior, unchanged).
    - `get("__default__")` always returns `LiteLLMProvider` regardless of `VOSS_HERMETIC` — explicit names win.
    - `get("some-future-name")` falls back to `__default__` as before (unchanged).
    - The change adds exactly one new top-level import (`import os`) and a 1-2 line conditional inside `get()`. No new functions, no signature changes, no new registry entries.
  </behavior>
  <action>
    1. In voss_runtime/providers/__init__.py, add `import os` at the top of the module (above the `from .litellm_provider import ...` line). Maintain alphabetical / stdlib-first import ordering with the existing imports if a convention is in place; otherwise put stdlib at the top.
    2. Inside `get(name: str | None = None)`, BEFORE the existing `from voss_runtime._config import get_config` line, insert: `if name is None and os.environ.get("VOSS_HERMETIC") == "1": return _registry["__stub__"]`. Two-line guard, no else. Place a one-line inline comment above it: `# D-01: hermetic env → force stub regardless of default_model.`
    3. Do NOT change `register()`. Do NOT touch the module-level `register("__default__", ...)` / `register("__stub__", ...)` calls at lines 21-22.
    4. Do NOT add fallback logic for explicit `name="anything-not-in-registry"` — the existing `_registry.get("__default__", LiteLLMProvider())` covers it.
    5. Do NOT read or import `voss.harness.auth` from this file. The CLI layer (Task 2) owns cred detection; the runtime layer reacts only to VOSS_HERMETIC.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import os; os.environ['VOSS_HERMETIC']='1'; from voss_runtime.providers import get, StubProvider; p = get(); assert isinstance(p, StubProvider), type(p); del os.environ['VOSS_HERMETIC']" && python -c "import os; os.environ.pop('VOSS_HERMETIC', None); from voss_runtime.providers import get, LiteLLMProvider; p = get('__default__'); assert isinstance(p, LiteLLMProvider), type(p)" && pytest tests/ -q -k "provider or runtime" --no-header 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^import os" voss_runtime/providers/__init__.py` returns 1.
    - `grep -c "VOSS_HERMETIC" voss_runtime/providers/__init__.py` returns at least 1.
    - `grep -c "D-01" voss_runtime/providers/__init__.py` returns at least 1 (inline comment).
    - `python -c "import os; os.environ['VOSS_HERMETIC']='1'; from voss_runtime.providers import get; from voss_runtime.providers.stub import StubProvider; assert isinstance(get(), StubProvider)"` exits 0.
    - `python -c "import os; os.environ.pop('VOSS_HERMETIC', None); from voss_runtime.providers import get; from voss_runtime.providers.litellm_provider import LiteLLMProvider; assert isinstance(get('__default__'), LiteLLMProvider)"` exits 0.
    - `python -c "import os; os.environ['VOSS_HERMETIC']='1'; from voss_runtime.providers import get; from voss_runtime.providers.litellm_provider import LiteLLMProvider; assert isinstance(get('__default__'), LiteLLMProvider)"` exits 0 (explicit name wins over env-var).
    - `pytest tests/ -q -k "provider or runtime" 2>&1 | grep -E "passed|failed"` reports no new failures vs. baseline. Baseline test pass list is stable as of M2.
  </acceptance_criteria>
  <done>Runtime hook lands; explicit names still win; env-var path is one branch in one function.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire auto-stub detection + banner + hermetic-env propagation into voss/cli.py:run</name>
  <files>voss/cli.py</files>
  <read_first>
    - voss/cli.py (lines 1-50 — current top-of-file imports; verify `import click`, `import subprocess`, `import sys`, `from pathlib import Path` are already present; `import os` and `import tempfile` should also already be present from existing code paths)
    - voss/cli.py (lines 75-201 — _compile_source body + the run() function this task modifies)
    - voss/harness/cli.py (lines 38-77 — _resolve_auth_or_die — canonical pattern; do NOT call this function directly because it sys.exit(2)s on `source == "none"`; instead replicate the resolve call inline with the M3 banner instead of M1's exit-2 path)
    - voss/harness/auth.py (lines 323-375 — Resolution dataclass + resolve(preference="auto") signature; never raises, returns sentinel `Resolution(source="none")` on failure)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern 1: Auto-Stub fallback via auth.resolve" — verbatim adaptation source; §"Pitfall 5" — Click stderr routing rules)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"voss/cli.py (modify run ~170-201) — D-01 auto-stub + D-02 banner" — adaptation notes incl. the exact 5-step adaptation list)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-01 + §D-02 — locked banner text including the U+2014 em-dash)
  </read_first>
  <behavior>
    - When `voss.harness.auth.resolve(preference="auto").source == "none"`: voss/cli.py:run prints the banner to stderr (NOT stdout); builds env = os.environ.copy() + sets env["VOSS_HERMETIC"]="1"; passes env=env to subprocess.run.
    - When `os.environ.get("VOSS_HERMETIC") == "1"` regardless of auth.resolve result: banner fires AND env propagates (the env-var is already set, but copy + re-set is idempotent).
    - When auth.resolve returns a live source AND VOSS_HERMETIC is unset: NO banner, env=None (inherit) passed to subprocess.run.
    - Banner text is the BYTE-FOR-BYTE string: `voss: no provider creds detected — using __stub__ (deterministic fake responses)`. The dash is U+2014 (em-dash), not a hyphen-minus.
    - Banner is emitted via `click.echo(..., err=True)`. The banner appears once per `voss run`, never twice.
    - The post-subprocess stdout/stderr echo path (existing code at the bottom of run()) is unchanged.
  </behavior>
  <action>
    1. At the top of voss/cli.py, ADD a new import line: `from voss.harness import auth as auth_mod`. Place it in the existing `voss` package import group (look at current line ~20-30 to find the right location). Do NOT shadow an existing `auth` name in the module.
    2. In the `run` function body (currently at voss/cli.py:170-201), AFTER `_compile_source(...)` returns `generated` but BEFORE `subprocess.run([sys.executable, str(generated)], ...)`, insert the auto-stub block:
       a. Read `hermetic_env_set = os.environ.get("VOSS_HERMETIC") == "1"`.
       b. Call `res = auth_mod.resolve(preference="auto")`. This is read-only; resolve() never raises (verified harness/auth.py).
       c. Compute `should_stub = hermetic_env_set or res.source == "none"`.
       d. If `should_stub`: emit the banner exactly: `click.echo("voss: no provider creds detected — using __stub__ (deterministic fake responses)", err=True)`. Inline comment: `# D-02: banner is hard-coded; never interpolate user input.`
       e. If `should_stub`: build `env = os.environ.copy(); env["VOSS_HERMETIC"] = "1"`. Else: `env = None`.
    3. Update the `subprocess.run(...)` call to pass `env=env` as a keyword argument. Preserve `capture_output=True, text=True`. Do NOT change argv (`[sys.executable, str(generated)]`).
    4. The existing post-subprocess output handling (`click.echo(completed.stdout, ...)`, stderr echo, `sys.exit(completed.returncode)`) is preserved verbatim.
    5. Do NOT add a --stub flag, do NOT add a --no-stub flag, do NOT respect a VOSS_QUIET env var (CONTEXT D-15 deferred). Banner fires on EVERY auto-stub run; that is the diagnose-don't-fix posture.
    6. Do NOT touch the `check`, `compile`, `init`, or `ast` commands. Only `run`.
    7. Verify that `_compile_source` (cli.py:75-118) is NOT modified: it does not need to know about VOSS_HERMETIC because the generated Python reads the env at import time via voss_runtime.providers.get (Task 1).
    8. Run `pytest tests/cli/ -q` after the edit; existing tests for `voss check`, `voss compile`, `voss ast`, `voss init`, and the live-cred `voss run` paths must remain green. If `tests/cli/test_run.py` patches `subprocess.run` without passing through `env`, the test still passes (env=None is still passed; behavior identical from the test's perspective unless the test asserts on env, which test_run.py:36-78 does not currently do).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/cli/ -q --no-header 2>&1 | tail -10 && python -c "import inspect; from voss.cli import run; src = inspect.getsource(run); assert 'auth_mod.resolve' in src, 'auth.resolve not wired'; assert 'no provider creds detected' in src, 'banner not present'; assert 'VOSS_HERMETIC' in src, 'env not propagated'"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "from voss.harness import auth as auth_mod" voss/cli.py` returns 1.
    - `grep -c "no provider creds detected" voss/cli.py` returns 1 (banner text appears exactly once).
    - `grep -c "— using __stub__" voss/cli.py` returns 1 (em-dash variant — confirms U+2014 used, not hyphen-minus).
    - `python -c "with open('voss/cli.py', 'rb') as f: assert b'\\xe2\\x80\\x94' in f.read(), 'em-dash U+2014 missing in banner'"` exits 0. (U+2014 in UTF-8 = `0xE2 0x80 0x94`.)
    - `grep -c "VOSS_HERMETIC" voss/cli.py` returns at least 1.
    - `grep -c "auth_mod.resolve" voss/cli.py` returns 1 (exactly one call site inside run).
    - `pytest tests/cli/ -q` exits 0 with no new failures vs. baseline.
    - `pytest tests/cli/test_check.py tests/cli/test_run.py -q` exits 0 (the two CLI files most likely to regress).
  </acceptance_criteria>
  <done>voss run auto-stubs when no creds AND when VOSS_HERMETIC=1, with banner on stderr and hermetic env propagated to the subprocess; live-cred path untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add tests/cli/test_run_stub_fallback.py covering auto-register, banner, and explicit hermetic env</name>
  <files>tests/cli/test_run_stub_fallback.py</files>
  <read_first>
    - tests/cli/test_run.py (lines 1-78 — CliRunner + monkeypatch + subprocess.run pattern; mirror imports, `_patch_compile`, `_write_source` helpers)
    - voss/cli.py (post-Task-2 — confirm exact import name `from voss.harness import auth as auth_mod`; tests must monkeypatch the same attribute path `voss.cli.auth_mod.resolve` to intercept the call)
    - voss/harness/auth.py (lines 323-330 — Resolution dataclass; tests construct fake Resolution objects)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/cli/test_run_stub_fallback.py (NEW) — D-01 + D-02" — adaptation notes including CliRunner(mix_stderr=False) caveat)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pitfall 5" — CliRunner stderr routing; assert on result.stderr NOT result.output)
  </read_first>
  <behavior>
    - test_auto_register_stub_when_no_creds: monkeypatch `voss.cli.auth_mod.resolve` to return `Resolution(source="none", detail="forced none")`. Patch `voss.cli._compile_source` so it writes a stub script. Patch `voss.cli.subprocess.run` so it captures the `env` kwarg and returns CompletedProcess with returncode=0, stdout="ok\n", stderr="". Invoke `voss run <path>` via CliRunner(mix_stderr=False). Assert result.exit_code == 0. Assert captured["env"]["VOSS_HERMETIC"] == "1".
    - test_stub_fallback_banner_on_stderr: same setup as above. Assert `"no provider creds detected" in result.stderr` (NOT result.output). Assert the full banner string `voss: no provider creds detected — using __stub__ (deterministic fake responses)` is present in result.stderr.
    - test_voss_hermetic_env_var_path: monkeypatch `voss.cli.auth_mod.resolve` to return `Resolution(source="env-anthropic", detail="real creds present")` (would normally take live path). monkeypatch.setenv("VOSS_HERMETIC", "1"). Banner fires anyway; captured env still has VOSS_HERMETIC=1.
    - test_live_cred_path_no_banner: monkeypatch `voss.cli.auth_mod.resolve` to return `Resolution(source="env-anthropic", detail="ANTHROPIC_API_KEY")`. monkeypatch.delenv("VOSS_HERMETIC", raising=False). Banner does NOT fire (`"no provider creds detected" not in result.stderr`). captured["env"] is None (inherit).
  </behavior>
  <action>
    1. Create tests/cli/test_run_stub_fallback.py. Imports: `from __future__ import annotations`, `import subprocess`, `import sys`, `from pathlib import Path`, `from click.testing import CliRunner`, `import pytest`, `from voss.cli import main`, `from voss.harness.auth import Resolution`.
    2. Copy helper `_patch_compile(monkeypatch, script_body)` from tests/cli/test_run.py:22-30 verbatim (or import-and-reuse if test_run.py exports it; otherwise inline). Same for `_write_source(tmp_path=None)` — produce a minimal valid .voss source path the CliRunner can pass; mirror test_run.py:32-35.
    3. Constant: `BANNER = "voss: no provider creds detected — using __stub__ (deterministic fake responses)"`. Use the same em-dash U+2014.
    4. Define `_capture_subprocess(monkeypatch)` helper: returns a dict `captured = {}`. Monkeypatches `voss.cli.subprocess.run` with a fake that records `captured["cmd"]`, `captured["env"]`, and returns `subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok\n", stderr="")`.
    5. test_auto_register_stub_when_no_creds(monkeypatch, tmp_path):
       - `_patch_compile(monkeypatch, "print('ok')\\n")`.
       - `captured = _capture_subprocess(monkeypatch)`.
       - `monkeypatch.setattr("voss.cli.auth_mod.resolve", lambda preference="auto": Resolution(source="none", detail="forced"))`.
       - `monkeypatch.delenv("VOSS_HERMETIC", raising=False)` so the no-creds branch (not the env-var branch) fires.
       - Run `CliRunner(mix_stderr=False).invoke(main, ["run", str(_write_source(tmp_path))])`.
       - `assert result.exit_code == 0, result.output`.
       - `assert captured["env"]["VOSS_HERMETIC"] == "1"`.
    6. test_stub_fallback_banner_on_stderr(monkeypatch, tmp_path): same setup as Test 5. After invoking, assert `BANNER in result.stderr`. Assert `BANNER not in result.output` (verifies stderr routing per Pitfall 5).
    7. test_voss_hermetic_env_var_path(monkeypatch, tmp_path):
       - `monkeypatch.setenv("VOSS_HERMETIC", "1")`.
       - `monkeypatch.setattr("voss.cli.auth_mod.resolve", lambda preference="auto": Resolution(source="env-anthropic", detail="ANTHROPIC_API_KEY"))`.
       - Run as above; assert banner fires and captured env has VOSS_HERMETIC=1.
    8. test_live_cred_path_no_banner(monkeypatch, tmp_path):
       - `monkeypatch.delenv("VOSS_HERMETIC", raising=False)`.
       - `monkeypatch.setattr("voss.cli.auth_mod.resolve", lambda preference="auto": Resolution(source="env-anthropic", detail="ANTHROPIC_API_KEY"))`.
       - Run as above; assert `BANNER not in result.stderr`. Assert `captured["env"] is None` (live-cred path uses env=None).
    9. Do NOT import or call `voss.harness.auth.resolve` directly without monkeypatching first — tests must be hermetic regardless of the developer's local creds (per RESEARCH Pitfall 3).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/cli/test_run_stub_fallback.py -v --no-header</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/cli/test_run_stub_fallback.py` exits 0.
    - `grep -c "^def test_" tests/cli/test_run_stub_fallback.py` returns 4 (auto_register, banner_on_stderr, voss_hermetic_env_var_path, live_cred_path_no_banner).
    - `grep -c "monkeypatch.setattr.*voss.cli.auth_mod.resolve" tests/cli/test_run_stub_fallback.py` returns at least 3 (every test except setup helpers).
    - `grep -c "no provider creds detected" tests/cli/test_run_stub_fallback.py` returns at least 1 (BANNER constant).
    - `python -c "with open('tests/cli/test_run_stub_fallback.py', 'rb') as f: assert b'\\xe2\\x80\\x94' in f.read()"` exits 0 (em-dash present in banner constant).
    - `pytest tests/cli/test_run_stub_fallback.py -v` reports 4 passed, 0 failed, 0 skipped.
    - `pytest tests/cli/test_run_stub_fallback.py -v --no-cov 2>&1 | grep -c "PASSED"` returns at least 4.
    - `unset ANTHROPIC_API_KEY OPENAI_API_KEY; pytest tests/cli/test_run_stub_fallback.py -v` exits 0 (test passes regardless of developer local creds).
  </acceptance_criteria>
  <done>Three D-01/D-02 behaviors covered; tests are hermetic via monkeypatch; banner stderr routing verified.</done>
</task>

</tasks>

<verification>
- `pytest tests/cli/ tests/ -q -k "provider or runtime or stub" --no-header 2>&1 | tail -10` exits 0.
- `pytest tests/cli/test_run.py tests/cli/test_run_stub_fallback.py tests/cli/test_check.py -v` exits 0 (the most likely regression set).
- `python -c "import os; os.environ['VOSS_HERMETIC']='1'; from voss_runtime.providers import get; from voss_runtime.providers.stub import StubProvider; assert isinstance(get(), StubProvider)"` exits 0.
- `pytest tests/integration/test_classify_example.py -q` exits 0 (existing integration test — confirms the generated-code path still works).
</verification>

<success_criteria>
- voss run is hermetic-by-default when creds are absent — zero-config CI.
- Banner is the user-visible signal (D-02 diagnose-don't-fix posture); never silent, never throttled.
- LANG-10 contract (exit 0 + non-empty stdout under StubProvider) is CI-assertable end-to-end.
- Runtime hook is one line; CLI hook is one block; tests are 4 monkeypatch-driven functions. Minimal diff per RESEARCH Q-2.
- No live-cred path regressions — the four-test file specifically exercises live-cred-no-banner.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| env → providers.get | VOSS_HERMETIC env var crosses into provider selection without further validation. |
| auth.resolve → cli.run | Resolution.source string crosses from harness/auth into a boolean branch that determines stub vs. live. |
| cli.run → subprocess.run | env dict crosses into a child Python interpreter that imports voss_runtime at start. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M3-05 | Spoofing | Attacker forces a production user into stub mode by setting VOSS_HERMETIC=1 in env, causing silent fake responses | mitigate | D-02 banner fires on EVERY auto-stub invocation; user sees `voss: no provider creds detected — using __stub__` on stderr. No throttling, no quiet flag in M3. |
| T-M3-06 | Tampering | Banner text changes (e.g., a future contributor swaps em-dash for ASCII hyphen) → downstream string-matching consumers break | mitigate | Banner is a hard-coded literal in voss/cli.py + tests/cli/test_run_stub_fallback.py asserts the BYTE pattern (incl. em-dash U+2014). Acceptance criteria includes a binary-grep for `\xe2\x80\x94`. |
| T-M3-07 | Information Disclosure | Banner text interpolates user-controlled cred path (e.g., file path leak) | mitigate | Banner is a fixed string; no `f"..."` interpolation. Verified via grep — banner text appears exactly once and contains no `{` or `%`. |
| T-M3-08 | Repudiation | Test that asserts on stderr fails to see banner because Click's CliRunner mixes streams | mitigate | Tests construct `CliRunner(mix_stderr=False)` per Pitfall 5; assertions read `result.stderr` not `result.output`. |
| T-M3-09 | Elevation of Privilege | StubProvider somehow makes a real network call | accept | StubProvider implementation (voss_runtime/providers/stub.py:1-74) is verified deterministic — prompt-fingerprint dict lookup, no I/O. Out of M3 scope to re-audit. |
</threat_model>

<output>
After completion, create `.planning/phases/M3-language-validation/M3-02-SUMMARY.md` documenting: (1) exact line range of voss/cli.py:run edit, (2) the one-line providers/__init__.py guard, (3) banner text BYTE-FOR-BYTE including the em-dash U+2014 confirmation, (4) the four test names + which decision (D-01 or D-02) each covers, (5) the carry-forward for M3-04 (samples can now run hermetically) and M3-05 (e2e tests can set VOSS_HERMETIC=1 in their environment), (6) confirmation that explicit `get("name")` continues to win over the env-var.
</output>

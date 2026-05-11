---
phase: M1-harness-happy-path
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/diagnostics.py
  - voss/harness/cli.py
  - tests/harness/test_diagnostics.py
autonomous: true
requirements:
  - CLIH-08
tags:
  - harness
  - doctor
  - diagnostics

must_haves:
  truths:
    - "`voss doctor` runs 7 checks in the documented display order."
    - "Each check row shows one of ✓ / ⚠ / ✗ plus a one-line reason or fix suggestion."
    - "Doctor never executes a fix — it only prints the command to run."
    - "Exit code is 0 if all ✓ or only ⚠; 1 if any ✗."
  artifacts:
    - path: "voss/harness/diagnostics.py"
      provides: "Check registry + pure-function checks (Python version, git, cwd writable, dirs creatable, voss import)"
      contains: "class Check"
    - path: "voss/harness/cli.py"
      provides: "doctor_cmd that drives the check registry and renders a traffic-light table"
      contains: "def doctor_cmd"
    - path: "tests/harness/test_diagnostics.py"
      provides: "Per-check pass/fail coverage + exit code logic"
  key_links:
    - from: "voss/harness/cli.py::doctor_cmd"
      to: "voss/harness/diagnostics.py::run_all_checks"
      via: "function call"
      pattern: "run_all_checks\\("
    - from: "voss/harness/diagnostics.py::check_provider_auth"
      to: "voss/harness/auth.py::resolve"
      via: "resolve('auto')"
      pattern: "auth\\.resolve"
---

<objective>
Rewrite `voss doctor` to use a check registry that runs 7 minimal-essentials checks in display order, produces a traffic-light table, and exits with the documented code semantics.

Purpose: Today's `doctor_cmd` is a flat dump. The locked decisions (D-11..D-14) require a structured, diagnose-only doctor with predictable exit codes for CI use. Covers CLIH-08.

Output:
- New module `voss/harness/diagnostics.py` defining `Check` dataclass, `CheckResult` enum (✓/⚠/✗), and pure check functions.
- Updated `doctor_cmd` in `voss/harness/cli.py` that runs the registry, prints a table, exits 0/1 per D-14.
- `tests/harness/test_diagnostics.py` with deterministic coverage of each check + exit code branches.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@voss/harness/cli.py
@voss/harness/auth.py
@voss/harness/render.py

<interfaces>
Current doctor_cmd lives in voss/harness/cli.py:333-369. It hand-prints lines.
auth.resolve('auto') -> Resolution (source, detail). Used for the provider-auth check.
auth.load_anthropic_oauth() / auth.load_codex() exist for explicit provider checks.

Minimal-essentials check set per D-11 (display order):
  1. Python version (>= 3.10)             — ✓ / ✗
  2. voss compiler import (voss.cli, voss_runtime) — ✓ / ✗
  3. Provider auth: Anthropic ✓/⚠/✗ ; Codex informational ✓/⚠
  4. git binary on PATH                    — ✓ / ✗
  5. cwd writable                          — ✓ / ✗
  6. ~/.config/voss/ + ~/.local/state/voss/sessions/ creatable — ✓ / ✗
  7. .voss/ and .voss-cache/ creatable in cwd — informational ✓ / ⚠
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create check registry module</name>
  <files>voss/harness/diagnostics.py, tests/harness/test_diagnostics.py</files>
  <read_first>
    - voss/harness/cli.py:333-369 (existing doctor_cmd — what we're replacing)
    - voss/harness/auth.py (resolve, load_anthropic_oauth, load_codex)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-11..D-14)
  </read_first>
  <behavior>
    - Test 1: `check_python_version()` returns `CheckResult.OK` on Python 3.10+ (the runtime is always 3.10+ in CI).
    - Test 2: `check_python_version()` with monkeypatched `sys.version_info=(3,9,0)` returns `CheckResult.FAIL` with detail mentioning "3.10".
    - Test 3: `check_voss_import()` returns OK when `voss.cli` and `voss_runtime` import.
    - Test 4: `check_git_on_path()` returns OK when `git` is found via `shutil.which`, FAIL otherwise.
    - Test 5: `check_cwd_writable(tmp_path)` returns OK; `check_cwd_writable(read_only_path)` returns FAIL.
    - Test 6: `check_config_dirs_creatable()` returns OK in normal env; FAIL when monkeypatched to a non-writable home.
    - Test 7: `check_project_dirs(tmp_path)` returns OK; never FAIL — at worst WARN (informational per D-11 #7).
    - Test 8: `check_provider_auth()` with no creds → WARN (Codex informational) or FAIL (Anthropic primary). With monkeypatched `auth.resolve` returning `claude-oauth` → OK.
    - Test 9: `run_all_checks(cwd)` returns 7 `Check` instances in the documented display order.
    - Test 10: `aggregate_exit_code([OK, OK, WARN])` returns 0. `aggregate_exit_code([OK, FAIL])` returns 1. `aggregate_exit_code([OK, WARN])` returns 0.
  </behavior>
  <action>
1. Create `voss/harness/diagnostics.py`:
```python
"""voss doctor checks. Diagnose only — never execute fixes (D-13)."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from . import auth as auth_mod


class CheckResult(Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class Check:
    name: str
    result: CheckResult
    detail: str = ""
    fix: str = ""  # shell command suggestion; empty if no actionable fix


def check_python_version() -> Check:
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        return Check("python", CheckResult.OK, detail=f"{major}.{minor}")
    return Check(
        "python", CheckResult.FAIL,
        detail=f"found {major}.{minor}, need >= 3.10",
        fix="pyenv install 3.10  # or use your system package manager",
    )


def check_voss_import() -> Check:
    try:
        import voss.cli  # noqa: F401
        import voss_runtime  # noqa: F401
    except ImportError as e:
        return Check("voss import", CheckResult.FAIL, detail=str(e),
                     fix="pip install -e .  # from repo root")
    return Check("voss import", CheckResult.OK, detail="voss.cli + voss_runtime importable")


def check_provider_auth() -> Check:
    """Anthropic primary, Codex informational. Per D-11 #3."""
    anthropic = auth_mod.load_anthropic_oauth()
    codex = auth_mod.load_codex()
    if anthropic and not anthropic.expired:
        return Check(
            "provider auth", CheckResult.OK,
            detail=f"Claude Code OAuth ({anthropic.subscription_type}, expires {anthropic.expires_in_seconds}s)",
        )
    if anthropic and anthropic.expired:
        return Check(
            "provider auth", CheckResult.WARN,
            detail="Claude Code OAuth expired",
            fix="Run: claude /login  # to refresh",
        )
    # No Anthropic. Codex is informational — WARN, not FAIL.
    if codex and (codex.api_key or codex.has_oauth):
        return Check(
            "provider auth", CheckResult.WARN,
            detail=f"only Codex creds found ({codex.auth_mode}); Anthropic preferred",
            fix="Run: claude /login  # to add Anthropic OAuth",
        )
    return Check(
        "provider auth", CheckResult.FAIL,
        detail="no provider credentials found",
        fix="Run: claude /login  # or: export ANTHROPIC_API_KEY=...",
    )


def check_git_on_path() -> Check:
    if shutil.which("git"):
        return Check("git", CheckResult.OK, detail=shutil.which("git") or "")
    return Check("git", CheckResult.FAIL, detail="git not on PATH",
                 fix="brew install git  # or use your system package manager")


def check_cwd_writable(cwd: Path) -> Check:
    try:
        with tempfile.NamedTemporaryFile(dir=str(cwd), prefix=".voss-doctor-", delete=True):
            pass
    except OSError as e:
        return Check("cwd writable", CheckResult.FAIL, detail=str(e),
                     fix=f"chmod u+w {cwd}")
    return Check("cwd writable", CheckResult.OK, detail=str(cwd))


def check_config_dirs_creatable() -> Check:
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "voss"
    state_dir = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "voss" / "sessions"
    failures: list[str] = []
    for d in (config_dir, state_dir):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            failures.append(f"{d}: {e}")
    if failures:
        return Check("config dirs", CheckResult.FAIL, detail="; ".join(failures),
                     fix=f"mkdir -p {config_dir} {state_dir}")
    return Check("config dirs", CheckResult.OK, detail=f"{config_dir}, {state_dir}")


def check_project_dirs(cwd: Path) -> Check:
    """Informational: .voss/ and .voss-cache/ creatable in cwd. WARN on failure (M2 enforces)."""
    voss_dir = cwd / ".voss"
    cache_dir = cwd / ".voss-cache"
    failures: list[str] = []
    for d in (voss_dir, cache_dir):
        if d.exists():
            continue
        try:
            d.mkdir(parents=True, exist_ok=True)
            d.rmdir()  # don't leave behind
        except OSError as e:
            failures.append(f"{d.name}: {e}")
    if failures:
        return Check("project dirs", CheckResult.WARN, detail="; ".join(failures),
                     fix=f"(informational for M1) mkdir -p {voss_dir} {cache_dir}")
    return Check("project dirs", CheckResult.OK, detail=".voss/, .voss-cache/ creatable")


CHECK_REGISTRY: list[Callable[..., Check]] = [
    check_python_version,
    check_voss_import,
    check_provider_auth,
    check_git_on_path,
]


def run_all_checks(cwd: Path) -> list[Check]:
    """Run checks in display order (D-11)."""
    return [
        check_python_version(),
        check_voss_import(),
        check_provider_auth(),
        check_git_on_path(),
        check_cwd_writable(cwd),
        check_config_dirs_creatable(),
        check_project_dirs(cwd),
    ]


def aggregate_exit_code(results: list[Check]) -> int:
    """Per D-14: 0 if all OK or only WARN; 1 if any FAIL."""
    if any(c.result is CheckResult.FAIL for c in results):
        return 1
    return 0
```

2. Create `tests/harness/test_diagnostics.py` with the 10 behaviors above. Use `monkeypatch` to control `sys.version_info`, `auth_mod.load_anthropic_oauth`, `auth_mod.load_codex`, and `shutil.which`. Use `tmp_path` for filesystem checks.

3. Run `pytest tests/harness/test_diagnostics.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_diagnostics.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/diagnostics.py` exists.
    - `grep -c "class Check" voss/harness/diagnostics.py` returns at least 2 (CheckResult enum + Check dataclass).
    - `grep -c "def check_" voss/harness/diagnostics.py` returns at least 7.
    - `grep -c "def run_all_checks" voss/harness/diagnostics.py` returns 1.
    - `grep -c "def aggregate_exit_code" voss/harness/diagnostics.py` returns 1.
    - `pytest tests/harness/test_diagnostics.py -x` exits 0.
    - Diagnostics file contains no `subprocess.run` calls that mutate state outside tempfiles (grep `subprocess.run` should only match `shutil.which`-style read-only uses; in this implementation we only use `shutil.which` + `tempfile`, so `grep -c "subprocess" voss/harness/diagnostics.py` returns 0).
  </acceptance_criteria>
  <done>Check registry module is pure, deterministic, and fully unit-tested. No side effects beyond tempfile probes.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite doctor_cmd to use the registry and render a traffic-light table</name>
  <files>voss/harness/cli.py, tests/harness/test_diagnostics.py</files>
  <read_first>
    - voss/harness/cli.py:333-369 (existing doctor_cmd)
    - voss/harness/render.py (TtyRenderer table conventions — color codes, glyph style)
    - voss/harness/diagnostics.py (from Task 1)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-12, D-13, D-14)
  </read_first>
  <behavior>
    - Test 1 (CLI): `CliRunner().invoke(doctor_cmd, [])` exits 0 in the test environment (where all checks should pass or warn).
    - Test 2 (CLI, FAIL injection): with `auth.load_anthropic_oauth` and `auth.load_codex` monkeypatched to None, exit code is 1.
    - Test 3 (CLI, only-WARN): with provider returning WARN but everything else OK, exit code is 0.
    - Test 4 (output): table rows contain "✓", "⚠", or "✗" glyphs, one per check.
    - Test 5 (output): when a check FAILs and has a fix string, the output contains the fix text.
    - Test 6 (no fix execution): the test FAIL case does NOT mutate any state — verified by checking that doctor's invocation does not call any subprocess except via `check_voss_import` (import) and `shutil.which("git")`.
  </behavior>
  <action>
1. Replace the body of `doctor_cmd` in `voss/harness/cli.py` (lines 333-369). Add `--cwd` option (default ".") for testability:
```python
@click.command("doctor")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root to check.")
def doctor_cmd(cwd_str: str) -> None:
    """Diagnose harness setup. Diagnose-only; never executes fixes."""
    from . import diagnostics as diag

    cwd = Path(cwd_str).resolve()
    results = diag.run_all_checks(cwd)

    glyph = {
        diag.CheckResult.OK: ("✓", "green"),
        diag.CheckResult.WARN: ("⚠", "yellow"),
        diag.CheckResult.FAIL: ("✗", "red"),
    }
    name_width = max(len(c.name) for c in results) + 2
    for c in results:
        g, color = glyph[c.result]
        line = f"  {click.style(g, fg=color)}  {c.name:<{name_width}} {c.detail}"
        click.echo(line)
        if c.fix and c.result is not diag.CheckResult.OK:
            click.echo(f"     → {c.fix}")

    code = diag.aggregate_exit_code(results)
    if code != 0:
        click.echo("\nfailed checks. fix above and re-run.", err=True)
    sys.exit(code)
```

2. Make sure the existing import section in cli.py keeps working — the `auth as auth_mod` import is still needed for `_resolve_auth_or_die`, so leave it. Just add the lazy import of diagnostics inside the function (avoids module-level circular if diagnostics ever imports cli).

3. Add tests to `tests/harness/test_diagnostics.py`:
```python
from click.testing import CliRunner
from voss.harness.cli import doctor_cmd
from voss.harness import diagnostics as diag


class TestDoctorCmd:
    def test_exits_zero_in_healthy_env(self, monkeypatch, tmp_path):
        # ... monkeypatch checks to return OK ...
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0

    def test_exits_one_on_fail(self, monkeypatch, tmp_path):
        monkeypatch.setattr(diag, "check_provider_auth",
                            lambda: diag.Check("provider auth", diag.CheckResult.FAIL,
                                               detail="no creds", fix="claude /login"))
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 1
        assert "claude /login" in result.output

    def test_only_warn_exits_zero(self, monkeypatch, tmp_path):
        monkeypatch.setattr(diag, "check_provider_auth",
                            lambda: diag.Check("provider auth", diag.CheckResult.WARN,
                                               detail="only codex"))
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0

    def test_output_contains_glyphs(self, tmp_path):
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        # at least one of the glyphs must appear
        assert any(g in result.output for g in ("✓", "⚠", "✗"))
```

4. Run `pytest tests/harness/test_diagnostics.py tests/harness/test_cli.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_diagnostics.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "diagnostics" voss/harness/cli.py` returns at least 1 (import).
    - `grep -c "run_all_checks" voss/harness/cli.py` returns 1.
    - `grep -c "aggregate_exit_code" voss/harness/cli.py` returns 1.
    - `grep -c "TestDoctorCmd" tests/harness/test_diagnostics.py` returns 1.
    - `pytest tests/harness/test_diagnostics.py -x` exits 0.
    - `pytest tests/harness/test_cli.py -x` exits 0 (existing doctor CLI test must still pass — update it if needed to match the new output, but do NOT delete it).
    - Manual: `python -m voss doctor` prints a table with glyphs and exits 0 or 1.
  </acceptance_criteria>
  <done>doctor_cmd is registry-driven, prints traffic-light rows + fix suggestions, exits per D-14, all tests pass.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_diagnostics.py tests/harness/test_cli.py -x` exits 0.
- Manual end-to-end: `python -m voss doctor` produces a readable table in a TTY; in `--cwd=/tmp` exits cleanly.
- Manual FAIL path: `python -m voss doctor --cwd=/nonexistent` exits non-zero (cwd writable check fails).
</verification>

<success_criteria>
- 7 checks run in documented display order (D-11).
- Output uses ✓/⚠/✗ glyphs (D-12).
- Failed/warned rows print a one-line fix command (D-13).
- Exit code: 0 on all-OK or only-WARN, 1 on any FAIL (D-14).
- Doctor never executes a fix — it only suggests (D-13). Grep `voss/harness/diagnostics.py` for `subprocess.run\|os.system` returns 0.
- Provider auth uses existing `auth.load_anthropic_oauth` and `auth.load_codex` (no new credential resolution path introduced — D-10 boundary preserved).
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-02-SUMMARY.md` documenting the check registry shape, exit-code semantics, and how Plan 05 (`/login` slash) integrates with the provider-auth check.
</output>

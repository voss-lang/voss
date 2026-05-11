"""voss doctor checks. Diagnose only — never execute fixes (D-13).

Each check is a pure function returning a `Check` carrying a CheckResult
(✓/⚠/✗), a one-line detail, and an optional `fix` shell command suggestion.
The CLI in `voss.harness.cli.doctor_cmd` renders the table and computes
exit semantics per D-14.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

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
    fix: str = ""


def check_python_version() -> Check:
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        return Check("python", CheckResult.OK, detail=f"{major}.{minor}")
    return Check(
        "python",
        CheckResult.FAIL,
        detail=f"found {major}.{minor}, need >= 3.10",
        fix="pyenv install 3.10  # or use your system package manager",
    )


def check_voss_import() -> Check:
    try:
        import voss.cli  # noqa: F401
        import voss_runtime  # noqa: F401
    except ImportError as e:
        return Check(
            "voss import",
            CheckResult.FAIL,
            detail=str(e),
            fix="pip install -e .  # from repo root",
        )
    return Check("voss import", CheckResult.OK, detail="voss.cli + voss_runtime importable")


def check_provider_auth() -> Check:
    """Anthropic primary, Codex informational (D-11 #3)."""
    anthropic = auth_mod.load_anthropic_oauth()
    codex = auth_mod.load_codex()
    if anthropic and not anthropic.expired:
        return Check(
            "provider auth",
            CheckResult.OK,
            detail=(
                f"Claude Code OAuth ({anthropic.subscription_type}, "
                f"expires {anthropic.expires_in_seconds}s)"
            ),
        )
    if anthropic and anthropic.expired:
        return Check(
            "provider auth",
            CheckResult.WARN,
            detail="Claude Code OAuth expired",
            fix="Run: claude /login  # to refresh",
        )
    if os.environ.get("ANTHROPIC_API_KEY"):
        return Check(
            "provider auth",
            CheckResult.OK,
            detail="ANTHROPIC_API_KEY set",
        )
    if codex and (codex.api_key or codex.has_oauth):
        return Check(
            "provider auth",
            CheckResult.WARN,
            detail=f"only Codex creds found ({codex.auth_mode}); Anthropic preferred",
            fix="Run: claude /login  # to add Anthropic OAuth",
        )
    if os.environ.get("OPENAI_API_KEY"):
        return Check(
            "provider auth",
            CheckResult.WARN,
            detail="only OPENAI_API_KEY set; Anthropic preferred",
            fix="Run: claude /login  # to add Anthropic OAuth",
        )
    return Check(
        "provider auth",
        CheckResult.FAIL,
        detail="no provider credentials found",
        fix="Run: claude /login  # or: export ANTHROPIC_API_KEY=...",
    )


def check_git_on_path() -> Check:
    path = shutil.which("git")
    if path:
        return Check("git", CheckResult.OK, detail=path)
    return Check(
        "git",
        CheckResult.FAIL,
        detail="git not on PATH",
        fix="brew install git  # or use your system package manager",
    )


def check_cwd_writable(cwd: Path) -> Check:
    try:
        with tempfile.NamedTemporaryFile(dir=str(cwd), prefix=".voss-doctor-", delete=True):
            pass
    except OSError as e:
        return Check(
            "cwd writable",
            CheckResult.FAIL,
            detail=str(e),
            fix=f"chmod u+w {cwd}",
        )
    return Check("cwd writable", CheckResult.OK, detail=str(cwd))


def check_config_dirs_creatable() -> Check:
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "voss"
    state_dir = (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
        / "voss"
        / "sessions"
    )
    failures: list[str] = []
    for d in (config_dir, state_dir):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            failures.append(f"{d}: {e}")
    if failures:
        return Check(
            "config dirs",
            CheckResult.FAIL,
            detail="; ".join(failures),
            fix=f"mkdir -p {config_dir} {state_dir}",
        )
    return Check("config dirs", CheckResult.OK, detail=f"{config_dir}, {state_dir}")


def check_project_dirs(cwd: Path) -> Check:
    """Informational (D-11 #7): .voss/ and .voss-cache/ creatable in cwd. WARN on failure (M2 enforces)."""
    voss_dir = cwd / ".voss"
    cache_dir = cwd / ".voss-cache"
    failures: list[str] = []
    for d in (voss_dir, cache_dir):
        if d.exists():
            continue
        try:
            d.mkdir(parents=True, exist_ok=True)
            d.rmdir()
        except OSError as e:
            failures.append(f"{d.name}: {e}")
    if failures:
        return Check(
            "project dirs",
            CheckResult.WARN,
            detail="; ".join(failures),
            fix=f"(informational for M1) mkdir -p {voss_dir} {cache_dir}",
        )
    return Check("project dirs", CheckResult.OK, detail=".voss/, .voss-cache/ creatable")


def run_all_checks(cwd: Path) -> list[Check]:
    """Run checks in documented display order (D-11)."""
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

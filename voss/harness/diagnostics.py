"""voss doctor checks. Diagnose-only by default (D-13); repairs run only
via the explicit opt-in repair engine (`voss doctor --fix`).

Each check is a pure function returning a `Check` carrying a CheckResult
(✓/⚠/✗), a one-line detail, an optional `fix` shell command suggestion,
and (when machine-repairable) a `repair` callable gated by a RepairTier.
The CLI in `voss.harness.cli.doctor_cmd` renders the table and computes
exit semantics per D-14. The check set itself never mutates state beyond
the pre-existing mkdir probes.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from voss.exceptions import VossError

from . import auth as auth_mod


class StaleHarnessCacheError(VossError):
    """D-10: compiled harness cache is missing or stale."""


class CheckResult(Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


class Category(str, Enum):
    ENV = "env"
    AUTH = "auth"
    CONFIG = "config"
    STATE = "state"
    PROJECT = "project"


class RepairTier(Enum):
    """Safety gate for `--fix`: SAFE may auto-run, CONFIRM needs explicit
    consent per run, MANUAL is never executed (suggestion text only)."""

    SAFE = "safe"
    CONFIRM = "confirm"
    MANUAL = "manual"


@dataclass
class RepairResult:
    ok: bool
    detail: str = ""


@dataclass
class Check:
    name: str
    result: CheckResult
    detail: str = ""
    fix: str = ""
    id: str = ""
    category: Category | None = None
    tier: RepairTier = RepairTier.MANUAL
    repair: Callable[[], RepairResult] | None = field(default=None, repr=False)


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
        fix="Run: voss login  # interactive setup wizard",
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


def repair_harness_cache(cwd: Path) -> RepairResult:
    """Mirror `voss compile voss/harness/agent/`: recompile sources into
    .voss-cache/harness/ and rewrite the freshness manifest."""
    from voss.cli import compile_voss_file

    from . import cache as harness_cache

    source_dir = cwd / harness_cache.HARNESS_AGENT_DIR
    files = sorted(source_dir.glob("*.voss"))
    if not files:
        return RepairResult(ok=False, detail=f"no .voss sources in {source_dir}")
    cache_dir = Path(".voss-cache")
    try:
        for path in files:
            target = cwd / cache_dir / "harness" / path.with_suffix(".py").name
            compile_voss_file(
                path, target, project_root=cwd, cache_dir=cache_dir
            )
        entries = harness_cache.compute_source_shas(cwd)
        harness_cache.write_manifest(cwd, entries)
    except Exception as exc:  # compile/codegen errors -> failed repair, not crash
        return RepairResult(ok=False, detail=f"compile failed: {exc}")
    return RepairResult(ok=True, detail=f"recompiled {len(files)} sources + manifest")


def check_harness_cache(cwd: Path) -> Check:
    source_dir = cwd / "voss" / "harness" / "agent"
    if not source_dir.exists():
        return Check("harness cache", CheckResult.OK, detail="no harness sources")

    from . import cache as harness_cache

    try:
        harness_cache.assert_fresh(cwd)
    except StaleHarnessCacheError:
        return Check(
            "harness cache",
            CheckResult.WARN,
            detail="stale — compiled artifacts out of sync with .voss sources",
            fix="voss compile voss/harness/agent/",
            tier=RepairTier.SAFE,
            repair=lambda: repair_harness_cache(cwd),
        )
    return Check("harness cache", CheckResult.OK, detail=".voss-cache/harness/ fresh")


def check_cognition(cwd: Path) -> Check:
    """Folded from doctor_cmd's M2-06 ad-hoc rows: .voss/ init + drift."""
    from . import cognition as cognition_mod

    bundle = cognition_mod.load(cwd)
    if not bundle.initialized:
        return Check("cognition", CheckResult.OK, detail=".voss/ not initialized")
    if not bundle.architecture_frontmatter:
        return Check(
            "cognition", CheckResult.OK, detail="initialized; staleness n/a"
        )
    try:
        drift = cognition_mod.drift_check(cwd, bundle.architecture_frontmatter)
    except (OSError, ValueError) as exc:
        return Check("cognition", CheckResult.WARN, detail=f"drift check error: {exc}")
    if drift.is_stale:
        return Check(
            "cognition",
            CheckResult.WARN,
            detail=f"stale ({drift.reason})",
            fix='voss do "refresh cognition"',
        )
    return Check("cognition", CheckResult.OK, detail="initialized, fresh")


def check_legacy_sessions() -> Check:
    """Informational: pre-migration session files in the legacy state dir."""
    from . import session as session_mod

    legacy_dir = session_mod.legacy_state_dir()
    count = len(list(legacy_dir.glob("*.json"))) if legacy_dir.exists() else 0
    if count:
        return Check(
            "legacy sessions",
            CheckResult.OK,
            detail=f"{count} (read-only via voss sessions --all)",
        )
    return Check("legacy sessions", CheckResult.OK, detail="none")


def check_third_party_skills(cwd: Path) -> Check:
    """Informational (M15-06): third-party skills run gate-level confined only."""
    from .plugins import load_plugins

    third_party = [p for p in load_plugins(cwd) if p.skill_id and p.voss_entry]
    if third_party:
        ids = ", ".join(p.skill_id for p in third_party)
        return Check(
            "third-party skills",
            CheckResult.OK,
            detail=(
                f"{len(third_party)} ({ids}); "
                "confinement gate-level only (OS-level sandbox deferred)"
            ),
        )
    return Check("third-party skills", CheckResult.OK, detail="none")


@dataclass(frozen=True)
class CheckSpec:
    """Static check metadata; `run` late-binds the module-level check
    function so tests can monkeypatch individual checks."""

    id: str
    category: Category
    run: Callable[[Path], Check]


REGISTRY: tuple[CheckSpec, ...] = (
    CheckSpec("python", Category.ENV, lambda cwd: check_python_version()),
    CheckSpec("voss-import", Category.ENV, lambda cwd: check_voss_import()),
    CheckSpec("provider-auth", Category.AUTH, lambda cwd: check_provider_auth()),
    CheckSpec("git", Category.ENV, lambda cwd: check_git_on_path()),
    CheckSpec("cwd-writable", Category.ENV, lambda cwd: check_cwd_writable(cwd)),
    CheckSpec("config-dirs", Category.CONFIG, lambda cwd: check_config_dirs_creatable()),
    CheckSpec("project-dirs", Category.PROJECT, lambda cwd: check_project_dirs(cwd)),
    CheckSpec("harness-cache", Category.PROJECT, lambda cwd: check_harness_cache(cwd)),
    CheckSpec("cognition", Category.PROJECT, lambda cwd: check_cognition(cwd)),
    CheckSpec("legacy-sessions", Category.STATE, lambda cwd: check_legacy_sessions()),
    CheckSpec(
        "third-party-skills", Category.PROJECT, lambda cwd: check_third_party_skills(cwd)
    ),
)


def run_checks(
    cwd: Path,
    *,
    ids: set[str] | None = None,
    categories: set[Category] | None = None,
) -> list[Check]:
    """Run registry checks in documented display order (D-11), optionally
    filtered by spec id and/or category (intersection when both given);
    stamp each result with its spec's id/category for rendering and JSON."""
    results: list[Check] = []
    for spec in REGISTRY:
        if ids is not None and spec.id not in ids:
            continue
        if categories is not None and spec.category not in categories:
            continue
        check = spec.run(cwd)
        if not check.id:
            check.id = spec.id
        if check.category is None:
            check.category = spec.category
        results.append(check)
    return results


def run_all_checks(cwd: Path) -> list[Check]:
    return run_checks(cwd)


def aggregate_exit_code(results: list[Check]) -> int:
    """Per D-14: 0 if all OK or only WARN; 1 if any FAIL."""
    if any(c.result is CheckResult.FAIL for c in results):
        return 1
    return 0

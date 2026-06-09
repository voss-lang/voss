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

import json
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


def check_keyring() -> Check:
    """OS keychain availability for voss-stored API keys (env vars and
    upstream-CLI creds still work without it, hence WARN not FAIL)."""
    kr = auth_mod._keyring_module()
    if kr is None:
        return Check(
            "keyring",
            CheckResult.WARN,
            detail="keyring package not importable; voss-stored keys unavailable (env vars still work)",
            fix="pip install keyring",
        )
    if not auth_mod._keyring_available():
        return Check(
            "keyring",
            CheckResult.WARN,
            detail="no usable keyring backend; voss-stored keys unavailable (env vars still work)",
        )
    try:
        backend = type(kr.get_keyring()).__name__
    except Exception:  # noqa: BLE001 — backend probing mirrors auth module
        backend = "unknown backend"
    return Check("keyring", CheckResult.OK, detail=backend)


def check_codex_auth() -> Check:
    """Informational: Codex (~/.codex/auth.json) credential state.

    CodexCreds carries no expiry timestamp, so this reports auth mode only.
    """
    codex = auth_mod.load_codex()
    if codex is None:
        return Check("codex auth", CheckResult.OK, detail="not configured")
    if codex.api_key:
        return Check("codex auth", CheckResult.OK, detail=f"API key ({codex.auth_mode})")
    if codex.has_oauth:
        return Check("codex auth", CheckResult.OK, detail=f"OAuth tokens ({codex.auth_mode})")
    return Check(
        "codex auth",
        CheckResult.WARN,
        detail=f"auth.json present but no usable credentials ({codex.auth_mode})",
        fix="codex login",
    )


def repair_model_prefs() -> RepairResult:
    """Prune (provider, model) pairs absent from the cached model catalog."""
    from . import model_catalog, model_prefs, model_router

    data, _ = model_catalog._read_cache(model_catalog.cache_path())
    if data is None:
        return RepairResult(ok=False, detail="no catalog cache to validate against")
    groups = model_catalog.parse_catalog(data)
    prefs = model_prefs._load()
    removed = 0
    for key in ("recent", "favorites"):
        pairs = model_prefs._pairs(prefs, key)
        kept = [
            list(p) for p in pairs if model_router.find_entry(groups, *p) is not None
        ]
        removed += len(pairs) - len(kept)
        prefs[key] = kept
    if not model_prefs._save(prefs):
        return RepairResult(ok=False, detail="could not write model_prefs.json")
    return RepairResult(ok=True, detail=f"pruned {removed} dangling pair(s)")


def check_model_prefs() -> Check:
    """Recents/favorites must reference models present in the cached
    catalog. Validates offline only — never fetches the catalog."""
    from . import model_catalog, model_prefs, model_router

    pairs = model_prefs.recent() + model_prefs.favorites()
    if not pairs:
        return Check("model prefs", CheckResult.OK, detail="none recorded")
    data, _ = model_catalog._read_cache(model_catalog.cache_path())
    if data is None:
        return Check(
            "model prefs",
            CheckResult.OK,
            detail=f"{len(pairs)} pair(s); no catalog cache to validate against",
        )
    groups = model_catalog.parse_catalog(data)
    dangling = sorted(
        {f"{p}/{m}" for (p, m) in pairs if model_router.find_entry(groups, p, m) is None}
    )
    if dangling:
        shown = ", ".join(dangling[:4]) + ("…" if len(dangling) > 4 else "")
        return Check(
            "model prefs",
            CheckResult.WARN,
            detail=f"{len(dangling)} dangling pair(s): {shown}",
            fix="voss doctor --fix  # prunes dangling picker entries",
            tier=RepairTier.CONFIRM,
            repair=repair_model_prefs,
        )
    return Check(
        "model prefs",
        CheckResult.OK,
        detail=f"{len(pairs)} pair(s) valid against catalog cache",
    )


def repair_session_store(paths: list[Path]) -> RepairResult:
    """Quarantine corrupt session files by renaming to *.corrupt."""
    moved = 0
    for p in paths:
        try:
            p.rename(p.with_name(p.name + ".corrupt"))
            moved += 1
        except OSError as e:
            return RepairResult(
                ok=False, detail=f"{p.name}: {e} (quarantined {moved} before failure)"
            )
    return RepairResult(ok=True, detail=f"quarantined {moved} file(s) as *.corrupt")


def check_session_store(cwd: Path) -> Check:
    """Session JSON files (project + legacy stores) must parse."""
    from . import session as session_mod

    dirs = [session_mod._sessions_dir(cwd), session_mod.legacy_state_dir()]
    corrupt: list[Path] = []
    total = 0
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            total += 1
            try:
                json.loads(p.read_text())
            except (OSError, ValueError):
                corrupt.append(p)
    if corrupt:
        names = ", ".join(p.name for p in corrupt[:3])
        return Check(
            "session store",
            CheckResult.WARN,
            detail=f"{len(corrupt)} corrupt of {total} session file(s) ({names})",
            fix="voss doctor --fix  # quarantines corrupt files as *.corrupt",
            tier=RepairTier.CONFIRM,
            repair=lambda: repair_session_store(corrupt),
        )
    return Check("session store", CheckResult.OK, detail=f"{total} session file(s) parseable")


def check_toolchain() -> Check:
    """Informational: optional toolchains for app/crate development.
    Always OK — doctor is not a package manager."""
    tools = {name: shutil.which(name) for name in ("node", "pnpm", "cargo")}
    found = [n for n, p in tools.items() if p]
    missing = [n for n, p in tools.items() if not p]
    detail = f"found: {', '.join(found) or 'none'}"
    if missing:
        detail += f"; missing: {', '.join(missing)} (only needed for app/crate dev)"
    return Check("toolchain", CheckResult.OK, detail=detail)


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
    CheckSpec("keyring", Category.AUTH, lambda cwd: check_keyring()),
    CheckSpec("codex-auth", Category.AUTH, lambda cwd: check_codex_auth()),
    CheckSpec("git", Category.ENV, lambda cwd: check_git_on_path()),
    CheckSpec("cwd-writable", Category.ENV, lambda cwd: check_cwd_writable(cwd)),
    CheckSpec("config-dirs", Category.CONFIG, lambda cwd: check_config_dirs_creatable()),
    CheckSpec("model-prefs", Category.CONFIG, lambda cwd: check_model_prefs()),
    CheckSpec("project-dirs", Category.PROJECT, lambda cwd: check_project_dirs(cwd)),
    CheckSpec("harness-cache", Category.PROJECT, lambda cwd: check_harness_cache(cwd)),
    CheckSpec("cognition", Category.PROJECT, lambda cwd: check_cognition(cwd)),
    CheckSpec("session-store", Category.STATE, lambda cwd: check_session_store(cwd)),
    CheckSpec("legacy-sessions", Category.STATE, lambda cwd: check_legacy_sessions()),
    CheckSpec(
        "third-party-skills", Category.PROJECT, lambda cwd: check_third_party_skills(cwd)
    ),
    CheckSpec("toolchain", Category.ENV, lambda cwd: check_toolchain()),
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


def to_dict(check: Check) -> dict:
    """Wire shape for a check — single source for CLI --json and the
    server GET /doctor payload."""
    return {
        "id": check.id,
        "name": check.name,
        "category": check.category.value if check.category else "",
        "status": check.result.name,
        "detail": check.detail,
        "fix": check.fix,
    }


def aggregate_exit_code(results: list[Check]) -> int:
    """Per D-14: 0 if all OK or only WARN; 1 if any FAIL."""
    if any(c.result is CheckResult.FAIL for c in results):
        return 1
    return 0

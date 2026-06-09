"""Project cognition: load durable .voss/ state, drift-check, helpers.

Pure module. Never raises out of `load()` or `drift_check()` — failures
populate `CognitionBundle.load_errors` or fall back to sentinel values.
All YAML parsing uses `yaml.safe_load` (T-M2-01). Subprocess calls wrapped
in try/except for OSError + SubprocessError (T-M2-03).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from voss.template_render import render_package_template

from .cognition_schemas import (
    ConstraintsConfig,
    PermissionsConfig,
    ProjectMeta,
    SafetyConfig,
    ValidationConfig,
)

ANALYZER_VERSION = 1
DRIFT_COMMITS = 20
HEAD_CAP_BYTES = 4096
README_CANDIDATES = ("README.md", "readme.md", "Readme.md", "README", "readme")
DRIFT_FILE_PCT = 0.10
DRIFT_DAYS = 7

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass(frozen=True)
class ArchitectureFrontmatter:
    git_head: str
    analyzed_at: str
    file_count: int
    analyzer_version: int


@dataclass(frozen=True)
class CognitionBundle:
    initialized: bool
    project: Optional[ProjectMeta] = None
    architecture_md: Optional[str] = None
    architecture_frontmatter: Optional[ArchitectureFrontmatter] = None
    constraints: Optional[ConstraintsConfig] = None
    permissions: Optional[PermissionsConfig] = None
    validation: Optional[ValidationConfig] = None
    safety: Optional[SafetyConfig] = None
    architecture_tokens: int = 0
    load_errors: list[str] = field(default_factory=list)


@dataclass
class DriftStatus:
    is_stale: bool
    head_diverged_by: int
    file_count_delta: int
    days_elapsed: int
    reason: str = ""


def voss_dir(cwd: Path) -> Path:
    return cwd / ".voss"


def cache_dir(cwd: Path) -> Path:
    return cwd / ".voss-cache"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path, model, errors: list[str]):
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        errors.append(f"{path}: invalid JSON: {e}")
        return None
    try:
        return model.model_validate(raw)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"]) or "<root>"
            errors.append(f"{path}: {loc}: {err['msg']}")
        return None


def _parse_arch_text(path_label: str, text: str, errors: list[str]):
    """Shared frontmatter parse — used by VOSS.md fence body + legacy architecture.md."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text, None

    fm_text, body = m.group(1), m.group(2)
    try:
        fm_data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        errors.append(f"{path_label}: invalid frontmatter YAML: {e}")
        return body, None

    try:
        arch_fm = ArchitectureFrontmatter(
            git_head=str(fm_data.get("git_head", "")),
            analyzed_at=str(fm_data.get("analyzed_at", "")),
            file_count=int(fm_data.get("file_count", 0)),
            analyzer_version=int(fm_data.get("analyzer_version", ANALYZER_VERSION)),
        )
    except (TypeError, ValueError) as e:
        errors.append(f"{path_label}: frontmatter field error: {e}")
        return body, None

    return body, arch_fm


def _load_arch(path: Path, errors: list[str]):
    """DEPRECATED post-M8: legacy read of `.voss/architecture.md`.

    Retained as a fallback so M2-style direct-write tests still pass when
    no VOSS.md is present. Production read path is
    `_load_arch_from_voss_md` below.
    """
    if not path.exists():
        return None, None
    try:
        text = path.read_text()
    except OSError as e:
        errors.append(f"{path}: read error: {e}")
        return None, None
    return _parse_arch_text(str(path), text, errors)


def _load_arch_from_voss_md(cwd: Path, errors: list[str]):
    """Read the id=architecture fence body from cwd/VOSS.md (Pitfall 2 read-path).

    On HashMismatch (human-edited drift): use `exc.on_disk` as body — read
    paths must keep working; `voss memory adopt` (M8-04) is the formal accept
    flow for promoting the edit into a new recorded hash.

    Falls back to legacy `.voss/architecture.md` via `_load_arch` when
    cwd/VOSS.md does not exist (backward compat for tests that write the
    legacy file directly).
    """
    from . import voss_md as _voss_md  # local import; voss_md may import cognition

    voss_md_path = cwd / "VOSS.md"
    if not voss_md_path.exists():
        return _load_arch(voss_dir(cwd) / "architecture.md", errors)

    try:
        body = _voss_md.read_fence_body(voss_md_path, fence_id="architecture")
    except _voss_md.HashMismatch as exc:
        body = exc.on_disk
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{voss_md_path}: read error: {exc}")
        return None, None

    if body is None:
        return _load_arch(voss_dir(cwd) / "architecture.md", errors)

    return _parse_arch_text(str(voss_md_path), body, errors)


def _load_yaml(path: Path, model, errors: list[str]):
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        errors.append(f"{path}: invalid YAML: {e}")
        return None
    try:
        return model.model_validate(raw)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"]) or "<root>"
            errors.append(f"{path}: {loc}: {err['msg']}")
        return None


def _git_rev_list_count(cwd: Path, sha: str) -> int:
    """Return commit count between sha and HEAD. On failure return DRIFT_COMMITS."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{sha}..HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            # Unreachable SHA (force-rebase) — treat as drifted (Pitfall 4)
            return DRIFT_COMMITS
        return int(result.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return DRIFT_COMMITS


def _git_ls_files_count(cwd: Path) -> int:
    """Return count of tracked files. On failure return -1 (signal unknown)."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return -1
        return len(result.stdout.splitlines())
    except (OSError, subprocess.SubprocessError):
        return -1


def _days_since(analyzed_at: str) -> int:
    """Parse ISO timestamp and return elapsed days. On parse failure return 0."""
    try:
        then = datetime.fromisoformat(analyzed_at)
        now = datetime.now(timezone.utc)
        # Ensure both are aware
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return max(0, (now - then).days)
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _is_initialized(cwd: Path) -> bool:
    """Post-M8 initialization gate: VOSS.md present OR legacy architecture.md present."""
    if (cwd / "VOSS.md").exists():
        return True
    return (voss_dir(cwd) / "architecture.md").exists()


def load(cwd: Path, *, token_count: "callable | None" = None) -> CognitionBundle:
    root = voss_dir(cwd)
    if not _is_initialized(cwd):
        return CognitionBundle(initialized=False)

    errors: list[str] = []
    proj = _load_json(root / "project.json", ProjectMeta, errors)
    arch_body, arch_fm = _load_arch_from_voss_md(cwd, errors)
    constraints = _load_yaml(root / "constraints.yml", ConstraintsConfig, errors)
    permissions = _load_yaml(root / "permissions.yml", PermissionsConfig, errors)
    validation = _load_yaml(root / "validation.yml", ValidationConfig, errors)
    # V12: optional project-local safety policy (missing file → None, no error).
    safety = _load_yaml(root / "safety.yml", SafetyConfig, errors)
    tok = token_count(arch_body) if (token_count and arch_body) else 0
    return CognitionBundle(
        initialized=True,
        project=proj,
        architecture_md=arch_body,
        architecture_frontmatter=arch_fm,
        constraints=constraints,
        permissions=permissions,
        validation=validation,
        safety=safety,
        architecture_tokens=tok,
        load_errors=errors,
    )


def drift_check(cwd: Path, fm: ArchitectureFrontmatter) -> DriftStatus:
    head_div = _git_rev_list_count(cwd, fm.git_head)
    cur_files_raw = _git_ls_files_count(cwd)
    # If ls-files failed, use fm.file_count so there's no delta
    cur_files = cur_files_raw if cur_files_raw >= 0 else fm.file_count
    file_delta = cur_files - fm.file_count
    days = _days_since(fm.analyzed_at)

    triggers: list[str] = []
    if head_div >= DRIFT_COMMITS:
        triggers.append(f"HEAD +{head_div} commits")
    if abs(file_delta) / max(fm.file_count, 1) >= DRIFT_FILE_PCT:
        sign = "+" if file_delta >= 0 else ""
        triggers.append(f"{sign}{file_delta} files")
    if days >= DRIFT_DAYS:
        triggers.append(f"{days}d old")

    return DriftStatus(
        is_stale=bool(triggers),
        head_diverged_by=head_div,
        file_count_delta=file_delta,
        days_elapsed=days,
        reason=", ".join(triggers),
    )


def build_repo_idx(cwd: Path) -> dict:
    """Build a repo.idx JSON manifest (D-05)."""
    # Get git HEAD sha
    git_head = ""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_head = result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    # Get file list via git ls-files
    file_paths: list[Path] = []
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for rel in result.stdout.splitlines():
                if rel.strip():
                    file_paths.append(cwd / rel)
        else:
            raise subprocess.SubprocessError("git ls-files nonzero")
    except (OSError, subprocess.SubprocessError):
        # Fall back: walk the directory
        for p in cwd.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                file_paths.append(p)

    files = []
    for fp in file_paths:
        try:
            stat = fp.stat()
            raw = fp.read_bytes()
            # Truncated SHA-256 for repo-index fingerprinting. Not security-
            # critical (local cache invalidation only) but SHA-1 is prohibited
            # for new code by NIST/BSI/ANSSI regardless of intent.
            sha = hashlib.sha256(raw).hexdigest()[:40]
            files.append(
                {
                    "path": fp.relative_to(cwd).as_posix(),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "sha": sha,
                }
            )
        except (OSError, ValueError):
            continue

    return {"version": 1, "git_head": git_head, "files": files}


def render_constraints_bullets(c: "ConstraintsConfig | None") -> str:
    if not c or not c.rules:
        return ""
    lines = []
    for r in c.rules:
        if r.forbid:
            lines.append(f"- forbid: {', '.join(r.forbid)}")
        if r.require_tests_for:
            lines.append(f"- require tests for: {', '.join(r.require_tests_for)}")
        if r.max_file_size_lines:
            lines.append(f"- max file size: {r.max_file_size_lines} lines")
        if r.custom:
            lines.append(f"- {r.custom}")
    return "\n".join(lines)


def append_gitignore_line_idempotent(path: Path, line: str) -> bool:
    """Return True if the line was appended, False if already present."""
    line_stripped = line.strip()
    if path.exists():
        for existing in path.read_text().splitlines():
            if existing.strip() == line_stripped:
                return False
    with path.open("a") as f:
        # Ensure there's a newline before the appended line if file is non-empty
        if path.stat().st_size > 0 if path.exists() else False:
            # Check if file ends with newline
            current = path.read_text()
            if current and not current.endswith("\n"):
                f.write("\n")
        f.write(line.rstrip("\n") + "\n")
    return True


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60] or "untitled"


def reserve_filename(dir_: Path, base: str, ext: str = ".md") -> Path:
    """Return a non-colliding filename under dir_. Does NOT mkdir."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = dir_ / f"{today}-{base}{ext}"
    n = 2
    while p.exists():
        p = dir_ / f"{today}-{base}-{n}{ext}"
        n += 1
    return p


# ---------------------------------------------------------------------------
# M2-04: hybrid bootstrap helpers
# ---------------------------------------------------------------------------


_LANG_BY_EXT = {
    "py": "python",
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "swift": "swift",
    "rs": "rust",
    "go": "go",
    "rb": "ruby",
    "java": "java",
    "kt": "kotlin",
    "cs": "csharp",
    "cpp": "c-or-cpp",
    "cc": "c-or-cpp",
    "cxx": "c-or-cpp",
    "c": "c-or-cpp",
    "m": "objective-c",
    "mm": "objective-c",
    "php": "php",
}

_VENDORED = {"node_modules", ".venv", ".git", "dist", "build", "target", ".voss-cache"}

_MANIFEST_CANDIDATES = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "Package.swift",
    "go.mod",
    "Gemfile",
)


def _git_rev_parse_head(cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or "UNKNOWN"
    except (OSError, subprocess.SubprocessError):
        pass
    return "UNKNOWN"


def _git_ls_files(cwd: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return [ln for ln in result.stdout.splitlines() if ln.strip()]
    except (OSError, subprocess.SubprocessError):
        return None


def _walk_files_fallback(cwd: Path) -> list[str]:
    files: list[str] = []
    for p in cwd.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _VENDORED for part in p.parts):
            continue
        try:
            files.append(p.relative_to(cwd).as_posix())
        except ValueError:
            continue
    return files


def detect_primary_language(cwd: Path) -> str:
    """Return the primary language for cwd, or 'unknown'."""
    rels = _git_ls_files(cwd)
    if rels is None:
        rels = _walk_files_fallback(cwd)

    counts: dict[str, int] = {}
    for rel in rels:
        name = rel.rsplit("/", 1)[-1]
        if name.startswith("."):
            continue
        parts = rel.split("/")
        if any(p in _VENDORED for p in parts):
            continue
        if "." not in name:
            continue
        ext = name.rsplit(".", 1)[-1].lower()
        lang = _LANG_BY_EXT.get(ext)
        if lang is None:
            continue
        counts[lang] = counts.get(lang, 0) + 1

    if not counts:
        return "unknown"
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _read_head(path: Path, limit: int = HEAD_CAP_BYTES) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(errors="replace")[:limit]
    except OSError:
        return ""


def _find_manifest(cwd: Path) -> tuple[str | None, str]:
    for cand in _MANIFEST_CANDIDATES:
        p = cwd / cand
        if p.exists() and p.is_file():
            return cand, _read_head(p)
    return None, ""


def _count_files_pruned(d: Path) -> int:
    """Recursively count files under d, pruning vendored + hidden dirs."""
    total = 0
    try:
        for _, dirs, files in os.walk(d):
            dirs[:] = [
                x for x in dirs if x not in _VENDORED and not x.startswith(".")
            ]
            total += len(files)
    except OSError:
        return 0
    return total


def _dir_tree(cwd: Path, limit: int = 12) -> list[tuple[str, int]]:
    entries: list[tuple[str, int]] = []
    try:
        children = sorted(cwd.iterdir())
    except OSError:
        return entries
    for child in children:
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in _VENDORED:
            continue
        entries.append((child.name, _count_files_pruned(child)))
        if len(entries) >= limit:
            break
    return entries


def build_bootstrap_inventory(cwd: Path) -> dict:
    """Pre-compute the inventory injected into the bootstrap LLM prompt."""
    rels = _git_ls_files(cwd)
    if rels is None:
        rels = _walk_files_fallback(cwd)
    manifest_path, manifest_head = _find_manifest(cwd)
    readme_head = ""
    for name in README_CANDIDATES:
        p = cwd / name
        if p.exists() and p.is_file():
            readme_head = _read_head(p)
            break
    return {
        "name": cwd.name,
        "git_head": _git_rev_parse_head(cwd),
        "file_count": len(rels),
        "analyzed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "primary_language": detect_primary_language(cwd),
        "dir_tree": _dir_tree(cwd),
        "manifest_path": manifest_path,
        "manifest_head": manifest_head,
        "readme_head": readme_head,
    }


def init_voss_stubs(cwd: Path, *, inventory: dict) -> dict[str, bool]:
    """Write the 4 deterministic cognition files preserve-if-exists.

    Returns a dict mapping filename -> True if newly written, False if preserved.
    """
    voss_dir(cwd).mkdir(parents=True, exist_ok=True)

    project_meta = ProjectMeta(
        name=inventory["name"],
        primary_language=inventory["primary_language"],
    )

    targets: list[tuple[str, Callable[[], str]]] = [
        (
            "project.json",
            lambda: json.dumps(project_meta.model_dump(), indent=2) + "\n",
        ),
        (
            "constraints.yml",
            lambda: yaml.safe_dump(ConstraintsConfig().model_dump(), sort_keys=False),
        ),
        (
            "permissions.yml",
            lambda: yaml.safe_dump(PermissionsConfig().model_dump(), sort_keys=False),
        ),
        (
            "validation.yml",
            lambda: yaml.safe_dump(ValidationConfig().model_dump(), sort_keys=False),
        ),
    ]

    results: dict[str, bool] = {}
    for name, build in targets:
        path = voss_dir(cwd) / name
        if path.exists():
            results[name] = False
            continue
        path.write_text(build())
        results[name] = True
    return results


def write_voss_gitignore(cwd: Path) -> bool:
    """Write `.voss/.gitignore` preserve-if-exists."""
    target = voss_dir(cwd) / ".gitignore"
    voss_dir(cwd).mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    target.write_text("# voss session state and rebuildable cache\nsessions/\n")
    return True


def bootstrap_prompt(inventory: dict, *, target_path: str = ".voss/architecture.md") -> str:
    """Single-turn prompt: agent emits ONE fs_write to target_path.

    Post-M8: callers pass `.voss/.analyze.staging.md`; the harness folds the
    staged file into VOSS.md's id=architecture fence via voss_md.write_fence_body.
    """
    return render_package_template(
        "voss",
        "templates/cognition/bootstrap.md.jinja",
        {
            "name": inventory["name"],
            "target_path": target_path,
            "git_head": inventory["git_head"],
            "analyzed_at": inventory["analyzed_at"],
            "file_count": inventory["file_count"],
            "primary_language": inventory["primary_language"],
            "dir_tree": inventory["dir_tree"],
            "manifest_path": inventory["manifest_path"],
            "manifest_head": inventory["manifest_head"],
            "readme_head": inventory["readme_head"],
        },
    )


def _render_steps_for_plan_md(steps) -> str:
    lines: list[str] = []
    for step in steps:
        args = getattr(step, "args", {}) or {}
        kwargs_str = ", ".join(
            f"{k}={json.dumps(v, separators=(',', ':'))}" for k, v in args.items()
        )
        why = getattr(step, "why", "") or ""
        lines.append(f"- {step.name}({kwargs_str}) — {why}")
    if not lines:
        return "- (no steps)"
    return "\n".join(lines)


def write_plan_md(
    cwd: Path,
    plan,
    *,
    session_id: str,
    model: str,
    title: str | None = None,
) -> Path:
    """Persist a Plan to .voss/plans/YYYY-MM-DD-<slug>.md."""
    plans_dir = voss_dir(cwd) / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    base_source = title or (plan.rationale[:40] if plan.rationale else "plan")
    base = slug(base_source)
    path = reserve_filename(plans_dir, base)
    id_str = path.stem
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    confidence = float(getattr(plan, "confidence", 0.0))
    rationale = getattr(plan, "rationale", "") or ""
    steps_block = _render_steps_for_plan_md(getattr(plan, "steps", []) or [])
    heading = title or "Plan"
    content = (
        "---\n"
        f"id: {id_str}\n"
        "status: open\n"
        f"related_session: {session_id}\n"
        f"model: {model}\n"
        f"confidence: {confidence:.2f}\n"
        f"created_at: {created_at}\n"
        "---\n\n"
        f"# {heading}\n\n"
        "## Rationale\n\n"
        f"{rationale}\n\n"
        "## Steps\n\n"
        f"{steps_block}\n"
    )
    path.write_text(content)
    return path

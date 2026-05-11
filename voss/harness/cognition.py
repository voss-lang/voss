"""Project cognition: load durable .voss/ state, drift-check, helpers.

Pure module. Never raises out of `load()` or `drift_check()` — failures
populate `CognitionBundle.load_errors` or fall back to sentinel values.
All YAML parsing uses `yaml.safe_load` (T-M2-01). Subprocess calls wrapped
in try/except for OSError + SubprocessError (T-M2-03).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from .cognition_schemas import (
    ConstraintsConfig,
    PermissionsConfig,
    ProjectMeta,
    ValidationConfig,
)

ANALYZER_VERSION = 1
DRIFT_COMMITS = 20
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


def _load_arch(path: Path, errors: list[str]):
    """Return (body_str, ArchitectureFrontmatter | None). Never raises."""
    if not path.exists():
        return None, None
    try:
        text = path.read_text()
    except OSError as e:
        errors.append(f"{path}: read error: {e}")
        return None, None

    m = FRONTMATTER_RE.match(text)
    if not m:
        # No frontmatter — return raw text as body
        return text, None

    fm_text, body = m.group(1), m.group(2)
    try:
        fm_data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        errors.append(f"{path}: invalid frontmatter YAML: {e}")
        return body, None

    try:
        arch_fm = ArchitectureFrontmatter(
            git_head=str(fm_data.get("git_head", "")),
            analyzed_at=str(fm_data.get("analyzed_at", "")),
            file_count=int(fm_data.get("file_count", 0)),
            analyzer_version=int(fm_data.get("analyzer_version", ANALYZER_VERSION)),
        )
    except (TypeError, ValueError) as e:
        errors.append(f"{path}: frontmatter field error: {e}")
        return body, None

    return body, arch_fm


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


def load(cwd: Path, *, token_count: "callable | None" = None) -> CognitionBundle:
    root = voss_dir(cwd)
    if not (root / "architecture.md").exists():
        return CognitionBundle(initialized=False)

    errors: list[str] = []
    proj = _load_json(root / "project.json", ProjectMeta, errors)
    arch_body, arch_fm = _load_arch(root / "architecture.md", errors)
    constraints = _load_yaml(root / "constraints.yml", ConstraintsConfig, errors)
    permissions = _load_yaml(root / "permissions.yml", PermissionsConfig, errors)
    validation = _load_yaml(root / "validation.yml", ValidationConfig, errors)
    tok = token_count(arch_body) if (token_count and arch_body) else 0
    return CognitionBundle(
        initialized=True,
        project=proj,
        architecture_md=arch_body,
        architecture_frontmatter=arch_fm,
        constraints=constraints,
        permissions=permissions,
        validation=validation,
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
            sha = hashlib.sha1(raw).hexdigest()
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

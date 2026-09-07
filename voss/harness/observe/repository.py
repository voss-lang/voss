"""Repository identity and state fingerprints for observe events (OBS-03/05)."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class NotARepositoryError(ValueError):
    pass


def _git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(path),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise NotARepositoryError(
            f"git {' '.join(args)} failed in {path}: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def canonical_worktree_root(path: str | Path) -> Path:
    return Path(_git(Path(path), "rev-parse", "--show-toplevel")).resolve()


def canonical_common_dir(path: str | Path) -> Path:
    path = Path(path)
    raw = _git(path, "rev-parse", "--git-common-dir")
    p = Path(raw)
    if not p.is_absolute():
        p = path.resolve() / p
    return p.resolve()


def repository_id(path: str | Path) -> str:
    return hashlib.sha256(str(canonical_common_dir(path)).encode()).hexdigest()


def worktree_id(path: str | Path) -> str:
    return hashlib.sha256(str(canonical_worktree_root(path)).encode()).hexdigest()


def repository_state_id(path: str | Path) -> str:
    path = Path(path)
    try:
        head = _git(path, "rev-parse", "--verify", "HEAD")
    except NotARepositoryError:
        head = "unborn"
    status = _git(path, "status", "--porcelain")
    diff = _git(path, "diff", "HEAD", "--") if head != "unborn" else ""
    status_hash = hashlib.sha256(status.encode()).hexdigest()[:12]
    diff_hash = hashlib.sha256(diff.encode()).hexdigest()[:12]
    return f"{head}:{status_hash}:{diff_hash}"


__all__ = [
    "NotARepositoryError",
    "canonical_common_dir",
    "canonical_worktree_root",
    "repository_id",
    "repository_state_id",
    "worktree_id",
]

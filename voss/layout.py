"""Layout-context derivation for `voss sync` (V16, R2).

Derives project layout facts from git/fs probes at sync time. Deterministic
by construction: no timestamps, no mtimes, no environment-dependent ordering
— the same unchanged tree always yields the same Layout.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from voss.harness.cognition import voss_dir


@dataclass(frozen=True)
class Layout:
    project_name: str
    project_root: Path
    is_worktree: bool
    command_prefix: str
    voss_dir: Path
    docs_dir: Path


def _git_rev_parse(cwd: Path, *args: str) -> str | None:
    """Run `git rev-parse <args>`; return stripped stdout or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def derive_layout(cwd: Path) -> Layout:
    """Derive the project layout for `cwd` from git, falling back to fs-only.

    Worktree detection: inside a `git worktree add` checkout,
    `git rev-parse --git-dir` and `git rev-parse --git-common-dir` diverge
    (the worktree's git-dir lives under <main>/.git/worktrees/<name>).
    """
    cwd = cwd.resolve()
    toplevel = _git_rev_parse(cwd, "--show-toplevel")
    if (cwd / ".voss").is_dir():
        # A .voss tree at cwd marks the project root even when nested inside
        # a larger git checkout (dotfiles-tracked $HOME, monorepo) — the
        # enclosing toplevel would silently misdirect config reads and writes.
        project_root = cwd
    elif toplevel:
        project_root = Path(toplevel).resolve()
    else:
        project_root = cwd

    is_worktree = False
    git_dir = _git_rev_parse(cwd, "--git-dir")
    common_dir = _git_rev_parse(cwd, "--git-common-dir")
    if git_dir is not None and common_dir is not None:
        # rev-parse may emit relative paths (e.g. ".git"); anchor at cwd.
        is_worktree = (cwd / git_dir).resolve() != (cwd / common_dir).resolve()

    vdir = voss_dir(project_root)
    return Layout(
        project_name=project_root.name,
        project_root=project_root,
        is_worktree=is_worktree,
        command_prefix="voss",
        voss_dir=vdir,
        docs_dir=vdir / "docs",
    )


__all__ = ["Layout", "derive_layout"]

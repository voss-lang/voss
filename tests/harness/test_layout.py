"""V16-01 layout-context derivation tests (R2)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from voss.layout import derive_layout


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Plain `git init` repo root with one commit (worktree add needs HEAD)."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(["init", "-q"], root)
    _git(
        [
            "-c", "user.email=test@test",
            "-c", "user.name=test",
            "commit", "--allow-empty", "-m", "init",
        ],
        root,
    )
    return root


@pytest.fixture()
def worktree(repo: Path, tmp_path: Path) -> Path:
    wt = tmp_path / "proj-wt"
    _git(["worktree", "add", str(wt)], repo)
    return wt


class TestRepoRoot:
    def test_plain_repo_root(self, repo: Path) -> None:
        layout = derive_layout(repo)
        assert layout.is_worktree is False
        assert layout.project_root == repo.resolve()
        assert layout.project_name == "proj"
        assert layout.voss_dir == repo.resolve() / ".voss"
        assert layout.docs_dir == repo.resolve() / ".voss" / "docs"
        assert layout.command_prefix


class TestWorktree:
    def test_worktree_checkout(self, repo: Path, worktree: Path) -> None:
        layout = derive_layout(worktree)
        assert layout.is_worktree is True
        assert layout.project_root == worktree.resolve()
        assert layout.project_name == "proj-wt"

    def test_repo_root_and_worktree_differ(self, repo: Path, worktree: Path) -> None:
        assert derive_layout(repo).is_worktree is False
        assert derive_layout(worktree).is_worktree is True


class TestDeterminism:
    def test_same_tree_same_layout(self, repo: Path) -> None:
        assert derive_layout(repo) == derive_layout(repo)

    def test_worktree_deterministic(self, worktree: Path) -> None:
        assert derive_layout(worktree) == derive_layout(worktree)


class TestNonGitFallback:
    def test_non_git_dir_falls_back_to_fs(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        layout = derive_layout(plain)
        assert layout.is_worktree is False
        assert layout.project_root == plain.resolve()
        assert layout.project_name == "plain"

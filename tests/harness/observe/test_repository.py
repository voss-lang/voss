from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from voss.harness.observe.repository import (
    NotARepositoryError,
    canonical_common_dir,
    canonical_worktree_root,
    repository_id,
    repository_state_id,
    worktree_id,
)


def test_repository_id_stable_and_hex(git_repo: Path) -> None:
    first = repository_id(git_repo)
    assert first == repository_id(git_repo)
    assert len(first) == 64
    int(first, 16)


def test_repository_id_shared_from_subdirectory(git_repo: Path) -> None:
    sub = git_repo / "src" / "pkg"
    sub.mkdir(parents=True)
    assert repository_id(sub) == repository_id(git_repo)
    assert worktree_id(sub) == worktree_id(git_repo)


def test_repository_id_differs_across_repos(git_repo: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init"], cwd=other, check=True, capture_output=True)
    assert repository_id(other) != repository_id(git_repo)
    assert worktree_id(other) != worktree_id(git_repo)


def test_canonical_paths(git_repo: Path) -> None:
    assert canonical_worktree_root(git_repo) == git_repo.resolve()
    assert canonical_common_dir(git_repo) == (git_repo / ".git").resolve()


def test_linked_worktree_shares_repository_id(git_repo: Path, tmp_path: Path) -> None:
    linked = tmp_path / "linked"
    subprocess.run(
        ["git", "worktree", "add", str(linked)],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    assert repository_id(linked) == repository_id(git_repo)
    assert worktree_id(linked) != worktree_id(git_repo)


def test_repository_state_id_tracks_content(git_repo: Path) -> None:
    clean = repository_state_id(git_repo)
    assert repository_state_id(git_repo) == clean

    (git_repo / "README.md").write_text("# changed\n")
    dirty = repository_state_id(git_repo)
    assert dirty != clean

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "change"], cwd=git_repo, check=True, capture_output=True
    )
    committed = repository_state_id(git_repo)
    assert committed != dirty
    assert committed.split(":")[0] != clean.split(":")[0]


def test_not_a_repository(tmp_path: Path) -> None:
    with pytest.raises(NotARepositoryError):
        repository_id(tmp_path)
    with pytest.raises(NotARepositoryError):
        repository_state_id(tmp_path)

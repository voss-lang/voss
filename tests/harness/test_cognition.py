"""Wave 1 tests for voss/harness/cognition.py (COG-01, COG-02, COG-07)."""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from voss.harness.cognition import (
    ArchitectureFrontmatter,
    append_gitignore_line_idempotent,
    build_repo_idx,
    drift_check,
    load,
    reserve_filename,
    slug,
)


@pytest.mark.skip(reason="Wave 2 — pending plan M2-04")
def test_analyze_writes_project_json() -> None:
    pass


@pytest.mark.skip(reason="Wave 2 — pending plan M2-04")
def test_architecture_md_frontmatter_well_formed() -> None:
    pass


def test_load_parses_frontmatter(git_repo: Path) -> None:
    voss = git_repo / ".voss"
    voss.mkdir()
    (voss / "architecture.md").write_text(
        "---\n"
        "git_head: abc\n"
        "analyzed_at: 2026-05-10T00:00:00+00:00\n"
        "file_count: 5\n"
        "analyzer_version: 1\n"
        "---\n"
        "# Arch\n"
    )

    b = load(git_repo)
    assert b.initialized is True
    assert b.architecture_md == "# Arch\n"
    assert b.architecture_frontmatter is not None
    assert b.architecture_frontmatter.git_head == "abc"
    assert b.architecture_frontmatter.file_count == 5


def test_drift_commits_threshold(git_repo: Path) -> None:
    voss = git_repo / ".voss"
    voss.mkdir()
    # Use an unreachable SHA — 40-char hex but not in repo history
    unreachable_sha = "deadbeef" * 5
    now_iso = datetime.now(timezone.utc).isoformat()
    (voss / "architecture.md").write_text(
        f"---\n"
        f"git_head: {unreachable_sha}\n"
        f"analyzed_at: {now_iso}\n"
        f"file_count: 1\n"
        f"analyzer_version: 1\n"
        f"---\n"
        f"# Arch\n"
    )

    b = load(git_repo)
    assert b.architecture_frontmatter is not None
    result = drift_check(git_repo, b.architecture_frontmatter)
    assert result.is_stale is True
    reason_lower = result.reason.lower()
    assert "head" in reason_lower or "commit" in reason_lower


def test_drift_file_count_threshold(git_repo: Path) -> None:
    # Add a second file and commit it
    (git_repo / "second.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=str(git_repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "more"],
        cwd=str(git_repo),
        check=True,
        capture_output=True,
    )

    # Get the first commit's SHA (HEAD~1)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD~1"],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
        check=True,
    )
    first_sha = result.stdout.strip()

    voss = git_repo / ".voss"
    voss.mkdir()
    now_iso = datetime.now(timezone.utc).isoformat()
    # frontmatter says 1 file, but repo now has 2
    (voss / "architecture.md").write_text(
        f"---\n"
        f"git_head: {first_sha}\n"
        f"analyzed_at: {now_iso}\n"
        f"file_count: 1\n"
        f"analyzer_version: 1\n"
        f"---\n"
        f"# Arch\n"
    )

    b = load(git_repo)
    assert b.architecture_frontmatter is not None
    drift = drift_check(git_repo, b.architecture_frontmatter)
    assert drift.is_stale is True
    assert drift.file_count_delta > 0


def test_drift_days_threshold(git_repo: Path) -> None:
    # Get current HEAD
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
        check=True,
    )
    current_head = result.stdout.strip()

    # Get current file count
    ls_result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
        check=True,
    )
    current_count = len(ls_result.stdout.splitlines())

    # analyzed_at is 10 days ago
    ten_days_ago = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    voss = git_repo / ".voss"
    voss.mkdir()
    (voss / "architecture.md").write_text(
        f"---\n"
        f"git_head: {current_head}\n"
        f"analyzed_at: {ten_days_ago}\n"
        f"file_count: {current_count}\n"
        f"analyzer_version: 1\n"
        f"---\n"
        f"# Arch\n"
    )

    b = load(git_repo)
    assert b.architecture_frontmatter is not None
    drift = drift_check(git_repo, b.architecture_frontmatter)
    assert drift.is_stale is True
    assert "d old" in drift.reason


def test_plan_filename_and_frontmatter(tmp_path: Path) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = reserve_filename(tmp_path / "plans", slug("My Plan Title"))
    assert p.name.startswith(today + "-")
    assert p.name.endswith("-my-plan-title.md")


def test_reserve_filename_collision(tmp_path: Path) -> None:
    d = tmp_path / "plans"
    d.mkdir()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = slug("collision test")

    # Create the first candidate
    first = d / f"{today}-{base}.md"
    first.write_text("exists\n")

    p2 = reserve_filename(d, base)
    assert p2.name == f"{today}-{base}-2.md"

    # Create the second candidate too
    p2.write_text("exists\n")
    p3 = reserve_filename(d, base)
    assert p3.name == f"{today}-{base}-3.md"


@pytest.mark.skip(reason="Wave 2 — pending plan M2-03")
def test_decision_frontmatter() -> None:
    pass


def test_repo_idx_schema(git_repo: Path) -> None:
    idx = build_repo_idx(git_repo)
    assert idx["version"] == 1
    assert len(idx["git_head"]) == 40
    assert all(c in "0123456789abcdef" for c in idx["git_head"])
    assert isinstance(idx["files"], list)
    assert len(idx["files"]) > 0
    entry = idx["files"][0]
    assert set(entry.keys()) == {"path", "size", "mtime", "sha"}
    assert len(entry["sha"]) == 40
    assert all(c in "0123456789abcdef" for c in entry["sha"])


def test_gitignore_idempotent(tmp_path: Path) -> None:
    g = tmp_path / ".gitignore"
    assert append_gitignore_line_idempotent(g, ".voss-cache/") is True
    assert append_gitignore_line_idempotent(g, ".voss-cache/") is False
    assert g.read_text().count(".voss-cache/") == 1


@pytest.mark.skip(reason="Wave 2 — pending plan M2-04")
def test_voss_gitignore_autogenerated() -> None:
    pass


@pytest.mark.skip(reason="Wave 2 — pending plan M2-04")
def test_analyze_invokes_natural_language_route() -> None:
    pass


@pytest.mark.skip(reason="Wave 2 — pending plan M2-04")
def test_analyze_emits_project_root_gitignore_append() -> None:
    pass

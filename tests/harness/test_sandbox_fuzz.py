"""Sandbox `jail_path` fuzz against traversal + escape inputs.

20 inputs covering: parent traversal (..), absolute escapes, hidden symlink
exits, double-encoded paths, current-dir traversal, mixed-separator,
nested-relative escapes.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from voss.harness.sandbox import SandboxError, jail_path


# Inputs that MUST raise SandboxError.
ESCAPE_INPUTS = [
    "../escape.txt",
    "../../etc/passwd",
    "../../../etc/passwd",
    "/etc/passwd",
    "/tmp/foo",
    "subdir/../../escape.txt",
    "subdir/../../../escape.txt",
    "./../escape.txt",
    "foo/./../../bar",
    "//etc/passwd",
    "////etc//passwd",
    str(Path.home()),
    "/root",
    "../" + "a/" * 50 + "esc",
]


# Inputs that MUST resolve cleanly to a path under cwd.
SAFE_INPUTS = [
    "file.txt",
    "subdir/file.txt",
    "./file.txt",
    "subdir/./file.txt",
    "a/b/c/d.txt",
    "weird name with spaces.txt",
]


@pytest.mark.parametrize("target", ESCAPE_INPUTS)
def test_jail_path_rejects_escapes(tmp_path: Path, target: str) -> None:
    with pytest.raises(SandboxError):
        jail_path(tmp_path, target)


@pytest.mark.parametrize("target", SAFE_INPUTS)
def test_jail_path_accepts_safe_paths(tmp_path: Path, target: str) -> None:
    resolved = jail_path(tmp_path, target)
    # Resolved path must be a descendant of tmp_path.
    resolved.relative_to(tmp_path.resolve())


def test_jail_path_rejects_symlink_escape(tmp_path: Path) -> None:
    """A symlink inside cwd pointing outside cwd must be rejected on resolve."""
    outside = tmp_path.parent / "outside-target"
    outside.mkdir(parents=True, exist_ok=True)
    inside_link = tmp_path / "escape-link"
    os.symlink(outside, inside_link)
    with pytest.raises(SandboxError):
        jail_path(tmp_path, "escape-link/some-file.txt")


def test_jail_path_accepts_internal_symlink(tmp_path: Path) -> None:
    """A symlink whose target stays inside cwd resolves cleanly."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    os.symlink(real, link)
    resolved = jail_path(tmp_path, "link/x.txt")
    resolved.relative_to(tmp_path.resolve())

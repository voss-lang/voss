"""M9-05 refactor: compute_diff_text returns same body as stderr preview."""
from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.permissions import (
    PermissionGate,
    PermissionStore,
    compute_diff_text,
)


def test_compute_diff_text_fs_write_returns_unified_diff(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    target.write_text("alpha\n")
    diff = compute_diff_text(
        "fs_write", {"path": "x.txt", "content": "beta\n"}, tmp_path
    )
    assert "-alpha" in diff
    assert "+beta" in diff
    assert "a/x.txt" in diff and "b/x.txt" in diff


def test_compute_diff_text_fs_edit_replacement(tmp_path: Path) -> None:
    target = tmp_path / "y.txt"
    target.write_text("hello world\n")
    diff = compute_diff_text(
        "fs_edit",
        {"path": "y.txt", "old": "world", "new": "there"},
        tmp_path,
    )
    assert "-hello world" in diff
    assert "+hello there" in diff


def test_compute_diff_text_empty_when_no_change(tmp_path: Path) -> None:
    target = tmp_path / "z.txt"
    target.write_text("same\n")
    diff = compute_diff_text(
        "fs_write", {"path": "z.txt", "content": "same\n"}, tmp_path
    )
    assert diff == ""


def test_compute_diff_text_empty_when_path_missing(tmp_path: Path) -> None:
    assert compute_diff_text("fs_write", {}, tmp_path) == ""


def test_render_diff_preview_uses_compute_diff_text(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    target = tmp_path / "a.txt"
    target.write_text("old\n")
    gate = PermissionGate(mode="edit", store=PermissionStore(cwd=tmp_path))
    # _render_diff_preview is called inside check(); easier to call directly.
    gate._render_diff_preview(
        "fs_write", {"path": str(target), "content": "new\n"}
    )
    err = capsys.readouterr().err
    assert "diff preview" in err
    assert "-old" in err
    assert "+new" in err

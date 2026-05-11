"""Wave 1 RunRecorder tests (COG-08 mechanical capture, M2-02)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from voss.harness.recorder import RunRecorder


def test_inspect_captures_fs_read() -> None:
    rec = RunRecorder.start()
    rec.observe("fs_read", {"path": "src/a.py"}, "contents", ok=True)
    assert rec.inspected == ["src/a.py"]


def test_change_captures_fs_write() -> None:
    rec = RunRecorder.start()
    rec.observe(
        "fs_write",
        {"path": "out.md", "content": "x"},
        "wrote 1 bytes to out.md",
        ok=True,
    )
    assert rec.changed == ["out.md"]


def test_validation_captures_exit_code() -> None:
    rec = RunRecorder.start()
    rec.observe(
        "shell_run",
        {"cmd": "pytest"},
        "[exit 1]\nfailed assertion",
        ok=True,
    )
    assert rec.validation[0]["exit"] == 1
    assert rec.validation[0]["cmd"] == "pytest"
    summary = rec.validation[0]["summary"]
    assert isinstance(summary, str) and 0 < len(summary) <= 160


def test_failure_captures_tool_error() -> None:
    rec = RunRecorder.start()
    rec.observe(
        "fs_write",
        {"path": "/etc/passwd", "content": "x"},
        "<error: path escapes cwd>",
        ok=False,
    )
    assert rec.failures[0]["tool"] == "fs_write"
    assert "path escapes cwd" in rec.failures[0]["error"]


def test_diff_summary_from_git(git_repo: Path) -> None:
    # Modify README.md after initial commit so `git diff --stat` has content.
    (git_repo / "README.md").write_text("# t\nmodified line\n")
    rec = RunRecorder.start()
    result = rec.finalize(git_repo, cost_usd=0.01)
    assert result.diff_summary, "diff_summary should be non-empty after modification"
    assert "README.md" in result.diff_summary or "file" in result.diff_summary


@pytest.mark.skip(reason="Wave 2 — pending plan M2-03")
def test_decisions_mirror_to_markdown() -> None:
    pass

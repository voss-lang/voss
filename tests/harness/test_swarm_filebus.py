"""Unit tests for the swarm file-bus (R3 A13-format task/result transport).

Covers the round trip the host depends on: write a task file from a Task, then
read it back; parse a hand-authored result file (matching A13-SPEC.md); and the
"not done yet" sentinel where a missing result returns None.
"""
from __future__ import annotations

from pathlib import Path

from voss.harness.swarm_filebus import (
    read_result_file,
    result_exists,
    swarm_dir,
    tasks_dir,
    write_shared_context,
    write_task_file,
)
from voss.harness.swarm_store import Task

SWARM_ID = "swarm-test-1"


def test_write_task_file_roundtrip(tmp_path: Path) -> None:
    task = Task(id="t1", goal="Refactor auth", owned_files=["src/auth/repo.py", "src/auth/svc.py"])

    path = write_task_file(
        tmp_path, SWARM_ID, "builder-1", task, agent="claude", model="opus",
        context="Use the repository pattern.",
    )

    assert path == tasks_dir(tmp_path, SWARM_ID) / "builder-1.task.md"
    text = path.read_text()
    # Frontmatter carries the routing axis; `cli` mirrors `agent` for the A13 reader.
    assert "swarm: swarm-test-1" in text
    assert "agent: claude" in text
    assert "cli: claude" in text
    assert "model: opus" in text
    # Body restates goal, ownedFiles, the supplied context, and the result-write loop.
    assert "Refactor auth" in text
    assert "src/auth/repo.py" in text
    assert "Use the repository pattern." in text
    assert "results/builder-1.result.md" in text


def test_write_shared_context(tmp_path: Path) -> None:
    path = write_shared_context(tmp_path, SWARM_ID, "Monorepo. Python 3.13.")
    assert path == swarm_dir(tmp_path, SWARM_ID) / "shared" / "context.md"
    assert path.read_text() == "Monorepo. Python 3.13."


def test_read_result_file_parses_handwritten(tmp_path: Path) -> None:
    # Author a result file by hand in the EXACT A13-SPEC format.
    results = swarm_dir(tmp_path, SWARM_ID) / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "builder-1.result.md").write_text(
        "---\n"
        "agent: claude\n"
        "status: complete\n"
        'files_modified: ["src/auth/repo.py", "src/auth/svc.py"]\n'
        "duration_secs: 45\n"
        "---\n\n"
        "## Summary\n\n"
        "Refactored auth module to use the repository pattern.\n"
    )

    result = read_result_file(tmp_path, SWARM_ID, "builder-1")

    assert result is not None
    assert result.agent == "claude"
    assert result.status == "complete"
    assert result.files_modified == ["src/auth/repo.py", "src/auth/svc.py"]
    assert result.duration_secs == 45
    assert "repository pattern" in result.summary


def test_read_missing_result_returns_none(tmp_path: Path) -> None:
    assert read_result_file(tmp_path, SWARM_ID, "builder-9") is None
    assert result_exists(tmp_path, SWARM_ID, "builder-9") is False


def test_task_then_result_full_loop(tmp_path: Path) -> None:
    # End-to-end shape: host writes task, member (simulated) writes result, host reads.
    task = Task(id="t2", goal="Add tests", owned_files=["tests/test_x.py"])
    write_task_file(tmp_path, SWARM_ID, "builder-2", task, agent="codex", model="default")
    assert result_exists(tmp_path, SWARM_ID, "builder-2") is False

    (swarm_dir(tmp_path, SWARM_ID) / "results" / "builder-2.result.md").write_text(
        "---\nagent: codex\nstatus: complete\nfiles_modified: [\"tests/test_x.py\"]\n---\n\n"
        "Added coverage for x.\n"
    )
    result = read_result_file(tmp_path, SWARM_ID, "builder-2")
    assert result is not None and result.status == "complete"
    assert result.duration_secs is None  # omitted key → None, not a crash
    assert result.summary == "Added coverage for x."

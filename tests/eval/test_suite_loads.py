"""M5 D-05: suite loader walks task directories in stable order."""
from __future__ import annotations

from pathlib import Path

from voss.eval.suite import load_suite


EXPECTED = {"01-foo", "02-bar", "03-baz"}


def _write_task(root: Path, task_id: str, *, mode: str = "plan") -> None:
    task_dir = root / task_id
    task_dir.mkdir()
    (task_dir / "task.toml").write_text(
        "\n".join(
            [
                f'prompt = "Prompt for {task_id}"',
                f'mode = "{mode}"',
                f'rubric = "PASS if {task_id} works"',
                "",
            ]
        )
    )


def _suite_root(tmp_path: Path) -> Path:
    _write_task(tmp_path, "02-bar")
    _write_task(tmp_path, "01-foo")
    _write_task(tmp_path, "03-baz")
    (tmp_path / "README.md").write_text("# ignored\n")
    (tmp_path / "empty").mkdir()
    return tmp_path


def test_suite_finds_expected_fixtures(tmp_path: Path) -> None:
    tasks = load_suite(_suite_root(tmp_path), suite="")
    ids = [task_id for task_id, _ in tasks]

    assert ids == sorted(EXPECTED)


def test_each_task_parses(tmp_path: Path) -> None:
    tasks = load_suite(_suite_root(tmp_path), suite="")

    for _, spec in tasks:
        assert spec.prompt
        assert spec.rubric
        assert spec.mode in {"plan", "edit", "auto"}

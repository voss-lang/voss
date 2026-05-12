"""M5 D-05: suite loader finds expected fixtures and skips unrelated entries."""
from voss.eval.suite import load_suite


def _write_task(root, task_id, *, mode="plan"):
    task_dir = root / task_id
    task_dir.mkdir()
    (task_dir / "task.toml").write_text(
        f'prompt = "Do {task_id}"\n'
        f'mode = "{mode}"\n'
        f'rubric = "PASS if {task_id} succeeds"\n'
    )


def test_suite_finds_expected_fixtures(tmp_path):
    expected = {"01-foo", "02-bar", "03-baz"}
    for task_id in expected:
        _write_task(tmp_path, task_id)
    (tmp_path / "README.md").write_text("# ignored\n")
    (tmp_path / "empty").mkdir()

    tasks = load_suite(tmp_path, suite="")
    ids = [task_id for task_id, _ in tasks]

    assert ids == sorted(expected)


def test_each_task_parses(tmp_path):
    for task_id in ("01-foo", "02-bar", "03-baz"):
        _write_task(tmp_path, task_id)

    tasks = load_suite(tmp_path, suite="")

    for _, spec in tasks:
        assert spec.prompt
        assert spec.rubric
        assert spec.mode in {"plan", "edit", "auto"}

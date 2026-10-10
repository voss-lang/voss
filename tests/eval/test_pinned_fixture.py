from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from voss.eval import runner
from voss.eval.suite import TaskSpec, load_suite


def spec(**extra) -> TaskSpec:
    return TaskSpec(prompt="x", mode="plan", rubric="...", **extra)


def test_task_spec_accepts_pinned_corpus_and_recall() -> None:
    assert spec().corpus is None
    assert spec().recall is None
    assert spec(corpus="pinned", recall="active").corpus == "pinned"
    for recall in ("off", "shadow", "active"):
        assert spec(recall=recall).recall == recall


@pytest.mark.parametrize("extra", [{"corpus": "repo"}, {"recall": "on"}])
def test_task_spec_rejects_unknown_corpus_or_recall(extra: dict) -> None:
    with pytest.raises(ValidationError):
        spec(**extra)


def test_golden_tasks_still_load() -> None:
    root = Path(__file__).parent / "golden"
    assert all(s.corpus is None and s.recall is None for _, s in load_suite(root))


def test_apply_overrides_validates_through_task_spec() -> None:
    tasks = [("t1", spec(recall="off")), ("t2", spec())]

    applied = runner._apply_overrides(tasks, {"recall": "active"})

    assert [(t, s.recall) for t, s in applied] == [("t1", "active"), ("t2", "active")]
    assert tasks[0][1].recall == "off"
    assert runner._apply_overrides(tasks, None) is tasks
    with pytest.raises(ValidationError):
        runner._apply_overrides(tasks, {"recall": "bogus"})


def test_pinned_fixture_copies_corpus_and_overlay(monkeypatch, tmp_path: Path) -> None:
    pinned = tmp_path / "pinned"
    (pinned / "src").mkdir(parents=True)
    (pinned / "src" / "a.py").write_text("A = 1\n")
    (pinned / ".complete").touch()
    (pinned / runner.PINNED_INDEX_MARKER).touch()
    monkeypatch.setattr(runner, "pinned_corpus", lambda: pinned)
    task_dir = tmp_path / "task"
    (task_dir / "fixture" / "tests").mkdir(parents=True)
    (task_dir / "fixture" / "tests" / "test_a.py").write_text("def test_a(): pass\n")

    cwd = runner._prepare_fixture(task_dir, tmp_path / "run", corpus="pinned")

    assert (cwd / "src" / "a.py").read_text() == "A = 1\n"
    assert (cwd / "tests" / "test_a.py").exists()
    assert not (cwd / ".complete").exists()
    assert not (cwd / runner.PINNED_INDEX_MARKER).exists()
    log = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
    )
    assert log.stdout.strip() == "1"


def test_pinned_fixture_without_overlay(monkeypatch, tmp_path: Path) -> None:
    pinned = tmp_path / "pinned"
    pinned.mkdir()
    (pinned / "a.py").write_text("A = 1\n")
    monkeypatch.setattr(runner, "pinned_corpus", lambda: pinned)

    cwd = runner._prepare_fixture(tmp_path / "task", tmp_path / "run", corpus="pinned")

    assert (cwd / "a.py").exists()


def test_default_corpus_keeps_task_fixture(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner, "pinned_corpus", lambda: pytest.fail("must not materialize"))
    task_dir = tmp_path / "task"
    (task_dir / "fixture").mkdir(parents=True)
    (task_dir / "fixture" / "hello.txt").write_text("hi\n")

    cwd = runner._prepare_fixture(task_dir, tmp_path / "run")

    assert (cwd / "hello.txt").read_text() == "hi\n"


def test_check_env_strips_api_key_and_prefers_eval_python(monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret")

    env = runner._check_env()

    assert "TYPESAFE_API_KEY" not in env
    assert env["PATH"].split(os.pathsep)[0] == os.path.dirname(sys.executable)
    assert os.environ["TYPESAFE_API_KEY"] == "secret"


def test_run_checks_uses_given_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret")
    check = TaskSpec.model_validate(
        {"prompt": "x", "mode": "plan", "rubric": "...",
         "checks": [{"type": "cmd", "run": 'test -z "$TYPESAFE_API_KEY"'}]}
    ).checks

    assert runner._run_checks(check, tmp_path)[0] is False
    assert runner._run_checks(check, tmp_path, env=runner._check_env())[0] is True

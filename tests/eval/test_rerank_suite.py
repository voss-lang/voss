"""J3 D-16: the code-recall-ab suite is pinned, dev-sourced, and has deterministic checks."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from voss.eval import runner
from voss.eval.suite import load_suite, load_task

SUITE = Path(__file__).parent / "code-recall-ab"
QUERIES = Path(__file__).resolve().parents[2] / "evals" / "retrieval" / "queries"
TASK_IDS = sorted(p.name for p in SUITE.iterdir() if (p / "task.toml").exists())


def _group_splits() -> dict[str, set[str]]:
    splits: dict[str, set[str]] = {}
    for path in sorted(QUERIES.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                splits.setdefault(row["group"], set()).add(row["split"])
    return splits


def test_suite_has_thirty_pinned_tasks_with_cmd_checks() -> None:
    tasks = load_suite(SUITE, suite="code-recall-ab")

    assert len(tasks) == 30
    for task_id, spec in tasks:
        assert spec.corpus == "pinned", task_id
        assert spec.recall is None, task_id
        assert any(check.type == "cmd" for check in spec.checks), task_id
        assert not (SUITE / task_id / "fixture").exists(), task_id


def test_sources_map_every_task_to_dev_only_groups() -> None:
    sources = json.loads((SUITE / "SOURCES.json").read_text())
    splits = _group_splits()

    assert sorted(sources) == TASK_IDS
    for task_id, groups in sources.items():
        assert groups, task_id
        for group in groups:
            assert splits.get(group) == {"dev"}, (task_id, group)


@pytest.mark.slow
@pytest.mark.parametrize("task_id", TASK_IDS)
def test_check_fails_untouched_and_passes_with_reference(task_id: str, tmp_path: Path) -> None:
    task_dir = SUITE / task_id
    checks = load_task(task_dir).checks
    cwd = runner._prepare_fixture(task_dir, tmp_path, corpus="pinned")
    final = cwd / ".voss-eval-final.txt"
    final.write_text("")

    assert runner._run_checks(checks, cwd, env=runner._check_env())[0] is False

    if (task_dir / "reference.txt").exists():
        final.write_text((task_dir / "reference.txt").read_text())
    else:
        subprocess.run(["git", "apply", str(task_dir / "reference.patch")], cwd=cwd, check=True)

    assert runner._run_checks(checks, cwd, env=runner._check_env())[0] is True

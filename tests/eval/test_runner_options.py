from __future__ import annotations

import json
from pathlib import Path

from voss.eval import runner
from voss.eval.suite import TaskSpec
from voss_runtime.providers import StubProvider, register


def _write_task(root: Path, task_id: str, task_toml: str) -> None:
    task_dir = root / "tests" / "eval" / "golden" / task_id
    (task_dir / "fixture").mkdir(parents=True)
    (task_dir / "fixture" / "README.md").write_text("# Fixture\n")
    (task_dir / "task.toml").write_text(task_toml)


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_task_model_overrides_runner_model(monkeypatch, tmp_path: Path) -> None:
    _write_task(
        tmp_path,
        "01-model",
        "\n".join(
            [
                'prompt = "Say hello."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                'model = "task-model"',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        runner,
        "_provider_for_eval",
        lambda *, stub, auth_pref: (StubProvider(), None),
    )
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: None)

    runner.run_suite(stub=False, model="runner-model", task="01-model", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["model"] == "task-model"
    assert row["judge_model"] == "task-model"


def test_task_provider_selects_registered_provider() -> None:
    default_provider = StubProvider()
    task_provider = StubProvider(default_response="task-provider")
    register("__eval_task_provider__", task_provider)
    spec = TaskSpec(
        prompt="x",
        mode="plan",
        rubric="...",
        provider="__eval_task_provider__",
    )

    selected = runner._provider_for_task(
        default_provider=default_provider,
        spec=spec,
        stub=False,
    )

    assert selected is task_provider


def test_stub_mode_ignores_task_provider_and_model(monkeypatch, tmp_path: Path) -> None:
    _write_task(
        tmp_path,
        "01-stub",
        "\n".join(
            [
                'prompt = "Say hello."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                'provider = "__eval_task_provider__"',
                'model = "task-model"',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: None)

    runner.run_suite(stub=True, auth_pref="none", task="01-stub", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["model"] == "__stub__"


def test_judge_exception_is_recorded_as_error(monkeypatch, tmp_path: Path) -> None:
    _write_task(
        tmp_path,
        "01-judge",
        "\n".join(
            [
                'prompt = "Say hello."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: StubProvider())

    async def raise_from_judge(**kwargs):
        raise RuntimeError("judge unavailable")

    monkeypatch.setattr(runner, "judge_run", raise_from_judge)

    runner.run_suite(stub=True, auth_pref="none", task="01-judge", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["success"] is None
    assert row["judge_verdict"] == "error"
    assert "judge error: RuntimeError: judge unavailable" in row["judge_rationale"]


def test_live_flag_is_recorded(monkeypatch, tmp_path: Path) -> None:
    _write_task(
        tmp_path,
        "01-live",
        "\n".join(
            [
                'prompt = "Say hello."',
                'mode = "plan"',
                'rubric = "Pass if the run completes."',
                "",
            ]
        ),
    )
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        runner,
        "_provider_for_eval",
        lambda *, stub, auth_pref: (StubProvider(), None),
    )
    monkeypatch.setattr(runner, "_judge_provider_for_eval", lambda *, auth_pref: None)

    runner.run_suite(live=True, task="01-live", out=out)

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["live"] is True

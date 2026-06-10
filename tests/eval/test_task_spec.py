"""M5 D-07: TaskSpec rejects unknown keys; validates mode + judge_inputs."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from voss.eval.suite import CmdCheck, FileContainsCheck, FileExistsCheck, TaskSpec


def test_minimal_spec() -> None:
    spec = TaskSpec(prompt="x", mode="plan", rubric="PASS if ok")

    assert spec.judge_inputs == ["final", "file_diff"]
    assert spec.auto_approve_edits is False


def test_invalid_mode() -> None:
    with pytest.raises(ValidationError):
        TaskSpec(prompt="x", mode="rust", rubric="...")


def test_unknown_key_rejected() -> None:
    """ConfigDict(extra='forbid') guards against task.toml schema drift."""
    with pytest.raises(ValidationError):
        TaskSpec(prompt="x", mode="plan", rubric="...", typo_field=1)


def test_auto_approve_edits_round_trip() -> None:
    spec = TaskSpec(
        prompt="x",
        mode="edit",
        rubric="...",
        auto_approve_edits=True,
    )

    assert spec.auto_approve_edits is True


def test_checks_defaults_empty() -> None:
    spec = TaskSpec.model_validate({"prompt": "x", "mode": "plan", "rubric": "..."})

    assert spec.checks == []


def test_checks_cmd_default_timeout() -> None:
    spec = TaskSpec.model_validate(
        {
            "prompt": "x",
            "mode": "plan",
            "rubric": "...",
            "checks": [{"type": "cmd", "run": "true"}],
        }
    )

    assert len(spec.checks) == 1
    assert isinstance(spec.checks[0], CmdCheck)
    assert spec.checks[0].run == "true"
    assert spec.checks[0].timeout == 60


def test_checks_cmd_custom_timeout() -> None:
    spec = TaskSpec.model_validate(
        {
            "prompt": "x",
            "mode": "plan",
            "rubric": "...",
            "checks": [{"type": "cmd", "run": "true", "timeout": 5}],
        }
    )

    assert isinstance(spec.checks[0], CmdCheck)
    assert spec.checks[0].timeout == 5


def test_checks_file_exists() -> None:
    spec = TaskSpec.model_validate(
        {
            "prompt": "x",
            "mode": "plan",
            "rubric": "...",
            "checks": [{"type": "file_exists", "path": "x"}],
        }
    )

    assert isinstance(spec.checks[0], FileExistsCheck)
    assert spec.checks[0].path == "x"


def test_checks_file_contains() -> None:
    spec = TaskSpec.model_validate(
        {
            "prompt": "x",
            "mode": "plan",
            "rubric": "...",
            "checks": [{"type": "file_contains", "path": "x", "text": "y"}],
        }
    )

    assert isinstance(spec.checks[0], FileContainsCheck)
    assert spec.checks[0].path == "x"
    assert spec.checks[0].text == "y"


def test_checks_bogus_type_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(
            {
                "prompt": "x",
                "mode": "plan",
                "rubric": "...",
                "checks": [{"type": "bogus"}],
            }
        )


def test_checks_extra_key_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(
            {
                "prompt": "x",
                "mode": "plan",
                "rubric": "...",
                "checks": [{"type": "cmd", "run": "true", "extra_key": 1}],
            }
        )


def test_surface_defaults_internal() -> None:
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")

    assert spec.surface == "internal"


def test_surface_cli_do() -> None:
    spec = TaskSpec.model_validate(
        {"prompt": "x", "mode": "plan", "rubric": "...", "surface": "cli:do"}
    )

    assert spec.surface == "cli:do"


def test_surface_invalid_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(
            {"prompt": "x", "mode": "plan", "rubric": "...", "surface": "bogus"}
        )


def test_target_file_defaults_none() -> None:
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")

    assert spec.target_file is None


def test_permission_choice_default_and_deny() -> None:
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")
    assert spec.permission_choice == "a"

    deny = TaskSpec.model_validate(
        {
            "prompt": "x",
            "mode": "plan",
            "rubric": "...",
            "surface": "serve",
            "permission_choice": "d",
        }
    )
    assert deny.permission_choice == "d"

    with pytest.raises(ValidationError):
        TaskSpec.model_validate(
            {"prompt": "x", "mode": "plan", "rubric": "...", "permission_choice": "x"}
        )


def test_target_file_cli_edit() -> None:
    spec = TaskSpec.model_validate(
        {
            "prompt": "x",
            "mode": "edit",
            "rubric": "...",
            "surface": "cli:edit",
            "target_file": "calc.py",
        }
    )

    assert spec.target_file == "calc.py"

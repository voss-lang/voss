"""M5 D-07: TaskSpec rejects unknown keys; validates mode + judge_inputs."""
import pytest
from pydantic import ValidationError

from voss.eval.suite import TaskSpec


def test_minimal_spec():
    spec = TaskSpec(prompt="x", mode="plan", rubric="PASS if ok")
    assert spec.judge_inputs == ["final", "file_diff"]
    assert spec.auto_approve_edits is False


def test_invalid_mode():
    with pytest.raises(ValidationError):
        TaskSpec(prompt="x", mode="rust", rubric="...")


def test_unknown_key_rejected():
    """ConfigDict(extra='forbid') guards against task.toml schema drift."""
    with pytest.raises(ValidationError):
        TaskSpec(prompt="x", mode="plan", rubric="...", typo_field=1)


def test_auto_approve_edits_round_trip():
    spec = TaskSpec(prompt="x", mode="edit", rubric="...", auto_approve_edits=True)
    assert spec.auto_approve_edits is True

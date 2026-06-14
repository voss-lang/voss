from __future__ import annotations

import pytest

from .runner import CliRunner


_NO_STRUCTURED_RUN = """
async def _ambient_complete(**_kwargs):
    raise AssertionError("ambient provider should not be called")

def _boom_run_turn(_cwd):
    raise AssertionError("structured run should not start")

_stub.complete = _ambient_complete
_hcli._resolve_run_turn = _boom_run_turn
"""


_PROMOTED_RUN = """
from voss.harness.agent import Plan, TurnResult

async def _ambient_complete(**_kwargs):
    raise AssertionError("ambient provider should not be called")

async def _fake_run_turn(task, **_kwargs):
    return TurnResult(
        plan=Plan(rationale="promoted", steps=[], confidence=0.9),
        confidence=0.9,
        final="promoted run",
        tool_results=[],
        cost_usd=0.0,
        run=None,
    )

def _resolve_run_turn(_cwd):
    return _fake_run_turn

_stub.complete = _ambient_complete
_hcli._resolve_run_turn = _resolve_run_turn
"""


@pytest.mark.parametrize("args", [(), ("chat", "--plain")])
def test_status_question_does_not_enter_structured_loop(
    tmp_project,
    tmp_path,
    args: tuple[str, ...],
) -> None:
    runner = CliRunner(
        project_root=tmp_project,
        state_home=tmp_path / "_state",
        extra_sitecustomize=_NO_STRUCTURED_RUN,
    )

    result = runner.run(*args, stdin="status\n/exit\n", timeout=20.0)

    assert result.returncode == 0, result.output
    assert "Phase: ambient" in result.output
    assert "structured run should not start" not in result.output
    assert "ambient provider should not be called" not in result.output


@pytest.mark.parametrize("args", [(), ("chat", "--plain")])
def test_work_intent_promotes_to_run_loop(
    tmp_project,
    tmp_path,
    args: tuple[str, ...],
) -> None:
    runner = CliRunner(
        project_root=tmp_project,
        state_home=tmp_path / "_state",
        extra_sitecustomize=_PROMOTED_RUN,
    )

    result = runner.run(*args, stdin="implement ambient routing\n/exit\n", timeout=20.0)

    assert result.returncode == 0, result.output
    assert "promoted run" in result.output
    assert "ambient provider should not be called" not in result.output

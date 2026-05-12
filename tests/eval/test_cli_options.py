from __future__ import annotations

from click.testing import CliRunner

from voss.harness.cli import eval_cmd


def test_eval_help_lists_runner_flags() -> None:
    result = CliRunner().invoke(eval_cmd, ["--help"])

    assert result.exit_code == 0
    for flag in (
        "--suite",
        "--stub",
        "--live",
        "-k",
        "--out",
        "--judge-model",
        "--task",
        "--auth",
    ):
        assert flag in result.output

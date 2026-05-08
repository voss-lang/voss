from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner


def _import_main():
    from voss.cli import main

    return main


def test_root_help_lists_phase5_commands():
    main = _import_main()
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, result.output
        for cmd in ("compile", "run", "check", "init", "ast"):
            assert cmd in result.output
        assert not (Path(fs) / ".voss-cache").exists()


@pytest.mark.parametrize("subcommand", ["compile", "run", "check", "init", "ast"])
def test_subcommand_help_exits_zero(subcommand):
    main = _import_main()
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        result = runner.invoke(main, [subcommand, "--help"])
        assert result.exit_code == 0, result.output
        assert not (Path(fs) / ".voss-cache").exists()


def test_root_version_option_exits_zero():
    main = _import_main()
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0, result.output

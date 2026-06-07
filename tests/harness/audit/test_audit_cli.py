"""V9 RED scaffolds for the ``voss audit`` CLI command (VAUD-01).

Pins ``voss.harness.cli.audit_cmd`` (a click command). Expected RED until
V9-04/V9-06 land. Uses tmp_path; never writes to the real ``.voss/``. No
xfail masking. The audit_cmd import is inside each test so collection
succeeds before the command exists.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.harness.audit.test_o6_fixtures import build_fixture_tree


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    build_fixture_tree(tmp_path)
    return tmp_path


class TestAuditCli:
    def test_exits_0_for_latest(self, fixture_root: Path):
        from voss.harness.cli import audit_cmd

        result = CliRunner().invoke(audit_cmd, ["--cwd", str(fixture_root)])
        assert result.exit_code == 0

    def test_exits_0_for_named_run(self, fixture_root: Path):
        from voss.harness.cli import audit_cmd

        result = CliRunner().invoke(
            audit_cmd, ["root_aabbcc0001", "--cwd", str(fixture_root)]
        )
        assert result.exit_code == 0

    def test_unknown_run_nonzero_with_stderr(self, fixture_root: Path):
        from voss.harness.cli import audit_cmd

        result = CliRunner().invoke(
            audit_cmd, ["nonexistent_run_id", "--cwd", str(fixture_root)]
        )
        assert result.exit_code != 0
        assert "unknown" in result.output.lower()

    def test_traversal_guard(self, fixture_root: Path):
        from voss.harness.cli import audit_cmd

        result = CliRunner().invoke(
            audit_cmd, ["../escape", "--cwd", str(fixture_root)]
        )
        assert result.exit_code != 0

    def test_format_json(self, fixture_root: Path):
        from voss.harness.cli import audit_cmd

        result = CliRunner().invoke(
            audit_cmd, ["--cwd", str(fixture_root), "--format", "json"]
        )
        assert result.exit_code == 0
        json.loads(result.output)  # must parse

    def test_deterministic_output(self, fixture_root: Path):
        from voss.harness.cli import audit_cmd

        r1 = CliRunner().invoke(audit_cmd, ["--cwd", str(fixture_root), "--format", "json"])
        r2 = CliRunner().invoke(audit_cmd, ["--cwd", str(fixture_root), "--format", "json"])
        assert r1.output == r2.output

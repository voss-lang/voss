"""V9 RED scaffolds for sign-off risk forcing (VAUD-SIGNOFF).

Pins ``voss.harness.cli._write_signoff_ack`` (the .signoff-ack.json writer)
and the team_run_cmd acknowledgement gate. Expected RED until V9-06 lands.
Uses tmp_path; never writes to the real ``.voss/``. No xfail masking.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.harness.audit.test_o6_fixtures import build_fixture_tree


class TestAckWriter:
    def test_ack_writer_creates_sidecar(self, tmp_path: Path):
        from voss.harness.cli import _write_signoff_ack

        path = _write_signoff_ack(
            tmp_path, "rootX", killed_count=1, misroute_count=2
        )
        assert path == tmp_path / ".voss" / "sessions" / "rootX" / ".signoff-ack.json"
        data = json.loads(path.read_text())
        assert data["killed_count"] == 1
        assert data["misroute_count"] == 2
        assert "ack_ts" in data
        # 0o600 file mode (owner-only), mirroring _persist_run_final.
        assert (path.stat().st_mode & 0o777) == 0o600

    def test_ack_is_new_file_not_mutation(self, tmp_path: Path):
        from voss.harness.cli import _write_signoff_ack

        # Seed a run-final.json + a node file; the ack write must not touch them.
        build_fixture_tree(tmp_path)
        run_dir = tmp_path / ".voss" / "sessions" / "root_aabbcc0001"
        rf_before = (run_dir / "run-final.json").read_text()
        node_before = (run_dir / "node_done_0001.json").read_text()

        _write_signoff_ack(
            tmp_path, "root_aabbcc0001", killed_count=1, misroute_count=0
        )

        assert (run_dir / "run-final.json").read_text() == rf_before
        assert (run_dir / "node_done_0001.json").read_text() == node_before


class TestAckGate:
    def test_approve_refused_without_ack(self, tmp_path: Path):
        from voss.harness.cli import team_run_cmd

        # When killed/misroute risks exist, a non-"yes" acknowledgement must
        # abort sign-off with a non-zero exit and an acknowledgement message.
        result = CliRunner().invoke(
            team_run_cmd,
            ["build a thing", "--cwd", str(tmp_path)],
            input="no\n",
        )
        assert result.exit_code != 0
        assert "acknowledg" in result.output.lower()

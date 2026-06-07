"""VBOARD-10 `voss board [root_id]` read-only CLI — Wave 0 RED scaffold.

Drives the REAL planned command voss.harness.cli.board_cmd (V5-03), a
read-only renderer over persisted session-tree nodes
(<cwd>/.voss/sessions/<root_id>/<node_id>.json).

RED until V5-03 lands: `board_cmd` does not exist yet. The import is inside
each test method so collection still succeeds (no import-time crash). Node-JSON
fixtures use the REAL persisted shape (transitions / envelope{spent,limit} /
terminal_state). No xfail/skip masking — failures are genuine ImportError.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner


def _write_node(cwd: Path, root_id: str, node_id: str) -> Path:
    """Materialize a minimal persisted node with the real JSON shape."""
    root_dir = cwd / ".voss" / "sessions" / root_id
    root_dir.mkdir(parents=True, exist_ok=True)
    node_path = root_dir / f"{node_id}.json"
    node_path.write_text(json.dumps({
        "id": node_id,
        "root_id": root_id,
        "transitions": [],
        "envelope": {"spent": 0, "limit": 100},
        "terminal_state": None,
    }))
    return node_path


class TestBoardCLI:
    def test_no_sessions_dir_exits_nonzero(self, tmp_path):
        from voss.harness.cli import board_cmd

        result = CliRunner().invoke(board_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code != 0

    def test_unknown_root_exits_nonzero_with_stderr(self, tmp_path):
        from voss.harness.cli import board_cmd

        _write_node(tmp_path, "abc123", "n1")
        result = CliRunner(mix_stderr=False).invoke(
            board_cmd, ["does-not-exist", "--cwd", str(tmp_path)],
        )
        assert result.exit_code != 0
        assert result.stderr  # error message on stderr

    def test_default_latest(self, tmp_path):
        from voss.harness.cli import board_cmd

        _write_node(tmp_path, "abc123", "n1")
        result = CliRunner().invoke(board_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_named_root(self, tmp_path):
        from voss.harness.cli import board_cmd

        _write_node(tmp_path, "abc123", "n1")
        result = CliRunner().invoke(board_cmd, ["abc123", "--cwd", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_default_latest_picks_most_recent(self, tmp_path):
        from voss.harness.cli import board_cmd

        _write_node(tmp_path, "oldroot", "n1")
        newer = _write_node(tmp_path, "newroot", "n2")
        # Bump mtime of the newer root so it is unambiguously most-recent
        # (UUID-hex root ids are not chronologically sortable — V5-RESEARCH
        # Pitfall 3: latest = mtime, not lexical).
        future = os.path.getmtime(newer) + 1000
        os.utime(newer, (future, future))
        os.utime(newer.parent, (future, future))
        result = CliRunner().invoke(board_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "newroot" in result.output

    def test_path_traversal_rejected(self, tmp_path):
        from voss.harness.cli import board_cmd

        _write_node(tmp_path, "abc123", "n1")
        # T-V5-03: a traversal root_id must not escape .voss/sessions/.
        traversal = CliRunner(mix_stderr=False).invoke(
            board_cmd, ["../../etc", "--cwd", str(tmp_path)],
        )
        assert traversal.exit_code != 0
        assert traversal.stderr
        # A root_id containing a path separator is likewise rejected.
        slashed = CliRunner(mix_stderr=False).invoke(
            board_cmd, ["a/b", "--cwd", str(tmp_path)],
        )
        assert slashed.exit_code != 0

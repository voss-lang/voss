"""E2E for `voss sessions` listing.

Covers: empty state, cwd-scoped vs --all legacy XDG merging. Sessions are
written directly to the filesystem (not via the CLI, because `voss do` does
not persist today) so the test exercises only the listing path.
"""
from __future__ import annotations

import json
from pathlib import Path

from .runner import CliRunner


def _write_session(dir_path: Path, sid: str, name: str, cwd: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / f"{sid}.json").write_text(
        json.dumps(
            {
                "id": sid,
                "name": name,
                "cwd": cwd,
                "model": "claude-test",
                "started_at": "2026-05-10T00:00:00+00:00",
                "updated_at": "2026-05-10T00:00:00+00:00",
                "total_cost_usd": 0.0,
                "turns": [],
                "runs": [],
            }
        )
    )


def test_sessions_empty(cli_runner: CliRunner) -> None:
    r = cli_runner.run("sessions")
    assert r.returncode == 0, r.output
    assert "(no sessions)" in r.stdout


def test_sessions_lists_cwd_scoped(cli_runner: CliRunner) -> None:
    sessions_dir = cli_runner.project_root / ".voss" / "sessions"
    _write_session(
        sessions_dir, "abc12345def0", "session-abc", str(cli_runner.project_root)
    )
    r = cli_runner.run("sessions")
    assert r.returncode == 0, r.output
    assert "abc12345" in r.stdout, r.stdout
    assert "claude-test" in r.stdout


def test_sessions_all_includes_legacy(cli_runner: CliRunner, tmp_path: Path) -> None:
    """`voss sessions --all` merges in legacy XDG-state sessions."""
    legacy_dir = (
        Path(cli_runner.env()["XDG_STATE_HOME"]) / "voss" / "sessions"
    )
    _write_session(legacy_dir, "leg12345abcd", "legacy-one", str(tmp_path))

    r_default = cli_runner.run("sessions")
    assert "leg12345" not in r_default.stdout, r_default.stdout

    r_all = cli_runner.run("sessions", "--all")
    assert r_all.returncode == 0, r_all.output
    assert "leg12345" in r_all.stdout, r_all.stdout
    assert "[legacy]" in r_all.stdout, r_all.stdout

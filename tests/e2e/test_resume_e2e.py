"""E2E for `voss resume <session>`.

Strategy: write a session JSON directly (since `voss do` doesn't persist),
then resume by id-prefix + drive REPL via stdin `/exit\\n`. Verify the
"resumed: …" line confirms history was hydrated.

Failure path: resume with a bogus id exits 1 with a clear stderr message.
"""
from __future__ import annotations

import json
from pathlib import Path

from .runner import CliRunner


def _seed_session(project: Path, sid: str, turns: list[dict]) -> Path:
    sessions_dir = project / ".voss" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{sid}.json"
    path.write_text(
        json.dumps(
            {
                "id": sid,
                "name": "round-trip",
                "cwd": str(project),
                "model": "claude-test",
                "started_at": "2026-05-10T00:00:00+00:00",
                "updated_at": "2026-05-10T00:00:00+00:00",
                "total_cost_usd": 0.0,
                "turns": turns,
                "runs": [],
            }
        )
    )
    return path


def test_resume_hydrates_prior_turns(cli_runner: CliRunner) -> None:
    sid = "rt12345abc01"
    _seed_session(
        cli_runner.project_root,
        sid,
        turns=[
            {"role": "user", "content": "first task"},
            {"role": "assistant", "content": "first response"},
        ],
    )
    # /exit immediately so the REPL closes after hydration.
    r = cli_runner.run("resume", sid, stdin="/exit\n", timeout=20.0)
    assert r.returncode == 0, r.output
    assert "resumed: round-trip" in r.stdout, r.stdout
    assert "2 prior turns" in r.stdout, r.stdout


def test_resume_accepts_id_prefix(cli_runner: CliRunner) -> None:
    sid = "abcdef123456"
    _seed_session(cli_runner.project_root, sid, turns=[])
    r = cli_runner.run("resume", "abcdef", stdin="/exit\n", timeout=20.0)
    assert r.returncode == 0, r.output


def test_resume_missing_id_exits_1(cli_runner: CliRunner) -> None:
    r = cli_runner.run("resume", "deadbeef", stdin="/exit\n", timeout=10.0)
    assert r.returncode == 1, r.output
    assert "resume failed" in r.stderr.lower(), r.stderr

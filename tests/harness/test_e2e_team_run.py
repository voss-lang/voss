"""V10 RED scaffold — e2e `voss team run` on a V10 .voss/team.voss (VLANG-08).

Writes a V10-grammar team file (principles + gate + memory blocks the grammar
does not parse yet), runs the deterministic stub stack via team_run_cmd, and
expects a clean completion + sign-off. RED today: the new blocks fail to parse
(exit 2). No expected-fail/skip masks (gsd-scaffold-fictional-api).
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from voss.harness.cli import team_check_cmd, team_run_cmd
from voss.harness import team as team_mod

_TEAM_VOSS = """# .voss/team.voss — V10 end-to-end example
team Engineering {
  ceiling {
    budget: 200000 tokens
    scope: "src/**"
    latency: 3600s
  }

  principles {
    diff: "Make the smallest diff that solves the task."
    evidence: "No factual claim without evidence."
  }

  gate done {
    require tests_passed
    require independent_review
    require evidence_refs
  }

  memory {
    decisions: ".voss/decisions"
    sessions: ".voss/sessions"
    semantic: ".voss-cache/semantic"
  }

  roster engineers {
    backend {
      model: "cheap"
      scope: "src/**"
      tools: ["fs_read", "code"]
    }
    reviewer {
      model: "strong"
      scope: "src/**"
      tools: ["fs_read", "git"]
    }
  }
}
"""


def test_team_run_completes_on_stub(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VOSS_HERMETIC", "1")
    captured: dict = {}
    real_compile = team_mod.compile_team

    def capture_compile(decl, *, cwd=None):
        captured["cwd"] = cwd
        return real_compile(decl, cwd=cwd)

    monkeypatch.setattr(team_mod, "compile_team", capture_compile)
    (tmp_path / ".voss").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".voss" / "team.voss").write_text(_TEAM_VOSS, encoding="utf-8")

    result = CliRunner().invoke(
        team_run_cmd,
        ["ship a small feature", "--cwd", str(tmp_path)],
        input="approve\n",
    )
    assert result.exit_code == 0, result.output
    assert "run complete" in result.output
    assert "sign-off recorded: approve" in result.output
    assert captured["cwd"] == tmp_path.resolve()


def test_team_check_passes_on_v10_file(tmp_path: Path) -> None:
    # The same V10 team file passes the semantic-validation verb (voss team check).
    (tmp_path / ".voss").mkdir(parents=True, exist_ok=True)
    team_file = tmp_path / ".voss" / "team.voss"
    team_file.write_text(_TEAM_VOSS, encoding="utf-8")
    result = CliRunner().invoke(team_check_cmd, [str(team_file)])
    assert result.exit_code == 0, result.output

"""CLI tests for `voss team check` (VTEAM-10).

Thin wrapper over compile_team: valid -> exit 0 + roster/ceiling summary;
invalid -> exit 1 + first error; missing file -> non-zero + clear message;
--json -> parseable {"ok": ...} object.
"""

from __future__ import annotations

import json

import click
import pytest
from click.testing import CliRunner

from voss.harness import cli

_VALID = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { budget: 50 tokens, scope: "src/api/**", tools: ["fs"] }
  }
}
'''

# role budget over the ceiling -> VossTeamConfigError naming 200 and 100.
_INVALID = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { budget: 200 tokens, scope: "src/api/**", tools: ["fs"] }
  }
}
'''


@pytest.fixture()
def root() -> click.Group:
    g = click.Group("voss")
    cli.register(g)
    return g


def _write(tmp_path, src: str):
    d = tmp_path / ".voss"
    d.mkdir()
    f = d / "team.voss"
    f.write_text(src, encoding="utf-8")
    return f


def test_valid_exits_zero_with_summary(root, tmp_path) -> None:
    f = _write(tmp_path, _VALID)
    res = CliRunner().invoke(root, ["team", "check", str(f)])
    assert res.exit_code == 0, res.output
    assert "PASS" in res.output
    assert "backend" in res.output
    assert "100" in res.output  # ceiling budget


def test_invalid_exits_one_with_error(root, tmp_path) -> None:
    f = _write(tmp_path, _INVALID)
    res = CliRunner().invoke(root, ["team", "check", str(f)])
    assert res.exit_code == 1
    assert "200" in res.stderr and "100" in res.stderr


def test_missing_file_exits_nonzero(root, tmp_path) -> None:
    missing = tmp_path / ".voss" / "team.voss"  # not created
    res = CliRunner().invoke(root, ["team", "check", str(missing)])
    assert res.exit_code != 0
    assert "not found" in res.stderr


def test_json_valid_emits_ok_true(root, tmp_path) -> None:
    f = _write(tmp_path, _VALID)
    res = CliRunner().invoke(root, ["team", "check", "--json", str(f)])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["ok"] is True
    assert payload["team"] == "Eng"
    assert isinstance(payload["roster"], list)
    assert "backend" in payload["roster"]
    assert payload["ceiling"]["budget_tokens"] == 100


def test_team_group_registered() -> None:
    assert any(getattr(c, "name", None) == "team" for c in cli.AGENT_COMMANDS)

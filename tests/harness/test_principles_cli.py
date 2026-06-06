"""V2-03: `voss principles show` (+ --json) CLI (VPRIN-07)."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from voss.harness.cli import AGENT_COMMANDS, principles_group


def _run(args: list[str]):
    return CliRunner().invoke(principles_group, args)


def _write(cwd: Path, text: str) -> None:
    (cwd / ".voss").mkdir(parents=True, exist_ok=True)
    (cwd / ".voss" / "principles.yml").write_text(text, encoding="utf-8")


_DEFAULT_KEYS = ["diff", "evidence", "tests", "scope", "review", "reversibility"]


def test_registered_in_agent_commands() -> None:
    assert principles_group in AGENT_COMMANDS


def test_no_file_six_defaults(tmp_path: Path) -> None:
    res = _run(["show", "--cwd", str(tmp_path)])
    assert res.exit_code == 0, res.output
    for k in _DEFAULT_KEYS:
        assert k in res.output
    assert "[default]" in res.output
    assert "[project]" not in res.output


def test_add_key_shows_project_source(tmp_path: Path) -> None:
    _write(tmp_path, 'bias: "Prefer boring tech."\n')
    res = _run(["show", "--cwd", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert "bias" in res.output
    assert "[project]" in res.output


def test_override_shows_project_string(tmp_path: Path) -> None:
    _write(tmp_path, 'tests: "Custom tests rule."\n')
    res = _run(["show", "--cwd", str(tmp_path)])
    assert "Custom tests rule." in res.output


def test_disable_omits_scope(tmp_path: Path) -> None:
    _write(tmp_path, "disable: [scope]\n")
    res = _run(["show", "--cwd", str(tmp_path)])
    # scope key should not be listed as its own principle line
    assert not any(
        line.startswith("scope ") or line.startswith("scope\t") or line.strip().startswith("scope  ")
        for line in res.output.splitlines()
    )


def test_json_shape(tmp_path: Path) -> None:
    _write(tmp_path, 'bias: "Prefer boring tech."\n')
    res = _run(["show", "--cwd", str(tmp_path), "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert isinstance(data, list)
    keys = {d["key"]: d["source"] for d in data}
    assert keys["diff"] == "default"
    assert keys["bias"] == "project"
    for d in data:
        assert set(d) == {"key", "text", "source"}


def test_malformed_file_nonzero(tmp_path: Path) -> None:
    _write(tmp_path, "tests: 5\n")  # non-string value
    res = _run(["show", "--cwd", str(tmp_path)])
    assert res.exit_code != 0
    assert "error" in res.output.lower()

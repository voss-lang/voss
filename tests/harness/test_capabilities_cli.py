"""V1-02: `voss capabilities list|inspect` (CAP-04/05)."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from voss.harness.cli import capabilities_group
from voss.harness.tools import CAPABILITY_GROUPS


def _run(args: list[str]):
    return CliRunner().invoke(capabilities_group, args)


def test_list_human_grouped(tmp_path: Path) -> None:
    res = _run(["list", "--cwd", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert "fs:" in res.output  # group header
    assert "fs_write" in res.output


def test_list_json_shape(tmp_path: Path) -> None:
    res = _run(["list", "--cwd", str(tmp_path), "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert isinstance(data, dict)
    assert set(data).issubset(set(CAPABILITY_GROUPS))
    assert "fs_write" in data["fs"]
    assert data["fs"] == sorted(data["fs"])  # sorted names


def test_inspect_json(tmp_path: Path) -> None:
    res = _run(["inspect", "fs_write", "--cwd", str(tmp_path), "--json"])
    assert res.exit_code == 0, res.output
    cap = json.loads(res.output)
    assert cap["is_mutating"] is True
    assert cap["group"] == "fs"
    assert "input_schema" in cap
    assert "audit_behavior" in cap
    assert cap["scope_requirements"] == ["fs"]


def test_inspect_human(tmp_path: Path) -> None:
    res = _run(["inspect", "fs_write", "--cwd", str(tmp_path)])
    assert res.exit_code == 0, res.output
    assert "fs_write" in res.output
    assert "group" in res.output
    assert "audit_behavior" in res.output


def test_inspect_unknown_errors(tmp_path: Path) -> None:
    res = _run(["inspect", "bogus_capability", "--cwd", str(tmp_path)])
    assert res.exit_code != 0
    assert "unknown capability" in res.output


def test_registered_in_main_cli() -> None:
    from voss.harness.cli import AGENT_COMMANDS

    assert capabilities_group in AGENT_COMMANDS


def test_help_labels_capabilities_as_static_registry() -> None:
    res = _run(["--help"])
    assert res.exit_code == 0, res.output
    assert "static project capability registry" in res.output
    assert "does not open MCP sessions" in res.output

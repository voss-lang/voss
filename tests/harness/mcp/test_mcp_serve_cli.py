"""M12-04: CliRunner-level surface tests for `voss mcp serve`.

Surface checks only — no actual stdio server loop (that's M12-05's e2e
subprocess concern).
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from voss.harness.cli import mcp_group


def test_mode_required_when_omitted() -> None:
    result = CliRunner().invoke(mcp_group, ["serve"])
    assert result.exit_code != 0
    combined = result.output + (result.stderr if result.stderr_bytes else "")
    assert "--mode" in combined or "Missing option" in combined


def test_mode_rejects_invalid_value() -> None:
    result = CliRunner().invoke(mcp_group, ["serve", "--mode", "yolo"])
    assert result.exit_code != 0
    assert "yolo" in result.output or "Invalid value" in result.output


def test_help_documents_cost_attribution() -> None:
    result = CliRunner().invoke(mcp_group, ["serve", "--help"])
    assert result.exit_code == 0
    out = result.output
    assert "REQUIRED" in out
    assert "plan" in out
    assert "auto" in out
    assert "SERVER's configured LLM provider" in out


def test_help_mentions_three_modes() -> None:
    out = CliRunner().invoke(mcp_group, ["serve", "--help"]).output
    assert "plan" in out and "edit" in out and "auto" in out


def test_serve_is_sibling_of_list_and_call() -> None:
    assert {"list", "call", "serve"} <= set(mcp_group.commands.keys())


def test_malformed_mcp_yaml_exits_nonzero(tmp_path: Path) -> None:
    (tmp_path / ".voss").mkdir()
    (tmp_path / ".voss" / "mcp.yml").write_text("this is not yaml: [unclosed")
    result = CliRunner().invoke(
        mcp_group, ["serve", "--mode", "plan", "--cwd", str(tmp_path)]
    )
    assert result.exit_code != 0
    combined = result.output + (result.stderr if result.stderr_bytes else "")
    assert "mcp config" in combined

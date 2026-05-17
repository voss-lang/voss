"""Wave 0 scaffold for NET-03a mcp config loader. Bodies land in T3-07."""

from __future__ import annotations

import pytest

from voss.harness.mcp.config import McpConfigError, load_mcp_config, substitute_server


def test_loader_parses_fixture(tmp_path) -> None:
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir()
    (voss_dir / "mcp.yml").write_text(
        "servers:\n"
        "  filesystem:\n"
        "    command: [npx, '-y', '@modelcontextprotocol/server-filesystem', '{cwd}']\n"
        "    timeout_s: 30.0\n"
    )

    config = load_mcp_config(tmp_path)

    assert config is not None
    assert "filesystem" in config.servers
    assert config.servers["filesystem"].command == [
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "{cwd}",
    ]
    assert config.servers["filesystem"].timeout_s == 30.0


def test_loader_returns_none_when_absent(tmp_path) -> None:
    assert load_mcp_config(tmp_path) is None


def test_var_substitution_raises_on_unset(tmp_path, monkeypatch) -> None:
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir()
    (voss_dir / "mcp.yml").write_text(
        "servers:\n"
        "  test:\n"
        "    command: [echo, '${VOSS_TEST_TOKEN}']\n"
    )
    monkeypatch.delenv("VOSS_TEST_TOKEN", raising=False)

    config = load_mcp_config(tmp_path)
    assert config is not None
    with pytest.raises(McpConfigError, match="VOSS_TEST_TOKEN"):
        substitute_server(config.servers["test"], cwd=tmp_path)

    monkeypatch.setenv("VOSS_TEST_TOKEN", "abc")
    result = substitute_server(config.servers["test"], cwd=tmp_path)
    assert "abc" in result.command


def test_cwd_substitution(tmp_path) -> None:
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir()
    (voss_dir / "mcp.yml").write_text(
        "servers:\n"
        "  test:\n"
        "    command: [echo, '{cwd}']\n"
    )

    config = load_mcp_config(tmp_path)

    assert config is not None
    result = substitute_server(config.servers["test"], cwd=tmp_path)
    assert result.command[1] == str(tmp_path)

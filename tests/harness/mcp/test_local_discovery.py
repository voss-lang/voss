from __future__ import annotations

import json
import sys
import asyncio

import pytest
from click.testing import CliRunner

from voss.harness import local_sources
from voss.harness.cli import mcp_list_cmd
from voss.harness.mcp.config import load_mcp_config, substitute_server
from voss.harness.mcp.client import McpClient
from voss.harness.mcp.registry import register_mcp_tools
from .test_mcp_client import MOCK_SERVER_SRC


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def test_discovery_precedence_and_disabled_servers(tmp_path):
    write(local_sources.user_home() / ".claude.json", json.dumps({
        "mcpServers": {"shared": {"command": "claude"}, "claude": {"command": "claude"}},
        "projects": {str(tmp_path): {"mcpServers": {"project": {"command": "local"}}}},
    }))
    write(local_sources.codex_home() / "config.toml", '''
[mcp_servers.shared]
command = "codex"
[mcp_servers.disabled]
enabled = false
command = "never"
''')
    write(tmp_path / ".mcp.json", '{"mcpServers":{"shared":{"command":"project"}}}')
    write(tmp_path / ".voss" / "mcp.yml", "servers:\n  shared:\n    command: [voss]\n  claude:\n    enabled: false\n")

    config = load_mcp_config(tmp_path)

    assert set(config.servers) == {"shared", "project"}
    assert config.servers["shared"].command == ["voss"]
    assert config.servers["project"].command == ["local"]


def test_imported_env_cwd_headers_and_tool_filters(tmp_path, monkeypatch):
    write(local_sources.codex_home() / "config.toml", '''
[mcp_servers.remote]
url = "https://example.test/mcp"
bearer_token_env_var = "TEST_TOKEN"
enabled_tools = ["read"]
disabled_tools = ["write"]
[mcp_servers.remote.env_http_headers]
X-Account = "TEST_ACCOUNT"
[mcp_servers.local]
command = "python"
args = ["server.py"]
cwd = "{cwd}"
env_vars = ["TEST_TOKEN"]
[mcp_servers.local.env]
TEST_VALUE = "${TEST_VALUE}"
''')
    monkeypatch.setenv("TEST_VALUE", "synthetic")

    config = load_mcp_config(tmp_path)
    server = substitute_server(config.servers["local"], cwd=tmp_path)

    assert server.env == {"TEST_VALUE": "synthetic"}
    assert server.cwd == str(tmp_path)
    assert server.env_vars == ["TEST_TOKEN"]
    assert config.servers["remote"].env_headers == {"X-Account": "TEST_ACCOUNT"}
    assert config.servers["remote"].enabled_tools == ["read"]
    assert config.servers["remote"].disabled_tools == ["write"]


def test_configured_inventory_never_launches_or_prints_arguments(tmp_path):
    marker = tmp_path / "launched"
    write(tmp_path / ".mcp.json", json.dumps({"mcpServers": {"test": {
        "command": sys.executable,
        "args": ["-c", f"open({str(marker)!r}, 'w').close()", "synthetic-secret"],
    }}}))

    result = CliRunner().invoke(mcp_list_cmd, ["--cwd", str(tmp_path), "--configured", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["servers"][0]["source"] == "claude"
    assert "synthetic-secret" not in result.output
    assert not marker.exists()


def test_malformed_source_does_not_hide_valid_voss_config(tmp_path):
    write(local_sources.codex_home() / "config.toml", 'invalid = "synthetic-secret')
    write(tmp_path / ".voss" / "mcp.yml", "servers:\n  local:\n    command: [echo]\n")

    with pytest.warns(UserWarning) as warnings:
        config = load_mcp_config(tmp_path)

    assert list(config.servers) == ["local"]
    assert "synthetic-secret" not in str(warnings[0].message)


def test_claude_disabled_project_server_can_be_overridden_by_voss(tmp_path):
    write(local_sources.user_home() / ".claude.json", json.dumps({
        "mcpServers": {"shared": {"command": "claude"}},
        "projects": {str(tmp_path): {"disabledMcpServers": ["shared"]}},
    }))
    assert load_mcp_config(tmp_path) is None
    write(tmp_path / ".voss/mcp.yml", "servers:\n  shared:\n    command: [voss]\n")
    assert load_mcp_config(tmp_path).servers["shared"].command == ["voss"]


def test_imported_tool_filters_are_enforced(tmp_path):
    write(local_sources.codex_home() / "config.toml", '''
[mcp_servers.local]
command = "mock"
enabled_tools = ["read", "write"]
disabled_tools = ["write"]
''')
    config = load_mcp_config(tmp_path)
    client = McpClient(config)
    client._tools_cache["local"] = [{"name": name} for name in ("read", "write", "delete")]
    assert list(register_mcp_tools(config, {}, client)) == ["local__read"]


def mock_project(tmp_path):
    script = tmp_path / "mcp_server.py"
    script.write_text(MOCK_SERVER_SRC)
    write(tmp_path / ".mcp.json", json.dumps({"mcpServers": {"local": {
        "command": sys.executable, "args": ["-u", str(script)],
    }}}))
    write(tmp_path / ".agents/skills/review/SKILL.md", "---\nname: review\ndescription: Review changes\n---\nRead the diff.")


def test_cli_tools_work_across_turn_event_loops(tmp_path, monkeypatch):
    from voss.harness.cli import _run_turn_with_teardown
    from voss.harness.tools import make_toolset

    mock_project(tmp_path)
    processes = []
    original = McpClient.ensure_launched

    async def capture(self, name):
        proc = await original(self, name)
        processes.append(proc)
        return proc

    monkeypatch.setattr(McpClient, "ensure_launched", capture)
    tools = make_toolset(tmp_path, net=object(), background_indexing=False)

    async def turn():
        assert await tools["local__read_text_file"].invoke_dict({}) == "mock-result"
        assert "Read the diff" in await tools["skill_read"].invoke(name="review")

    for _ in range(2):
        asyncio.run(_run_turn_with_teardown(turn(), None, tools=tools, cwd=tmp_path))
        assert all(proc.returncode is not None for proc in processes)


@pytest.mark.asyncio
async def test_server_turn_receives_imported_tools_and_closes_connections(tmp_path, monkeypatch):
    from voss.harness.server import app as appmod
    from voss.harness.agent import Plan, TurnResult

    mock_project(tmp_path)
    processes = []
    original = McpClient.ensure_launched

    async def capture(self, name):
        proc = await original(self, name)
        processes.append(proc)
        return proc

    calls = []

    async def run_turn(text, *, tools, **kwargs):
        calls.append(await tools["local__read_text_file"].invoke_dict({}))
        assert "Read the diff" in await tools["skill_read"].invoke(name="review")
        return TurnResult(plan=Plan(rationale="done", steps=[], confidence=1),
                          final="done", confidence=1, tool_results=[], cost_usd=0, run=None)

    monkeypatch.setattr(McpClient, "ensure_launched", capture)
    monkeypatch.setattr(appmod, "run_turn", run_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda *args: None)
    session = appmod.create_app("test-token").state.sessions.create(cwd=tmp_path, model="test", provider=object())

    await appmod._run_turn(session, "review the open PR", "plan")

    assert calls == ["mock-result"]
    assert all(proc.returncode is not None for proc in processes)

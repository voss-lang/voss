"""Wave 0 scaffold for NET-04 mcp scope gating. Bodies land in T3-07."""

from __future__ import annotations

import asyncio
import sys
import textwrap
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from voss.harness import lifecycle
from voss.harness.cognition_schemas import PermissionsConfig
from voss.harness.mcp.config import McpConfig, McpServerConfig
from voss.harness.mcp.registry import register_mcp_tools
from voss.harness.tools import make_toolset


def test_default_plan_scope() -> None:
    assert PermissionsConfig.model_validate({}).mcp == {}
    assert PermissionsConfig.model_validate({"mcp": {"filesystem": "plan"}}).mcp == {
        "filesystem": "plan"
    }


def test_edit_scope() -> None:
    assert PermissionsConfig.model_validate({"mcp": {"filesystem": "edit"}}).mcp == {
        "filesystem": "edit"
    }
    with pytest.raises(ValidationError):
        PermissionsConfig.model_validate({"mcp": {"filesystem": "delete"}})

    config = PermissionsConfig.model_validate(
        {"tool_policy": {"allow": [], "deny": []}, "mcp": {"x": "auto"}}
    )
    assert config.tool_policy.allow == []
    assert config.tool_policy.deny == []
    assert config.mcp == {"x": "auto"}


class FakeMcpClient:
    def __init__(self, tools: list[dict] | None = None) -> None:
        self._tools_cache = {
            "filesystem": tools
            or [
                {
                    "name": "read_text_file",
                    "description": "Read",
                    "inputSchema": {"type": "object"},
                    "annotations": {
                        "readOnlyHint": True,
                        "destructiveHint": False,
                    },
                },
                {
                    "name": "write_file",
                    "description": "Write",
                    "inputSchema": {"type": "object"},
                    "annotations": {
                        "readOnlyHint": False,
                        "destructiveHint": True,
                    },
                },
            ]
        }

    async def call_tool(self, server: str, tool: str, args: dict) -> dict:
        return {
            "content": [{"type": "text", "text": f"{server}:{tool}:ok"}],
            "isError": False,
        }


def _config() -> McpConfig:
    return McpConfig(
        servers={"filesystem": McpServerConfig(command=["mock-server"])}
    )


@pytest.mark.asyncio
async def test_scope_denial() -> None:
    entries = register_mcp_tools(_config(), {}, FakeMcpClient())

    assert entries["filesystem__write_file"].is_mutating is False
    result = await entries["filesystem__write_file"].invoke_dict({"path": "x"})

    assert result == (
        "<error: denied by mcp scope: filesystem at plan, requires edit>"
    )


@pytest.mark.asyncio
async def test_auto_does_not_override_scope() -> None:
    entries = register_mcp_tools(
        _config(), {"filesystem": "plan"}, FakeMcpClient()
    )

    result = await entries["filesystem__write_file"].invoke_dict({})

    assert result == (
        "<error: denied by mcp scope: filesystem at plan, requires edit>"
    )


def test_destructive_hint_absent_defaults_to_true() -> None:
    client = FakeMcpClient(
        [
            {
                "name": "unknown_risk",
                "description": "No annotations",
                "inputSchema": {"type": "object"},
            }
        ]
    )
    entries = register_mcp_tools(_config(), {"filesystem": "edit"}, client)

    assert entries["filesystem__unknown_risk"].is_mutating is True


def test_make_toolset_merges_mcp_tools(tmp_path: Path) -> None:
    script = tmp_path / "mock_mcp.py"
    script.write_text(
        textwrap.dedent(
            """
            import json
            import sys

            req = json.loads(sys.stdin.readline())
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0",
                "id": req["id"],
                "result": {"protocolVersion": "2025-11-25", "capabilities": {}},
            }) + "\\n")
            sys.stdout.flush()
            sys.stdin.readline()
            req = json.loads(sys.stdin.readline())
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0",
                "id": req["id"],
                "result": {"tools": [{
                    "name": "read_text_file",
                    "description": "Read text",
                    "inputSchema": {"type": "object"},
                    "annotations": {"destructiveHint": False},
                }]},
            }) + "\\n")
            sys.stdout.flush()
            sys.stdin.read()
            """
        )
    )
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir()
    (voss_dir / "mcp.yml").write_text(
        yaml.safe_dump(
            {
                "servers": {
                    "mock": {
                        "command": [sys.executable, "-u", str(script)],
                    }
                }
            }
        )
    )

    try:
        tools = make_toolset(tmp_path, net=object())  # type: ignore[arg-type]
        entry = tools["mock__read_text_file"]
        assert entry.is_network is True
        assert entry.is_mutating is False
    finally:
        asyncio.run(lifecycle.reap_all())
        lifecycle.reset_for_tests()

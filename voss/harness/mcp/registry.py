"""Register MCP-discovered tools as harness ToolEntry records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from voss.harness.tools import ToolEntry
from voss_runtime import ToolDescriptor

if TYPE_CHECKING:
    from voss.harness.mcp.client import McpClient
    from voss.harness.mcp.config import McpConfig


def _is_mutating_from_descriptor(tool: dict[str, Any], scope: str) -> bool:
    """Map MCP destructiveHint into ToolEntry.is_mutating for a server scope."""

    if scope == "plan":
        return False
    annotations = tool.get("annotations") or {}
    return bool(annotations.get("destructiveHint", True))


def _first_text_content(result: dict[str, Any]) -> str:
    content = result.get("content", [])
    if not isinstance(content, list):
        return ""
    texts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            texts.append(str(item.get("text", "")))
    return "\n".join(texts)


def _make_mcp_descriptor(
    server_name: str,
    tool_name: str,
    tool_metadata: dict[str, Any],
    mcp_client: "McpClient",
    scope: str,
) -> ToolDescriptor:
    annotations = tool_metadata.get("annotations") or {}
    is_destructive = bool(annotations.get("destructiveHint", True))

    async def invoke(**kwargs: Any) -> str:
        if scope == "plan" and is_destructive:
            return (
                f"<error: denied by mcp scope: {server_name} "
                "at plan, requires edit>"
            )
        result = await mcp_client.call_tool(server_name, tool_name, kwargs)
        if result.get("isError"):
            return _first_text_content(result) or "<error: mcp tool: unknown>"
        return _first_text_content(result)

    return ToolDescriptor(
        name=f"{server_name}__{tool_name}",
        description=str(tool_metadata.get("description", "")),
        parameters=tool_metadata.get("inputSchema", {"type": "object"}),
        func=invoke,
    )


def register_mcp_tools(
    config: "McpConfig",
    permissions_mcp: dict[str, str],
    mcp_client: "McpClient",
) -> dict[str, ToolEntry]:
    """Wrap cached MCP tools as namespaced read/network harness tools."""

    entries: dict[str, ToolEntry] = {}
    for server_name in config.servers:
        scope = permissions_mcp.get(server_name, "plan")
        tools = mcp_client._tools_cache.get(server_name, [])
        for tool in tools:
            tool_name = str(tool["name"])
            descriptor = _make_mcp_descriptor(
                server_name, tool_name, tool, mcp_client, scope
            )
            entries[descriptor.name] = ToolEntry(
                descriptor=descriptor,
                is_mutating=_is_mutating_from_descriptor(tool, scope),
                is_network=True,
            )
    return entries

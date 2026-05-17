"""Public MCP harness package surface."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from voss.harness.mcp.config import (
    McpConfig,
    McpConfigError,
    McpServerConfig,
    load_mcp_config,
    substitute_server,
)

if TYPE_CHECKING:
    from voss.harness.mcp.client import McpClient
    from voss.harness.mcp.registry import register_mcp_tools

__all__ = [
    "McpServerConfig",
    "McpConfig",
    "load_mcp_config",
    "substitute_server",
    "McpConfigError",
    "McpClient",
    "register_mcp_tools",
]


def __getattr__(name: str) -> Any:
    if name == "McpClient":
        from voss.harness.mcp.client import McpClient

        return McpClient
    if name == "register_mcp_tools":
        from voss.harness.mcp.registry import register_mcp_tools

        return register_mcp_tools
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

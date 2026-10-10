"""Streamable HTTP transport for MCP JSON-RPC requests."""
from __future__ import annotations

import json
import os

import httpx

from .config import McpConfigError, McpServerConfig


class HttpConnection:
    def __init__(self, server: McpServerConfig) -> None:
        headers = {"Accept": "application/json, text/event-stream", **server.headers}
        for name, variable in server.env_headers.items():
            if variable not in os.environ:
                raise McpConfigError(f"required env var {variable!r} is unset")
            headers[name] = os.environ[variable]
        if server.bearer_token_env_var:
            token = os.environ.get(server.bearer_token_env_var)
            if not token:
                raise McpConfigError(f"required env var {server.bearer_token_env_var!r} is unset")
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.AsyncClient(headers=headers, timeout=server.timeout_s)
        self.url = server.url
        self.response: dict | None = None

    async def write(self, message: dict) -> None:
        try:
            await self._write(message)
        except (httpx.HTTPError, ValueError):
            raise McpConfigError("MCP HTTP transport failed") from None

    async def _write(self, message: dict) -> None:
        self.response = None
        async with self.client.stream("POST", self.url, json=message) as response:
            if response.status_code in (401, 403):
                raise McpConfigError("MCP authentication required; configure a bearer token or auth headers in Voss")
            if response.is_error:
                raise McpConfigError(f"MCP HTTP request failed ({response.status_code})")
            session = response.headers.get("mcp-session-id")
            if session:
                self.client.headers["Mcp-Session-Id"] = session
            if "id" not in message:
                return
            if "text/event-stream" in response.headers.get("content-type", ""):
                data: list[str] = []
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        value = json.loads("\n".join(data))
                        data.clear()
                        if value.get("id") == message["id"]:
                            self.response = value
                            break
            else:
                self.response = json.loads(await response.aread())
        if not isinstance(self.response, dict) or self.response.get("id") != message["id"]:
            raise McpConfigError("MCP server returned no matching response")
        if message["method"] == "initialize":
            version = self.response.get("result", {}).get("protocolVersion")
            if version:
                self.client.headers["MCP-Protocol-Version"] = version

    async def aclose(self) -> None:
        await self.client.aclose()

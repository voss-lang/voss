"""Stdio JSON-RPC MCP client for harness network tools."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from voss.harness import lifecycle, telemetry

try:
    from voss.harness.mcp.config import McpConfigError, substitute_server
except ModuleNotFoundError:  # pragma: no cover - Task 1 owns config.py.

    class McpConfigError(Exception):
        """Raised for MCP configuration or transport setup failures."""

    def substitute_server(config: Any, *, cwd: Path) -> Any:
        return config


_PROTOCOL_VERSION = "2025-11-25"


def _emit_mcp_request(data: dict[str, Any]) -> None:
    telemetry.emit("mcp.request", "info", data=data)


def _emit_mcp_response(level: str, data: dict[str, Any]) -> None:
    telemetry.emit("mcp.response", level, data=data)


class McpClient:
    def __init__(self, config: Any) -> None:
        self._config = config
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._tools_cache: dict[str, list[dict[str, Any]]] = {}
        self._next_id = 1
        self._cwd = Path.cwd()

    def set_cwd(self, cwd: Path) -> None:
        self._cwd = cwd

    async def ensure_launched(self, server_name: str) -> asyncio.subprocess.Process:
        proc = self._procs.get(server_name)
        if proc is not None and proc.returncode is None:
            return proc
        if proc is not None:
            del self._procs[server_name]
            self._tools_cache.pop(server_name, None)

        server = self._server_config(server_name)
        server = substitute_server(server, cwd=self._cwd)
        env = self._build_env(server)

        proc = await asyncio.create_subprocess_exec(
            *server.command,
            *getattr(server, "args", []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self._cwd),
            env=env,
        )
        try:
            timeout_s = float(getattr(server, "timeout_s", 30.0))
            await self._handshake(proc, timeout_s)
            self._tools_cache[server_name] = await self._tools_list(proc, timeout_s)
        except Exception:
            await self._stop_failed_launch(proc)
            raise

        self._procs[server_name] = proc
        lifecycle.register_subprocess(proc)
        return proc

    async def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        await self.ensure_launched(server_name)
        return self._tools_cache[server_name]

    async def call_tool(
        self, server_name: str, tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        proc = await self.ensure_launched(server_name)
        msg_id = self._next_rpc_id()
        req = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
        }
        started = time.monotonic()
        if telemetry.enabled():
            _emit_mcp_request(
                {
                    "server": server_name,
                    "tool": tool_name,
                    "args": telemetry.redact_tool_args(args),
                    "started_at": started,
                },
            )

        try:
            await self._write(proc, req)
            resp = await self._read(
                proc,
                timeout=float(
                    getattr(self._server_config(server_name), "timeout_s", 30.0)
                ),
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            if telemetry.enabled():
                _emit_mcp_response(
                    "warn",
                    {
                        "server": server_name,
                        "tool": tool_name,
                        "status": "error",
                        "duration_ms": duration_ms,
                        "error": str(exc),
                    },
                )
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": "<error: mcp transport: connection lost>"}
                ],
            }

        duration_ms = int((time.monotonic() - started) * 1000)
        if "error" in resp:
            message = str(resp.get("error", {}).get("message", "unknown"))
            if telemetry.enabled():
                _emit_mcp_response(
                    "warn",
                    {
                        "server": server_name,
                        "tool": tool_name,
                        "status": "error",
                        "duration_ms": duration_ms,
                        "error": message,
                    },
                )
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"<error: mcp tool: {message}>"}],
            }

        if telemetry.enabled():
            _emit_mcp_response(
                "info",
                {
                    "server": server_name,
                    "tool": tool_name,
                    "status": "ok",
                    "duration_ms": duration_ms,
                    "error": None,
                },
            )
        return resp.get("result", {})

    async def _handshake(
        self, proc: asyncio.subprocess.Process, timeout_s: float
    ) -> None:
        await self._write(
            proc,
            {
                "jsonrpc": "2.0",
                "id": self._next_rpc_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": _PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "voss-harness", "version": "0.2"},
                },
            },
        )
        resp = await self._read(proc, timeout=timeout_s)
        actual = resp.get("result", {}).get("protocolVersion")
        if actual != _PROTOCOL_VERSION and telemetry.enabled():
            telemetry.emit(
                "mcp.protocol_warning",
                "warn",
                data={"expected": _PROTOCOL_VERSION, "actual": actual},
            )
        await self._write(
            proc, {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )

    async def _tools_list(
        self, proc: asyncio.subprocess.Process, timeout_s: float
    ) -> list[dict[str, Any]]:
        await self._write(
            proc,
            {
                "jsonrpc": "2.0",
                "id": self._next_rpc_id(),
                "method": "tools/list",
                "params": {},
            },
        )
        resp = await self._read(proc, timeout=timeout_s)
        tools = resp.get("result", {}).get("tools", [])
        return tools if isinstance(tools, list) else []

    async def _write(self, proc: asyncio.subprocess.Process, msg: dict[str, Any]) -> None:
        if proc.stdin is None:
            raise McpConfigError("MCP server stdin is not available")
        line = json.dumps(msg, separators=(",", ":")).encode("utf-8") + b"\n"
        proc.stdin.write(line)
        await proc.stdin.drain()

    async def _read(self, proc: asyncio.subprocess.Process, *, timeout: float) -> dict[str, Any]:
        if proc.stdout is None:
            raise McpConfigError("MCP server stdout is not available")
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
        if not line:
            raise McpConfigError("MCP server closed stdout unexpectedly")
        try:
            value = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise McpConfigError(f"MCP server returned invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise McpConfigError("MCP server returned a non-object JSON-RPC message")
        return value

    def _next_rpc_id(self) -> int:
        msg_id = self._next_id
        self._next_id += 1
        return msg_id

    def _server_config(self, server_name: str) -> Any:
        servers = getattr(self._config, "servers", {})
        if server_name not in servers:
            raise McpConfigError(f"unknown MCP server: {server_name!r}")
        return servers[server_name]

    def _build_env(self, server: Any) -> dict[str, str] | None:
        allowlist = getattr(server, "env", None)
        if allowlist is None:
            return None
        return {key: os.environ[key] for key in allowlist if key in os.environ}

    async def _stop_failed_launch(self, proc: asyncio.subprocess.Process) -> None:
        if proc.returncode is not None:
            return
        try:
            proc.terminate()
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                return
            await proc.wait()

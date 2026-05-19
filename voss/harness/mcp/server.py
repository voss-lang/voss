"""Stdio JSON-RPC MCP server scaffold for exposing harness tools."""

from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable, Mapping

from voss.harness import telemetry
from voss.harness.mcp.client import _PROTOCOL_VERSION

LINE_LIMIT_BYTES = 1_048_576


def _emit_mcp_server_request(data: dict[str, Any]) -> None:
    telemetry.emit("mcp.server.request", "info", data=data)


def _emit_mcp_server_response(level: str, data: dict[str, Any]) -> None:
    telemetry.emit("mcp.server.response", level, data=data)


def _json_rpc_error(*, id: Any, code: int, message: str) -> bytes:
    return _encode_message(
        {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    )


def _encode_message(message: Mapping[str, Any]) -> bytes:
    return json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"


class McpServer:
    def __init__(
        self,
        *,
        name: str,
        tool_descriptors: list[Mapping[str, Any]],
        dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        self._name = name
        self._tool_descriptors = list(tool_descriptors)
        self._tool_names = {
            str(descriptor["name"])
            for descriptor in self._tool_descriptors
            if "name" in descriptor
        }
        self._dispatch = dispatch

    async def serve_stdio(
        self,
        reader: Any,
        writer: Any,
        *,
        mode: str | None = None,
    ) -> None:
        pending = bytearray()
        while True:
            line = await _read_line(reader, pending)
            if line == b"":
                return
            if len(line) > LINE_LIMIT_BYTES:
                await self._write(
                    writer,
                    _json_rpc_error(
                        id=None,
                        code=-32700,
                        message="parse error: line too long",
                    ),
                )
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as exc:
                await self._write(
                    writer,
                    _json_rpc_error(
                        id=None,
                        code=-32700,
                        message=f"parse error: {exc}",
                    ),
                )
                continue
            if not isinstance(msg, dict):
                await self._write(
                    writer,
                    _json_rpc_error(
                        id=None,
                        code=-32600,
                        message="invalid request: expected object",
                    ),
                )
                continue
            response = await self._handle_message(msg, mode=mode)
            if response is not None:
                await self._write(writer, response)

    async def _handle_message(
        self, msg: dict[str, Any], *, mode: str | None
    ) -> bytes | None:
        msg_id = msg.get("id")
        method = msg.get("method")
        if method == "initialize":
            return _encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": _PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": self._name, "version": "0.1.0"},
                    },
                }
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": self._tool_descriptors},
                }
            )
        if method == "tools/call":
            return await self._handle_tools_call(msg, mode=mode)
        return _json_rpc_error(
            id=msg_id,
            code=-32601,
            message=f"method not found: {method}",
        )

    async def _handle_tools_call(
        self, msg: dict[str, Any], *, mode: str | None
    ) -> bytes:
        msg_id = msg.get("id")
        params = msg.get("params")
        params = params if isinstance(params, dict) else {}
        name = str(params.get("name", ""))
        raw_args = params.get("arguments", {})
        args = dict(raw_args) if isinstance(raw_args, Mapping) else {}
        redacted_args = telemetry.redact_tool_args(args)
        _emit_mcp_server_request({"name": name, "args": redacted_args, "mode": mode})

        start = time.monotonic()
        if name not in self._tool_names:
            message = f"tool not found: {name}"
            _emit_mcp_server_response(
                "warning",
                {
                    "name": name,
                    "elapsed_ms": int((time.monotonic() - start) * 1000),
                    "ok": False,
                    "error": message,
                },
            )
            return _json_rpc_error(id=msg_id, code=-32601, message=message)

        try:
            result = await self._dispatch(name, args)
        except Exception as exc:
            message = str(exc)
            _emit_mcp_server_response(
                "warning",
                {
                    "name": name,
                    "elapsed_ms": int((time.monotonic() - start) * 1000),
                    "ok": False,
                    "error": message,
                },
            )
            return _json_rpc_error(id=msg_id, code=-32603, message=message)

        if result.get("isError"):
            content = result.get("content", [])
            message = _result_error_text(content)
            _emit_mcp_server_response(
                "warning",
                {
                    "name": name,
                    "elapsed_ms": int((time.monotonic() - start) * 1000),
                    "ok": False,
                    "error": message,
                },
            )
        else:
            _emit_mcp_server_response(
                "info",
                {
                    "name": name,
                    "elapsed_ms": int((time.monotonic() - start) * 1000),
                    "ok": True,
                    "content_len": len(result.get("content", [])),
                },
            )
        return _encode_message({"jsonrpc": "2.0", "id": msg_id, "result": result})

    async def _write(self, writer: Any, line: bytes) -> None:
        writer.write(line)
        await writer.drain()


def _result_error_text(content: Any) -> str:
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                return text
    return "tool returned error"


async def _read_line(reader: Any, pending: bytearray) -> bytes:
    while True:
        newline = pending.find(b"\n")
        if newline >= 0:
            line = bytes(pending[: newline + 1])
            del pending[: newline + 1]
            return line
        chunk = await reader.read(4096)
        if chunk == b"":
            if not pending:
                return b""
            line = bytes(pending)
            pending.clear()
            return line
        pending.extend(chunk)
        if len(pending) > LINE_LIMIT_BYTES:
            await _discard_until_newline(reader, pending)
            return b"x" * (LINE_LIMIT_BYTES + 1)


async def _discard_until_newline(reader: Any, pending: bytearray) -> None:
    newline = pending.find(b"\n")
    if newline >= 0:
        del pending[: newline + 1]
        return
    pending.clear()
    while True:
        chunk = await reader.read(4096)
        if chunk == b"":
            return
        newline = chunk.find(b"\n")
        if newline >= 0:
            pending.extend(chunk[newline + 1 :])
            return

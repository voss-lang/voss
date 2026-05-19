from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from voss.harness.mcp.server import McpServer


class _MemoryWriter:
    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    async def drain(self) -> None:
        return None

    def messages(self) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in bytes(self.data).splitlines()
            if line.strip()
        ]


def _reader(*messages: bytes | dict[str, Any]) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    for message in messages:
        if isinstance(message, bytes):
            line = message
        else:
            line = json.dumps(message).encode("utf-8") + b"\n"
        reader.feed_data(line)
    reader.feed_eof()
    return reader


async def _dispatch_ok(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": "ok"}], "isError": False}


def _initialize(msg_id: int = 1) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "0"},
        },
    }


@pytest.mark.asyncio
async def test_handshake_roundtrip() -> None:
    writer = _MemoryWriter()
    server = McpServer(name="voss-test", tool_descriptors=[], dispatch=_dispatch_ok)

    await server.serve_stdio(_reader(_initialize()), writer)

    messages = writer.messages()
    assert len(messages) == 1
    assert messages[0]["result"]["protocolVersion"] == "2025-11-25"
    assert messages[0]["result"]["serverInfo"]["name"] == "voss-test"


@pytest.mark.asyncio
async def test_tools_list_returns_descriptors() -> None:
    descriptor = {
        "name": "fs_read",
        "description": "x",
        "inputSchema": {"type": "object", "properties": {}},
    }
    writer = _MemoryWriter()
    server = McpServer(
        name="voss-test", tool_descriptors=[descriptor], dispatch=_dispatch_ok
    )

    await server.serve_stdio(
        _reader(_initialize(), {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        writer,
    )

    assert writer.messages()[1]["result"] == {"tools": [descriptor]}


@pytest.mark.asyncio
async def test_tools_call_dispatches_and_emits_telemetry(monkeypatch) -> None:
    events: list[tuple[str, str, dict[str, Any] | None]] = []

    def emit(kind: str, level: str, msg: str | None = None, *, data=None) -> None:
        events.append((kind, level, data))

    monkeypatch.setattr("voss.harness.telemetry.emit", emit)
    writer = _MemoryWriter()
    server = McpServer(
        name="voss-test",
        tool_descriptors=[{"name": "x", "inputSchema": {"type": "object"}}],
        dispatch=_dispatch_ok,
    )

    await server.serve_stdio(
        _reader(
            _initialize(),
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "x", "arguments": {"a": 1}},
            },
        ),
        writer,
    )

    mcp_events = [event for event in events if event[0].startswith("mcp.server.")]
    assert [event[0] for event in mcp_events] == [
        "mcp.server.request",
        "mcp.server.response",
    ]
    assert mcp_events[0][1] == "info"
    assert mcp_events[1][1] == "info"
    assert mcp_events[1][2] is not None
    assert mcp_events[1][2]["ok"] is True
    assert writer.messages()[1]["result"] == {
        "content": [{"type": "text", "text": "ok"}],
        "isError": False,
    }


@pytest.mark.asyncio
async def test_tool_not_found_returns_method_error() -> None:
    async def fail_dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("dispatch should not be called")

    writer = _MemoryWriter()
    server = McpServer(name="voss-test", tool_descriptors=[], dispatch=fail_dispatch)

    await server.serve_stdio(
        _reader(
            _initialize(),
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "missing", "arguments": {}},
            },
        ),
        writer,
    )

    error = writer.messages()[1]["error"]
    assert error["code"] == -32601
    assert "tool not found: missing" in error["message"]


@pytest.mark.asyncio
async def test_parse_error_does_not_kill_loop() -> None:
    writer = _MemoryWriter()
    server = McpServer(name="voss-test", tool_descriptors=[], dispatch=_dispatch_ok)

    await server.serve_stdio(
        _reader(
            _initialize(),
            b"not-json\n",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ),
        writer,
    )

    messages = writer.messages()
    assert messages[0]["result"]["protocolVersion"] == "2025-11-25"
    assert messages[1]["error"]["code"] == -32700
    assert messages[2]["result"] == {"tools": []}


@pytest.mark.asyncio
async def test_eof_returns_cleanly() -> None:
    writer = _MemoryWriter()
    server = McpServer(name="voss-test", tool_descriptors=[], dispatch=_dispatch_ok)

    await asyncio.wait_for(server.serve_stdio(_reader(), writer), timeout=0.5)

    assert writer.messages() == []

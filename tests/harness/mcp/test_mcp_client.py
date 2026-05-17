from __future__ import annotations

import json
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from voss.harness import lifecycle, telemetry
from voss.harness.mcp.client import McpClient


MOCK_SERVER_SRC = textwrap.dedent(
    r'''
    import json
    import sys

    line = sys.stdin.readline()
    req = json.loads(line)
    resp = {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "mock", "version": "1"},
        },
    }
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

    sys.stdin.readline()

    line = sys.stdin.readline()
    req = json.loads(line)
    tools = [
        {
            "name": "read_text_file",
            "description": "Read text",
            "inputSchema": {"type": "object"},
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        },
        {
            "name": "write_file",
            "description": "Write",
            "inputSchema": {"type": "object"},
            "annotations": {"readOnlyHint": False, "destructiveHint": True},
        },
    ]
    resp = {"jsonrpc": "2.0", "id": req["id"], "result": {"tools": tools}}
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        req = json.loads(line)
        resp = {
            "jsonrpc": "2.0",
            "id": req["id"],
            "result": {"content": [{"type": "text", "text": "mock-result"}], "isError": False},
        }
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
    '''
)


@dataclass
class _ServerConfig:
    command: list[str]
    args: list[str] = field(default_factory=list)
    timeout_s: float = 5.0
    env: list[str] | None = None


@dataclass
class _McpConfig:
    servers: dict[str, _ServerConfig]


@pytest.fixture(autouse=True)
async def _reset_lifecycle() -> None:
    lifecycle.reset_for_tests()
    telemetry.reset_session_sink()
    try:
        yield
    finally:
        await lifecycle.reap_all()
        lifecycle.reset_for_tests()
        telemetry.reset_session_sink()


def _write_mock_server(tmp_path: Path, src: str = MOCK_SERVER_SRC) -> Path:
    path = tmp_path / "mock_server.py"
    path.write_text(src)
    return path


def _client_for_server(tmp_path: Path, script: Path) -> McpClient:
    config = _McpConfig(
        servers={"mock": _ServerConfig(command=[sys.executable, "-u", str(script)])}
    )
    client = McpClient(config)
    client.set_cwd(tmp_path)
    return client


@pytest.mark.asyncio
async def test_lazy_launch(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    client = _client_for_server(tmp_path, script)

    proc = await client.ensure_launched("mock")

    assert proc.returncode is None
    tools = client._tools_cache["mock"]
    assert [tool["name"] for tool in tools] == ["read_text_file", "write_file"]

    result = await client.call_tool("mock", "read_text_file", {"path": "x"})
    assert result["content"][0]["text"] == "mock-result"

    proc.terminate()
    await proc.wait()


@pytest.mark.asyncio
async def test_sigterm_reap(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    client = _client_for_server(tmp_path, script)
    proc = await client.ensure_launched("mock")

    started = time.monotonic()
    await lifecycle.reap_all()

    assert proc.returncode is not None
    assert time.monotonic() - started < 5.0


@pytest.mark.asyncio
async def test_call_tool_emits_mcp_telemetry(tmp_path: Path, monkeypatch) -> None:
    logf = tmp_path / "events.ndjson"
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(logf))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()

    script = _write_mock_server(tmp_path)
    client = _client_for_server(tmp_path, script)
    await client.ensure_launched("mock")

    result = await client.call_tool(
        "mock", "read_text_file", {"path": "x", "api_token": "secret"}
    )

    assert result["content"][0]["text"] == "mock-result"
    telemetry.reset_session_sink()
    events = [json.loads(line) for line in logf.read_text().splitlines()]
    mcp_events = [event for event in events if event["kind"].startswith("mcp.")]
    assert [event["kind"] for event in mcp_events] == ["mcp.request", "mcp.response"]
    assert not any(event["kind"].startswith("net.") for event in events)
    assert mcp_events[0]["data"]["args"]["api_token"] == "<redacted>"

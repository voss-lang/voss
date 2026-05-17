from __future__ import annotations

import asyncio
import json as json_lib
import sys
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness import lifecycle, telemetry
from voss.harness.cli import (
    _parse_arg_kvs,
    mcp_call_cmd,
    mcp_group,
    mcp_list_cmd,
)


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
        params = req.get("params", {})
        if params.get("name") == "fail_tool":
            result = {
                "content": [{"type": "text", "text": "mock-tool-error"}],
                "isError": True,
            }
        else:
            result = {
                "content": [{"type": "text", "text": "mock-result"}],
                "isError": False,
            }
        resp = {"jsonrpc": "2.0", "id": req["id"], "result": result}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
    '''
)


@pytest.fixture(autouse=True)
def _reset_lifecycle() -> None:
    lifecycle.reset_for_tests()
    telemetry.reset_session_sink()
    try:
        yield
    finally:
        asyncio.run(lifecycle.reap_all())
        lifecycle.reset_for_tests()
        telemetry.reset_session_sink()


def _write_mock_server(tmp_path: Path) -> Path:
    path = tmp_path / "mock_server.py"
    path.write_text(MOCK_SERVER_SRC)
    return path


def _write_mcp_yml(cwd: Path, server_script: Path) -> None:
    (cwd / ".voss").mkdir(exist_ok=True)
    command = json_lib.dumps([sys.executable, "-u", str(server_script)])
    (cwd / ".voss" / "mcp.yml").write_text(
        textwrap.dedent(
            f"""
            servers:
              mock:
                command: {command}
                timeout_s: 30.0
            """
        )
    )


def test_mcp_group_help_lists_subcommands() -> None:
    result = CliRunner().invoke(mcp_group, ["--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "call" in result.output


def test_mcp_list_no_config(tmp_path: Path) -> None:
    result = CliRunner().invoke(mcp_list_cmd, ["--cwd", str(tmp_path)])

    assert result.exit_code == 0
    assert "<no MCP servers configured>" in result.output


def test_mcp_list_no_config_json(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        mcp_list_cmd, ["--json", "--cwd", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert json_lib.loads(result.output) == {"servers": []}


def test_mcp_list_with_servers(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    _write_mcp_yml(tmp_path, script)

    result = CliRunner().invoke(mcp_list_cmd, ["--cwd", str(tmp_path)])

    assert result.exit_code == 0
    assert "mock:" in result.output
    assert "read_text_file" in result.output
    assert "write_file" in result.output


def test_mcp_list_json_shape(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    _write_mcp_yml(tmp_path, script)

    result = CliRunner().invoke(
        mcp_list_cmd, ["--json", "--cwd", str(tmp_path)]
    )

    assert result.exit_code == 0
    data = json_lib.loads(result.output)
    assert len(data["servers"]) == 1
    server = data["servers"][0]
    assert server["name"] == "mock"
    assert "read_text_file" in server["tools"]
    assert "write_file" in server["tools"]
    assert server["command"] == [sys.executable, "-u", str(script)]


def test_mcp_call_success(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    _write_mcp_yml(tmp_path, script)

    result = CliRunner().invoke(
        mcp_call_cmd,
        ["mock", "read_text_file", "--arg", "path=./README.md", "--cwd", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "mock-result" in result.output


def test_mcp_call_unknown_server(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    _write_mcp_yml(tmp_path, script)

    result = CliRunner().invoke(
        mcp_call_cmd,
        ["nonexistent", "read_text_file", "--cwd", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "<error: unknown server" in result.output


def test_mcp_call_server_side_tool_error_exits_2(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    _write_mcp_yml(tmp_path, script)

    result = CliRunner().invoke(
        mcp_call_cmd,
        ["mock", "fail_tool", "--cwd", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "mock-tool-error" in result.output


def test_arg_json_parsing() -> None:
    assert _parse_arg_kvs(("count=10",)) == {"count": 10}
    assert _parse_arg_kvs(("verbose=true",)) == {"verbose": True}
    assert _parse_arg_kvs(('path="./README.md"',)) == {"path": "./README.md"}
    assert _parse_arg_kvs(("path=./README.md",)) == {"path": "./README.md"}
    assert _parse_arg_kvs(('items=["a","b"]',)) == {"items": ["a", "b"]}
    assert _parse_arg_kvs(("null_val=null",)) == {"null_val": None}


def test_mcp_call_invalid_arg_format(tmp_path: Path) -> None:
    script = _write_mock_server(tmp_path)
    _write_mcp_yml(tmp_path, script)

    result = CliRunner().invoke(
        mcp_call_cmd,
        ["mock", "read_text_file", "--arg", "no_equals_sign", "--cwd", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "expected key=value" in result.output

"""M12-05: end-to-end subprocess acceptance for `voss mcp serve`.

Spawns the real CLI as a subprocess and exchanges JSON-RPC over stdio.
Closes MCP-01..07 at the wire level. Nyquist Dim-8 acceptance gate.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

_HANDSHAKE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "t", "version": "0"},
    },
}
_INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}

_EXPECTED_TOOLS = {
    "fs_read", "fs_glob", "fs_grep", "voss_check", "git_status", "git_diff",
    "analyze", "rename-symbol", "voss-lint-as-skill", "summarize-diff",
    "audit-cognition", "add-test", "port-py-to-voss",
}


def _spawn_server(tmp: Path, *, mode: str, env_extra: dict | None = None):
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    env["XDG_STATE_HOME"] = str(tmp / "state")
    env["XDG_CONFIG_HOME"] = str(tmp / "config")
    if env_extra:
        env.update(env_extra)
    return subprocess.Popen(
        [sys.executable, "-m", "voss.cli", "mcp", "serve",
         "--mode", mode, "--cwd", str(tmp)],
        cwd=str(tmp),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def _write(proc, payload: dict) -> None:
    proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _send_request(proc, payload: dict) -> dict:
    _write(proc, payload)
    deadline = time.monotonic() + 8.0
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(f"no response within 8s for {payload}")
        raw = proc.stdout.readline()
        if not raw:
            err = proc.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"server EOF before response; stderr: {err}")
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"non-JSON line on stdout (renderer leak?): {raw!r}"
            ) from e
        if msg.get("id") == payload.get("id"):
            return msg


def _handshake(proc) -> dict:
    resp = _send_request(proc, _HANDSHAKE)
    _write(proc, _INITIALIZED)  # notification — no response expected
    return resp


def _close(proc) -> None:
    try:
        proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_handshake_lists_thirteen_tools(tmp_path: Path) -> None:
    proc = _spawn_server(tmp_path, mode="plan")
    try:
        resp = _handshake(proc)
        assert resp["result"]["protocolVersion"] == "2025-11-25"
        assert resp["result"]["serverInfo"]["name"] in ("voss",)

        listed = _send_request(
            proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tools = listed["result"]["tools"]
        assert len(tools) == 13, [t["name"] for t in tools]
        names = {t["name"] for t in tools}
        assert _EXPECTED_TOOLS <= names, _EXPECTED_TOOLS - names
        for t in tools:
            assert isinstance(t["annotations"]["destructiveHint"], bool), t
    finally:
        _close(proc)


def test_plan_mode_denies_mutating_tool(tmp_path: Path) -> None:
    proc = _spawn_server(tmp_path, mode="plan")
    try:
        _handshake(proc)
        resp = _send_request(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "analyze", "arguments": {"args": []}},
        })
        assert resp["result"]["isError"] is True, resp
        assert "denied by mode plan" in resp["result"]["content"][0]["text"]
    finally:
        _close(proc)


def test_plan_mode_allows_read_only_tool(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("hi mcp")
    proc = _spawn_server(tmp_path, mode="plan")
    try:
        _handshake(proc)
        resp = _send_request(proc, {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "fs_read", "arguments": {"path": "hello.txt"}},
        })
        assert resp["result"]["isError"] is False, resp
        assert "hi mcp" in resp["result"]["content"][0]["text"]
    finally:
        _close(proc)


def test_edit_mode_passes_read_only_skill_through_gate(tmp_path: Path) -> None:
    src = (
        Path(__file__).resolve().parents[2]
        / "skills" / "fixtures" / "voss-lint" / "bad.voss"
    )
    (tmp_path / "bad.voss").write_text(src.read_text())
    proc = _spawn_server(tmp_path, mode="edit")
    try:
        _handshake(proc)
        resp = _send_request(proc, {
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "voss-lint-as-skill", "arguments": {"args": ["."]}},
        })
        assert resp["result"]["isError"] is False, resp
        schema = json.loads(resp["result"]["content"][0]["text"])
        assert schema["version"] == 1
    finally:
        _close(proc)


def test_unknown_tool_returns_jsonrpc_error(tmp_path: Path) -> None:
    # M12-01 server guards unadvertised names with a JSON-RPC error BEFORE
    # dispatch (-32601 tool not found), so M12-02's "unknown tool:" envelope
    # is unreachable through the server. Assert the shipped contract.
    proc = _spawn_server(tmp_path, mode="plan")
    try:
        _handshake(proc)
        resp = _send_request(proc, {
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        })
        assert "result" not in resp, resp
        assert resp["error"]["code"] == -32601, resp
        assert "tool not found: nope" in resp["error"]["message"], resp
    finally:
        _close(proc)


def test_eof_exits_subprocess_cleanly(tmp_path: Path) -> None:
    proc = _spawn_server(tmp_path, mode="plan")
    proc.stdin.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        pytest.fail("server did not exit on stdin EOF within 5s")
    assert proc.returncode == 0, proc.stderr.read().decode(errors="replace")


def test_telemetry_emits_mcp_server_events(tmp_path: Path) -> None:
    tel = tmp_path / "tel.ndjson"
    proc = _spawn_server(
        tmp_path, mode="plan",
        env_extra={"VOSS_LOG": "1", "VOSS_LOG_PATH": str(tel)},
    )
    try:
        _handshake(proc)
        (tmp_path / "hello.txt").write_text("hi")
        _send_request(proc, {
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "fs_read", "arguments": {"path": "hello.txt"}},
        })
    finally:
        _close(proc)

    assert tel.exists(), "telemetry file not written"
    events: list[str] = []
    for line in tel.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        # The path sink writes plain JSON lines; tolerate a possible prefix.
        brace = line.find("{")
        if brace == -1:
            continue
        try:
            events.append(json.loads(line[brace:]).get("kind", ""))
        except json.JSONDecodeError:
            continue
    assert "mcp.server.request" in events, events
    assert "mcp.server.response" in events, events

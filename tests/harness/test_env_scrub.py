from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from voss.harness import lifecycle
from voss.harness.sandbox import scrubbed_env

SENTINEL = "jev-sentinel-123"
_PYTHON_BIN = shutil.which("python3") or shutil.which("python")


def _probe(key: str = "TYPESAFE_API_KEY") -> str:
    return f"{_PYTHON_BIN} -c \"print(__import__('os').environ.get('{key}'))\""


@pytest.fixture(autouse=True)
def _sentinel(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", SENTINEL)
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()


async def _invoke(tools: dict[str, Any], name: str, **kwargs: Any) -> str:
    result = tools[name].descriptor.invoke(**kwargs)
    if asyncio.iscoroutine(result):
        result = await result
    return result


def test_scrubbed_env_drops_only_jev_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-sentinel")
    env = scrubbed_env()
    assert "TYPESAFE_API_KEY" not in env
    assert env == {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_shell_run_hides_jev_key(tmp_path: Path) -> None:
    from voss.harness.tools import make_toolset

    out = asyncio.run(_invoke(make_toolset(tmp_path), "shell_run", cmd=_probe()))
    assert out.startswith("[exit 0]")
    assert "None" in out
    assert SENTINEL not in out


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_shell_run_keeps_other_provider_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from voss.harness.tools import make_toolset

    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-sentinel")
    out = asyncio.run(
        _invoke(make_toolset(tmp_path), "shell_run", cmd=_probe("ANTHROPIC_API_KEY"))
    )
    assert "anthropic-sentinel" in out


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_shell_run_background_hides_jev_key(tmp_path: Path) -> None:
    async def _drive() -> str:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        handle = await _invoke(tools, "shell_run_background", cmd=_probe())
        output = ""
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            await asyncio.sleep(0.05)
            output = await _invoke(tools, "shell_monitor", handle=handle, since_ms=0)
            if "[exit " in output.split("\n", 1)[0]:
                break
        return output

    out = asyncio.run(_drive())
    assert "[exit " in out
    assert "None" in out
    assert SENTINEL not in out


def test_shell_capture_hides_jev_key(tmp_path: Path) -> None:
    from voss.harness.tools import _shell_capture

    out = asyncio.run(
        _shell_capture(
            tmp_path,
            [sys.executable, "-c", "print(__import__('os').environ.get('TYPESAFE_API_KEY'))"],
        )
    )
    assert "None" in out
    assert SENTINEL not in out


def test_swarm_subprocess_spawn_hides_jev_key(tmp_path: Path) -> None:
    from voss.harness.swarm_runtime import subprocess_spawn

    code = (
        "import os, pathlib; "
        "pathlib.Path('env.txt').write_text(str(os.environ.get('TYPESAFE_API_KEY')))"
    )
    handle = subprocess_spawn([sys.executable, "-c", code], tmp_path)
    assert handle.wait(timeout=30) == 0
    written = (tmp_path / "env.txt").read_text()
    assert written == "None"


def test_claude_subscription_shadows_jev_key() -> None:
    from voss.harness.claude_agent_provider import _subscription_env_overrides

    assert _subscription_env_overrides()["TYPESAFE_API_KEY"] == ""


def test_mcp_server_without_allowlist_gets_scrubbed_env() -> None:
    from voss.harness.mcp.client import McpClient

    env = McpClient(SimpleNamespace(servers={}))._build_env(SimpleNamespace(env=None))
    assert "TYPESAFE_API_KEY" not in env
    assert env["PATH"] == os.environ["PATH"]


def test_mcp_server_allowlist_stays_authoritative() -> None:
    from voss.harness.mcp.client import McpClient

    env = McpClient(SimpleNamespace(servers={}))._build_env(
        SimpleNamespace(env=["TYPESAFE_API_KEY"])
    )
    assert env == {"TYPESAFE_API_KEY": SENTINEL}


def test_skill_subprocess_hides_jev_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    import voss.cli
    from voss.harness.skill import adapter
    from voss.harness.skill.scope import ScopeSpec

    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(voss.cli, "compile_voss_file", lambda *a, **k: None)
    monkeypatch.setattr(adapter.subprocess, "run", fake_run)

    handler = adapter.make_voss_skill_handler(
        tmp_path / "skill.voss", ScopeSpec(tools="read-only", fs="cwd", net=False)
    )
    handler(SimpleNamespace(cwd=tmp_path, record=None), [])

    assert captured["VOSS_HERMETIC"] == "1"
    assert "TYPESAFE_API_KEY" not in captured

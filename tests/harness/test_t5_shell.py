from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from voss.harness import lifecycle


_PYTHON_BIN = shutil.which("python3") or shutil.which("python")
_EMIT = Path(__file__).parent / "fixtures" / "emit.py"


@pytest.fixture(autouse=True)
def _reset_registries():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()


def _emit_cmd(line_count: int) -> str:
    assert _PYTHON_BIN is not None
    return f"{_PYTHON_BIN} {_EMIT} {line_count}"


def _tool(tools: dict[str, Any], name: str) -> Any:
    if name not in tools:
        pytest.fail(f"T5 shell tool {name!r} is not registered")
    return tools[name].descriptor


async def _invoke(tools: dict[str, Any], name: str, **kwargs: Any) -> str:
    result = _tool(tools, name).invoke(**kwargs)
    if asyncio.iscoroutine(result):
        result = await result
    assert isinstance(result, str), f"{name} should return a string envelope"
    return result


def _cursor(prefix: str) -> int:
    match = re.search(r"\[cursor (\d+)\]", prefix)
    assert match is not None, f"missing cursor prefix: {prefix!r}"
    return int(match.group(1))


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_shell_run_30kb_truncation(tmp_path: Path) -> None:
    script = tmp_path / "big_output.py"
    script.write_text(
        "import sys\n"
        "sys.stdout.write('x' * 40000)\n"
        "sys.stdout.flush()\n"
    )

    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        out = await _invoke(make_toolset(tmp_path), "shell_run", cmd=f"{_PYTHON_BIN} {script}")
        assert "<truncated, total 40000 bytes>" in out
        body = out.split("\n", 1)[1].split("\n<truncated", 1)[0]
        assert len(body) == 30720

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_background_returns_handle(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        result = await _invoke(
            make_toolset(tmp_path),
            "shell_run_background",
            cmd=_emit_cmd(2),
        )
        assert result == "bg-001"
        assert "pid" not in result.lower()

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_handle_counter(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        first = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(1))
        second = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(1))
        assert first == "bg-001"
        assert second == "bg-002"

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_monitor_cursor_progression(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        handle = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(6))
        first = await _invoke(tools, "shell_monitor", handle=handle, since_ms=0)
        first_prefix, first_chunk = first.split("\n", 1)
        first_cursor = _cursor(first_prefix)
        assert "[running]" in first_prefix
        assert first_cursor >= 0

        await asyncio.sleep(0.4)
        second = await _invoke(tools, "shell_monitor", handle=handle, since_ms=first_cursor)
        second_prefix, second_chunk = second.split("\n", 1)
        assert "[exit " in second_prefix
        assert _cursor(second_prefix) >= first_cursor
        assert first_chunk + second_chunk

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_monitor_across_turns(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        first_turn = make_toolset(tmp_path)
        handle = await _invoke(first_turn, "shell_run_background", cmd=_emit_cmd(4))
        await asyncio.sleep(0.12)

        second_turn = make_toolset(tmp_path)
        monitor = await _invoke(second_turn, "shell_monitor", handle=handle, since_ms=0)
        assert monitor.startswith("[cursor ")
        assert "line 0" in monitor

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_signal_surface(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        handle = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(40))
        assert "<denied:" not in await _invoke(tools, "shell_signal", handle=handle, signal="INT")

        handle = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(40))
        assert "<denied:" not in await _invoke(tools, "shell_signal", handle=handle, signal="TERM")
        assert await _invoke(tools, "shell_signal", handle=handle, signal="KILL") == (
            "<denied: unsupported signal>"
        )
        assert await _invoke(tools, "shell_signal", handle=handle, signal="NOPE") == (
            "<denied: unsupported signal>"
        )

    asyncio.run(_drive())


@pytest.mark.skipif(os.name != "posix", reason="posix signals required")
@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_signal_terminates(tmp_path: Path) -> None:
    script = tmp_path / "wait.py"
    script.write_text(
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
        "time.sleep(60)\n"
    )

    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        handle = await _invoke(tools, "shell_run_background", cmd=f"{_PYTHON_BIN} {script}")
        assert "<denied:" not in await _invoke(tools, "shell_signal", handle=handle, signal="TERM")
        await asyncio.sleep(0.2)
        monitor = await _invoke(tools, "shell_monitor", handle=handle, since_ms=0)
        assert "[exit 0]" in monitor

    asyncio.run(_drive())


def test_voss_jobs_reads_sidecar(tmp_path: Path) -> None:
    try:
        from voss.harness.cli import jobs_cmd
    except (ImportError, AttributeError):
        pytest.fail("T5 jobs CLI should expose jobs_cmd for `voss jobs`")

    from click.testing import CliRunner

    jobs_root = tmp_path / ".voss-cache" / "jobs"
    session_dir = jobs_root / "sess-abc"
    session_dir.mkdir(parents=True)
    (jobs_root / ".active-session").write_text("sess-abc\n")
    sidecar = session_dir / "bg-001.meta.json"
    sidecar.write_text(
        json.dumps(
            {
                "handle": "bg-001",
                "pid": 12345,
                "started_at": "2026-05-17T00:00:00Z",
                "cmd": "python3 emit.py 2",
                "log_path": str(session_dir / "bg-001.log"),
                "status": "running",
                "exit_code": None,
                "runtime_ms": 42,
            }
        )
    )

    table = CliRunner().invoke(jobs_cmd, ["--cwd", str(tmp_path)])
    assert table.exit_code == 0, table.output
    assert "bg-001" in table.output
    assert "running" in table.output

    json_lines = CliRunner().invoke(jobs_cmd, ["--cwd", str(tmp_path), "--json"])
    assert json_lines.exit_code == 0, json_lines.output
    assert json.loads(json_lines.output)["handle"] == "bg-001"


@pytest.mark.skipif(os.name != "posix", reason="posix signals required")
@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_reap_jobs_escalation(tmp_path: Path) -> None:
    try:
        from voss.harness.lifecycle import reap_jobs, register_job
    except ImportError:
        pytest.fail("T5 lifecycle should expose register_job and reap_jobs")

    script = (
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "sys.stdout.write('ready\\n')\n"
        "sys.stdout.flush()\n"
        "time.sleep(60)\n"
    )

    async def _drive() -> None:
        proc = await asyncio.create_subprocess_exec(
            _PYTHON_BIN,
            "-u",
            "-c",
            script,
            cwd=str(tmp_path),
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
        assert line.strip() == b"ready"
        register_job(handle="bg-001", proc=proc, cmd="stubborn", log_path=str(tmp_path / "bg-001.log"))

        start = time.monotonic()
        await reap_jobs()
        elapsed = time.monotonic() - start
        assert proc.returncode is not None
        assert 4.5 <= elapsed <= 6.5

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_no_output_watchdog(tmp_path: Path) -> None:
    quiet = tmp_path / "quiet.py"
    quiet.write_text("import time\ntime.sleep(60)\n")

    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        handle = await _invoke(
            tools,
            "shell_run_background",
            cmd=f"{_PYTHON_BIN} {quiet}",
            no_output_deadline_s=0.3,
        )
        await asyncio.sleep(0.6)
        monitor = await _invoke(tools, "shell_monitor", handle=handle, since_ms=0)
        assert "reason=\"watchdog_no_output\"" in monitor
        assert "shell.background.reap" in monitor

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_rss_watchdog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _drive() -> None:
        from voss.harness import lifecycle as lifecycle_mod
        from voss.harness.tools import make_toolset

        monkeypatch.setattr(
            lifecycle_mod,
            "_tree_rss_bytes",
            lambda _pid: 101 * 1024 * 1024,
            raising=False,
        )
        tools = make_toolset(tmp_path)
        handle = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(40))
        await asyncio.sleep(0.2)
        monitor = await _invoke(tools, "shell_monitor", handle=handle, since_ms=0)
        assert "reason=\"watchdog_mem\"" in monitor
        assert "shell.background.reap" in monitor

    asyncio.run(_drive())


def test_edit_mode_denies_background_and_signal() -> None:
    from voss.harness.permissions import mode_allows

    assert mode_allows("edit", "shell_run_background", True)[0] is False
    assert mode_allows("edit", "shell_signal", True)[0] is False
    assert mode_allows("edit", "shell_monitor", False)[0] is True


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_toolset_path_uses_real_session_id(tmp_path: Path) -> None:
    from voss.harness.tools import make_toolset

    try:
        tools = make_toolset(tmp_path, session_id="sess-abc")
    except TypeError as exc:
        pytest.fail(f"make_toolset should accept session_id for job sidecars: {exc}")

    async def _drive() -> None:
        handle = await _invoke(tools, "shell_run_background", cmd=_emit_cmd(1))
        expected = tmp_path / ".voss-cache" / "jobs" / "sess-abc" / f"{handle}.meta.json"
        orphan = tmp_path / ".voss-cache" / "jobs" / "_nosession" / f"{handle}.meta.json"
        assert expected.exists()
        assert not orphan.exists()

    asyncio.run(_drive())

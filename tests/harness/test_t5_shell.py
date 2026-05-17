from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pytest


_PYTHON_BIN = shutil.which("python3") or shutil.which("python")
_EMIT = Path(__file__).parent / "fixtures" / "emit.py"


@pytest.fixture(autouse=True)
def _reset_registries():
    from voss.harness.lifecycle import reset_for_tests

    reset_for_tests()
    try:
        yield
    finally:
        reset_for_tests()


def _emit_cmd(line_count: int) -> str:
    assert _PYTHON_BIN is not None
    return f"{_PYTHON_BIN} {_EMIT} {line_count}"


def _json_obj(raw: Any) -> dict[str, Any]:
    assert isinstance(raw, str), f"expected JSON string result, got {type(raw).__name__}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"expected JSON object result, got {raw!r}: {exc}")
    assert isinstance(data, dict), f"expected JSON object result, got {data!r}"
    return data


def _require_tool(tools: dict[str, Any], name: str) -> Any:
    if name not in tools:
        pytest.fail(f"T5 shell tool {name!r} is not registered")
    return tools[name]


async def _invoke(tools: dict[str, Any], name: str, **kwargs: Any) -> Any:
    result = _require_tool(tools, name).invoke(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def test_shell_run_30kb_truncation() -> None:
    import inspect as _inspect

    from voss.harness import tools as tools_mod

    src = _inspect.getsource(tools_mod.make_toolset)
    match = re.search(
        r'@tool\(name="shell_run".*?@tool\(name="fs_write"',
        src,
        flags=re.DOTALL,
    )
    assert match is not None, "make_toolset should define shell_run before fs_write"
    shell_run_src = match.group(0)
    assert "30720" in shell_run_src, "shell_run stdout/stderr cap should be 30KB"
    assert "4096" not in shell_run_src, "shell_run should no longer use the legacy 4KB cap"


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_background_returns_handle(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        result = await _invoke(
            make_toolset(tmp_path),
            "shell_background",
            cmd=_emit_cmd(3),
        )
        data = _json_obj(result)
        assert data["handle"].startswith("job-")
        assert isinstance(data["pid"], int)
        assert data["status"] in {"running", "exited"}

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_handle_counter(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        first = _json_obj(await _invoke(tools, "shell_background", cmd=_emit_cmd(1)))
        second = _json_obj(await _invoke(tools, "shell_background", cmd=_emit_cmd(1)))

        assert first["handle"] == "job-1"
        assert second["handle"] == "job-2"

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_monitor_cursor_progression(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        job = _json_obj(await _invoke(tools, "shell_background", cmd=_emit_cmd(6)))
        await asyncio.sleep(0.14)
        first = _json_obj(await _invoke(tools, "shell_monitor", handle=job["handle"], cursor=0))
        await asyncio.sleep(0.16)
        second = _json_obj(
            await _invoke(tools, "shell_monitor", handle=job["handle"], cursor=first["cursor"])
        )

        assert first["cursor"] > 0
        assert "line 0" in first["output"]
        assert second["cursor"] > first["cursor"]
        assert "line 0" not in second["output"]

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_monitor_across_turns(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        first_turn_tools = make_toolset(tmp_path)
        job = _json_obj(
            await _invoke(first_turn_tools, "shell_background", cmd=_emit_cmd(4))
        )
        await asyncio.sleep(0.12)

        next_turn_tools = make_toolset(tmp_path)
        monitor = _json_obj(
            await _invoke(next_turn_tools, "shell_monitor", handle=job["handle"], cursor=0)
        )

        assert monitor["handle"] == job["handle"]
        assert monitor["cursor"] > 0
        assert "line 0" in monitor["output"]

    asyncio.run(_drive())


def test_signal_surface(tmp_path: Path) -> None:
    from voss.harness.tools import make_toolset

    signal_tool = _require_tool(make_toolset(tmp_path), "shell_signal")
    params = str(signal_tool.parameters)
    assert "handle" in params
    assert "signal" in params


@pytest.mark.skipif(os.name != "posix", reason="posix signals required")
@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_signal_terminates(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        job = _json_obj(await _invoke(tools, "shell_background", cmd=_emit_cmd(100)))
        sent = _json_obj(
            await _invoke(tools, "shell_signal", handle=job["handle"], signal="TERM")
        )
        await asyncio.sleep(0.1)
        monitor = _json_obj(
            await _invoke(tools, "shell_monitor", handle=job["handle"], cursor=0)
        )

        assert sent["signal"] == "TERM"
        assert monitor["status"] in {"terminated", "exited"}
        assert monitor["returncode"] is not None

    asyncio.run(_drive())


def test_voss_jobs_reads_sidecar(tmp_path: Path) -> None:
    try:
        from voss.harness.cli import jobs_cmd
    except ImportError:
        pytest.fail("T5 jobs CLI should expose jobs_cmd for `voss jobs`")

    from click.testing import CliRunner

    jobs_dir = tmp_path / ".voss" / "jobs"
    jobs_dir.mkdir(parents=True)
    (jobs_dir / "job-7.json").write_text(
        json.dumps(
            {
                "handle": "job-7",
                "cmd": "python emit.py 2",
                "status": "running",
                "pid": 12345,
            }
        )
    )

    result = CliRunner().invoke(jobs_cmd, ["--cwd", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "job-7" in result.output
    assert "running" in result.output


def test_reap_jobs_escalation() -> None:
    try:
        from voss.harness.lifecycle import reap_jobs, register_job
    except ImportError:
        pytest.fail("T5 lifecycle should expose register_job and reap_jobs")

    class StubbornJob:
        handle = "job-stubborn"
        terminate_calls = 0
        kill_calls = 0
        returncode = None

        async def terminate(self) -> None:
            self.terminate_calls += 1

        async def wait(self, timeout: float | None = None) -> None:
            raise TimeoutError

        async def kill(self) -> None:
            self.kill_calls += 1
            self.returncode = -9

    async def _drive() -> None:
        job = StubbornJob()
        register_job(job)
        await reap_jobs(term_deadline_s=0.01)
        assert job.terminate_calls == 1
        assert job.kill_calls == 1

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_no_output_watchdog(tmp_path: Path) -> None:
    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        job = _json_obj(
            await _invoke(
                tools,
                "shell_background",
                cmd=_emit_cmd(100),
                no_output_timeout_s=0.01,
            )
        )
        await asyncio.sleep(0.2)
        monitor = _json_obj(
            await _invoke(tools, "shell_monitor", handle=job["handle"], cursor=0)
        )

        assert monitor["status"] == "no_output_timeout"
        assert monitor["returncode"] is not None

    asyncio.run(_drive())


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_rss_watchdog(tmp_path: Path) -> None:
    hog = tmp_path / "rss_hog.py"
    hog.write_text(
        "import time\n"
        "chunks = [bytearray(1024 * 1024) for _ in range(50)]\n"
        "time.sleep(10)\n"
    )

    async def _drive() -> None:
        from voss.harness.tools import make_toolset

        tools = make_toolset(tmp_path)
        job = _json_obj(
            await _invoke(
                tools,
                "shell_background",
                cmd=f"{_PYTHON_BIN} {hog}",
                rss_limit_mb=5,
            )
        )
        await asyncio.sleep(0.4)
        monitor = _json_obj(
            await _invoke(tools, "shell_monitor", handle=job["handle"], cursor=0)
        )

        assert monitor["status"] == "rss_limit"
        assert monitor["returncode"] is not None

    asyncio.run(_drive())


def test_edit_mode_denies_background_and_signal(tmp_path: Path) -> None:
    from voss.harness.permissions import PermissionGate

    gate = PermissionGate(mode="edit")
    for tool_name, args in (
        ("shell_background", {"cmd": "python emit.py 2"}),
        ("shell_signal", {"handle": "job-1", "signal": "TERM"}),
    ):
        allowed, reason = gate.check(tool_name, args, is_mutating=True)
        assert not allowed
        assert reason == "denied by mode edit"


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
def test_toolset_path_uses_real_session_id(tmp_path: Path) -> None:
    from voss.harness.tools import make_toolset

    session_id = "sess-real"
    try:
        tools = make_toolset(tmp_path, session_id=session_id)
    except TypeError as exc:
        pytest.fail(f"make_toolset should accept a real session_id for job sidecars: {exc}")

    async def _drive() -> None:
        job = _json_obj(await _invoke(tools, "shell_background", cmd=_emit_cmd(1)))
        sidecar = tmp_path / ".voss" / "jobs" / f"{session_id}.jsonl"
        assert sidecar.exists(), f"expected job sidecar at {sidecar}"
        text = sidecar.read_text()
        assert session_id in text
        assert job["handle"] in text

    asyncio.run(_drive())

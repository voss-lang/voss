"""Wave 0 RED tests for M14 long-running watch support."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

import pytest
from click.testing import CliRunner

from voss.harness import cli as harness_cli
from voss.harness import lifecycle
from voss.harness import tools as harness_tools


@pytest.fixture(autouse=True)
def _reset_registries():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()


@pytest.fixture
def daemon_pid_cleanup():
    pids: list[int] = []
    yield pids
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


async def _poll_for(
    predicate: Callable[[], bool | Awaitable[bool]],
    *,
    timeout_s: float = 2.0,
    interval_s: float = 0.05,
) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        if await _maybe_await(predicate()):
            return True
        await asyncio.sleep(interval_s)
    return False


def _require_attr(module: Any, name: str) -> Any:
    assert hasattr(module, name), f"missing M14 symbol: {module.__name__}.{name}"
    return getattr(module, name)


def _watchdog_classes() -> tuple[type[Any], type[Any]]:
    try:
        from watchdog.events import PatternMatchingEventHandler
        from watchdog.observers import Observer
    except Exception as exc:  # noqa: BLE001 - runtime failure, not collection error.
        pytest.fail(f"watchdog>=4.0,<7 must be importable for M14 WATCH tests: {exc!r}")
    return Observer, PatternMatchingEventHandler


def _jsonl_event_count(text: str) -> int:
    body = text.split("\n", 1)[1] if "\n" in text else ""
    count = 0
    for line in body.splitlines():
        try:
            json.loads(line)
        except json.JSONDecodeError:
            continue
        count += 1
    return count


async def _register_test_watcher(
    tmp_path: Path,
    *,
    globs: list[str],
    session_id: str = "m14-test",
    debounce_ms: int = 200,
) -> tuple[str, Any]:
    register_watcher = _require_attr(lifecycle, "register_watcher")
    find_watcher = _require_attr(lifecycle, "_find_watcher")
    handle = await _maybe_await(
        register_watcher(
            cwd=tmp_path,
            globs=globs,
            session_id=session_id,
            debounce_ms=debounce_ms,
        )
    )
    assert isinstance(handle, str), "register_watcher must return a watch handle"
    assert handle.startswith("watch-"), "watch handles must use the watch-NNN prefix"
    rec = find_watcher(handle, session_id=session_id)
    assert rec is not None, f"watcher {handle} must be registered"
    return handle, rec


@pytest.mark.skipif(sys.platform == "win32", reason="WATCH-05 Windows non-gating")
async def test_debounce_coalesces_rapid_writes(tmp_path: Path) -> None:
    Observer, _ = _watchdog_classes()
    watched = tmp_path / "watched.txt"
    watched.write_text("initial")
    handle, rec = await _register_test_watcher(tmp_path, globs=["*.txt"])
    assert isinstance(rec.observer, Observer)
    assert rec.observer.daemon is True
    assert await _poll_for(lambda: rec.observer.is_alive())

    watched.write_text("changed once")

    read_log_cursor = _require_attr(lifecycle, "_read_log_cursor")
    observed = await _poll_for(
        lambda: _jsonl_event_count(
            read_log_cursor(Path(rec.log_path), 0, status=rec.status)
        )
        == 1
    )
    assert observed, f"{handle} should emit exactly one coalesced JSONL event"
    assert _jsonl_event_count(read_log_cursor(Path(rec.log_path), 0, status=rec.status)) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="WATCH-05 Windows non-gating")
async def test_non_matching_glob_no_event(tmp_path: Path) -> None:
    _watchdog_classes()
    watched = tmp_path / "note.txt"
    watched.write_text("initial")
    _handle, rec = await _register_test_watcher(tmp_path, globs=["*.voss"])
    assert await _poll_for(lambda: rec.observer.is_alive())

    watched.write_text("changed once")

    read_log_cursor = _require_attr(lifecycle, "_read_log_cursor")
    saw_event = await _poll_for(
        lambda: _jsonl_event_count(
            read_log_cursor(Path(rec.log_path), 0, status=rec.status)
        )
        > 0
    )
    assert saw_event is False
    assert _jsonl_event_count(read_log_cursor(Path(rec.log_path), 0, status=rec.status)) == 0


async def test_watcher_registry_and_reap(tmp_path: Path) -> None:
    watchers = _require_attr(lifecycle, "_WATCHERS")
    reap_watchers = _require_attr(lifecycle, "reap_watchers")
    next_watch_handle = _require_attr(lifecycle, "_next_watch_handle")
    assert next_watch_handle("session-a") == "watch-001"
    handle, rec = await _register_test_watcher(tmp_path, globs=["*.py"])
    assert any(record.handle == handle for record in watchers.values())
    assert rec.observer.daemon is True

    await reap_watchers()

    assert all(record.handle != handle for record in watchers.values())
    assert await _poll_for(lambda: not rec.observer.is_alive())


async def test_fs_watch_tool_cursor_read(tmp_path: Path) -> None:
    toolset = harness_tools.make_toolset(tmp_path, session_id="m14-tools")
    assert "fs_watch" in toolset, "make_toolset must expose fs_watch"
    assert "fs_watch_poll" in toolset, "make_toolset must expose fs_watch_poll"
    assert toolset["fs_watch"].is_mutating is False
    assert toolset["fs_watch_poll"].is_mutating is False

    watched = tmp_path / "watched.txt"
    watched.write_text("initial")
    handle = await _maybe_await(
        toolset["fs_watch"].invoke(globs=["*.txt"], debounce_ms=200)
    )
    assert isinstance(handle, str)
    assert handle.startswith("watch-")

    watched.write_text("changed once")

    async def _has_one_event() -> bool:
        output = await _maybe_await(toolset["fs_watch_poll"].invoke(handle=handle, since_ms=0))
        assert output.startswith("[cursor ")
        assert "][watching]\n" in output or "][stopped]\n" in output
        return _jsonl_event_count(output) == 1

    assert await _poll_for(_has_one_event)


def test_shared_cursor_reader_format(tmp_path: Path) -> None:
    read_log_cursor = _require_attr(lifecycle, "_read_log_cursor")
    log_path = tmp_path / "watch.log"
    payload = '{"path":"watched.txt","event_type":"modified"}\n'
    log_path.write_text(payload)

    output = read_log_cursor(log_path, 0, status="watching")

    assert output == f"[cursor {len(payload.encode())}][watching]\n{payload}"


def test_voss_watch_reruns_on_change(tmp_path: Path) -> None:
    watch_cmd = _require_attr(harness_cli, "watch_cmd")
    assert watch_cmd in harness_cli.AGENT_COMMANDS
    runner = CliRunner()

    result = runner.invoke(harness_cli.main, ["watch", "--help"])

    assert result.exit_code == 0
    assert "--glob" in result.output
    assert "--daemon" in result.output
    assert "--_is-worker" in {
        opt for param in watch_cmd.params for opt in getattr(param, "opts", [])
    }


def test_watch_command_allowlist(tmp_path: Path) -> None:
    _require_attr(harness_cli, "watch_cmd")
    runner = CliRunner()

    result = runner.invoke(
        harness_cli.main,
        [
            "watch",
            "python -c 'print(1)' && python -c 'print(2)'",
            "--cwd",
            str(tmp_path),
            "--glob",
            "*.py",
            "--_is-worker",
        ],
    )

    assert result.exit_code != 0 or "<denied:" in result.output
    assert "metacharacter" in result.output or "denied" in result.output.lower()


async def test_nondaemon_watch_reaped_on_exit(tmp_path: Path) -> None:
    _require_attr(harness_cli, "watch_cmd")
    handle, rec = await _register_test_watcher(tmp_path, globs=["*.py"])
    assert rec.observer.is_alive()

    await lifecycle.reap_all()

    watchers = _require_attr(lifecycle, "_WATCHERS")
    assert all(record.handle != handle for record in watchers.values())
    assert await _poll_for(lambda: not rec.observer.is_alive())


def test_daemon_watch_survives_exit(tmp_path: Path, daemon_pid_cleanup: list[int]) -> None:
    try:
        daemon_mod = importlib.import_module("voss.harness.watch.daemon")
    except ModuleNotFoundError as exc:
        assert False, f"missing M14 module: voss.harness.watch.daemon ({exc})"
    spawn_detached_worker = _require_attr(daemon_mod, "spawn_detached_worker")
    argv = [
        sys.executable,
        "-m",
        "voss.harness.cli",
        "watch",
        "--_is-worker",
        "--cwd",
        str(tmp_path),
        "--glob",
        "*.py",
        "python -c 'import time; time.sleep(60)'",
    ]

    pid = spawn_detached_worker(argv)
    daemon_pid_cleanup.append(pid)
    lifecycle.reset_for_tests()

    assert isinstance(pid, int)
    os.kill(pid, 0)


def test_watchdog_dependency_importable() -> None:
    Observer, PatternMatchingEventHandler = _watchdog_classes()
    watchdog_version = importlib.import_module("watchdog.version")
    major = int(watchdog_version.VERSION_STRING.split(".", 1)[0])

    assert issubclass(Observer, object)
    assert PatternMatchingEventHandler.__name__ == "PatternMatchingEventHandler"
    assert 4 <= major < 7

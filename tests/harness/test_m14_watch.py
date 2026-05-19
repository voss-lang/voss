"""M14 WATCH scaffold tests.

These tests intentionally bind the public names and behavior that later M14
plans implement. Wave 0 expects the file to collect cleanly while most tests
fail RED against today's production code.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

import pytest
from click.testing import CliRunner

from voss.cli import main as voss_main
from voss.harness import lifecycle
from voss.harness.tools import make_toolset


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


def _require_attr(obj: Any, name: str) -> Any:
    assert hasattr(obj, name), f"missing WATCH contract: {obj!r}.{name}"
    return getattr(obj, name)


def _poll_for(
    predicate: Callable[[], Any],
    *,
    timeout_s: float = 2.0,
    interval_s: float = 0.05,
) -> Any:
    deadline = time.monotonic() + timeout_s
    last: Any = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval_s)
    return last


def _event_lines(log_path: str | Path) -> list[dict[str, Any]]:
    path = Path(log_path)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def _cursor_from(envelope: str) -> int:
    match = re.match(r"\[cursor (\d+)\]\[[^\]]+\]\n", envelope)
    assert match is not None, envelope
    return int(match.group(1))


async def _invoke(entry: Any, **kwargs: Any) -> Any:
    result = entry.invoke(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def test_watchdog_dependency_importable() -> None:
    from watchdog.events import PatternMatchingEventHandler
    from watchdog.observers import Observer
    from watchdog.version import VERSION_STRING

    major = int(VERSION_STRING.split(".", 1)[0])
    assert 4 <= major < 7
    assert Observer is not None
    assert PatternMatchingEventHandler is not None


@pytest.mark.skipif(sys.platform == "win32", reason="WATCH-05 Windows non-gating")
async def test_debounce_coalesces_rapid_writes(tmp_path: Path) -> None:
    register_watcher = _require_attr(lifecycle, "register_watcher")
    find_watcher = _require_attr(lifecycle, "_find_watcher")
    reap_watchers = _require_attr(lifecycle, "reap_watchers")

    handle = await register_watcher(
        ["**/*.py"],
        tmp_path,
        session_id="watch-test",
        debounce_ms=200,
    )
    assert handle == "watch-001"

    watched = tmp_path / "sample.py"
    watched.write_text("print('one')\n")

    def matching_events() -> list[dict[str, Any]]:
        rec = find_watcher(handle, session_id="watch-test")
        assert rec is not None
        return [
            row
            for row in _event_lines(rec.log_path)
            if row.get("path") == str(watched) or row.get("src_path") == str(watched)
        ]

    events = _poll_for(matching_events, timeout_s=2.0, interval_s=0.05)
    assert len(events) == 1

    await reap_watchers()


@pytest.mark.skipif(sys.platform == "win32", reason="WATCH-05 Windows non-gating")
async def test_non_matching_glob_no_event(tmp_path: Path) -> None:
    register_watcher = _require_attr(lifecycle, "register_watcher")
    find_watcher = _require_attr(lifecycle, "_find_watcher")
    reap_watchers = _require_attr(lifecycle, "reap_watchers")

    handle = await register_watcher(
        ["**/*.py"],
        tmp_path,
        session_id="watch-test",
        debounce_ms=200,
    )
    rec = find_watcher(handle, session_id="watch-test")
    assert rec is not None

    (tmp_path / "notes.txt").write_text("not watched\n")

    def any_events() -> list[dict[str, Any]]:
        return _event_lines(rec.log_path)

    events = _poll_for(any_events, timeout_s=0.6, interval_s=0.05)
    assert events == []

    await reap_watchers()


async def test_watcher_registry_and_reap(tmp_path: Path) -> None:
    watchers = _require_attr(lifecycle, "_WATCHERS")
    next_watch_handle = _require_attr(lifecycle, "_next_watch_handle")
    register_watcher = _require_attr(lifecycle, "register_watcher")
    reap_watchers = _require_attr(lifecycle, "reap_watchers")

    assert next_watch_handle("handles") == "watch-001"
    assert next_watch_handle("handles") == "watch-002"
    assert lifecycle._next_handle("handles") == "bg-001"

    handle = await register_watcher(["**/*.py"], tmp_path, session_id="registry-test")
    assert handle == "watch-001"
    assert len(watchers) == 1
    rec = next(iter(watchers.values()))
    assert rec.handle == handle
    assert rec.observer.is_alive()

    await reap_watchers()
    assert watchers == {}
    assert not rec.observer.is_alive()


async def test_fs_watch_tool_cursor_read(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path, session_id="tool-test")
    assert "fs_watch" in tools
    assert "fs_watch_poll" in tools
    assert tools["fs_watch"].is_mutating is False
    assert tools["fs_watch_poll"].is_mutating is False

    handle = await _invoke(tools["fs_watch"], globs=["**/*.py"], debounce_ms=200)
    assert handle == "watch-001"

    changed = tmp_path / "tool_target.py"
    changed.write_text("print('tool')\n")

    def poll_output() -> str:
        text = tools["fs_watch_poll"].invoke(handle=handle, since_ms=0)
        assert isinstance(text, str)
        if str(changed) in text or "tool_target.py" in text:
            return text
        return ""

    first = _poll_for(poll_output, timeout_s=2.0, interval_s=0.05)
    assert first.startswith("[cursor ")
    assert "][watching]\n" in first
    assert "tool_target.py" in first

    cursor = _cursor_from(first)
    second = tools["fs_watch_poll"].invoke(handle=handle, since_ms=cursor)
    assert isinstance(second, str)
    assert second.startswith(f"[cursor {cursor}]")
    assert "tool_target.py" not in second


def test_shared_cursor_reader_format(tmp_path: Path) -> None:
    read_log_cursor = _require_attr(lifecycle, "_read_log_cursor")
    log = tmp_path / "watch.log"
    log.write_text("alpha\nbeta\n")

    output = read_log_cursor(log, 0, status="watching")

    assert output == "[cursor 11][watching]\nalpha\nbeta\n"
    assert read_log_cursor(tmp_path / "missing.log", 0, status="stopped") == (
        "[cursor 0][stopped]\n"
    )


def test_voss_watch_help() -> None:
    result = CliRunner().invoke(voss_main, ["watch", "--help"])
    assert result.exit_code == 0
    assert "--glob" in result.output
    assert "--_is-worker" in result.output


@pytest.mark.skipif(sys.platform == "win32", reason="WATCH-05 Windows non-gating")
def test_voss_watch_reruns_on_change(tmp_path: Path) -> None:
    # Each spawn appends to `marker`; a clean re-run yields >= 2 writes.
    command = "python -c \"open('marker','a').write('r')\""

    def trigger() -> None:
        (tmp_path / "trigger.py").write_text("x = 1\n")

    timer = threading.Timer(0.3, trigger)
    timer.start()
    try:
        result = CliRunner().invoke(
            voss_main,
            [
                "watch",
                command,
                "--glob",
                "**/*.py",
                "--cwd",
                str(tmp_path),
                "--debounce-ms",
                "50",
                "--_idle-timeout-ms",
                "1000",
            ],
        )
    finally:
        timer.cancel()

    assert result.exit_code == 0, result.output
    assert "watch-001" in result.output

    marker = tmp_path / "marker"
    written = _poll_for(
        lambda: marker.read_text() if marker.exists() else "",
        timeout_s=3.0,
        interval_s=0.05,
    )
    assert written.count("r") >= 2, f"expected >=2 runs, got {written!r}"


def test_watch_command_allowlist(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        voss_main,
        ["watch", "echo ok | cat", "--cwd", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "<denied:" in result.output


def test_nondaemon_watch_reaped_on_exit(tmp_path: Path) -> None:
    register_watcher = _require_attr(lifecycle, "register_watcher")
    assert register_watcher is not None

    result = CliRunner().invoke(
        voss_main,
        [
            "watch",
            "python -m http.server 0",
            "--glob",
            "**/*.py",
            "--cwd",
            str(tmp_path),
            "--_idle-timeout-ms",
            "300",
        ],
    )

    assert result.exit_code == 0, result.output
    assert lifecycle._JOBS == {}
    assert _require_attr(lifecycle, "_WATCHERS") == {}


def test_daemon_watch_survives_exit(
    monkeypatch: pytest.MonkeyPatch,
    daemon_pid_cleanup: list[int],
) -> None:
    try:
        from voss.harness.watch import daemon
    except ModuleNotFoundError:
        pytest.fail("missing WATCH contract: voss.harness.watch.daemon")

    calls: list[dict[str, Any]] = []

    class DummyProc:
        pid = 424242

        def wait(self) -> None:
            raise AssertionError("daemon detach must not wait on the child")

    def fake_popen(argv: list[str], **kwargs: Any) -> DummyProc:
        calls.append({"argv": argv, "kwargs": kwargs})
        return DummyProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    pid = daemon.spawn_detached_worker(
        ["--daemon", "pytest -q", "--glob", "**/*.py"]
    )
    daemon_pid_cleanup.append(pid)

    assert pid == 424242
    assert calls
    argv = calls[0]["argv"]
    assert argv[:4] == [sys.executable, "-m", "voss.harness.cli", "watch"]
    assert "--daemon" not in argv
    assert argv.count("--_is-worker") == 1
    assert calls[0]["kwargs"]["stdin"] is subprocess.DEVNULL
    assert calls[0]["kwargs"]["stdout"] is subprocess.DEVNULL
    assert calls[0]["kwargs"]["stderr"] is subprocess.DEVNULL
    assert calls[0]["kwargs"]["start_new_session"] is True

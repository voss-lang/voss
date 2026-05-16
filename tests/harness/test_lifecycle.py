"""Tests for voss.harness.lifecycle reap hook."""

from __future__ import annotations

import asyncio
import shutil
import time

import pytest

from voss.harness import lifecycle


@pytest.fixture(autouse=True)
def _reset_registries():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()


_SLEEP_BIN = shutil.which("sleep")
_PYTHON_BIN = shutil.which("python3") or shutil.which("python")


@pytest.mark.skipif(_SLEEP_BIN is None, reason="unix sleep required")
async def test_register_subprocess_terminate_path() -> None:
    proc = await asyncio.create_subprocess_exec(_SLEEP_BIN, "60")
    lifecycle.register_subprocess(proc)
    start = time.monotonic()
    await lifecycle.reap_all()
    elapsed = time.monotonic() - start
    assert proc.returncode is not None
    assert elapsed < 1.0, f"SIGTERM path took {elapsed:.2f}s; expected < 1.0"


@pytest.mark.skipif(_PYTHON_BIN is None, reason="python interpreter required")
async def test_register_subprocess_sigkill_fallback() -> None:
    script = (
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "sys.stdout.write('ready\\n')\n"
        "sys.stdout.flush()\n"
        "time.sleep(60)\n"
    )
    proc = await asyncio.create_subprocess_exec(
        _PYTHON_BIN, "-u", "-c", script, stdout=asyncio.subprocess.PIPE
    )
    assert proc.stdout is not None
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
    assert line.strip() == b"ready"
    lifecycle.register_subprocess(proc)
    start = time.monotonic()
    await lifecycle.reap_all()
    elapsed = time.monotonic() - start
    assert proc.returncode is not None
    assert 4.5 <= elapsed <= 6.5, (
        f"SIGKILL fallback elapsed {elapsed:.2f}s; expected 4.5..6.5"
    )


async def test_register_session_aclose_called() -> None:
    class StubSession:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    stub = StubSession()
    lifecycle.register_session(stub)
    await lifecycle.reap_all()
    assert stub.closed is True


async def test_aclose_exception_does_not_propagate() -> None:
    class BadSession:
        async def aclose(self) -> None:
            raise RuntimeError("boom")

    lifecycle.register_session(BadSession())
    await lifecycle.reap_all()


async def test_reset_for_tests_clears_registries() -> None:
    class StubSession:
        async def aclose(self) -> None:
            pass

    class FakeProc:
        returncode = 0

    lifecycle.register_session(StubSession())
    lifecycle._SUBPROCESSES.append(FakeProc())  # type: ignore[arg-type]
    lifecycle.reset_for_tests()
    assert lifecycle._SUBPROCESSES == []
    assert lifecycle._SESSIONS == []

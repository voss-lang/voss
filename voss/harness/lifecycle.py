"""Shared lifecycle reap hook for MCP subprocesses and net sessions.

Contract: register_session accepts any object that exposes an awaitable
``aclose(self) -> None`` method (duck typed; no import of NetSession to avoid
circular dependency with voss.harness.net).

reap_all sends SIGTERM to every still-running subprocess, waits up to 5.0s,
then sends SIGKILL on timeout. After subprocesses, every registered session
gets ``await session.aclose()`` wrapped in a swallow-all guard so a single
failing aclose never aborts the reap loop.

atexit fallback: at interpreter shutdown we attempt ``asyncio.run(reap_all())``.
If a running loop is detected (RuntimeError on asyncio.run), we fall back to a
fresh ``asyncio.new_event_loop().run_until_complete``. Both paths are wrapped
in try/except — atexit hooks must not raise.
"""

from __future__ import annotations

import asyncio
import atexit
import sys

_SUBPROCESSES: list[asyncio.subprocess.Process] = []
_SESSIONS: list[object] = []

_TERM_DEADLINE_S = 5.0


def register_subprocess(proc: asyncio.subprocess.Process) -> None:
    _SUBPROCESSES.append(proc)


def register_session(session: object) -> None:
    _SESSIONS.append(session)


async def reap_all() -> None:
    for proc in list(_SUBPROCESSES):
        if proc.returncode is not None:
            continue
        try:
            proc.terminate()
        except ProcessLookupError:
            continue
        except Exception as exc:
            sys.stderr.write(f"lifecycle.reap_all: terminate failed: {exc!r}\n")
            continue
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERM_DEADLINE_S)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            except Exception as exc:
                sys.stderr.write(f"lifecycle.reap_all: kill failed: {exc!r}\n")
            try:
                await proc.wait()
            except Exception as exc:
                sys.stderr.write(f"lifecycle.reap_all: wait failed: {exc!r}\n")
        except Exception as exc:
            sys.stderr.write(f"lifecycle.reap_all: wait_for failed: {exc!r}\n")

    for session in list(_SESSIONS):
        try:
            await session.aclose()
        except BaseException as exc:
            sys.stderr.write(f"lifecycle.reap_all: aclose failed: {exc!r}\n")

    _SUBPROCESSES.clear()
    _SESSIONS.clear()


def reset_for_tests() -> None:
    _SUBPROCESSES.clear()
    _SESSIONS.clear()


def _atexit_hook() -> None:
    if not _SUBPROCESSES and not _SESSIONS:
        return
    try:
        asyncio.run(reap_all())
        return
    except RuntimeError:
        pass
    except Exception as exc:
        sys.stderr.write(f"lifecycle._atexit_hook: asyncio.run failed: {exc!r}\n")

    try:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(reap_all())
        finally:
            loop.close()
    except Exception as exc:
        sys.stderr.write(f"lifecycle._atexit_hook: fallback failed: {exc!r}\n")


atexit.register(_atexit_hook)

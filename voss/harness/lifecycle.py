"""Shared lifecycle reap hook for MCP subprocesses, net sessions, and jobs.

Contract: register_session accepts any object that exposes an awaitable
``aclose(self) -> None`` method (duck typed; no import of NetSession to avoid
circular dependency with voss.harness.net).

reap_all sends SIGTERM to every still-running subprocess, waits up to 5.0s,
then sends SIGKILL on timeout. After subprocesses, every registered session
gets ``await session.aclose()`` wrapped in a swallow-all guard so a single
failing aclose never aborts the reap loop. Background jobs are then reaped via
the parallel _JOBS registry.

atexit fallback: at interpreter shutdown we attempt ``asyncio.run(reap_all())``.
If a running loop is detected (RuntimeError on asyncio.run), we fall back to a
fresh ``asyncio.new_event_loop().run_until_complete``. Both paths are wrapped
in try/except — atexit hooks must not raise.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import signal as signal_mod
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

_SUBPROCESSES: list[asyncio.subprocess.Process] = []
_SESSIONS: list[object] = []
# _JOBS is separate because background jobs have distinct reap semantics:
# watchdog timers, mid-life signals, and lifetimes beyond the 5s subprocess deadline.
_JOBS: dict[str, "JobRecord"] = {}
_HANDLE_COUNTERS: dict[str, int] = {}

_TERM_DEADLINE_S = 5.0
_MEM_LIMIT_BYTES = 100 * 1024 * 1024
_READ_CHUNK_BYTES = 65536
_MONITOR_CAP_BYTES = 30720

_JOB_FIELDS = {
    "handle",
    "pid",
    "started_at",
    "cmd",
    "log_path",
    "status",
    "exit_code",
    "runtime_ms",
}


@dataclass
class JobRecord:
    handle: str
    pid: int
    started_at: str
    cmd: str
    log_path: str
    status: str
    exit_code: int | None
    runtime_ms: int
    proc: asyncio.subprocess.Process | Any | None = field(
        default=None, repr=False, compare=False
    )
    task: asyncio.Task | None = field(default=None, repr=False, compare=False)
    started_monotonic: float = field(
        default_factory=time.monotonic, repr=False, compare=False
    )
    use_process_group: bool = field(default=False, repr=False, compare=False)
    reap_reason: str | None = field(default=None, repr=False, compare=False)
    reap_signal: str | None = field(default=None, repr=False, compare=False)

    def to_meta(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "pid": self.pid,
            "started_at": self.started_at,
            "cmd": self.cmd,
            "log_path": self.log_path,
            "status": self.status,
            "exit_code": self.exit_code,
            "runtime_ms": self.runtime_ms,
        }


def _hydrate_job(data: dict[str, Any]) -> JobRecord:
    known = {k: data[k] for k in _JOB_FIELDS if k in data}
    return JobRecord(**known)


def register_subprocess(proc: asyncio.subprocess.Process) -> None:
    _SUBPROCESSES.append(proc)


def register_session(session: object) -> None:
    _SESSIONS.append(session)


def _job_dir(cwd: Path, session_id: str) -> Path:
    from .sandbox import jail_path

    root = jail_path(cwd, ".voss-cache/jobs")
    root.mkdir(parents=True, exist_ok=True)
    session_dir = jail_path(root, session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _log_path(cwd: Path, session_id: str, handle: str) -> Path:
    return _job_dir(cwd, session_id) / f"{handle}.log"


def _meta_path(rec: JobRecord) -> Path:
    return Path(rec.log_path).with_suffix(".meta.json")


def _write_meta(rec: JobRecord) -> None:
    target = _meta_path(rec)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(rec.to_meta(), sort_keys=True) + "\n")
    tmp.replace(target)


def _refresh_runtime(rec: JobRecord) -> None:
    rec.runtime_ms = max(0, int((time.monotonic() - rec.started_monotonic) * 1000))


def _tree_rss_bytes(pid: int) -> int:
    try:
        proc = psutil.Process(pid)
        total = proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return total
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def _kill_tree(
    proc: asyncio.subprocess.Process | Any,
    sig: int,
    *,
    use_process_group: bool = True,
) -> None:
    try:
        if os.name == "posix" and use_process_group:
            os.killpg(os.getpgid(proc.pid), sig)
        elif sig == signal_mod.SIGKILL and hasattr(proc, "kill"):
            proc.kill()
        elif hasattr(proc, "send_signal"):
            proc.send_signal(sig)
        elif sig == signal_mod.SIGTERM and hasattr(proc, "terminate"):
            proc.terminate()
        elif hasattr(proc, "kill"):
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass


def _emit_reap(
    rec: JobRecord,
    *,
    sig_name: str,
    reason: str,
    exit_code: int | None = None,
) -> None:
    _refresh_runtime(rec)
    if exit_code is not None:
        rec.exit_code = exit_code
    rec.reap_signal = sig_name
    rec.reap_reason = reason
    try:
        from . import telemetry

        telemetry.emit(
            "shell.background.reap",
            "info",
            data={
                "handle": rec.handle,
                "pid": rec.pid,
                "signal": sig_name,
                "exit_code": rec.exit_code,
                "runtime_ms": rec.runtime_ms,
                "reason": reason,
            },
        )
    except Exception as exc:
        sys.stderr.write(f"lifecycle._emit_reap: emit failed: {exc!r}\n")


async def _wait_after_kill(proc: asyncio.subprocess.Process | Any) -> None:
    try:
        await proc.wait()
    except Exception as exc:
        sys.stderr.write(f"lifecycle: wait after kill failed: {exc!r}\n")


async def _supervise(rec: JobRecord, no_output_deadline_s: float = 30.0) -> None:
    proc = rec.proc
    if proc is None:
        return
    stdout = getattr(proc, "stdout", None)
    last_rss_poll = 0.0
    try:
        with open(rec.log_path, "ab", buffering=0) as fh:
            while True:
                if stdout is None:
                    await proc.wait()
                    rec.exit_code = proc.returncode
                    rec.status = "done"
                    _refresh_runtime(rec)
                    _write_meta(rec)
                    break
                try:
                    chunk = await asyncio.wait_for(
                        stdout.read(_READ_CHUNK_BYTES),
                        timeout=no_output_deadline_s,
                    )
                except asyncio.TimeoutError:
                    _kill_tree(
                        proc,
                        signal_mod.SIGKILL,
                        use_process_group=rec.use_process_group,
                    )
                    await _wait_after_kill(proc)
                    rec.exit_code = proc.returncode
                    rec.status = "killed"
                    _emit_reap(rec, sig_name="KILL", reason="watchdog_no_output")
                    _write_meta(rec)
                    break
                if not chunk:
                    await proc.wait()
                    rec.exit_code = proc.returncode
                    rec.status = "done"
                    _refresh_runtime(rec)
                    _write_meta(rec)
                    break
                fh.write(chunk)
                _refresh_runtime(rec)
                _write_meta(rec)
                now = time.monotonic()
                if now - last_rss_poll >= 1.0:
                    last_rss_poll = now
                    if _tree_rss_bytes(rec.pid) > _MEM_LIMIT_BYTES:
                        _kill_tree(
                            proc,
                            signal_mod.SIGKILL,
                            use_process_group=rec.use_process_group,
                        )
                        await _wait_after_kill(proc)
                        rec.exit_code = proc.returncode
                        rec.status = "killed"
                        _emit_reap(rec, sig_name="KILL", reason="watchdog_mem")
                        _write_meta(rec)
                        break
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        sys.stderr.write(f"lifecycle._supervise: failed: {exc!r}\n")
        _refresh_runtime(rec)
        _write_meta(rec)


def _next_handle(session_id: str) -> str:
    n = _HANDLE_COUNTERS.get(session_id, 0) + 1
    _HANDLE_COUNTERS[session_id] = n
    return f"bg-{n:03d}"


def _store_record(
    *,
    handle: str,
    proc: asyncio.subprocess.Process | Any,
    cmd: str,
    log_path: Path,
    use_process_group: bool,
    no_output_deadline_s: float = 30.0,
    start_task: bool = True,
) -> JobRecord:
    rec = JobRecord(
        handle=handle,
        pid=int(proc.pid),
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        cmd=cmd,
        log_path=str(log_path.resolve()),
        status="running",
        exit_code=None,
        runtime_ms=0,
        proc=proc,
        use_process_group=use_process_group,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)
    _JOBS[handle] = rec
    _write_meta(rec)
    if start_task:
        rec.task = asyncio.create_task(
            _supervise(rec, no_output_deadline_s=no_output_deadline_s)
        )
    return rec


async def _spawn_job(
    *,
    cmd: str,
    argv: list[str],
    cwd: Path,
    session_id: str,
    no_output_deadline_s: float = 30.0,
) -> str:
    handle = _next_handle(session_id)
    log_path = _log_path(cwd, session_id, handle)
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=(os.name == "posix"),
    )
    _store_record(
        handle=handle,
        proc=proc,
        cmd=cmd,
        log_path=log_path,
        use_process_group=(os.name == "posix"),
        no_output_deadline_s=no_output_deadline_s,
    )
    return handle


def register_job(
    *,
    cmd: str,
    argv: list[str] | None = None,
    cwd: Path | None = None,
    session_id: str = "_nosession",
    proc: asyncio.subprocess.Process | Any | None = None,
    handle: str | None = None,
    log_path: str | Path | None = None,
    no_output_deadline_s: float = 30.0,
) -> str | asyncio.Future:
    if proc is not None:
        job_handle = handle or _next_handle(session_id)
        path = Path(log_path) if log_path is not None else _log_path(Path.cwd(), session_id, job_handle)
        _store_record(
            handle=job_handle,
            proc=proc,
            cmd=cmd,
            log_path=path,
            use_process_group=False,
            no_output_deadline_s=no_output_deadline_s,
            start_task=False,
        )
        return job_handle
    if argv is None or cwd is None:
        raise TypeError("register_job requires argv and cwd when proc is not supplied")
    return _spawn_job(
        cmd=cmd,
        argv=argv,
        cwd=Path(cwd),
        session_id=session_id,
        no_output_deadline_s=no_output_deadline_s,
    )


async def reap_jobs() -> None:
    for rec in list(_JOBS.values()):
        proc = rec.proc
        if proc is None:
            _JOBS.pop(rec.handle, None)
            continue
        if rec.status != "running" or getattr(proc, "returncode", None) is not None:
            if getattr(proc, "returncode", None) is not None:
                rec.exit_code = proc.returncode
                rec.status = "done" if rec.exit_code == 0 else "killed"
                _refresh_runtime(rec)
                _write_meta(rec)
            _JOBS.pop(rec.handle, None)
            continue
        try:
            _kill_tree(proc, signal_mod.SIGTERM, use_process_group=rec.use_process_group)
        except Exception as exc:
            sys.stderr.write(f"lifecycle.reap_jobs: terminate failed: {exc!r}\n")
            continue
        killed_with = "TERM"
        try:
            await asyncio.wait_for(proc.wait(), timeout=_TERM_DEADLINE_S)
        except asyncio.TimeoutError:
            killed_with = "KILL"
            try:
                _kill_tree(
                    proc,
                    signal_mod.SIGKILL,
                    use_process_group=rec.use_process_group,
                )
            except Exception as exc:
                sys.stderr.write(f"lifecycle.reap_jobs: kill failed: {exc!r}\n")
            try:
                await proc.wait()
            except Exception as exc:
                sys.stderr.write(f"lifecycle.reap_jobs: wait failed: {exc!r}\n")
        except Exception as exc:
            sys.stderr.write(f"lifecycle.reap_jobs: wait_for failed: {exc!r}\n")

        rec.exit_code = proc.returncode
        rec.status = "done" if rec.exit_code == 0 and killed_with == "TERM" else "killed"
        _emit_reap(rec, sig_name=killed_with, reason="session_exit")
        _write_meta(rec)
        if rec.task is not None:
            rec.task.cancel()
        _JOBS.pop(rec.handle, None)


def signal_job(handle: str, sig: int) -> bool:
    rec = _JOBS.get(handle)
    if rec is None or rec.proc is None:
        return False
    try:
        rec.proc.send_signal(sig)
    except ProcessLookupError:
        return True
    return True


def monitor_job(handle: str, since_ms: int = 0) -> str:
    rec = _JOBS.get(handle)
    if rec is None:
        return "<error: unknown handle>"
    start = max(0, int(since_ms))
    path = Path(rec.log_path)
    try:
        with path.open("rb") as fh:
            fh.seek(start)
            chunk = fh.read(_MONITOR_CAP_BYTES + 1)
    except OSError as exc:
        return f"<error: {exc}>"
    more = len(chunk) > _MONITOR_CAP_BYTES
    if more:
        chunk = chunk[:_MONITOR_CAP_BYTES]
    cursor = start + len(chunk)
    if rec.status == "running":
        state = "running"
    else:
        state = f"exit {rec.exit_code if rec.exit_code is not None else -1}"
    text = chunk.decode("utf-8", errors="replace")
    if more:
        remaining = max(0, path.stat().st_size - cursor)
        text += f"\n<truncated, {remaining} more bytes — re-monitor with cursor {cursor}>"
    if rec.reap_reason:
        text += f'\nshell.background.reap reason="{rec.reap_reason}"'
    return f"[cursor {cursor}][{state}]\n{text}"


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

    await reap_jobs()

    _SUBPROCESSES.clear()
    _SESSIONS.clear()


def reset_for_tests() -> None:
    for rec in list(_JOBS.values()):
        if rec.task is not None:
            try:
                rec.task.cancel()
            except Exception:
                pass
        proc = rec.proc
        if proc is not None and getattr(proc, "returncode", None) is None:
            _kill_tree(proc, signal_mod.SIGKILL, use_process_group=rec.use_process_group)
    _SUBPROCESSES.clear()
    _SESSIONS.clear()
    _JOBS.clear()
    _HANDLE_COUNTERS.clear()


def _atexit_hook() -> None:
    if not _SUBPROCESSES and not _SESSIONS and not _JOBS:
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

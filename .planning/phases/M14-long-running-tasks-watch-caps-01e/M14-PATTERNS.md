# Phase M14: Long-running Tasks + Watch (CAPS-01e) - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 9 new/modified files
**Analogs found:** 7 / 9 (2 greenfield — flagged below)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/lifecycle.py` (modify) | service | event-driven | itself — extend `_JOBS` / `reap_jobs` / `reset_for_tests` | exact (self-analog) |
| `voss/harness/tools.py` (modify) | service / API | request-response | `shell_run_background` / `shell_monitor` (lines 171–244) | exact |
| `voss/harness/cli.py` (modify) | CLI | request-response | `jobs_cmd` (lines 2115–2175) + `AGENT_COMMANDS` (lines 2878–2902) | exact |
| `voss/harness/watch/__init__.py` | config | — | `voss/harness/mcp/__init__.py` (package marker) | role-match |
| `voss/harness/watch/backend.py` | service | event-driven | no close analog — greenfield (watchdog Observer/Debouncer/asyncio bridge) | none |
| `voss/harness/watch/daemon.py` | utility | request-response | `_spawn_job` / `start_new_session` pattern in `lifecycle.py` lines 330–356 | partial |
| `tests/harness/test_m14_watch.py` | test | event-driven | `tests/harness/test_lifecycle.py` (autouse fixture, async test structure) | role-match |
| `pyproject.toml` (modify) | config | — | existing `psutil>=5.9,<8` pin (line 23) | exact |
| `.github/workflows/ci.yml` (modify) | config | — | existing `ubuntu-latest` matrix entry | role-match |

---

## Pattern Assignments

### `voss/harness/lifecycle.py` (modify — add `_WATCHERS` registry, `reap_watchers`, `_read_log_cursor` factor-out, `reset_for_tests` extension)

**Analog:** itself — the `_JOBS` / `JobRecord` / `reap_jobs` / `reset_for_tests` block

**Registry declaration pattern** (lines 35–40 — copy this structure for `_WATCHERS`):
```python
# _JOBS is separate because background jobs have distinct reap semantics:
# watchdog timers, mid-life signals, and lifetimes beyond the 5s subprocess deadline.
_JOBS: dict[tuple[str, str], "JobRecord"] = {}
_HANDLE_COUNTERS: dict[str, int] = {}
```
New sibling to add immediately after line 40:
```python
# _WATCHERS is separate because watchdog Observer is a thread (no pid/proc);
# it is stopped via observer.stop()/join(), not SIGTERM.
_WATCHERS: dict[tuple[str, str], "WatcherRecord"] = {}
_WATCH_HANDLE_COUNTERS: dict[str, int] = {}
```

**`JobRecord` dataclass pattern** (lines 59–91 — model `WatcherRecord` on this):
```python
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
    session_id: str = field(default="_nosession", repr=False, compare=False)
    proc: asyncio.subprocess.Process | Any | None = field(
        default=None, repr=False, compare=False
    )
    task: asyncio.Task | None = field(default=None, repr=False, compare=False)
    ...
    use_process_group: bool = field(default=False, repr=False, compare=False)
    reap_reason: str | None = field(default=None, repr=False, compare=False)
```
`WatcherRecord` replaces `pid`/`proc`/`use_process_group`/`exit_code`/`runtime_ms` with `observer`/`drain_task`/`debouncer`/`globs`. All other fields (`handle`, `started_at`, `log_path`, `status`, `session_id`, `task`) follow the same `field(default=..., repr=False, compare=False)` convention.

**`_job_dir` / `_log_path` helper pattern** (lines 107–118 — model `_watch_dir` / `_watch_log_path`):
```python
def _job_dir(cwd: Path, session_id: str) -> Path:
    from .sandbox import jail_path
    root = jail_path(cwd, ".voss-cache/jobs")
    root.mkdir(parents=True, exist_ok=True)
    session_dir = jail_path(root, session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def _log_path(cwd: Path, session_id: str, handle: str) -> Path:
    return _job_dir(cwd, session_id) / f"{handle}.log"
```
New helpers: replace `"jobs"` with `"watch"`, rename to `_watch_dir` / `_watch_log_path`.

**`_next_handle` pattern** (lines 276–279 — add `prefix` param to avoid `bg-`/`watch-` collision):
```python
def _next_handle(session_id: str) -> str:
    n = _HANDLE_COUNTERS.get(session_id, 0) + 1
    _HANDLE_COUNTERS[session_id] = n
    return f"bg-{n:03d}"
```
New watch variant — use `_WATCH_HANDLE_COUNTERS` + `"watch"` prefix:
```python
def _next_watch_handle(session_id: str) -> str:
    n = _WATCH_HANDLE_COUNTERS.get(session_id, 0) + 1
    _WATCH_HANDLE_COUNTERS[session_id] = n
    return f"watch-{n:03d}"
```

**`_find_job` lookup pattern** (lines 286–292 — model `_find_watcher`):
```python
def _find_job(handle: str, session_id: str | None = None) -> JobRecord | None:
    if session_id is not None:
        return _JOBS.get(_job_key(session_id, handle))
    matches = [rec for (sid, h), rec in _JOBS.items() if h == handle]
    if len(matches) == 1:
        return matches[0]
    return None
```

**`monitor_job` — extract `_read_log_cursor` from** (lines 454–482 — D-02: factor this into a shared helper):
```python
def monitor_job(handle: str, since_ms: int = 0, *, session_id: str | None = None) -> str:
    rec = _find_job(handle, session_id=session_id)
    if rec is None:
        return f"<error: unknown handle {handle}>"
    start = max(0, int(since_ms))
    path = Path(rec.log_path)
    chunk = b""
    file_size = start
    try:
        with path.open("rb") as fh:
            fh.seek(start)
            chunk = fh.read(_MONITOR_CAP_BYTES)
            file_size = path.stat().st_size
    except FileNotFoundError:
        pass
    except OSError as exc:
        return f"<error: {exc}>"
    cursor = start + len(chunk)
    if rec.status == "running":
        state = "running"
    else:
        state = f"exit {rec.exit_code if rec.exit_code is not None else -1}"
    text = chunk.decode("utf-8", errors="replace")
    if file_size > cursor:
        remaining = max(0, file_size - cursor)
        text += f"\n<truncated, {remaining} more bytes — re-monitor with cursor {cursor}>"
    if rec.reap_reason:
        text += f'\nshell.background.reap reason="{rec.reap_reason}"'
    return f"[cursor {cursor}][{state}]\n{text}"
```
Extract the byte-read block into:
```python
def _read_log_cursor(
    log_path: Path,
    since_ms: int,
    *,
    status: str,
    cap_bytes: int = _MONITOR_CAP_BYTES,
    reap_reason: str | None = None,
) -> str:
    start = max(0, int(since_ms))
    chunk = b""
    file_size = start
    try:
        with log_path.open("rb") as fh:
            fh.seek(start)
            chunk = fh.read(cap_bytes)
            file_size = log_path.stat().st_size
    except FileNotFoundError:
        pass
    except OSError as exc:
        return f"<error: {exc}>"
    cursor = start + len(chunk)
    text = chunk.decode("utf-8", errors="replace")
    if file_size > cursor:
        remaining = max(0, file_size - cursor)
        text += f"\n<truncated, {remaining} more bytes — re-monitor with cursor {cursor}>"
    if reap_reason:
        text += f'\nshell.background.reap reason="{reap_reason}"'
    return f"[cursor {cursor}][{status}]\n{text}"
```
`monitor_job` then becomes a thin wrapper: `return _read_log_cursor(Path(rec.log_path), since_ms, status=state, reap_reason=rec.reap_reason)`.

**`reap_jobs` pattern** (lines 395–440 — model `reap_watchers`):
```python
async def reap_jobs() -> None:
    for key, rec in list(_JOBS.items()):
        proc = rec.proc
        if proc is None:
            _JOBS.pop(key, None)
            continue
        if rec.status != "running" or getattr(proc, "returncode", None) is not None:
            ...
            _JOBS.pop(key, None)
            continue
        try:
            _kill_tree(proc, signal_mod.SIGTERM, use_process_group=rec.use_process_group)
        except Exception as exc:
            sys.stderr.write(f"lifecycle.reap_jobs: terminate failed: {exc!r}\n")
            continue
        ...
        _JOBS.pop(key, None)
```
`reap_watchers` follows the same `for key, rec in list(_WATCHERS.items())` / `_WATCHERS.pop(key, None)` frame, but the kill sequence is `rec.debouncer.cancel_all(); rec.observer.stop(); rec.observer.join(timeout=2.0)` instead of `_kill_tree`.

**`reap_all` call site** (lines 485–521 — add `reap_watchers()` before `reap_jobs()`):
```python
async def reap_all() -> None:
    ...                     # existing subprocess + session reap
    await reap_jobs()       # line 518 — ADD reap_watchers() BEFORE this line
    _SUBPROCESSES.clear()
    _SESSIONS.clear()
```
Add `await reap_watchers()` at line 517 (before `await reap_jobs()`).

**`reset_for_tests` pattern** (lines 524–537 — extend with `_WATCHERS`):
```python
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
```
Add at the top of the function (before `_JOBS`-loop): stop+join each watcher, cancel drain tasks, then `_WATCHERS.clear(); _WATCH_HANDLE_COUNTERS.clear()`.

**`_atexit_hook` guard** (lines 540–561 — extend fast-path guard):
```python
def _atexit_hook() -> None:
    if not _SUBPROCESSES and not _SESSIONS and not _JOBS:   # line 541
        return
```
Change to: `if not _SUBPROCESSES and not _SESSIONS and not _JOBS and not _WATCHERS:`

**`_kill_tree` / `signal_job`** (lines 151–169 / 443–451 — reuse UNCHANGED for `voss watch` child TERM-before-rerun):
```python
def _kill_tree(
    proc: asyncio.subprocess.Process | Any,
    sig: int,
    *,
    use_process_group: bool = True,
) -> None:
    try:
        if os.name == "posix" and use_process_group:
            os.killpg(os.getpgid(proc.pid), sig)
        ...
    except (ProcessLookupError, PermissionError):
        pass
```

**`_spawn_job` daemon-detach precedent** (lines 330–356 — `start_new_session` pattern used by `daemon.py`):
```python
proc = await asyncio.create_subprocess_exec(
    *argv,
    cwd=str(cwd),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    start_new_session=(os.name == "posix"),   # <-- the key precedent
)
```

---

### `voss/harness/tools.py` (modify — add `fs_watch`, `fs_watch_poll` tools + `result` dict entries)

**Analog:** `shell_run_background` (lines 171–203) and `shell_monitor` (lines 205–221)

**Imports pattern** (lines 1–17):
```python
from __future__ import annotations

import asyncio
import json
import os
import signal as _signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from voss_runtime import ToolDescriptor, tool

from .sandbox import jail_path, shell_allowed, split_command, SandboxError
```

**`shell_run_background` tool — allowlist gate to copy for `fs_watch`** (lines 171–203):
```python
@tool(
    name="shell_run_background",
    description=(...),
)
async def shell_run_background(
    cmd: str,
    no_output_deadline_s: float = 30.0,
) -> str:
    ok, reason = shell_allowed(cmd)
    if not ok:
        return f"<denied: {reason}>"
    try:
        argv = split_command(cmd)
    except SandboxError as e:
        return f"<denied: {e}>"
    from . import lifecycle
    return await lifecycle.register_job(
        cmd=cmd,
        argv=argv,
        cwd=cwd,
        session_id=session_id or "_nosession",
        no_output_deadline_s=no_output_deadline_s,
    )
```
`fs_watch` copies the `shell_allowed` + `split_command` gate for its `command` parameter (WATCH-03); the watcher registration itself calls `lifecycle.register_watcher(...)` instead.

**`shell_monitor` tool — cursor-read pattern to copy for `fs_watch_poll`** (lines 205–221):
```python
@tool(
    name="shell_monitor",
    description=(
        "Read incremental output from a background job by handle. since_ms "
        "is an opaque byte cursor (0 = from start); pass back the returned "
        "cursor to continue. Non-blocking. Returns [cursor N][running|exit M] "
        "then the new output."
    ),
)
async def shell_monitor(handle: str, since_ms: int = 0) -> str:
    from . import lifecycle
    return lifecycle.monitor_job(
        handle,
        since_ms=since_ms,
        session_id=session_id or "_nosession",
    )
```
`fs_watch_poll` is structurally identical but calls `lifecycle._find_watcher(handle, session_id=...)` and `lifecycle._read_log_cursor(Path(rec.log_path), since_ms, status=rec.status)`.

**`shell_signal` tool — unknown-handle error pattern** (lines 223–243):
```python
async def shell_signal(handle: str, signal: str) -> str:
    ...
    if not lifecycle.signal_job(handle, sig, session_id=session_id or "_nosession"):
        return f"<error: unknown handle {handle}>"
    return f"[signal {signal} -> {handle}]"
```
`fs_watch` and `fs_watch_poll` use the same `<error: unknown handle {handle}>` guard.

**`result` dict registration pattern** (lines 505–539 — copy `is_mutating` classification):
```python
result = {
    ...
    "shell_run_background": ToolEntry(descriptor=shell_run_background, is_mutating=True),
    "shell_monitor": ToolEntry(descriptor=shell_monitor, is_mutating=False),
    "shell_signal": ToolEntry(descriptor=shell_signal, is_mutating=True),
    ...
}
```
Add after `shell_signal` entry:
```python
"fs_watch": ToolEntry(descriptor=fs_watch, is_mutating=True),   # creates watcher thread + log file
"fs_watch_poll": ToolEntry(descriptor=fs_watch_poll, is_mutating=False),
```

---

### `voss/harness/cli.py` (modify — add `watch_cmd`, add to `AGENT_COMMANDS`)

**Analog:** `jobs_cmd` (lines 2115–2175)

**`jobs_cmd` Click command pattern** (lines 2115–2118):
```python
@click.command("jobs")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def jobs_cmd(cwd_str: str, json_mode: bool) -> None:
    """List background jobs for the current session."""
    cwd = Path(cwd_str).resolve()
    ...
```
`watch_cmd` follows the same `@click.command("watch")` decorator with `--cwd` and adds `--glob` (multiple), `--daemon`, `--debounce-ms` options. The function resolves `cwd = Path(cwd_str).resolve()` on entry — same convention.

**`AGENT_COMMANDS` tuple — insertion point** (lines 2878–2902):
```python
AGENT_COMMANDS = (
    do_cmd,
    ...
    jobs_cmd,          # line 2886 — add watch_cmd immediately after
    inspect_group,
    ...
)
```

**`logs watch` subcommand — must NOT conflict** (lines 2844–2875):
```python
@click.group("logs")
def logs_group() -> None:
    """Tail NDJSON harness telemetry ..."""

@logs_group.command("watch")     # <-- this is logs_group.watch, NOT a top-level "watch"
def logs_watch_cmd(path: Path, poll_interval: float) -> None:
    ...
```
`watch_cmd` is a standalone `@click.command("watch")` (peer of `jobs_cmd`), not attached to any group. No namespace collision.

**`register` function** (lines 2905–2908 — no change needed):
```python
def register(group: click.Group) -> None:
    """Attach all agent commands to a click Group."""
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)
```

---

### `voss/harness/watch/__init__.py` (new — package marker)

**Analog:** Any existing `__init__.py` in `voss/harness/mcp/` or `voss/harness/code/`

No code to copy — empty file or single-line `"""voss.harness.watch — file-watch backend."""`.

---

### `voss/harness/watch/backend.py` (new — GREENFIELD)

**No close analog exists.** This file contains the `watchdog`-specific logic:
- `WatcherRecord` dataclass (mirrors `JobRecord` shape — see lifecycle.py pattern above)
- `_GlobHandler(PatternMatchingEventHandler)` — dispatches to `Debouncer`
- `Debouncer` class with `dict[str, threading.Timer]` + `threading.Lock`
- `_WatchBackend` — owns `asyncio.Queue`, `Debouncer`, `loop.call_soon_threadsafe` bridge
- `drain_loop` coroutine — reads queue, writes JSONL to log file
- `start_watcher(globs, watch_root, log_path, loop, debounce_ms)` async factory

**Contracts (the planner must implement, no copy-from source):**

Pattern shape from RESEARCH.md (all ASSUMED/CITED — not from existing codebase):
```python
# Pattern 1 — Observer schedule (watchdog API)
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

class _GlobHandler(PatternMatchingEventHandler):
    def __init__(self, globs: list[str], debouncer: "Debouncer") -> None:
        super().__init__(patterns=globs, ignore_directories=True, case_sensitive=True)
        self._debouncer = debouncer

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._debouncer.on_event(event.src_path, event.event_type)

# Pattern 2 — Per-path debounce (threading.Timer)
import threading
class Debouncer:
    def on_event(self, path: str, event_type: str) -> None:
        with self._lock:
            existing = self._timers.get(path)
            if existing is not None:
                existing.cancel()
            t = threading.Timer(self._debounce_s, self._fire, args=(path, event_type))
            t.daemon = True   # CRITICAL — prevents pytest hang
            self._timers[path] = t
            t.start()

# Pattern 3 — Thread→asyncio bridge
loop.call_soon_threadsafe(self._queue.put_nowait, record)  # NEVER queue.put_nowait() directly

# Critical flags:
observer.daemon = True   # BEFORE observer.start() — prevents interpreter hang
```

**Module location rationale:** `watch/backend.py` keeps `lifecycle.py` from growing; `lifecycle.py` owns `_WATCHERS` registry + `_read_log_cursor` + `reap_watchers` (the coordination layer), `backend.py` owns the watchdog thread plumbing.

---

### `voss/harness/watch/daemon.py` (new — PARTIAL analog: `_spawn_job`)

**Analog (partial):** `_spawn_job` in `lifecycle.py` (lines 330–356) for the `start_new_session=True` precedent.

**`_spawn_job` pattern to adapt** (lines 340–346):
```python
proc = await asyncio.create_subprocess_exec(
    *argv,
    cwd=str(cwd),
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    start_new_session=(os.name == "posix"),
)
```

`daemon.py` uses `subprocess.Popen` (synchronous, not asyncio) because the daemon detach path does NOT supervise the child:
```python
# From RESEARCH.md Pattern 5 [CITED: docs.python.org/3/library/subprocess.html]
import subprocess, sys

def spawn_detached_worker(argv: list[str]) -> int:
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,   # POSIX: setsid(); mirrors lifecycle.py precedent
    )
    # proc.wait() intentionally NOT called — parent detaches immediately
    return proc.pid
```

**Re-entry guard contract (no analog — planner decides flag name):**
- Strip `--daemon` from argv, add `--_is-worker` (or similar) before re-exec
- Worker path checks for `--_is-worker` flag and skips the detach logic entirely
- Prevents Pitfall 5 (infinite re-spawn loop)

**`_kill_tree` platform guard to reuse** (lines 151–169):
```python
if os.name == "posix" and use_process_group:
    os.killpg(os.getpgid(proc.pid), sig)
```
Same `os.name == "posix"` idiom applies in daemon path.

---

### `tests/harness/test_m14_watch.py` (new)

**Analog:** `tests/harness/test_lifecycle.py`

**`_reset_registries` autouse fixture** (lines 14–18 — copy and extend for watchers):
```python
@pytest.fixture(autouse=True)
def _reset_registries():
    lifecycle.reset_for_tests()
    yield
    lifecycle.reset_for_tests()
```
New `_reset_watchers` (or extend `_reset_registries`) — same shape: call `lifecycle.reset_for_tests()` before and after. Because `reset_for_tests()` is extended in M14 to also clear `_WATCHERS`, the same fixture call is sufficient — no duplicate fixture needed.

**Async test structure** (lines 25–33 — copy imports + pytest.mark.skipif pattern):
```python
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
    ...
```

**Additional test infrastructure needed (no analog):**
- Daemon PID cleanup fixture: `os.kill(daemon_pid, signal.SIGTERM)` in teardown
- Platform skip for event-timing tests: `@pytest.mark.skipif(sys.platform == "win32", reason="Windows non-gating WATCH-05")`
- Poll-with-retry helper (not `time.sleep`) for FSEvents latency on macOS

**`conftest.py`** (in `tests/harness/` — already exists; check if `asyncio_mode = "auto"` is already set):
```python
# tests/harness/conftest.py — already exists; no new fixture needed if reset_for_tests is extended
```

---

### `pyproject.toml` (modify — add `watchdog` runtime dependency)

**Analog:** `psutil>=5.9,<8` line 23 — exact style to copy:
```toml
[project]
dependencies = [
    ...
    "psutil>=5.9,<8",       # <-- copy this pin style
]
```
New line to add immediately after `psutil`:
```toml
    "watchdog>=4.0,<7",
```
Also add to `[project.optional-dependencies] dev` section (line 40–51) for test access:
```toml
dev = [
    ...
    "watchdog>=4.0,<7",
]
```

---

### `.github/workflows/ci.yml` (modify — add `macos-latest` to watch test matrix)

**Analog:** existing `ubuntu-latest` matrix entry (verified from RESEARCH.md — ci.yml read during research phase).

The existing CI runs `ubuntu-latest` + python 3.11/3.12. For WATCH-05 acceptance, add `macos-latest` to the matrix for the WATCH event tests only (or as a separate job), with the comment:
```yaml
# WATCH-05: macOS CI required for FSEvents event delivery acceptance.
# Windows is explicitly non-gating (SPEC WATCH-05).
```

---

## Shared Patterns

### Registry pattern — `_JOBS` / `_WATCHERS` parallelism
**Source:** `voss/harness/lifecycle.py` lines 35–40, 282–292
**Apply to:** all new `_WATCHERS`-touching code in `lifecycle.py`
```python
_job_key = lambda session_id, handle: (session_id, handle)   # shared key type
_JOBS: dict[tuple[str, str], JobRecord] = {}
# New:
_WATCHERS: dict[tuple[str, str], WatcherRecord] = {}
```
Use `_job_key(session_id, handle)` (same function) as the dict key for `_WATCHERS` — no new key function needed.

### Error return format
**Source:** `voss/harness/tools.py` lines 196, 240–242; `lifecycle.py` line 457
**Apply to:** `fs_watch`, `fs_watch_poll`, any new lifecycle lookup
```python
return f"<error: unknown handle {handle}>"
return f"<denied: {reason}>"
return f"<error: {exc}>"
```

### Session ID default
**Source:** `voss/harness/tools.py` lines 200, 218, 240
**Apply to:** all new tool closures and lifecycle calls
```python
session_id=session_id or "_nosession"
```

### `sys.stderr.write` error logging in reap loops
**Source:** `voss/harness/lifecycle.py` lines 411–412, 425–426
**Apply to:** `reap_watchers()`
```python
sys.stderr.write(f"lifecycle.reap_jobs: terminate failed: {exc!r}\n")
# Pattern: f"lifecycle.{function_name}: {description}: {exc!r}\n"
```

### `jail_path` for all user-provided paths
**Source:** `voss/harness/lifecycle.py` line 108; `tools.py` line 102
**Apply to:** `_watch_dir()`, any path derived from `--cwd` or `--glob` in `watch_cmd`
```python
from .sandbox import jail_path
root = jail_path(cwd, ".voss-cache/watch")
```

### `dataclass` with `repr=False, compare=False` for mutable/heavy fields
**Source:** `voss/harness/lifecycle.py` lines 71–79
**Apply to:** `WatcherRecord.observer`, `WatcherRecord.drain_task`, `WatcherRecord.debouncer`
```python
observer: _Observer = field(repr=False, compare=False)
drain_task: asyncio.Task | None = field(default=None, repr=False, compare=False)
debouncer: "Debouncer | None" = field(default=None, repr=False, compare=False)
```

---

## No Analog Found (Greenfield)

Files with no close match in the codebase — planner must use RESEARCH.md patterns instead:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `voss/harness/watch/backend.py` | service | event-driven | No watchdog Observer, no Debouncer, no asyncio.Queue bridge exists anywhere in the codebase. Patterns from RESEARCH.md §Pattern 1–3 are the only reference (status: ASSUMED/CITED). |
| `voss/harness/watch/daemon.py` | utility | request-response | The `start_new_session=True` idiom exists in `lifecycle._spawn_job` (asyncio path) but the synchronous `subprocess.Popen` detach + re-entry guard is new. The re-entry flag name (`--_is-worker` or similar) is Claude's Discretion. |

**Critical contracts planner must specify for these files:**

1. `backend.py` — `WatcherRecord` import location (defined in `lifecycle.py` or `backend.py`?). RESEARCH.md recommends `lifecycle.py` owns the dataclass (parallel to `JobRecord`), `backend.py` owns the `Debouncer` and `_GlobHandler`.

2. `daemon.py` — `spawn_detached_worker(argv)` argv reshaping: strip `--daemon`, inject internal worker flag, confirm whether to use `[sys.executable, "-m", "voss.harness.cli", "watch", ...]` or the `voss` entry point. Planner decides per CONTEXT.md §Claude's Discretion.

---

## Metadata

**Analog search scope:** `voss/harness/lifecycle.py`, `voss/harness/tools.py`, `voss/harness/cli.py`, `tests/harness/test_lifecycle.py`, `pyproject.toml`
**Files scanned:** 5 source files read in full relevant sections
**Pattern extraction date:** 2026-05-18

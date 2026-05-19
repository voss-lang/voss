# Phase M14: Long-running Tasks + Watch (CAPS-01e) — Research

**Researched:** 2026-05-18
**Domain:** File-watch backend (watchdog), thread↔asyncio bridge, daemon detach, T5 lifecycle reuse
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Debounce/coalescing defaults to 200ms, configurable via `fs_watch(globs, debounce_ms=200)`. Satisfies SPEC WATCH-01 "exactly one coalesced event within the window per path."
- **D-02:** Cursor API is an exact mirror of `shell_monitor`/`monitor_job`. Events appended as JSONL lines to `.voss-cache/watch/<session_id>/<handle>.log`. `fs_watch_poll(handle, since_ms=0)` reuses the SAME byte-cursor reader (factor shared, do NOT duplicate).
- **D-03 (HYBRID daemon detach):** Non-daemon = in-process watchdog Observer + child via T5 `register_job`, reaped by T5 unchanged. Daemon = re-spawn self as detached worker subprocess (`start_new_session=True` / new process group, no inherited TTY — reuse T5 `use_process_group` infra) NOT registered in `_JOBS`/`_WATCHERS` so session-exit reap cannot touch it.
- **D-04:** Live watchers live in a NEW sibling `_WATCHERS` registry in `lifecycle.py`, parallel to `_JOBS`. Watchdog Observer is a thread with no pid/proc and does NOT fit `JobRecord`. `_WATCHERS` gets its own teardown pass added to the existing session-exit `reap_all()` path.

### Claude's Discretion

- Exact `_WATCHERS` record dataclass field set
- The shared byte-cursor reader's module location
- Debounce timer implementation detail (per-path timer vs. single sweep)
- Detached-worker re-exec argv shape

### Deferred Ideas (OUT OF SCOPE)

- M9 TUI bottom-pane status strip — deferred to a follow-up phase
- M10 `code_refresh` file-watch hookback — deferred (separate wiring phase)
- Daemon management surface (`voss watch --list/--stop`) — not in M14
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WATCH-01 | watchdog-backed watcher registers glob patterns, coalesces rapid changes within bounded debounce window, lifecycle-managed with T5 `_JOBS` | §Standard Stack, §Architecture Patterns (Debounce, Observer lifecycle), §Code Examples |
| WATCH-02 | `fs_watch(globs)` agent tool + recorder-stream JSONL events + cursor-based read (mirror of T5 `shell_monitor`) | §Architecture Patterns (Thread↔asyncio bridge, Cursor API), §Code Examples |
| WATCH-03 | `voss watch <command>` CLI top-level, re-executes command on change, T5 `register_job` for child, shell allowlist applies | §Architecture Patterns (CLI wiring), §Existing Code Scout |
| WATCH-04 | `--daemon` opt-in survives session exit; non-daemon reap unchanged | §Architecture Patterns (Daemon detach), §Common Pitfalls |
| WATCH-05 | macOS + Linux verified on CI; Windows best-effort/non-gating | §Cross-platform Notes, §Validation Architecture |
</phase_requirements>

---

## Summary

M14 layers `watchdog` on top of the T5 background job engine. The core challenge is the thread boundary: `watchdog.Observer` runs in its own OS thread, while the harness is asyncio. The safe bridge is `loop.call_soon_threadsafe()` to push events into an `asyncio.Queue`, from which a coroutine drains and appends JSONL lines to the watch log file. This is the standard, well-established pattern and it avoids any lock/queue duplication with the existing `monitor_job` path.

The debounce requirement ("exactly one coalesced event within the window per path") is satisfied by a per-path `threading.Timer` pattern: on each event arrival, cancel the existing timer for that path (if any) and start a new one with `debounce_ms=200`. The timer fires only if no further event for the same path arrives within the window. A single `threading.Lock` protects the `{path: Timer}` dict, which is accessed from the watchdog Observer thread.

Daemon survival on POSIX (macOS/Linux) is cleanly achieved with `subprocess.Popen(..., start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`. This calls `setsid()` internally, creating a new process group that has no association with the parent's controlling terminal. T5 already contains the `_kill_tree`/`use_process_group` infrastructure and the D-03 decision confirms that the `--daemon` subprocess must NOT be registered in `_JOBS` or `_WATCHERS` so the session-exit reap pass cannot reach it.

**Primary recommendation:** Use `watchdog>=4.0,<7` pinned in `pyproject.toml` as a runtime dependency alongside the existing `psutil>=5.9,<8`. The `PatternMatchingEventHandler` handles glob→event filtering internally. Wire a single recursive `Observer.schedule()` call per watched directory root (derived from the glob set), with in-handler glob matching confirming each event. Factor `monitor_job`'s byte-cursor read into a standalone helper so both `shell_monitor` and `fs_watch_poll` share it without duplication.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| File-watch backend (glob registration, debounce, event emission) | Harness / Python process | — | Observer is a daemon thread owned by the harness process; JSONL log written by this same process |
| `fs_watch` / `fs_watch_poll` agent tools | API / Harness tool layer | — | Same tier as `shell_run_background` / `shell_monitor`; registered in `make_toolset` |
| `voss watch` CLI command | CLI entry point | Harness (spawns Observer + job) | Click subparser added to `AGENT_COMMANDS`; child process managed by T5 `register_job` |
| `--daemon` detached watch process | OS / detached subprocess | — | Re-spawned `voss watch --daemon` becomes a session-leader that outlives the parent; NOT tracked by harness registries |
| `_WATCHERS` registry + teardown | Harness lifecycle module | — | Parallel to `_JOBS`; teardown added to existing `reap_all()` call site |
| JSONL event log (`.voss-cache/watch/...`) | Filesystem / `.voss-cache` | — | Same layout contract as T5 `.voss-cache/jobs/...`; byte-cursor reader shared |
| Shared byte-cursor reader | Harness lifecycle or new helper module | tools.py (caller) | Factored out of `monitor_job` so both `shell_monitor` and `fs_watch_poll` share exactly one implementation |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `watchdog` | `>=4.0,<7` | File-system event observer (cross-platform) | Official Python ecosystem standard; 14 years of releases; uses FSEvents on macOS, inotify on Linux, ReadDirectoryChangesW on Windows; `PatternMatchingEventHandler` provides built-in glob filtering |
| `psutil` | `>=5.9,<8` (already pinned) | Process tree memory accounting | Already a T5 runtime dep — no change needed |

[VERIFIED: pip index versions watchdog — latest 6.0.0, released 2024-11-01; Python 3.9+ required; project is at 3.11+]

### Supporting (no new installs needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.Queue` | stdlib | Thread-safe bridge between Observer thread and asyncio loop | Use `loop.call_soon_threadsafe(queue.put_nowait, event)` |
| `threading.Timer` | stdlib | Per-path debounce timer; cancel+restart on each event | Preferred over a single sweep timer for per-path granularity |
| `threading.Lock` | stdlib | Protect the `{path: Timer}` debounce dict from race conditions | The Observer thread and any cancellation path both access the dict |
| `subprocess.Popen` | stdlib | Daemon detach via `start_new_session=True` | Only used by `voss watch --daemon`; redirects stdio to `DEVNULL` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `watchdog` | `watchfiles` (Rust-backed, async-native) | watchfiles has no `PatternMatchingEventHandler` equivalent; D-01 explicitly locks watchdog |
| per-path `threading.Timer` | single sweep timer (asyncio `call_later`) | Single sweep requires asyncio loop access from the Observer thread on every event; per-path timer is self-contained and thread-safe |
| `start_new_session=True` | double-fork (daemonize) | Double-fork is more portable but significantly more complex; `start_new_session=True` calls `setsid()` on POSIX and is sufficient for session isolation |

**Installation (new dependency only):**
```bash
pip install "watchdog>=4.0,<7"
```

**pyproject.toml addition (alongside existing `psutil>=5.9,<8`):**
```toml
"watchdog>=4.0,<7",
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `watchdog` | PyPI | ~14 years (2010) | Very high (top-100 Python packages) | github.com/gorakhargosh/watchdog | N/A (slopcheck unavailable) | Approved — widely used, canonical cross-platform FSE library, confirmed via official docs |

[ASSUMED] slopcheck was not installable in this environment. However, `watchdog` is the canonical cross-platform filesystem monitoring library for Python — used by Django, pytest-watch, Jupyter, and hundreds of other major projects. Its legitimacy is HIGH confidence based on official documentation at python-watchdog.readthedocs.io and the PyPI release history (51 versions over 14 years).

**Packages removed due to [SLOP]:** none
**Packages flagged [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
                     ┌──────────────────────────────────────────┐
                     │          voss harness process            │
                     │                                          │
  Agent turn ──────► │  fs_watch(globs)                        │
                     │    │                                     │
                     │    ▼                                     │
                     │  _WATCHERS registry (lifecycle.py)       │
                     │    │                                     │
                     │    ▼                                     │
                     │  WatcherRecord {handle, observer,        │
                     │    globs, log_path, debouncer}           │
                     │    │                                     │
                     │    ▼                                     │
                     │  watchdog.Observer (daemon thread)       │
                     │    │  (FSEvents / inotify / polling)     │
                     │    │                                     │
                     │    │  on_modified(event)                 │
                     │    │    │                                │
                     │    │    ▼                                │
                     │  Debouncer._on_event()  ◄── per-path    │
                     │    [threading.Lock]          Timer       │
                     │    │                                     │
                     │    │ loop.call_soon_threadsafe           │
                     │    ▼                                     │
                     │  asyncio.Queue                          │
                     │    │                                     │
                     │    ▼                                     │
                     │  drain_task (coroutine)                  │
                     │    │ append JSONL line                   │
                     │    ▼                                     │
                     │  .voss-cache/watch/<session>/<handle>.log│
                     │                                          │
  Agent turn ──────► │  fs_watch_poll(handle, since_ms)        │
                     │    │  shared byte-cursor reader          │
                     │    ▼                                     │
                     │  [cursor N][running] {path: ...}         │
                     └──────────────────────────────────────────┘

  voss watch <cmd> (non-daemon):
    CLI ──► Observer in-process + register_job(child) ──► T5 reap on exit

  voss watch --daemon <cmd>:
    CLI ──► Popen(start_new_session=True, stdio=DEVNULL)
              ──► detached worker (NOT in _JOBS/_WATCHERS)
                    ──► survives session exit
```

### Recommended Project Structure

```
voss/harness/
├── lifecycle.py           # ADD: _WATCHERS registry, WatcherRecord, register_watcher,
│                          #      stop_watcher, reap_watchers (new function), factor
│                          #      _read_log_cursor (shared by monitor_job + watch_poll)
├── tools.py               # ADD: fs_watch, fs_watch_poll tools in make_toolset;
│                          #      register in result dict as is_mutating=False for poll,
│                          #      is_mutating=True for register (creates watcher)
├── watch/
│   ├── __init__.py        # package marker
│   ├── backend.py         # WatcherRecord dataclass, Debouncer class (threading.Timer
│   │                      # per-path), _drain_loop coroutine, observer lifecycle helpers
│   └── daemon.py          # voss watch --daemon detach logic (spawn_detached_worker)
└── cli.py                 # ADD: watch_cmd (top-level click command), add to AGENT_COMMANDS
```

**Recommendation on module placement:** Put the new watch logic in a `voss/harness/watch/` subpackage rather than growing `lifecycle.py` further. `lifecycle.py` already defines `_JOBS` — it should own `_WATCHERS` and the factored `_read_log_cursor`, but the Observer/Debouncer implementation lives in `watch/backend.py`.

### Pattern 1: Observer Schedule with PatternMatchingEventHandler

**What:** Register a `PatternMatchingEventHandler` with a `watchdog.Observer` on the nearest common ancestor directory of all globs, with `recursive=True`. The handler's built-in glob matching filters events before the debounce step.

**When to use:** Always — this is the standard pattern. watchdog watches directories, not files; glob filtering happens in the handler.

```python
# Source: python-watchdog.readthedocs.io/en/stable/api.html [CITED]
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

class _GlobHandler(PatternMatchingEventHandler):
    def __init__(self, globs: list[str], debouncer: "Debouncer") -> None:
        # patterns= accepts shell glob patterns; watchdog matches src_path
        super().__init__(
            patterns=globs,
            ignore_directories=True,
            case_sensitive=True,
        )
        self._debouncer = debouncer

    def on_any_event(self, event: FileSystemEvent) -> None:
        # PatternMatchingEventHandler already filtered by glob before calling here
        self._debouncer.on_event(event.src_path, event.event_type)

observer = Observer()
observer.schedule(handler, path=str(watch_root), recursive=True)
observer.start()
# To stop: observer.stop(); observer.join()
```

**Key consideration:** watchdog watches a DIRECTORY. For `**/*.py` you schedule the project root with `recursive=True`. For single-directory globs like `src/*.ts` you can schedule `src/` with `recursive=False`. Multiple globs can share one `Observer.schedule()` call if their root is the same. [CITED: python-watchdog.readthedocs.io]

### Pattern 2: Per-Path Debounce with `threading.Timer`

**What:** A `Debouncer` class maintains a `dict[str, threading.Timer]` keyed by file path. On each event: acquire lock, cancel existing timer for that path (if any), start new 200ms timer. The timer callback fires in the `threading.Timer` thread — which is fine since it calls `loop.call_soon_threadsafe()`.

**When to use:** Required for WATCH-01 "exactly one coalesced event within the window per path." This is the canonical pattern in the watchdog ecosystem. [ASSUMED from multiple community sources; pattern well-established]

```python
# [ASSUMED] — debounce pattern; threading.Timer is [CITED: docs.python.org/3/library/threading]
import threading
from typing import Callable

class Debouncer:
    def __init__(
        self,
        callback: Callable[[str, str], None],
        debounce_ms: int = 200,
    ) -> None:
        self._callback = callback  # called(path, event_type) after window
        self._debounce_s = debounce_ms / 1000.0
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def on_event(self, path: str, event_type: str) -> None:
        with self._lock:
            existing = self._timers.get(path)
            if existing is not None:
                existing.cancel()
            t = threading.Timer(
                self._debounce_s, self._fire, args=(path, event_type)
            )
            t.daemon = True
            self._timers[path] = t
            t.start()

    def _fire(self, path: str, event_type: str) -> None:
        with self._lock:
            self._timers.pop(path, None)
        self._callback(path, event_type)

    def cancel_all(self) -> None:
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            self._timers.clear()
```

**Thread-safety note:** The `_lock` must be acquired for both `_timers` read/write AND `cancel_all`. The `_fire` callback runs in the `Timer`'s thread — NOT the Observer thread and NOT the asyncio loop thread. `call_soon_threadsafe` handles the asyncio boundary. [CITED: docs.python.org/3/library/threading.html]

### Pattern 3: Thread→asyncio Bridge via `loop.call_soon_threadsafe`

**What:** The Observer thread cannot safely call `queue.put_nowait` directly if the queue is an `asyncio.Queue`. The correct bridge is `loop.call_soon_threadsafe(queue.put_nowait, item)`, which schedules the put on the event loop from a foreign thread. [CITED: docs.python.org/3/library/asyncio-eventloop.html]

```python
# [CITED: docs.python.org/3/library/asyncio-eventloop.html]
import asyncio

class _WatchBackend:
    def __init__(self, loop: asyncio.AbstractEventLoop, debounce_ms: int) -> None:
        self._loop = loop
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._debouncer = Debouncer(
            callback=self._on_debounced_event,
            debounce_ms=debounce_ms,
        )

    def _on_debounced_event(self, path: str, event_type: str) -> None:
        # Called from Timer thread — bridge to asyncio
        record = {"path": path, "event_type": event_type}
        self._loop.call_soon_threadsafe(self._queue.put_nowait, record)

    async def drain_loop(self, log_path: Path) -> None:
        """Runs as asyncio task; writes JSONL events to the watch log."""
        import json, time
        with log_path.open("ab", buffering=0) as fh:
            while True:
                try:
                    record = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                record["ts_ms"] = int(time.time() * 1000)
                fh.write((json.dumps(record) + "\n").encode())
```

**Why not direct `fh.write` from Observer thread?** The log file is also read by `fs_watch_poll` which uses the `_read_log_cursor` helper (a byte-offset file read). Raw appends from multiple threads without a lock would corrupt the JSONL lines. Routing through `asyncio.Queue` + a single drain coroutine guarantees serialized writes. [ASSUMED — the asyncio.Queue+drain pattern is the canonical solution; this specific reasoning is logical inference]

### Pattern 4: Shared Byte-Cursor Log Reader (Factoring `monitor_job`)

**What:** D-02 requires `fs_watch_poll` and `shell_monitor` to share the same byte-cursor reader. The existing `monitor_job` in `lifecycle.py` (lines 454–482) contains the reader inline. M14 should extract that reader into a standalone function `_read_log_cursor(log_path, since_ms, status_str)` and call it from both `monitor_job` and the new `watch_poll`.

**Current `monitor_job` byte-cursor logic (extracted from `lifecycle.py:454–482`):**
```python
# [VERIFIED: read from /Users/benjaminmarks/Projects/Voss/voss/harness/lifecycle.py]
def _read_log_cursor(
    log_path: Path,
    since_ms: int,
    *,
    status: str,
    cap_bytes: int = _MONITOR_CAP_BYTES,  # 30720
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

This function is the exact shared primitive. `monitor_job` becomes a thin wrapper passing its `rec` fields; `watch_poll` becomes a thin wrapper passing the `WatcherRecord` fields.

### Pattern 5: Daemon Detach via `start_new_session=True`

**What:** `voss watch --daemon <cmd>` re-spawns itself as a detached worker that is NOT registered in `_JOBS` or `_WATCHERS`. Uses `subprocess.Popen` with `start_new_session=True` (POSIX: calls `setsid()`), stdin/stdout/stderr redirected to `DEVNULL`, and the process is NOT awaited — it is immediately detached.

```python
# [CITED: docs.python.org/3/library/subprocess.html — start_new_session]
# [ASSUMED: argv reshaping specifics]
import subprocess, sys, os

def spawn_detached_worker(argv: list[str]) -> int:
    """Respawn 'voss watch' in detached mode. Returns child PID."""
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,          # don't inherit parent file descriptors
        start_new_session=True,  # POSIX: setsid(); new process group, no TTY
    )
    return proc.pid
    # proc.wait() is intentionally NOT called — parent detaches immediately
```

**Argv reshaping for `--daemon`:** When `voss watch --daemon <cmd>` is invoked, the worker respawns the same CLI with a `--_worker` (or `--headless`) flag so the worker process runs the Observer loop directly without entering the daemon-detach path again. The exact flag name is Claude's Discretion. [ASSUMED: internal flag naming — planner decides]

**T5 `use_process_group` precedent:** T5's `_spawn_job` already uses `start_new_session=(os.name == "posix")` in `asyncio.create_subprocess_exec`. The `_kill_tree` function gates `os.killpg` on `os.name == "posix"` (lifecycle.py:152–169). The daemon detach path reuses the same platform detection idiom. [VERIFIED: read from lifecycle.py]

### Pattern 6: `_WATCHERS` Registry

**What:** A new module-level dict in `lifecycle.py` parallel to `_JOBS`:

```python
# [ASSUMED: field set (Claude's Discretion per CONTEXT.md D-04)]
from dataclasses import dataclass, field
from watchdog.observers import Observer as _Observer

_WATCHERS: dict[tuple[str, str], "WatcherRecord"] = {}

@dataclass
class WatcherRecord:
    handle: str
    globs: list[str]
    log_path: str
    status: str              # "watching" | "stopped"
    session_id: str
    started_at: str
    observer: _Observer      # the watchdog thread object
    drain_task: asyncio.Task | None = field(default=None, repr=False)
    debouncer: "Debouncer | None" = field(default=None, repr=False)
```

**Teardown (added to `reap_all()`):**
```python
# [ASSUMED: teardown ordering]
async def reap_watchers() -> None:
    for key, rec in list(_WATCHERS.items()):
        try:
            rec.debouncer.cancel_all()
            rec.observer.stop()
            rec.observer.join(timeout=2.0)
        except Exception as exc:
            sys.stderr.write(f"lifecycle.reap_watchers: {exc!r}\n")
        if rec.drain_task is not None:
            rec.drain_task.cancel()
        _WATCHERS.pop(key, None)
```

`reap_all()` calls `reap_watchers()` BEFORE `reap_jobs()` (Observer threads produce no new events after being stopped; job reap can then proceed without stray JSONL writes).

### Pattern 7: `voss watch` CLI Placement

**What:** New top-level `voss watch` Click command, registered in `AGENT_COMMANDS` tuple in `cli.py`, positioned after `jobs_cmd`. Distinct from the existing `logs_group` subcommand `logs watch` at line 2844.

```python
# [ASSUMED: exact flag names; based on [VERIFIED: jobs_cmd pattern from cli.py:2115]]
@click.command("watch")
@click.argument("command")
@click.option("--glob", "globs", multiple=True, default=["**/*"],
              help="Glob pattern(s) to watch (repeatable). Default: **/*")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--daemon", "daemon_mode", is_flag=True,
              help="Detach; survive session exit (opt-in).")
@click.option("--debounce-ms", default=200, type=int,
              help="Debounce window in milliseconds (default: 200).")
def watch_cmd(command: str, globs: tuple[str, ...], cwd_str: str,
              daemon_mode: bool, debounce_ms: int) -> None:
    """Watch files and re-run <command> on change."""
    ...
```

**AGENT_COMMANDS addition:**
```python
# In AGENT_COMMANDS tuple (after jobs_cmd):
AGENT_COMMANDS = (
    ...
    jobs_cmd,
    watch_cmd,   # NEW — top-level sibling
    ...
)
```

### Anti-Patterns to Avoid

- **Direct `queue.put_nowait` from Observer thread without `call_soon_threadsafe`:** asyncio data structures are not thread-safe; this causes silently dropped events or corruption. Always bridge via `loop.call_soon_threadsafe`. [CITED: docs.python.org/3/library/asyncio-dev.html]
- **Registering `WatcherRecord` in `_JOBS`:** `JobRecord` requires `pid`; watchdog Observer is a thread. The D-04 decision explicitly blocks this. [VERIFIED: lifecycle.py — `_JOBS` keyed on (session_id, handle) with `JobRecord.pid: int`]
- **Using `PollingObserver` as default:** `PollingObserver` has 1-second default polling interval (not suitable for 200ms debounce tests); reserve it as a fallback for network file systems. The default `Observer` uses FSEvents (macOS) / inotify (Linux) which are event-driven with sub-100ms latency. [CITED: python-watchdog.readthedocs.io/en/stable/api.html]
- **Registering the daemon subprocess in `_JOBS` or `_WATCHERS`:** D-03 is explicit — the daemon worker must NOT be registered so that session-exit reap cannot touch it. [VERIFIED: M14-CONTEXT.md D-03]
- **Duplicating the byte-cursor reader:** D-02 explicitly forbids duplication. The `_read_log_cursor` helper must be factored before `fs_watch_poll` is written. [VERIFIED: M14-CONTEXT.md D-02]
- **Observer.start() without `observer.daemon = True`:** If the Observer thread is not a daemon thread, Python's interpreter will not exit while the observer is running. Set `observer.daemon = True` BEFORE `observer.start()`. [ASSUMED based on Python threading semantics — confirmed by watchdog Observer inheriting from `threading.Thread`]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Glob→file matching | Custom glob evaluator | `PatternMatchingEventHandler(patterns=globs)` | watchdog's built-in handler uses `fnmatch` correctly, including `**` globbing; hand-rolling is a trap for edge cases (dotfiles, symlinks, case sensitivity) |
| Filesystem event dispatch | `select`/`kqueue`/inotify polling loop | `watchdog.Observer` | Platform-specific backend already handles macOS FSEvents, Linux inotify, Windows ReadDirectoryChangesW |
| Process tree kill | Custom signal cascade | `lifecycle._kill_tree()` (already in T5) | T5's `_kill_tree` handles POSIX process groups, SIGTERM→SIGKILL, and Windows `.kill()` |
| Session-exit subprocess reap | New reap loop | `reap_jobs()` (already in T5) | Existing path handles TERM deadline + KILL fallback; non-daemon `voss watch` child uses this unchanged |
| Background job spawn + supervision | Custom subprocess plumbing | `lifecycle.register_job(argv=..., cwd=...)` | T5 already handles pid tracking, output capture, meta.json sidecars, watchdog timers |
| Byte-cursor log read | New log reader | Factored `_read_log_cursor` from `monitor_job` | D-02: one reader, shared. avoids drift between `shell_monitor` and `fs_watch_poll` contract |

---

## Runtime State Inventory

> This phase is GREENFIELD for the watch subsystem (no existing `_WATCHERS`, no existing `watchdog` dependency, no existing `voss watch` command). Skip runtime state migration — there is nothing to rename or migrate.

**Nothing found in any category** — verified by grep on `_WATCHERS`, `watchdog`, and `voss watch` in the codebase: zero hits in production code. [VERIFIED: Bash grep on lifecycle.py, tools.py, cli.py]

---

## Common Pitfalls

### Pitfall 1: Observer Thread Safety — `asyncio.Queue` Without Bridge
**What goes wrong:** Calling `asyncio.Queue.put_nowait()` from the Observer thread (a non-asyncio thread) without `call_soon_threadsafe` corrupts the queue's internal state; events are silently lost or the loop crashes.
**Why it happens:** `asyncio` data structures assume single-threaded access from the event loop; the Observer fires `on_any_event` from its own thread.
**How to avoid:** ALWAYS use `loop.call_soon_threadsafe(queue.put_nowait, item)`. Capture the running loop via `asyncio.get_event_loop()` at Observer creation time (when called from async context) or pass the loop explicitly.
**Warning signs:** Events arrive inconsistently; `asyncio.Queue.qsize()` stays at 0 despite file changes.

### Pitfall 2: Debounce Timer Thread Not a Daemon Thread
**What goes wrong:** If `threading.Timer` instances are not daemon threads, the Python interpreter hangs on exit waiting for pending timers to fire.
**Why it happens:** Default `threading.Thread.daemon = False`; `Timer` inherits.
**How to avoid:** Set `t.daemon = True` before `t.start()` in the `Debouncer.on_event` method.
**Warning signs:** `pytest` hangs after the test function returns; the process does not exit.

### Pitfall 3: Observer Not Joined Before Process Exit
**What goes wrong:** `observer.stop()` signals the observer to stop but does NOT block until the thread exits. If the process exits immediately after `stop()`, the thread may be mid-callback, causing unclosed-file or corrupted-JSONL errors.
**Why it happens:** `Observer.stop()` is asynchronous (sets a stop event); `Observer.join()` blocks until the thread actually terminates.
**How to avoid:** Always call both: `observer.stop(); observer.join(timeout=2.0)`. `reap_watchers()` should do this.
**Warning signs:** Truncated JSONL lines in watch log; `ResourceWarning: unclosed file` in tests.

### Pitfall 4: macOS FSEvents Coalescing vs. Test Timing
**What goes wrong:** macOS FSEvents may coalesce multiple rapid writes to the same file into one event with a latency of up to ~100ms. A test that writes a file and expects an event within 50ms may time out on macOS CI runners.
**Why it happens:** FSEvents is designed for UI applications; it intentionally coalesces events for battery efficiency.
**How to avoid:** Use a test timeout of `debounce_ms * 3 + 300ms` (e.g., 900ms for 200ms debounce) to account for FSEvents latency + debounce window + async dispatch. Write to a `tmp_path` on local disk (not a network share). On CI, prefer `ubuntu-latest` runners for deterministic inotify timing; macOS tests are the WATCH-05 acceptance gate (they must pass but may be slower).
**Warning signs:** Tests pass consistently on Linux/inotify but flake on macOS.

### Pitfall 5: Daemon Worker Re-entry (double-daemon spawn)
**What goes wrong:** The detached daemon worker process also sees `--daemon` in its own argv and tries to spawn another subprocess, creating an infinite chain.
**Why it happens:** The `voss watch --daemon` respawn logic re-executes `sys.argv`.
**How to avoid:** Before entering the daemon-detach path, strip the `--daemon` flag and add an internal `--_is-worker` (or similar) flag. The worker path checks for `--_is-worker` and skips the detach logic entirely.
**Warning signs:** Process tree explodes with nested `voss watch` processes.

### Pitfall 6: `_next_handle` Counter Shared Between `bg-NNN` and `watch-NNN` Handles
**What goes wrong:** If `_WATCHERS` calls `_next_handle(session_id)` (which generates `bg-NNN`), handles conflict with existing background jobs in the same session.
**Why it happens:** `_next_handle` is the shared per-session counter; its prefix is hardcoded to `bg-`.
**How to avoid:** Either (a) add a `prefix` parameter to `_next_handle` so it can emit `watch-NNN`, or (b) maintain a separate `_WATCH_HANDLE_COUNTERS` dict. Option (a) is cleaner — planner decides.
**Warning signs:** `fs_watch_poll("bg-001")` accidentally resolves to a background job handle.

### Pitfall 7: Windows CI Gating
**What goes wrong:** Including `Windows` in the WATCH-01/02 CI matrix makes the build gate on Windows event delivery, which is unreliable in GH Actions due to ReadDirectoryChangesW quirks, NTFS tunneling, and lack of inotify.
**Why it happens:** SPEC WATCH-05 correctly marks Windows as "best-effort, non-gating."
**How to avoid:** CI matrix = `[ubuntu-latest, macos-latest]` for WATCH event tests. Windows runs at most as an `allow-failure` step (or is skipped entirely). Document this in the workflow comment.
**Warning signs:** Green macOS + Linux but red Windows unexpectedly breaks PRs.

---

## Code Examples

### WATCH-01: Glob Registration + Debounce (Full Flow)

```python
# [ASSUMED: full integration; individual components [CITED] as noted inline]
import asyncio
import time
import json
from pathlib import Path
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent
from watchdog.observers import Observer  # [CITED: python-watchdog.readthedocs.io]

class _GlobHandler(PatternMatchingEventHandler):
    def __init__(self, globs: list[str], debouncer: Debouncer) -> None:
        super().__init__(patterns=globs, ignore_directories=True, case_sensitive=True)
        self._debouncer = debouncer

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._debouncer.on_event(event.src_path, event.event_type)

async def start_watcher(
    globs: list[str],
    watch_root: Path,
    log_path: Path,
    loop: asyncio.AbstractEventLoop,
    debounce_ms: int = 200,
) -> tuple[Observer, asyncio.Task]:
    backend = _WatchBackend(loop, debounce_ms)
    handler = _GlobHandler(globs, backend._debouncer)
    observer = Observer()
    observer.daemon = True  # <-- CRITICAL: must be daemon thread
    observer.schedule(handler, str(watch_root), recursive=True)
    observer.start()
    drain = asyncio.create_task(backend.drain_loop(log_path))
    return observer, drain
```

### WATCH-02: `fs_watch_poll` Tool (shared cursor reader)

```python
# [VERIFIED: monitor_job logic from lifecycle.py:454-482]
# [ASSUMED: WatcherRecord field names — planner decides dataclass]
@tool(name="fs_watch_poll", description=(
    "Read incremental watch events by handle. since_ms is opaque byte cursor "
    "(0 = from start). Returns [cursor N][watching|stopped] then JSONL lines."
))
async def fs_watch_poll(handle: str, since_ms: int = 0) -> str:
    from . import lifecycle
    rec = lifecycle._find_watcher(handle, session_id=session_id or "_nosession")
    if rec is None:
        return f"<error: unknown watch handle {handle}>"
    status = rec.status  # "watching" | "stopped"
    return lifecycle._read_log_cursor(
        Path(rec.log_path),
        since_ms,
        status=status,
    )
```

### WATCH-04: Daemon Detach — POSIX `start_new_session=True`

```python
# [CITED: docs.python.org/3/library/subprocess.html]
import subprocess, sys

def spawn_detached_worker(original_argv: list[str]) -> int:
    # Strip --daemon, add --_is-worker to prevent re-entry
    worker_argv = [
        a for a in original_argv if a != "--daemon"
    ] + ["--_is-worker"]
    proc = subprocess.Popen(
        worker_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,  # POSIX: setsid() — new session leader, no TTY
    )
    # Do NOT call proc.wait() — detach immediately
    return proc.pid
```

### T5 Reuse: `register_job` for `voss watch` Child Process

```python
# [VERIFIED: register_job signature from lifecycle.py:359-392]
handle = await lifecycle.register_job(
    cmd=command,
    argv=split_argv,   # from split_command(command) after shell_allowed() check
    cwd=cwd,
    session_id=session_id,
    no_output_deadline_s=30.0,
)
# Returns "bg-NNN" handle; the child is supervised by T5 _supervise coroutine
# On session exit, reap_jobs() TERMs + KILLs this child (T5 path, unchanged)
```

---

## Existing Code Scout — Precise Reuse Seams

### lifecycle.py

| Symbol | Lines | M14 Action |
|--------|-------|------------|
| `_JOBS: dict[tuple[str,str], JobRecord]` | 39 | Model: add `_WATCHERS: dict[tuple[str,str], WatcherRecord]` sibling |
| `_HANDLE_COUNTERS: dict[str, int]` | 40 | Reuse or add `_WATCH_HANDLE_COUNTERS` to avoid `bg-`/`watch-` collision |
| `_next_handle(session_id)` | 276–279 | Add `prefix` param OR add separate `_next_watch_handle` |
| `_job_dir(cwd, session_id)` | 107–114 | Model for `_watch_dir(cwd, session_id)` → `.voss-cache/watch/<session>/` |
| `_log_path(cwd, session_id, handle)` | 117–118 | Model for `_watch_log_path(...)` |
| `monitor_job(handle, since_ms, ...)` | 454–482 | EXTRACT `_read_log_cursor()` from here; `monitor_job` calls it |
| `reap_jobs()` | 395–440 | Model for `reap_watchers()` (Observer.stop()+join() instead of SIGTERM) |
| `reap_all()` | 485–519 | ADD: `await reap_watchers()` call BEFORE `await reap_jobs()` |
| `reset_for_tests()` | 524–537 | ADD: `_WATCHERS.clear()` + `_WATCH_HANDLE_COUNTERS.clear()` |
| `_kill_tree(proc, sig, *, use_process_group)` | 151–169 | Reuse unchanged for pre-re-run TERM of prior child in `voss watch` |
| `signal_job(handle, sig, ...)` | 443–451 | Reuse unchanged for `voss watch` Ctrl-C (signal the child job) |
| `_TERM_DEADLINE_S = 5.0` | 42 | Reuse: watcher teardown join timeout |
| `_atexit_hook()` | 540–561 | No change needed; `reap_all` calls `reap_watchers` which covers watchers |

### tools.py

| Symbol | Lines | M14 Action |
|--------|-------|------------|
| `make_toolset(cwd, *, session_id, ...)` | 78–584 | ADD `fs_watch`, `fs_watch_poll` in the body; add to `result` dict |
| `shell_allowed(cmd)` / `split_command(cmd)` | imported from sandbox | Reuse UNCHANGED for `voss watch <command>` argv validation |
| `shell_run_background` tool | 171–203 | Model for `fs_watch` tool (same allowlist gate pattern) |
| `shell_monitor` tool | 205–221 | Model for `fs_watch_poll` tool (same cursor-read pattern; factor shared reader) |
| `result[...] = ToolEntry(descriptor=..., is_mutating=...)` | 505–539 | Pattern: `"fs_watch": ToolEntry(is_mutating=True)`, `"fs_watch_poll": ToolEntry(is_mutating=False)` |

### cli.py

| Symbol | Lines | M14 Action |
|--------|-------|------------|
| `jobs_cmd` | 2115–2175 | Model for `watch_cmd` (same Click pattern: `--cwd`, `--json`→`--glob`) |
| `AGENT_COMMANDS` tuple | 2878–2902 | ADD `watch_cmd` after `jobs_cmd` |
| `register(group)` | 2905–2908 | No change needed; iterates `AGENT_COMMANDS` |
| `logs_group` / `logs watch` | 2839–2875 | Must NOT conflict with new `watch_cmd`; these are in separate groups |

### Session-exit call site (where `reap_watchers` must hook in)

`reap_all()` at lifecycle.py:485–519 is called from:
1. `_atexit_hook()` at lifecycle.py:540 — via `asyncio.run(reap_all())`
2. `cli.py` `_run_repl` finally block — via `await lifecycle.reap_all()`

Both sites get watcher teardown for free once `reap_watchers()` is added inside `reap_all()`.

---

## Cross-Platform Notes

### macOS (FSEvents / kqueue)

- `watchdog.Observer` defaults to `FSEventsObserver` on macOS. [CITED: github.com/gorakhargosh/watchdog]
- FSEvents has ~100ms delivery latency for rapid writes. Test timeouts must account for: FSEvents latency (~100ms) + debounce window (200ms) + asyncio dispatch + queue drain ≈ 500ms total. Use 1–2s test timeout.
- FSEvents coalesces events for battery efficiency — "multiple writes within a short window may arrive as one modified event." This is COMPATIBLE with M14's debounce requirement but means the Observer may receive fewer raw events than actual file writes.
- `kqueue` (BSD/macOS fallback) is also available but FSEvents is preferred for directory watching.
- **WATCH-05 acceptance:** The WATCH-01/02 event test must pass on macOS CI (`macos-latest` runner). Use generous timeouts.

### Linux (inotify)

- `watchdog.Observer` defaults to `InotifyObserver` on Linux. Event delivery latency: typically < 5ms. [CITED: github.com/gorakhargosh/watchdog]
- inotify is deterministic enough for a 200ms debounce window; a 500ms test timeout is sufficient.
- In watchdog 6.0.0, the inotify implementation switched from `select.select()` to `select.poll()` — no impact on M14 code. [CITED: changelog.rst]
- **Test stability:** Write the file, flush/sync, then poll for the event with a bounded retry loop (e.g., check every 50ms up to 1000ms). Do NOT use a bare `time.sleep(debounce_ms + 50)` — it's brittle on slow CI.

### Windows (ReadDirectoryChangesW)

- watchdog provides `ReadDirectoryChangesW` on Windows. [CITED: github.com/gorakhargosh/watchdog]
- Windows CI (GH Actions) has historically been unreliable for file-watch tests due to NTFS event coalescing, antivirus interference, and timing.
- WATCH-05 explicitly designates Windows as "best-effort, non-gating." CI matrix should be `ubuntu-latest` + `macos-latest` only for WATCH event tests.
- If Windows tests are included, wrap with `pytest.mark.skipif(sys.platform == "win32", ...)` OR use a separate `--allow-failure` CI step.

### `PollingObserver` Fallback

- `PollingObserver` is platform-independent but polls every 1 second by default. [CITED: python-watchdog.readthedocs.io/en/stable/api.html]
- NOT appropriate as the default for M14 (200ms debounce requires sub-200ms event delivery).
- Consider making `PollingObserver` available via an env var (`VOSS_WATCH_POLL=1`) as a fallback for network file systems.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| `select.select()` in inotify backend | `select.poll()` | watchdog 6.0.0 (2024-11-01) | No impact on M14 code; internal to watchdog |
| `watchdog.observer.BaseObserverSubclassCallable` | `ObserverType` | watchdog 5.0.0 (2024-08-26) | Not used in M14 directly |
| Optional keyword args in watchdog 4.x | Mandatory keyword args | watchdog 5.0.0 | `PatternMatchingEventHandler` call must use `patterns=`, `ignore_directories=`, `case_sensitive=` as kwargs, NOT positional |
| Python 3.8 support | Dropped; Python 3.9+ required | watchdog 5.0.0 | Project is on Python 3.11+ — no impact |

**Deprecated/outdated:**
- Positional args to `PatternMatchingEventHandler.__init__`: watchdog 5.0.0 enforces kwargs. [CITED: changelog.rst]
- `observer.isAlive()`: Deprecated in Python 3.9 in favor of `observer.is_alive()`. Use `is_alive()`. [ASSUMED: based on Python threading deprecation; confirmed in watchdog quickstart example]

---

## Validation Architecture

> `nyquist_validation: true` in config.json — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (asyncio_mode=auto) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — already configured |
| Quick run command | `pytest tests/harness/test_m14_watch.py -q -x` |
| Full suite command | `pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WATCH-01 | Edit matching file → exactly one coalesced event within debounce window | Integration | `pytest tests/harness/test_m14_watch.py::test_debounce_coalesces_rapid_writes -x` | ❌ Wave 0 |
| WATCH-01 | Edit non-matching file → zero events | Integration | `pytest tests/harness/test_m14_watch.py::test_non_matching_glob_no_event -x` | ❌ Wave 0 |
| WATCH-01 | `_WATCHERS` registry populated; `reap_watchers()` stops Observer | Unit | `pytest tests/harness/test_m14_watch.py::test_watcher_registry_and_reap -x` | ❌ Wave 0 |
| WATCH-02 | `fs_watch` registers watcher; `fs_watch_poll` reads JSONL in later turn | Integration | `pytest tests/harness/test_m14_watch.py::test_fs_watch_tool_cursor_read -x` | ❌ Wave 0 |
| WATCH-02 | Shared `_read_log_cursor` produces identical output format as `shell_monitor` | Unit | `pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -x` | ❌ Wave 0 |
| WATCH-03 | `voss watch 'pytest -q'` re-executes command when watched file changes | Integration | `pytest tests/harness/test_m14_watch.py::test_voss_watch_reruns_on_change -x` | ❌ Wave 0 |
| WATCH-03 | Shell allowlist enforcement for `voss watch <command>` | Unit | `pytest tests/harness/test_m14_watch.py::test_watch_command_allowlist -x` | ❌ Wave 0 |
| WATCH-04 | Non-daemon `voss watch` is reaped on session exit (SIGTERM ≤ 2s / SIGKILL ≤ 5s) | Integration | `pytest tests/harness/test_m14_watch.py::test_nondaemon_watch_reaped_on_exit -x` | ❌ Wave 0 |
| WATCH-04 | Daemon `voss watch --daemon` is still running after session exits | Integration | `pytest tests/harness/test_m14_watch.py::test_daemon_watch_survives_exit -x` | ❌ Wave 0 |
| WATCH-05 | WATCH-01/02 event test passes on macOS + Linux | CI matrix | GitHub Actions `matrix: [ubuntu-latest, macos-latest]` for `test_debounce_*` | ❌ Wave 0 (CI config) |

### Flakiness Landmines and Mitigations

| Landmine | Platform | Mitigation |
|----------|----------|------------|
| FSEvents batch delivery latency (~100ms) | macOS | Use poll-with-retry loop (50ms interval, 2s max) instead of `sleep(debounce + 50)` |
| Debounce timer thread not joining before assert | All | After triggering event, poll queue/log for event with bounded retry; do NOT `time.sleep(debounce_ms/1000 + 0.1)` — it's always too short or too long |
| Observer not fully started before writing test file | All | After `observer.start()`, brief `time.sleep(0.05)` or probe `observer.is_alive()` with retry before the first file write |
| `threading.Timer` daemon=False hangs pytest | All | Always `t.daemon = True` in Debouncer (see Pitfall 2); test-level fixture calls `reset_for_tests()` which calls `cancel_all()` |
| Multiple rapid writes producing >1 event in test | All | Write file ONCE in test; assert exactly 1 event after window; do not write twice if testing single-event collapse |
| `tmp_path` on a network share (macOS GH Actions) | macOS | Use `tmp_path` from pytest (default is `/private/var/folders/...` on macOS, local FS) — confirm it's not NFS |
| `PollingObserver` used accidentally in test env | All | Tests should explicitly import `from watchdog.observers import Observer` (not `PollingObserver`) unless testing the fallback path |
| Daemon subprocess leaves orphan after test | All | Test for `test_daemon_watch_survives_exit` must record spawned PID and kill it in fixture teardown via `os.kill(pid, SIGTERM)` |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/test_m14_watch.py -q -x`
- **Per wave merge:** `pytest tests/harness/ -q -m "not live" -x`
- **Phase gate:** Full suite green (`pytest -q -m "not live"`) before `/gsd:verify-work`

### Wave 0 Gaps (test infrastructure to create)

- [ ] `tests/harness/test_m14_watch.py` — all WATCH-01..05 tests (10 tests)
- [ ] `_reset_watchers` autouse fixture (mirrors `_reset_registries` in `test_lifecycle.py` — calls `lifecycle.reset_for_tests()` extended with `_WATCHERS.clear()`)
- [ ] Daemon PID cleanup fixture (teardown: `os.kill(daemon_pid, signal.SIGTERM)` with swallow)
- [ ] CI workflow update — add `macos-latest` to the `stub` job matrix OR add a separate `watch-cross-platform` job
- [ ] `watchdog>=4.0,<7` added to `pyproject.toml` `[project] dependencies` and `[project.optional-dependencies] dev`

---

## Security Domain

> `security_enforcement` not set to false in config — section required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes — directory traversal | `jail_path` (sandbox.py) on all paths; `fs_watch` must jail watch root to cwd |
| V5 Input Validation | yes — glob injection, command injection | `shell_allowed` + `split_command` for `voss watch <command>`; restrict glob to project cwd |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Glob escaping cwd (e.g., `../../../etc/passwd`) | Tampering | Resolve watch root via `jail_path(cwd, ".")` — schedule Observer on `cwd`, never on raw user-provided path |
| Command injection via `voss watch` argument | Tampering | `shell_allowed(cmd)` + `split_command(cmd)` (already in T5; same gate) |
| Daemon subprocess inheriting sensitive env vars | Information Disclosure | `subprocess.Popen` inherits env by default; daemon worker should sanitize or pass only required vars (e.g., strip `ANTHROPIC_API_KEY`) |
| Daemon not stopping (no handle) | Denial of Service | Document: `--daemon` watches have no session-bound stop mechanism in M14; user must kill PID manually. Note for backlog: `voss watch --list/--stop` future phase |
| JSONL log readable by other users | Information Disclosure | `.voss-cache/watch/` should inherit the `0o600` mode pattern from T5 (jobs logs are not explicitly chmodded in T5 — this is a low risk in single-user dev scenarios; acceptable for M14) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | watchdog is the canonical PyPI library for this purpose (not watchfiles or similar) | Standard Stack | Low — SPEC explicitly requires watchdog; this is a locked decision |
| A2 | `PatternMatchingEventHandler` in watchdog 5.x/6.x requires keyword args (not positional) | Standard Stack, Code Examples | Medium — wrong calling convention causes TypeError at runtime; verify when pinning version |
| A3 | `observer.daemon = True` must be set before `observer.start()` to prevent interpreter hang | Architecture Patterns, Pitfalls | Medium — if wrong, test suite and process will hang on exit |
| A4 | `threading.Timer` instances must have `.daemon = True` for same reason | Pattern 2, Pitfalls | Medium — same hang risk |
| A5 | The `--_is-worker` internal flag (or equivalent) prevents double-daemon re-entry | Pattern 5, Pitfalls | High — if re-entry guard is absent, daemon spawning loops infinitely |
| A6 | `asyncio.Queue.put_nowait` from a foreign thread is unsafe without `call_soon_threadsafe` | Pattern 3, Pitfalls | High — race condition, data loss |
| A7 | `spawn_detached_worker` should `DEVNULL` all stdio to avoid inheriting parent's TTY | Pattern 5 | Medium — without DEVNULL, daemon process may be killed when parent's session exits (TTY hangup) |
| A8 | CI `macos-latest` runners write `tmp_path` to local APFS, not NFS | Validation Architecture | Low — standard GH Actions runner behavior; if NFS, switch to `PollingObserver` in tests |
| A9 | `_WATCHERS` record dataclass fields (planner-decided) — handle, globs, log_path, status, session_id, started_at, observer, drain_task, debouncer | Pattern 6 | Low — field set is Claude's Discretion; planner adjusts as needed |
| A10 | `reap_watchers()` should run BEFORE `reap_jobs()` in `reap_all()` | Existing Code Scout | Low — ordering matters only if watcher's drain task writes to a job log (it doesn't); either order is safe, but before is cleaner |

---

## Open Questions

1. **`_next_handle` prefix collision (`bg-NNN` vs `watch-NNN`)**
   - What we know: `_next_handle(session_id)` always emits `bg-{n:03d}`. `_find_job` looks up by handle in `_JOBS`.
   - What's unclear: If a watcher gets handle `bg-001` and a background job in the same session also gets `bg-001`, `_find_job("bg-001")` returns the job, not the watcher.
   - Recommendation: Add `prefix: str = "bg"` param to `_next_handle`; watchers use `prefix="watch"`. This is a one-line change and eliminates ambiguity.

2. **`fs_watch` tool mutability classification**
   - What we know: `shell_run_background` is `is_mutating=True`. `shell_monitor` is `is_mutating=False`.
   - What's unclear: `fs_watch` registers a watcher (side effect) but does not mutate files. `is_mutating=True` would deny it in plan-mode.
   - Recommendation: `fs_watch` → `is_mutating=False` (it doesn't write files; the PermissionGate comment says "is_mutating drives mode-tier denial"). This matches `shell_run_background`'s semantic of "starts a process" being mutating — but a watcher has no write side effect. However, it does spawn a thread and write to `.voss-cache`. Planner should confirm.

3. **Daemon worker re-exec argv shape**
   - What we know: D-03 says "re-spawn self as a detached worker subprocess."
   - What's unclear: Does the worker re-exec `sys.argv` (the original `voss watch ...` invocation), `[sys.executable, "-m", "voss.cli", "watch", ...]`, or the installed `voss` entry point?
   - Recommendation: Use `[sys.executable, "-m", "voss.harness.cli", "watch", "--_is-worker", ...]` to be independent of whether `voss` is on PATH. Planner decides.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | runtime (pyproject.toml) | ✓ | 3.11 (CI matrix) | — |
| `watchdog` | WATCH-01..05 | ✗ (not yet installed) | — (latest: 6.0.0) | none — must add as dependency |
| `psutil` | T5 (already pinned) | ✓ | `>=5.9,<8` | — |
| `pytest` / `pytest-asyncio` | WATCH tests | ✓ | pytest 8.x, asyncio_mode=auto | — |
| macOS CI runner | WATCH-05 | ✓ | `macos-latest` (GH Actions) | — |
| Linux CI runner | WATCH-05 | ✓ | `ubuntu-latest` (GH Actions) | — |
| Windows CI runner | WATCH-05 (non-gating) | ✓ (GH Actions) | — | Not required; best-effort only |

**Missing dependencies with no fallback:**
- `watchdog>=4.0,<7` — must be added to `pyproject.toml` `[project] dependencies` before any M14 code can be tested.

**Missing dependencies with fallback:**
- None.

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/voss/harness/lifecycle.py`] — full file read; `_JOBS`, `JobRecord`, `_next_handle`, `monitor_job`, `reap_jobs`, `reap_all`, `reset_for_tests`, `_kill_tree`, `_store_record`, `register_job`
- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/voss/harness/tools.py`] — `make_toolset`, `ToolEntry`, `shell_run_background`, `shell_monitor`, `shell_signal`, tool result dict pattern
- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/voss/harness/cli.py:2115–2175`] — `jobs_cmd` Click pattern
- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/voss/harness/cli.py:2878–2908`] — `AGENT_COMMANDS` tuple, `register()` function
- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/voss/harness/cli.py:2839–2875`] — existing `logs watch` subcommand (must NOT conflict)
- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/pyproject.toml`] — existing dependencies, psutil pin style, dev extras
- [VERIFIED: `/Users/benjaminmarks/Projects/Voss/.github/workflows/ci.yml`] — CI matrix (ubuntu-latest, python 3.11/3.12), test command
- [VERIFIED: `pip index versions watchdog`] — watchdog 6.0.0 latest, 51 versions, 14-year history
- [CITED: python-watchdog.readthedocs.io/en/stable/api.html] — Observer, PatternMatchingEventHandler, PollingObserver, schedule() API
- [CITED: github.com/gorakhargosh/watchdog/blob/master/changelog.rst] — v5.0 and v6.0 breaking changes
- [CITED: docs.python.org/3/library/asyncio-eventloop.html] — `loop.call_soon_threadsafe` specification
- [CITED: docs.python.org/3/library/subprocess.html] — `start_new_session=True`, `DEVNULL`
- [CITED: docs.python.org/3/library/threading.html] — `threading.Timer`, daemon attribute

### Secondary (MEDIUM confidence)

- [gist.github.com/mivade/f4cb26c282d421a62e8b9a341c7c65f6] — asyncio+watchdog bridge pattern using `loop.call_soon_threadsafe`; cross-verified with stdlib asyncio docs

### Tertiary (LOW confidence / ASSUMED)

- Debouncer per-path `threading.Timer` pattern — inferred from multiple community sources; not from an official watchdog doc. Tagged `[ASSUMED]` inline.
- Daemon worker `--_is-worker` re-entry guard flag — design decision, planner-controlled. Tagged `[ASSUMED]`.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — watchdog confirmed on PyPI (6.0.0), 14-year project, official docs read
- Architecture patterns: HIGH — lifecycle.py read in full; reuse seams verified against actual source code
- T5 reuse seams: HIGH — exact line numbers verified from lifecycle.py, tools.py, cli.py
- Debounce implementation: MEDIUM — pattern well-established but exact implementation is Claude's Discretion
- Daemon detach: HIGH — `start_new_session=True` is stdlib + T5 already uses it
- Cross-platform notes: HIGH — watchdog docs + changelog read; CI matrix verified from ci.yml
- Pitfalls: MEDIUM/HIGH — some from docs, some from known Python threading/asyncio semantics

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (watchdog is stable; main risk is a watchdog 6.x → 7.x breaking change)

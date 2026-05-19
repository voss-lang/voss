from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

# Never react to writes inside the harness cache (the watch log itself lives
# under .voss-cache/watch/<handle>.log). Without this a broad glob (e.g. the
# CLI default **/*) would feed the log writes back as events — a self loop.
_IGNORE_PATTERNS = ["*.voss-cache*"]


class _GlobHandler(PatternMatchingEventHandler):
    def __init__(self, globs: list[str], debouncer: "Debouncer") -> None:
        super().__init__(
            patterns=globs,
            ignore_patterns=_IGNORE_PATTERNS,
            ignore_directories=True,
            case_sensitive=True,
        )
        self._debouncer = debouncer

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._debouncer.on_event(str(event.src_path), event.event_type)


class Debouncer:
    def __init__(
        self,
        debounce_s: float,
        callback: Callable[[str, str], None],
    ) -> None:
        self._debounce_s = debounce_s
        self._callback = callback
        self._lock = threading.Lock()
        self._timers: dict[str, threading.Timer] = {}
        self._event_types: dict[str, str] = {}

    def on_event(self, path: str, event_type: str) -> None:
        with self._lock:
            existing = self._timers.get(path)
            if existing is not None:
                existing.cancel()
            self._event_types[path] = event_type
            timer = threading.Timer(self._debounce_s, self._fire, args=(path,))
            timer.daemon = True
            self._timers[path] = timer
            timer.start()

    def _fire(self, path: str) -> None:
        with self._lock:
            self._timers.pop(path, None)
            event_type = self._event_types.pop(path, "modified")
        self._callback(path, event_type)

    def cancel_all(self) -> None:
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
            self._event_types.clear()


class _WatchBackend:
    def __init__(self, debounce_ms: int) -> None:
        self._log_path: Path | None = None
        self._write_lock = threading.Lock()
        self._debouncer = Debouncer(
            max(0, debounce_ms) / 1000,
            self._on_debounced_event,
        )

    def _on_debounced_event(self, path: str, event_type: str) -> None:
        record = {
            "ts_ms": int(time.time() * 1000),
            "event_type": event_type,
            "path": path,
            "src_path": path,
        }
        self._write_record(record)

    def _write_record(self, record: dict[str, Any]) -> None:
        log_path = self._log_path
        if log_path is None:
            return
        line = json.dumps(record, sort_keys=True) + "\n"
        with self._write_lock:
            with log_path.open("ab", buffering=0) as fh:
                fh.write(line.encode("utf-8"))


async def start_watcher(
    globs: list[str],
    watch_root: Path,
    log_path: Path,
    debounce_ms: int = 200,
) -> tuple[Observer, Debouncer]:
    backend = _WatchBackend(debounce_ms)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)
    backend._log_path = log_path
    handler = _GlobHandler(globs, backend._debouncer)
    observer = Observer()
    observer.daemon = True
    observer.schedule(handler, str(watch_root), recursive=True)
    observer.start()
    await asyncio.sleep(0)
    deadline = time.monotonic() + 1.0
    while not observer.is_alive() and time.monotonic() < deadline:
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)
    return observer, backend._debouncer

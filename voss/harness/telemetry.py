"""Structured NDJSON telemetry for local harness debugging.

Enable with VOSS_LOG=1. Optional VOSS_LOG_PATH=<file> appends one JSON object per line.
If VOSS_LOG_PATH is unset, tries Unix fd 3 when open; otherwise writes VOSSLOG-prefixed
lines to stderr (grep-friendly).

Schema tag: voss.log/v1 (field ``v`` == 1).

Event Kinds (T3-03 contract — NET-06 / D-15)
--------------------------------------------
emit() is generic on `data: dict`; the schema below is documentation,
enforced at the T3-05 / T3-06 / T3-07 call sites (no runtime validation
here). Every `url` field MUST be passed through `redact_url` before
emit. Pre-T3 records that lack these kinds round-trip unchanged.

| kind          | required data fields                                                            |
|---------------|---------------------------------------------------------------------------------|
| net.request   | tool: str, url: <redacted>, method: str, started_at: float                      |
| net.response  | tool: str, url: <redacted>, status: int, bytes: int, duration_ms: int           |
| mcp.request   | server: str, tool: str, args: dict (redact_tool_args), started_at: float        |
| mcp.response  | server: str, tool: str, status: "ok"|"error", duration_ms: int, error: str|None |

Invariant (D-15): MCP stdio calls emit `mcp.*` events ONLY; HTTP/HTTPS
calls emit `net.*` events ONLY. The two never overlap on a single hop.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, TextIO
from urllib.parse import urlparse, urlunparse

_V = 1
_LINE_PREFIX = "VOSSLOG"

_sensitive_key_substrings = (
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
)

_SENSITIVE_EXACT = frozenset(
    {"content", "old", "new", "cmd"}  # cmd shortened separately
)

_DEFAULT_ARG_LEN = 160


def enabled() -> bool:
    return os.environ.get("VOSS_LOG", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


_trace_id: ContextVar[str | None] = ContextVar("voss_trace_id", default=None)
_turn_id: ContextVar[str | None] = ContextVar("voss_turn_id", default=None)
_turn_meta: ContextVar[dict[str, Any] | None] = ContextVar("voss_turn_meta", default=None)

_seq_lock = threading.Lock()
_seq = 0

_sink_lock = threading.Lock()
_sink: TextIO | None = None
_sink_kind: str | None = None  # "path" | "fd3" | "stderr"


def ensure_trace_id() -> str:
    tid = _trace_id.get()
    if tid is None:
        tid = uuid.uuid4().hex[:12]
        _trace_id.set(tid)
    return tid


def begin_turn() -> str:
    """Start a logical agent turn; returns turn id."""
    ensure_trace_id()
    tid = uuid.uuid4().hex[:12]
    _turn_id.set(tid)
    _turn_meta.set({})
    return tid


def clear_turn() -> None:
    _turn_id.set(None)
    _turn_meta.set(None)


def note_turn(**fields: Any) -> None:
    """Attach keys merged into turn.end (e.g. cost_usd, step_count)."""
    cur = dict(_turn_meta.get() or {})
    cur.update({k: v for k, v in fields.items() if v is not None})
    _turn_meta.set(cur)


def redact_tool_args(args: dict[str, Any]) -> dict[str, Any]:
    """Shallow redaction for tool argument telemetry."""
    verbose = os.environ.get("VOSS_LOG_VERBOSE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    max_len = 800 if verbose else _DEFAULT_ARG_LEN
    out: dict[str, Any] = {}
    for k, v in args.items():
        lk = str(k).lower()
        if lk in _SENSITIVE_EXACT and lk != "cmd":
            out[k] = f"<{len(str(v))} chars>" if verbose else "<redacted>"
            continue
        if any(s in lk for s in _sensitive_key_substrings):
            out[k] = "<redacted>"
            continue
        if lk == "cmd" and isinstance(v, str) and not verbose:
            parts = v.strip().split()
            out[k] = parts[0] if parts else ""
            continue
        if isinstance(v, str) and len(v) > max_len:
            out[k] = v[: max_len - 1] + "…"
        else:
            out[k] = v
    return out


def redact_url(url: str) -> str:
    """Strip query string, fragment, and userinfo from a URL.

    Preserves scheme, host, port, and path. Telemetry-safe: returns the
    sentinel '<redacted-url>' on parse failure so emit sites never raise.

    Userinfo (`user:pass@`) is dropped via `p.hostname`, which excludes
    credentials by definition. Port is preserved when present.
    """
    if not isinstance(url, str):
        return "<redacted-url>"
    try:
        p = urlparse(url)
        host = p.hostname or ""
        netloc = host if p.port is None else f"{host}:{p.port}"
        clean = p._replace(query="", fragment="", netloc=netloc)
        out = urlunparse(clean)
        return out if isinstance(out, str) else "<redacted-url>"
    except Exception:
        return "<redacted-url>"


def _open_sink() -> tuple[TextIO, str]:
    global _sink, _sink_kind
    path = os.environ.get("VOSS_LOG_PATH", "").strip()
    if path:
        fh = open(path, "a", encoding="utf-8", buffering=1)
        return fh, "path"
    try:
        os.fstat(3)
    except OSError:
        pass
    else:
        fh = open(3, "w", encoding="utf-8", buffering=1, closefd=False)
        return fh, "fd3"
    import sys

    return sys.stderr, "stderr"


def _get_sink() -> tuple[TextIO, str]:
    global _sink, _sink_kind
    if _sink is not None:
        return _sink, _sink_kind or "reuse"
    with _sink_lock:
        if _sink is None:
            _sink, _sink_kind = _open_sink()
    return _sink, _sink_kind or "?"


def _next_seq() -> int:
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq


def emit(
    kind: str,
    level: str,
    msg: str | None = None,
    *,
    data: dict[str, Any] | None = None,
) -> None:
    """Emit one telemetry event (no-op if VOSS_LOG is off)."""
    if not enabled():
        return
    payload: dict[str, Any] = {
        "v": _V,
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "seq": _next_seq(),
        "trace": ensure_trace_id(),
        "turn": _turn_id.get(),
        "kind": kind,
        "level": level,
    }
    if msg:
        payload["msg"] = msg
    if data:
        payload["data"] = data
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sink, kind_sink = _get_sink()
    try:
        if kind_sink == "stderr":
            sink.write(f"{_LINE_PREFIX}{line}\n")
        else:
            sink.write(line + "\n")
        sink.flush()
    except OSError:
        pass


def emit_harness_start(*, backend: str, cwd: str, model: str | None = None) -> None:
    emit(
        "harness.lifecycle",
        "info",
        "harness start",
        data={"phase": "start", "backend": backend, "cwd": cwd, "model": model},
    )


def finalize_turn(ok: bool, error: str | None) -> None:
    """Emit ``turn.end`` and reset turn context (pair with ``begin_turn``)."""
    meta = dict(_turn_meta.get() or {})
    emit(
        "turn.end",
        "info" if ok else "error",
        data={"ok": ok, "error": error, **meta},
    )
    clear_turn()


def reset_session_sink() -> None:
    """Close log sink (for tests)."""
    global _sink, _sink_kind, _seq
    with _sink_lock:
        if _sink is not None and _sink_kind in ("path", "fd3"):
            try:
                _sink.flush()
                _sink.close()
            except OSError:
                pass
        _sink = None
        _sink_kind = None
    with _seq_lock:
        _seq = 0
    _trace_id.set(None)
    _turn_id.set(None)
    _turn_meta.set(None)

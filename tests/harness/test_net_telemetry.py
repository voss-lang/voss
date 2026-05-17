"""NET-06 acceptance tests for redact_url + net.* / mcp.* event shapes."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from voss.harness import telemetry
from voss.harness.session import RunRecord
from voss.harness.telemetry import redact_url


@pytest.fixture(autouse=True)
def _reset_sink():
    telemetry.reset_session_sink()
    yield
    telemetry.reset_session_sink()


def test_redact_url_strips() -> None:
    """NET-06a: query, fragment, and userinfo stripped."""
    assert redact_url("https://x.com/p?k=v#f") == "https://x.com/p"
    assert (
        redact_url("https://api.example.com/v1/search?token=abc#section")
        == "https://api.example.com/v1/search"
    )
    # Userinfo stripping (Claude's Discretion 5 / Pattern 6).
    assert redact_url("https://user:pass@host/path?k=v") == "https://host/path"
    assert (
        redact_url("https://user:pass@host:8443/p?k=v#f")
        == "https://host:8443/p"
    )


def test_redact_url_noop() -> None:
    """NET-06b: no-op on clean URLs; port preserved; sentinel on bad input."""
    assert redact_url("https://x.com/p") == "https://x.com/p"
    # Port preservation.
    assert redact_url("https://x.com:8443/p") == "https://x.com:8443/p"
    # Empty string round-trips to empty (urllib does not raise).
    assert redact_url("") == ""
    # urllib parses bare tokens as a path-only URL; no exception, returns
    # the input unchanged. Pinned behavior.
    assert redact_url("not-a-url") == "not-a-url"
    # Non-string input hits the sentinel guard.
    assert redact_url(None) == "<redacted-url>"  # type: ignore[arg-type]
    assert redact_url(12345) == "<redacted-url>"  # type: ignore[arg-type]


def _emit_to_logfile(monkeypatch, tmp_path: Path) -> Path:
    """Wire VOSS_LOG to a tmp NDJSON file and return its path."""
    logf = tmp_path / "events.ndjson"
    monkeypatch.setenv("VOSS_LOG", "1")
    monkeypatch.setenv("VOSS_LOG_PATH", str(logf))
    telemetry.reset_session_sink()
    telemetry.ensure_trace_id()
    telemetry.begin_turn()
    return logf


def _read_events(logf: Path) -> list[dict]:
    telemetry.reset_session_sink()
    return [json.loads(ln) for ln in logf.read_text().splitlines() if ln.strip()]


def test_event_emission(monkeypatch, tmp_path: Path) -> None:
    """NET-06c: net.request / net.response carry redacted URLs."""
    logf = _emit_to_logfile(monkeypatch, tmp_path)
    raw = "https://api.example.com/v1?token=secret"
    safe = redact_url(raw)
    telemetry.emit(
        "net.request",
        "info",
        data={"tool": "web_fetch", "url": safe, "method": "GET", "started_at": 0.0},
    )
    telemetry.emit(
        "net.response",
        "info",
        data={
            "tool": "web_fetch",
            "url": safe,
            "status": 200,
            "bytes": 123,
            "duration_ms": 50,
        },
    )

    events = _read_events(logf)
    net_events = [e for e in events if e["kind"].startswith("net.")]
    assert [e["kind"] for e in net_events] == ["net.request", "net.response"]
    for e in net_events:
        assert e["data"]["url"] == "https://api.example.com/v1"
        assert "token" not in e["data"]["url"]
        assert "secret" not in json.dumps(e["data"])


def test_mcp_events(monkeypatch, tmp_path: Path) -> None:
    """NET-06d: mcp.request / mcp.response shape; no net.* events."""
    logf = _emit_to_logfile(monkeypatch, tmp_path)
    telemetry.emit(
        "mcp.request",
        "info",
        data={
            "server": "filesystem",
            "tool": "read_text_file",
            "args": {"path": "./README.md"},
            "started_at": 0.0,
        },
    )
    telemetry.emit(
        "mcp.response",
        "info",
        data={
            "server": "filesystem",
            "tool": "read_text_file",
            "status": "ok",
            "duration_ms": 12,
            "error": None,
        },
    )

    events = _read_events(logf)
    kinds = [e["kind"] for e in events]
    mcp_kinds = [k for k in kinds if k.startswith("mcp.")]
    assert mcp_kinds == ["mcp.request", "mcp.response"]
    # D-15: MCP stdio calls emit mcp.*, not net.*.
    assert not any(k.startswith("net.") for k in kinds)


def test_run_record_roundtrip() -> None:
    """NET-06e: pre-T3 RunRecord shape round-trips without schema migration.

    The events list lives on the telemetry NDJSON, not on RunRecord
    itself; the additive-schema invariant we verify here is that loading
    a record produced before the T3 event kinds existed still works
    against the current dataclass (no missing-field errors).
    """
    pre_t3 = RunRecord(
        id="r-1",
        started_at="2026-01-01T00:00:00",
        ended_at="2026-01-01T00:00:01",
        goal="pre-T3 record",
    )
    blob = json.dumps(asdict(pre_t3))
    rehydrated = RunRecord(**json.loads(blob))
    assert rehydrated.id == "r-1"
    assert rehydrated.goal == "pre-T3 record"
    assert rehydrated.iterations == []
    assert rehydrated.exit_reason is None
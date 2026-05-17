"""NET-01 web_fetch acceptance: registration, allow_net gate, 1 MB
truncation, timeout clamp, HTTP error envelope. Plus redaction + rate-
limit-envelope bonus coverage."""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import httpx
import pytest

from voss.harness import telemetry
from voss.harness.net import MAX_BYTES, NetSession
from voss.harness.tools import make_toolset
from voss_runtime._config import configure, reset_config


@pytest.fixture(autouse=True)
def _reset():
    reset_config()
    configure(allow_net=True)
    yield
    reset_config()


def make_mock_handler(
    *, status=200, body=b"", content_type="text/plain", reason="OK", headers=None
):
    def handler(request: httpx.Request) -> httpx.Response:
        hdr = {"content-type": content_type}
        if headers:
            hdr.update(headers)
        return httpx.Response(
            status_code=status, content=body, headers=hdr, extensions={"reason_phrase": reason.encode()}
        )

    return handler


def make_session(handler) -> NetSession:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        transport=transport, follow_redirects=True, max_redirects=5
    )
    return NetSession(client=client)


async def test_registration(tmp_path: Path) -> None:
    """NET-01a: web_fetch registered, is_network=True, is_mutating=False."""
    toolset = make_toolset(
        tmp_path, net=make_session(make_mock_handler(body=b"x"))
    )
    assert "web_fetch" in toolset
    assert toolset["web_fetch"].is_network is True
    assert toolset["web_fetch"].is_mutating is False


async def test_allow_net_gate(tmp_path: Path) -> None:
    """NET-01b: net=None → disabled-error envelope; no socket opened."""
    calls = [0]

    def counter(request: httpx.Request) -> httpx.Response:
        calls[0] += 1
        return httpx.Response(200, content=b"unreachable")

    toolset = make_toolset(tmp_path, net=None)
    result = await toolset["web_fetch"].invoke_dict({"url": "https://x.com"})
    assert result.startswith("<error: net disabled:")
    assert calls[0] == 0


async def test_truncation(tmp_path: Path) -> None:
    """NET-01c: >1 MB body truncates at exactly MAX_BYTES + marker."""
    big_body = b"a" * (2 * 1024 * 1024)
    session = make_session(make_mock_handler(body=big_body))
    result = await session.fetch("https://x.com")
    assert (
        "<truncated: response exceeded 1 MB cap "
        "(full size: 2097152 bytes)>" in result
    )
    # First MAX_BYTES chars decode-equal to first MAX_BYTES bytes of body.
    head = result.split("\n<truncated:")[0]
    assert head.encode("utf-8")[:MAX_BYTES] == big_body[:MAX_BYTES]
    assert len(head.encode("utf-8")) == MAX_BYTES


async def test_timeout_clamp(tmp_path: Path) -> None:
    """NET-01d: out-of-range timeout_s clamps with RuntimeWarning."""
    session = make_session(make_mock_handler(body=b"ok"))

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = await session.fetch("https://x.com", timeout_s=200.0)
    assert result == "ok"
    rt = [x for x in w if issubclass(x.category, RuntimeWarning)]
    assert len(rt) == 1
    assert "clamping" in str(rt[0].message)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = await session.fetch("https://x.com", timeout_s=0.0)
    assert result == "ok"
    assert any(issubclass(x.category, RuntimeWarning) for x in w)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = await session.fetch("https://x.com", timeout_s=15.0)
    assert result == "ok"
    assert [x for x in w if issubclass(x.category, RuntimeWarning)] == []


async def test_http_errors(tmp_path: Path) -> None:
    """NET-01e: 4xx/5xx return <error: http N: reason>, never raise."""
    for status, reason in (
        (404, "Not Found"),
        (500, "Internal Server Error"),
        (503, "Service Unavailable"),
    ):
        session = make_session(
            make_mock_handler(status=status, reason=reason)
        )
        result = await session.fetch("https://x.com")
        assert result == f"<error: http {status}: {reason}>"


async def test_redact_url_in_emit(tmp_path: Path, monkeypatch) -> None:
    """Every emit routes url through redact_url; no secret escapes."""
    captured: list[dict] = []

    monkeypatch.setattr(telemetry, "enabled", lambda: True)
    monkeypatch.setattr(
        telemetry,
        "emit",
        lambda kind, level, msg=None, *, data=None: captured.append(
            {"kind": kind, "data": data or {}}
        ),
    )

    session = make_session(make_mock_handler(body=b"ok"))
    await session.fetch("https://api.example.com/v1?token=secret")

    assert captured, "expected net.request / net.response events"
    for ev in captured:
        blob = repr(ev["data"])
        assert "token=secret" not in blob
    assert any(
        ev["data"].get("url") == "https://api.example.com/v1"
        for ev in captured
    )


async def test_rate_limit_returns_envelope(tmp_path: Path) -> None:
    """Exhausted bucket → <error: rate limit: retry after Ns> envelope."""
    transport = httpx.MockTransport(make_mock_handler(body=b"ok"))
    client = httpx.AsyncClient(transport=transport)
    session = NetSession(
        client=client, rate_overrides={"web_fetch": {"rate": 1, "burst": 1}}
    )
    first = await session.fetch("https://x.com")
    assert first == "ok"
    second = await session.fetch("https://x.com")
    assert re.match(r"<error: rate limit: retry after \d+s>", second), second

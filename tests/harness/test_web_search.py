"""NET-02 web_search acceptance tests.

These tests target the planned Brave-backed NetSession.search API. They
intentionally defer implementation-specific imports until runtime so this
file still collects while Task 1 is being integrated by another worker.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import httpx
import pytest

from voss.harness.net import NetSession
from voss.harness.tools import make_toolset
from voss_runtime._config import configure, get_config, reset_config


DISABLED_SEARCH = (
    "<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>"
)

BRAVE_10_RESULTS = {
    "web": {
        "results": [
            {
                "title": f"Title {i}",
                "url": f"https://example.com/{i}",
                "description": f"Desc {i}",
            }
            for i in range(10)
        ]
    }
}


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    reset_config()
    configure(allow_net=True)
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    yield
    reset_config()


def make_handler(*, status=200, response=None, headers=None, calls=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        if response is not None:
            return httpx.Response(
                status_code=status, json=response, headers=headers or {}
            )
        return httpx.Response(status_code=status, headers=headers or {})

    return handler


def make_session(handler) -> NetSession:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return NetSession(client=client)


async def test_no_key(monkeypatch, tmp_path: Path) -> None:
    """NET-02a: missing BRAVE_SEARCH_API_KEY returns disabled envelope."""
    calls: list[httpx.Request] = []
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    session = make_session(make_handler(calls=calls))

    result = await session.search("python asyncio", 10)

    assert get_config().allow_net is True
    assert result == DISABLED_SEARCH
    assert calls == []


async def test_mocked_results(monkeypatch) -> None:
    """NET-02b: mocked Brave response renders 10 results in API order."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key")
    session = make_session(make_handler(response=BRAVE_10_RESULTS))

    result = await session.search("python", 10)

    assert isinstance(result, str)
    assert "1. Title 0" in result
    assert "https://example.com/0" in result
    assert "Desc 0" in result
    assert "10. Title 9" in result
    order = re.findall(r"^\d+\. Title (\d+)", result, re.MULTILINE)
    assert order == [str(i) for i in range(10)]


async def test_count_clamp(monkeypatch) -> None:
    """NET-02c: count clamps to [1, 20] with RuntimeWarning."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key")

    high_calls: list[httpx.Request] = []
    high_session = make_session(
        make_handler(response=BRAVE_10_RESULTS, calls=high_calls)
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await high_session.search("foo", count=50)

    runtime_warnings = [
        w for w in caught if issubclass(w.category, RuntimeWarning)
    ]
    assert len(runtime_warnings) == 1
    assert "outside [1, 20]" in str(runtime_warnings[0].message)
    assert "clamping" in str(runtime_warnings[0].message)
    assert high_calls[0].url.params.get("count") == "20"

    low_calls: list[httpx.Request] = []
    low_session = make_session(
        make_handler(response=BRAVE_10_RESULTS, calls=low_calls)
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await low_session.search("foo", count=0)

    runtime_warnings = [
        w for w in caught if issubclass(w.category, RuntimeWarning)
    ]
    assert len(runtime_warnings) == 1
    assert "outside [1, 20]" in str(runtime_warnings[0].message)
    assert "clamping" in str(runtime_warnings[0].message)
    assert low_calls[0].url.params.get("count") == "1"


async def test_429_handling(monkeypatch) -> None:
    """NET-02d: Brave 429 maps to the specified rate-limit envelopes."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key")

    session = make_session(
        make_handler(status=429, headers={"Retry-After": "30"})
    )
    result = await session.search("foo", 10)
    assert result == "<error: rate limit: retry after 30s>"

    session = make_session(make_handler(status=429))
    result = await session.search("foo", 10)
    assert result == "<error: http 429: rate limited by backend>"


async def test_dedup_url(monkeypatch) -> None:
    """Bonus: duplicate result URLs are dropped; first occurrence wins."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key")
    response = {
        "web": {
            "results": [
                {
                    "title": "A",
                    "url": "https://x.com/",
                    "description": "first",
                },
                {
                    "title": "B",
                    "url": "https://y.com/",
                    "description": "second",
                },
                {
                    "title": "C",
                    "url": "https://x.com/",
                    "description": "DUP",
                },
            ]
        }
    }
    session = make_session(make_handler(response=response))

    result = await session.search("foo", 10)

    assert "first" in result
    assert "second" in result
    assert "DUP" not in result
    assert "1. A" in result
    assert "2. B" in result
    assert re.search(r"^3\.", result, re.MULTILINE) is None


async def test_disabled_when_net_is_none(
    tmp_path: Path, monkeypatch
) -> None:
    """Bonus: tool body short-circuits when net is disabled."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key")
    toolset = make_toolset(tmp_path, net=None)

    result = await toolset["web_search"].invoke_dict({"query": "foo"})

    assert result.startswith("<error: net disabled:")

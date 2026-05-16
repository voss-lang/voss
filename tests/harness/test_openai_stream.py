"""T1-03 Task 2: OpenAIOAuthProvider.stream() — Responses-API SSE decode + refresh + cancel."""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from voss.harness import auth as A
from voss.harness.agent import Plan
from voss.harness.providers import (
    Done,
    OpenAIOAuthProvider,
    ParsedPlan,
    TextDelta,
    Usage,
)


FIXTURE = Path(__file__).parent / "fixtures" / "openai_stream_plan.sse"


def _creds(mode: str = "chatgpt") -> A.CodexCreds:
    return A.CodexCreds(
        api_key=None if mode == "chatgpt" else "sk-A",
        access_token="acc",
        refresh_token="ref",
        account_id="acct_42",
        auth_mode=mode,
    )


def _sse_response(body_bytes: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        content=body_bytes,
        headers={"content-type": "text/event-stream"},
    )


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_stream_emits_documented_event_sequence() -> None:
    body = FIXTURE.read_bytes()
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = req.content.decode()
        captured["headers"] = dict(req.headers)
        captured["url"] = str(req.url)
        return _sse_response(body)

    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock_client(handler))
    events = []
    async for ev in p.stream(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-5",
        response_format=Plan,
    ):
        events.append(ev)

    # Documented sequence: TextDelta * 4, Usage, ParsedPlan, Done.
    types = [type(e).__name__ for e in events]
    assert types == [
        "TextDelta",
        "TextDelta",
        "TextDelta",
        "TextDelta",
        "Usage",
        "ParsedPlan",
        "Done",
    ]

    full = "".join(e.text for e in events if isinstance(e, TextDelta))
    assert "test rationale" in full

    usage = next(e for e in events if isinstance(e, Usage))
    assert usage.prompt_tokens == 120
    assert usage.completion_tokens == 60

    parsed = next(e for e in events if isinstance(e, ParsedPlan))
    assert isinstance(parsed.plan, Plan)
    assert parsed.plan.rationale == "test rationale"
    assert parsed.plan.confidence == pytest.approx(0.92)
    assert parsed.plan.final_when_done == "done"

    done = events[-1]
    assert isinstance(done, Done)
    assert done.stop_reason == "completed"

    # Request shape: stream=true + chatgpt-account-id header.
    assert '"stream":true' in captured["body"].replace(" ", "")
    assert captured["headers"].get("chatgpt-account-id") == "acct_42"


@pytest.mark.asyncio
async def test_stream_refreshes_on_401(monkeypatch) -> None:
    body = FIXTURE.read_bytes()
    call_count = {"n": 0}
    refresh_calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(401, content=b'{"error":"unauthorized"}')
        return _sse_response(body)

    refreshed_creds = A.CodexCreds(
        api_key=None,
        access_token="NEW",
        refresh_token="R2",
        account_id="acct_42",
        auth_mode="chatgpt",
    )

    def fake_refresh(creds):
        refresh_calls["n"] += 1
        return refreshed_creds

    monkeypatch.setattr("voss.harness.providers.auth.refresh_codex", fake_refresh)

    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock_client(handler))
    events = []
    async for ev in p.stream(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-5",
        response_format=Plan,
    ):
        events.append(ev)

    assert refresh_calls["n"] == 1
    assert call_count["n"] == 2
    assert any(isinstance(e, ParsedPlan) for e in events)
    assert isinstance(events[-1], Done)
    assert p.creds.access_token == "NEW"


@pytest.mark.asyncio
async def test_stream_cancel_closes_connection() -> None:
    close_count = {"n": 0}

    class CountingStream(httpx.AsyncByteStream):
        def __init__(self, chunks: list[bytes]):
            self._chunks = chunks

        async def __aiter__(self):
            for c in self._chunks:
                await asyncio.sleep(0)
                yield c

        async def aclose(self) -> None:
            close_count["n"] += 1

    chunks = [
        b'event: response.output_text.delta\ndata: '
        b'{"type":"response.output_text.delta","delta":"x"}\n\n',
    ] * 200

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            stream=CountingStream(chunks),
            headers={"content-type": "text/event-stream"},
        )

    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock_client(handler))
    gen = p.stream(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-5",
        response_format=Plan,
    )
    seen_text = False
    async for ev in gen:
        if isinstance(ev, TextDelta):
            seen_text = True
            break

    assert seen_text
    await gen.aclose()
    assert close_count["n"] >= 1

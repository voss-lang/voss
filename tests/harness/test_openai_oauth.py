"""OpenAI OAuth provider — request shape for ChatGPT and api-key modes."""
from __future__ import annotations

import json

import httpx
import pytest

from voss.harness import auth as A
from voss.harness.agent import Plan
from voss.harness.providers import OpenAIOAuthProvider


def _creds(mode: str = "chatgpt") -> A.CodexCreds:
    return A.CodexCreds(
        api_key=None if mode == "chatgpt" else "sk-A",
        access_token="acc",
        refresh_token="ref",
        account_id="acct_42",
        auth_mode=mode,
    )


def _mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _sse_response(
    *deltas: str,
    model: str = "gpt-5-codex",
    input_tokens: int = 3,
    output_tokens: int = 1,
) -> httpx.Response:
    output_text = "".join(deltas)
    lines: list[str] = []
    for delta in deltas:
        lines.extend(
            [
                "event: response.output_text.delta",
                "data: "
                + json.dumps(
                    {"type": "response.output_text.delta", "delta": delta}
                ),
                "",
            ]
        )
    lines.extend(
        [
            "event: response.completed",
            "data: "
            + json.dumps(
                {
                    "type": "response.completed",
                    "response": {
                        "id": "resp_test",
                        "model": model,
                        "status": "completed",
                        "output_text": output_text,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                        },
                    },
                }
            ),
            "",
        ]
    )
    return httpx.Response(
        200,
        content="\n".join(lines).encode(),
        headers={"content-type": "text/event-stream"},
    )


@pytest.mark.asyncio
async def test_chatgpt_mode_routes_to_chatgpt_endpoint() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.content)
        return _sse_response("four")

    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock(handler))
    resp = await p.complete(
        messages=[{"role": "user", "content": "what is 2+2?"}],
        model="gpt-5-codex",
    )
    assert "chatgpt.com/backend-api/codex/responses" in captured["url"]
    assert captured["headers"]["authorization"] == "Bearer acc"
    assert captured["headers"]["chatgpt-account-id"] == "acct_42"
    assert captured["body"]["stream"] is True
    assert resp.text == "four"
    assert resp.prompt_tokens == 3
    assert resp.completion_tokens == 1
    await p.aclose()


@pytest.mark.asyncio
async def test_api_key_mode_routes_to_api_openai() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        return httpx.Response(
            200,
            json={
                "model": "gpt-5",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    p = OpenAIOAuthProvider(_creds("ApiKey"), client=_mock(handler))
    await p.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-5")
    assert "api.openai.com/v1/responses" in captured["url"]
    await p.aclose()


@pytest.mark.asyncio
async def test_response_format_attaches_json_schema() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content)
        plan_json = json.dumps(
            {
                "rationale": "trivial",
                "steps": [],
                "confidence": 0.9,
                "open_question": None,
                "final_when_done": "done",
            }
        )
        return _sse_response(plan_json, input_tokens=1, output_tokens=1)

    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock(handler))
    resp = await p.complete(
        messages=[{"role": "user", "content": "plan"}],
        model="gpt-5-codex",
        response_format=Plan,
    )
    fmt = captured["body"]["text"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["name"] == "Plan"
    assert captured["body"]["stream"] is True
    assert isinstance(resp.parsed, Plan)
    assert resp.parsed.confidence == 0.9
    await p.aclose()


@pytest.mark.asyncio
async def test_assistant_history_uses_output_text() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content)
        return _sse_response("done", input_tokens=1, output_tokens=1)

    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock(handler))
    await p.complete(
        messages=[
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "prior reply"},
            {"role": "user", "content": "follow up"},
        ],
        model="gpt-5-codex",
    )
    items = captured["body"]["input"]
    assert items[0]["content"][0]["type"] == "input_text"
    assert items[1]["role"] == "assistant"
    assert items[1]["content"][0]["type"] == "output_text"
    assert items[2]["content"][0]["type"] == "input_text"
    await p.aclose()


@pytest.mark.asyncio
async def test_401_triggers_refresh_then_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(401, json={"error": "expired"})
        return _sse_response("after", input_tokens=1, output_tokens=1)

    refreshed = A.CodexCreds(
        api_key=None, access_token="NEW", refresh_token="R2", account_id="acct_42", auth_mode="chatgpt"
    )
    monkeypatch.setattr(A, "refresh_codex", lambda c, client=None: refreshed)
    p = OpenAIOAuthProvider(_creds("chatgpt"), client=_mock(handler))
    resp = await p.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-5-codex")
    assert resp.text == "after"
    assert p.creds.access_token == "NEW"
    assert calls["n"] == 2
    await p.aclose()

"""Anthropic OAuth provider — request shape + response parsing via mocked httpx."""
from __future__ import annotations

import json
import time

import httpx
import pytest

from voss.harness import auth as A
from voss.harness.agent import Plan
from voss.harness.providers import AnthropicOAuthProvider, OpenAIOAuthProvider


def _creds(expires_in: int = 3600) -> A.AnthropicOAuthCreds:
    return A.AnthropicOAuthCreds(
        access_token="sk-ant-oat01-A",
        refresh_token="sk-ant-ort01-R",
        expires_at_ms=int((time.time() + expires_in) * 1000),
        subscription_type="max",
    )


def _mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_oauth_provider_attaches_correct_headers() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "id": "msg_1",
                "model": "claude-sonnet-4-5",
                "content": [{"type": "text", "text": "hello"}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        )

    p = AnthropicOAuthProvider(_creds(), client=_mock(handler))
    resp = await p.complete(
        messages=[
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
        ],
        model="claude-sonnet-4-5",
    )
    assert resp.text == "hello"
    assert resp.prompt_tokens == 10
    assert resp.completion_tokens == 5
    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"]["authorization"] == "Bearer sk-ant-oat01-A"
    assert captured["headers"]["anthropic-beta"] == A.ANTHROPIC_OAUTH_BETA
    sys_blocks = captured["body"]["system"]
    assert isinstance(sys_blocks, list)
    assert sys_blocks[0]["text"].startswith("You are Claude Code")
    assert any(b["text"] == "be terse" for b in sys_blocks)
    assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]
    await p.aclose()


@pytest.mark.asyncio
async def test_oauth_provider_translates_response_format_to_tool_use() -> None:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content)
        # Echo a tool_use block matching a Plan.
        return httpx.Response(
            200,
            json={
                "id": "msg_2",
                "model": "claude-sonnet-4-5",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_1",
                        "name": "submit_response",
                        "input": {
                            "rationale": "test plan",
                            "steps": [],
                            "confidence": 0.85,
                            "open_question": None,
                            "final_when_done": "ok",
                        },
                    }
                ],
                "usage": {"input_tokens": 12, "output_tokens": 8},
            },
        )

    p = AnthropicOAuthProvider(_creds(), client=_mock(handler))
    resp = await p.complete(
        messages=[{"role": "user", "content": "plan"}],
        model="claude-sonnet-4-5",
        response_format=Plan,
    )
    assert isinstance(resp.parsed, Plan)
    assert resp.parsed.confidence == 0.85
    # Verify the request actually requested the tool.
    body = captured["body"]
    assert body["tool_choice"] == {"type": "tool", "name": "submit_response"}
    assert any(t["name"] == "submit_response" for t in body["tools"])
    await p.aclose()


@pytest.mark.asyncio
async def test_oauth_provider_refreshes_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(
            200,
            json={
                "model": "claude-sonnet-4-5",
                "content": [{"type": "text", "text": "after refresh"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    refreshed = A.AnthropicOAuthCreds(
        access_token="NEW",
        refresh_token="R2",
        expires_at_ms=int((time.time() + 3600) * 1000),
        subscription_type="max",
    )
    monkeypatch.setattr(A, "refresh_anthropic", lambda c, client=None: refreshed)
    p = AnthropicOAuthProvider(_creds(), client=_mock(handler))
    resp = await p.complete(
        messages=[{"role": "user", "content": "hi"}],
        model="claude-sonnet-4-5",
    )
    assert resp.text == "after refresh"
    assert calls["n"] == 2
    assert p.creds.access_token == "NEW"
    await p.aclose()


def _codex_creds() -> A.CodexCreds:
    return A.CodexCreds(
        api_key=None,
        access_token="A",
        refresh_token="R",
        account_id="acct_1",
        auth_mode="chatgpt",
    )


def test_openai_payload_omits_temperature_for_reasoning_models() -> None:
    # The PUBLIC OpenAI Responses endpoint (base_url not ending in /codex) sends
    # temperature for non-reasoning models, but gpt-5.x / o-series reject a
    # custom temperature (only the default is accepted) — so it must be omitted.
    p = OpenAIOAuthProvider(_codex_creds(), base_url=A.OPENAI_API_BASE)
    assert not p._is_codex_backend()  # confirm we exercise the public path

    reasoning = p._payload(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-5.5",
        response_format=None,
        temperature=0.2,
        max_tokens=None,
    )
    assert "temperature" not in reasoning

    legacy = p._payload(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-4o",
        response_format=None,
        temperature=0.2,
        max_tokens=None,
    )
    assert legacy["temperature"] == 0.2


@pytest.mark.asyncio
async def test_oauth_provider_surfaces_non_401_errors() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"type": "rate_limit_error", "message": "slow down"}})

    p = AnthropicOAuthProvider(_creds(), client=_mock(handler))
    with pytest.raises(RuntimeError, match=r"\[429\]"):
        await p.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="claude-sonnet-4-5",
        )
    await p.aclose()

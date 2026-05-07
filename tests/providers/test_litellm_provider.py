from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from voss_runtime.exceptions import ParseError, ProviderError
from voss_runtime.providers.litellm_provider import LiteLLMProvider


class _Greeting(BaseModel):
    message: str


def _fake_resp(content: str = "hello"):
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    resp._hidden_params = {"response_cost": 0.001}
    resp.model_dump = MagicMock(return_value={})
    return resp


async def test_complete_populates_fields(monkeypatch):
    async def fake_acompletion(**kwargs):
        return _fake_resp("hello")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    p = LiteLLMProvider()
    out = await p.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")
    assert out.text == "hello"
    assert out.model == "gpt-4o-mini"
    assert out.prompt_tokens == 10
    assert out.completion_tokens == 5
    assert out.cost_usd == pytest.approx(0.001)
    assert out.parsed is None
    assert out.raw == {}


async def test_complete_parse_failure_raises_parseerror(monkeypatch):
    async def fake_acompletion(**kwargs):
        return _fake_resp("not json")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    p = LiteLLMProvider()
    with pytest.raises(ParseError):
        await p.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o-mini",
            response_format=_Greeting,
        )


async def test_complete_network_failure_raises_providererror(monkeypatch):
    async def boom(**kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("litellm.acompletion", boom)

    p = LiteLLMProvider()
    with pytest.raises(ProviderError):
        await p.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")


def test_count_tokens_returns_positive_int():
    p = LiteLLMProvider()
    n = p.count_tokens(text="hello world", model="gpt-4o-mini")
    assert isinstance(n, int)
    assert n > 0


@pytest.mark.live
@pytest.mark.parametrize(
    "model",
    ["claude-sonnet-4-5", "gpt-4o-mini", "ollama/llama3.2:1b"],
)
async def test_live_complete_returns_text(model):
    p = LiteLLMProvider()
    out = await p.complete(
        messages=[{"role": "user", "content": "respond with the word OK"}],
        model=model,
        max_tokens=10,
    )
    assert out.text

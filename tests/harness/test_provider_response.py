"""CACHE-02: ProviderResponse cache field tests for T4-02."""

from types import SimpleNamespace

import pytest

from voss_runtime.providers._cache_tokens import extract_cache_tokens
from voss_runtime.providers.base import ProviderResponse


def test_provider_response_defaults_cache_fields_to_zero() -> None:
    response = ProviderResponse(
        text="x",
        model="m",
        prompt_tokens=1,
        completion_tokens=1,
        cost_usd=0.0,
    )

    assert response.cache_creation_input_tokens == 0
    assert response.cache_read_input_tokens == 0


def test_anthropic_usage_extraction() -> None:
    usage = SimpleNamespace(
        prompt_tokens=600,
        completion_tokens=100,
        cache_creation_input_tokens=1500,
        cache_read_input_tokens=0,
    )

    assert extract_cache_tokens(usage) == (1500, 0)


def test_openai_cached_tokens_extraction() -> None:
    usage = SimpleNamespace(
        prompt_tokens=600,
        completion_tokens=100,
        prompt_tokens_details=SimpleNamespace(cached_tokens=1200),
    )

    assert extract_cache_tokens(usage) == (0, 1200)


@pytest.mark.asyncio
async def test_litellm_provider_forwards_cache_tokens(monkeypatch) -> None:
    from voss_runtime.providers.litellm_provider import LiteLLMProvider

    usage = SimpleNamespace(
        prompt_tokens=600,
        completion_tokens=100,
        cache_creation_input_tokens=1500,
        cache_read_input_tokens=25,
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
        usage=usage,
        _hidden_params={"response_cost": 0.01},
        model_dump=lambda: {"usage": "redacted"},
    )

    async def fake_acompletion(**_kwargs):
        return response

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    result = await LiteLLMProvider().complete(messages=[], model="claude-test")

    assert result.cache_creation_input_tokens == 1500
    assert result.cache_read_input_tokens == 25

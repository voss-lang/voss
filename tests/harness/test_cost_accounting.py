"""CACHE-03: LiteLLM's cost_per_token charges for cache_creation_input_tokens.

Voss trusts this entirely (D-06). No Voss-owned pricing table. A4: if the
local LiteLLM pricing table lacks the test model, skip rather than inventing
fallback pricing in Voss.
"""

import pytest

from voss_runtime.providers.base import ProviderResponse


def test_litellm_cost_includes_cache_rates() -> None:
    try:
        import litellm

        pricing_kwargs = dict(
            model="claude-sonnet-4-5",
            prompt_tokens=1000,
            completion_tokens=200,
        )
        cost_with_cache_creation = sum(
            litellm.cost_per_token(
                **pricing_kwargs,
                cache_creation_input_tokens=2000,
                cache_read_input_tokens=0,
            )
        )
        cost_without_cache = sum(
            litellm.cost_per_token(
                **pricing_kwargs,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            )
        )
    except (ImportError, KeyError) as e:
        pytest.skip(f"litellm cost_per_token unavailable for claude-sonnet-4-5: {e}")

    response_with_cache = ProviderResponse(
        text="",
        model="claude-sonnet-4-5",
        prompt_tokens=1000,
        completion_tokens=200,
        cost_usd=cost_with_cache_creation,
        cache_creation_input_tokens=2000,
        cache_read_input_tokens=0,
    )
    response_without_cache = ProviderResponse(
        text="",
        model="claude-sonnet-4-5",
        prompt_tokens=1000,
        completion_tokens=200,
        cost_usd=cost_without_cache,
    )

    assert response_without_cache.cost_usd > 0
    assert response_with_cache.cost_usd > response_without_cache.cost_usd

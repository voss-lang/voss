"""CACHE-02: streaming Usage cache token field coverage for T4-04."""

from voss.harness.providers import Usage


def test_stream_usage_event_carries_cache_tokens() -> None:
    usage = Usage(
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.01,
        cache_creation_input_tokens=1500,
        cache_read_input_tokens=0,
    )

    assert usage.cache_creation_input_tokens == 1500
    assert usage.cache_read_input_tokens == 0


def test_usage_defaults_to_zero_cache_fields() -> None:
    usage = Usage(prompt_tokens=1, completion_tokens=1, cost_usd=0.0)

    assert usage.cache_creation_input_tokens == 0
    assert usage.cache_read_input_tokens == 0

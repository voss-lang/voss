"""CACHE-02: cache token extraction for T4-02."""

from types import SimpleNamespace

from voss_runtime.providers._cache_tokens import extract_cache_tokens


def test_anthropic_shape_returns_both_counts() -> None:
    usage = SimpleNamespace(cache_creation_input_tokens=120, cache_read_input_tokens=480)

    assert extract_cache_tokens(usage) == (120, 480)


def test_openai_shape_returns_read_only() -> None:
    usage = SimpleNamespace(prompt_tokens_details=SimpleNamespace(cached_tokens=300))

    assert extract_cache_tokens(usage) == (0, 300)


def test_missing_fields_default_to_zero() -> None:
    usage = SimpleNamespace()

    assert extract_cache_tokens(usage) == (0, 0)


def test_none_usage_returns_zero() -> None:
    assert extract_cache_tokens(None) == (0, 0)

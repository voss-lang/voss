"""CACHE-02/CACHE-03: cache token extraction stubs for T4-02."""

from types import SimpleNamespace

import pytest


def test_anthropic_shape_returns_both_counts() -> None:
    pytest.fail("T4-02 lands extract_cache_tokens")
    usage = SimpleNamespace(cache_creation_input_tokens=11, cache_read_input_tokens=22)
    assert (usage.cache_creation_input_tokens, usage.cache_read_input_tokens) == (11, 22)


def test_openai_shape_returns_read_only() -> None:
    pytest.fail("T4-02 lands extract_cache_tokens")
    usage = SimpleNamespace(prompt_tokens_details={"cached_tokens": 33})
    assert (0, usage.prompt_tokens_details["cached_tokens"]) == (0, 33)


def test_missing_fields_default_to_zero() -> None:
    pytest.fail("T4-02 lands extract_cache_tokens")
    usage = SimpleNamespace()
    assert (getattr(usage, "cache_creation_input_tokens", 0), getattr(usage, "cache_read_input_tokens", 0)) == (0, 0)


def test_none_usage_returns_zero() -> None:
    pytest.fail("T4-02 lands extract_cache_tokens")
    usage = None
    assert usage is None

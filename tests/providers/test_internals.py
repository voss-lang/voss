"""Coverage for the provider registry and cache-token helpers."""
from __future__ import annotations

from types import SimpleNamespace

from voss_runtime.providers import StubProvider


def test_default_provider_is_cached():
    from voss_runtime.providers import _default_provider

    assert _default_provider() is _default_provider()


def test_get_non_hermetic_returns_registered_provider(monkeypatch):
    from voss_runtime.providers import get, register

    monkeypatch.delenv("VOSS_HERMETIC", raising=False)
    sentinel = StubProvider()
    register("cov-nonhermetic-model", sentinel)
    assert get("cov-nonhermetic-model") is sentinel


def test_as_int_handles_bad_values():
    from voss_runtime.providers._cache_tokens import _as_int

    assert _as_int("abc") == 0
    assert _as_int(None) == 0
    assert _as_int(7) == 7


def test_extract_reads_cached_tokens_from_object_details():
    from voss_runtime.providers._cache_tokens import extract_cache_tokens

    usage = SimpleNamespace(
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        prompt_tokens_details=SimpleNamespace(cached_tokens=7),
    )
    assert extract_cache_tokens(usage) == (0, 7)


def test_extract_reads_cached_tokens_from_dict_details():
    from voss_runtime.providers._cache_tokens import extract_cache_tokens

    usage = SimpleNamespace(
        cache_creation_input_tokens=3,
        cache_read_input_tokens=0,
        prompt_tokens_details={"cached_tokens": 9},
    )
    assert extract_cache_tokens(usage) == (3, 9)


def test_get_hermetic_prefers_registered_name_then_stub(monkeypatch):
    from voss_runtime.providers import get, register

    monkeypatch.setenv("VOSS_HERMETIC", "1")
    sentinel = StubProvider()
    register("cov-hermetic-model", sentinel)
    assert get("cov-hermetic-model") is sentinel
    assert get("unregistered-name-xyz") is not sentinel

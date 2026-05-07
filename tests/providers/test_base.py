from __future__ import annotations

import voss_runtime.providers as providers
from voss_runtime.providers import (
    LiteLLMProvider,
    ModelProvider,
    ProviderResponse,
    StubProvider,
    get,
)


def test_provider_response_total_tokens():
    r = ProviderResponse(
        text="hi", model="m", prompt_tokens=10, completion_tokens=5, cost_usd=0.0
    )
    assert r.total_tokens == 15


def test_litellm_isinstance_modelprovider():
    assert isinstance(LiteLLMProvider(), ModelProvider)


def test_stub_isinstance_modelprovider():
    assert isinstance(StubProvider(), ModelProvider)


def test_get_stub_returns_registered_instance():
    p = get("__stub__")
    assert isinstance(p, StubProvider)
    assert p is providers._registry["__stub__"]


def test_get_unregistered_falls_back_to_default():
    p = get("not-a-real-model-xyz")
    assert isinstance(p, LiteLLMProvider)
    assert p is providers._registry["__default__"]

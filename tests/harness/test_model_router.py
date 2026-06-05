"""P1 tests: catalog entry -> provider + model string routing."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from voss.harness import model_router as mr
from voss.harness.model_catalog import ModelEntry
from voss_runtime.providers import LiteLLMProvider


def _entry(**kw) -> ModelEntry:
    base = dict(
        id="m",
        name="M",
        provider_id="p",
        provider_label="P",
        api_base=None,
        env_key=None,
        free=False,
        subscription=False,
        context=None,
        tool_call=True,
    )
    base.update(kw)
    return ModelEntry(**base)


NATIVE = _entry(id="claude-sonnet-4-5", provider_id="anthropic", env_key="ANTHROPIC_API_KEY")
COMPAT = _entry(
    id="gemma3:27b",
    provider_id="ollama-cloud",
    api_base="https://ollama.com/v1",
    env_key="OLLAMA_API_KEY",
    subscription=True,
)


def test_model_string_native_passes_through() -> None:
    assert mr.model_string(NATIVE) == "claude-sonnet-4-5"


def test_model_string_compat_gets_openai_prefix() -> None:
    assert mr.model_string(COMPAT) == "openai/gemma3:27b"


def test_build_native_has_no_api_base() -> None:
    provider, model = mr.build_provider_for_model(NATIVE, api_key="k")
    assert isinstance(provider, LiteLLMProvider)
    assert provider.api_base is None
    assert provider.api_key == "k"
    assert model == "claude-sonnet-4-5"


def test_build_compat_binds_api_base_and_key() -> None:
    provider, model = mr.build_provider_for_model(COMPAT, api_key="secret")
    assert provider.api_base == "https://ollama.com/v1"
    assert provider.api_key == "secret"
    assert model == "openai/gemma3:27b"


def test_resolve_key_from_getter() -> None:
    getter = {"OLLAMA_API_KEY": "tok"}.get
    none_kr = {}.get
    assert mr.resolve_key(COMPAT, getter=getter, keyring_get=none_kr) == "tok"
    assert mr.resolve_key(_entry(env_key=None), getter=getter, keyring_get=none_kr) is None
    assert mr.resolve_key(COMPAT, getter={}.get, keyring_get=none_kr) is None


def test_resolve_key_falls_back_to_keyring() -> None:
    # env empty, keyring has it -> keyring wins.
    assert mr.resolve_key(COMPAT, getter={}.get, keyring_get={"OLLAMA_API_KEY": "kr"}.get) == "kr"


def test_prepare_model_key_present_and_missing() -> None:
    none_kr = {}.get
    _, _, present = mr.prepare_model(COMPAT, getter={"OLLAMA_API_KEY": "t"}.get, keyring_get=none_kr)
    assert present is True
    _, _, missing = mr.prepare_model(COMPAT, getter={}.get, keyring_get=none_kr)
    assert missing is False


def test_prepare_model_native_without_env_key_is_present() -> None:
    # A provider that needs no key (env_key None) is always "present".
    entry = _entry(env_key=None)
    _, _, present = mr.prepare_model(entry, getter={}.get, keyring_get={}.get)
    assert present is True


# --- LiteLLMProvider routing-override plumbing ---


@pytest.mark.asyncio
async def test_litellm_provider_forwards_api_base_and_key(monkeypatch) -> None:
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content="ok"))]
        resp.usage = MagicMock(prompt_tokens=1, completion_tokens=1)
        resp._hidden_params = {"response_cost": 0.0}
        resp.model_dump = MagicMock(return_value={})
        return resp

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    p = LiteLLMProvider(api_base="https://ollama.com/v1", api_key="tok")
    await p.complete(messages=[{"role": "user", "content": "hi"}], model="openai/gemma3:27b")

    assert captured["api_base"] == "https://ollama.com/v1"
    assert captured["api_key"] == "tok"
    assert captured["model"] == "openai/gemma3:27b"


@pytest.mark.asyncio
async def test_litellm_provider_noarg_omits_routing(monkeypatch) -> None:
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content="ok"))]
        resp.usage = MagicMock(prompt_tokens=1, completion_tokens=1)
        resp._hidden_params = {"response_cost": 0.0}
        resp.model_dump = MagicMock(return_value={})
        return resp

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)

    p = LiteLLMProvider()  # historic no-arg path
    await p.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-4o")

    assert "api_base" not in captured
    assert "api_key" not in captured

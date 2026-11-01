"""P3 integration: the /models slash command selects + persists + swaps."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from voss.harness import cli
from voss.harness import config as harness_config
from voss.harness import model_catalog as mc
from voss_runtime._config import configure, get_config


def _raw():
    return {
        "ollama-cloud": {
            "id": "ollama-cloud",
            "name": "Ollama Cloud",
            "env": ["OLLAMA_API_KEY"],
            "api": "https://ollama.com/v1",
            "models": {
                "gemma3:27b": {
                    "id": "gemma3:27b",
                    "name": "gemma3:27b",
                    "tool_call": False,
                    "cost": None,
                    "limit": {"context": 131072},
                }
            },
        }
    }


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("OLLAMA_API_KEY", "tok-xyz")
    # Catalog comes from our fixture, never the network.
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(_raw()))
    configure(default_model="claude-sonnet-4-5")
    return tmp_path


def test_models_set_switches_and_persists(env) -> None:
    registry = cli._build_slash_registry()
    ctx = SimpleNamespace(provider=object())
    before = ctx.provider

    handled = registry.dispatch(ctx, "/models set gemma3:27b ollama-cloud")
    assert handled is True

    # provider swapped to a routed LiteLLM instance
    assert ctx.provider is not before
    assert getattr(ctx.provider, "api_base", None) == "https://ollama.com/v1"
    assert getattr(ctx.provider, "api_key", None) == "tok-xyz"

    # default model is the routed litellm string
    assert get_config().default_model == "openai/gemma3:27b"

    # persisted for next boot
    cfg = harness_config.load_harness_config()
    assert cfg.get("preferred_model") == "gemma3:27b"
    assert cfg.get("preferred_provider") == "ollama-cloud"


def test_models_set_missing_key_does_not_switch(env, monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    # also block any keyring fallback
    monkeypatch.setattr("voss.harness.auth.load_provider_key", lambda _k: None)
    registry = cli._build_slash_registry()
    ctx = SimpleNamespace(provider=object())
    before = ctx.provider

    registry.dispatch(ctx, "/models set gemma3:27b ollama-cloud")

    assert ctx.provider is before  # not switched — needs a key
    assert get_config().default_model == "claude-sonnet-4-5"


def test_models_unknown_id_no_switch(env) -> None:
    registry = cli._build_slash_registry()
    ctx = SimpleNamespace(provider=object())
    before = ctx.provider
    registry.dispatch(ctx, "/models set does-not-exist")
    assert ctx.provider is before

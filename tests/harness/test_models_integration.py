"""P6 integration: switch -> turn routes through the new provider; boot rebuilds.

Ties P1-P5 together end to end (catalog -> router -> /models -> persistence ->
live swap -> boot rebuild) with the network mocked.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from voss.harness import cli
from voss.harness import config as hconfig
from voss.harness import model_catalog as mc
from voss_runtime._config import configure, get_config


RAW = {
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
    monkeypatch.setenv("OLLAMA_API_KEY", "tok")
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(RAW))
    configure(default_model="claude-sonnet-4-5")
    return tmp_path


def _fake_acompletion(captured):
    async def _inner(**kwargs):
        captured.update(kwargs)
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content="ok"))]
        resp.usage = MagicMock(prompt_tokens=1, completion_tokens=1)
        resp._hidden_params = {"response_cost": 0.0}
        resp.model_dump = MagicMock(return_value={})
        return resp

    return _inner


@pytest.mark.asyncio
async def test_switch_then_turn_routes_through_new_provider(env, monkeypatch) -> None:
    # 1. switch model via the command -> swaps ctx.provider + configures model.
    registry = cli._build_slash_registry()
    ctx = SimpleNamespace(provider=object())
    registry.dispatch(ctx, "/models set gemma3:27b ollama-cloud")
    assert get_config().default_model == "openai/gemma3:27b"

    # 2. a turn uses ctx.provider + the configured model. The routed LiteLLM
    #    provider must carry the Ollama Cloud base + key into the actual call.
    captured: dict = {}
    monkeypatch.setattr("litellm.acompletion", _fake_acompletion(captured))
    out = await ctx.provider.complete(
        messages=[{"role": "user", "content": "hi"}],
        model=get_config().default_model,
    )
    assert out.text == "ok"
    assert captured["model"] == "openai/gemma3:27b"
    assert captured["api_base"] == "https://ollama.com/v1"
    assert captured["api_key"] == "tok"


def test_boot_rebuilds_from_persisted_selection(env) -> None:
    hconfig.set_preferred_routed("gemma3:27b", "ollama-cloud")
    configure(default_model="claude-sonnet-4-5")  # simulate a fresh default

    base = object()
    provider = cli._apply_boot_model(base, user_explicit=None)

    assert provider is not base
    assert getattr(provider, "api_base", None) == "https://ollama.com/v1"
    assert get_config().default_model == "openai/gemma3:27b"


def test_boot_explicit_model_wins(env) -> None:
    hconfig.set_preferred_routed("gemma3:27b", "ollama-cloud")
    base = object()
    out = cli._apply_boot_model(base, user_explicit="gpt-4o")
    assert out is base  # --model overrides the routed selection


def test_boot_no_selection_leaves_provider(env) -> None:
    base = object()
    out = cli._apply_boot_model(base, user_explicit=None)
    assert out is base


def test_switch_persists_and_records_recent(env) -> None:
    from voss.harness import model_prefs

    registry = cli._build_slash_registry()
    ctx = SimpleNamespace(provider=object())
    registry.dispatch(ctx, "/models set gemma3:27b ollama-cloud")

    cfg = hconfig.load_harness_config()
    assert cfg.get("preferred_provider") == "ollama-cloud"
    assert cfg.get("preferred_model") == "gemma3:27b"
    assert ("ollama-cloud", "gemma3:27b") in model_prefs.recent()

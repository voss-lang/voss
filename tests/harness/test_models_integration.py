"""P6 integration: switch -> turn routes through the new provider; boot rebuilds.

Ties P1-P5 together end to end (catalog -> router -> /models -> persistence ->
live swap -> boot rebuild) with the network mocked.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from voss.harness import auth
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
    assert cli._provider_label_for_runtime(provider, fallback="OpenAI") == "Ollama Cloud"
    assert get_config().default_model == "openai/gemma3:27b"


def test_boot_explicit_model_wins(env) -> None:
    hconfig.set_preferred_routed("gemma3:27b", "ollama-cloud")
    base = object()
    out = cli._apply_boot_model(base, user_explicit="gpt-4o")
    assert out is base  # --model overrides the routed selection


def test_boot_explicit_claude_auth_blocks_openai_routed_selection(env) -> None:
    hconfig.set_preferred_routed("gemma3:27b", "ollama-cloud")
    configure(default_model="claude-sonnet-4-5")

    base = object()
    out = cli._apply_boot_model(
        base,
        user_explicit=None,
        auth_source="claude-agent",
    )

    assert out is base
    assert get_config().default_model == "claude-sonnet-4-5"


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


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-6-astra", "gpt-6.1-sol"])
async def test_catalog_pick_uses_subscription_even_with_api_key(env, monkeypatch, model) -> None:
    from voss.harness.providers import OpenAIOAuthProvider

    creds = auth.CodexCreds(None, "test-access", "test-refresh", "test-account", "ChatGPT")
    monkeypatch.setattr(auth, "load_codex", lambda: creds)
    monkeypatch.setattr(auth, "load_codex_default_model", lambda: model)
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    raw = {"openai": {
        "name": "OpenAI", "env": ["OPENAI_API_KEY"],
        "models": {model: {"id": model, "name": model, "tool_call": True}},
    }}
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(raw))
    ctx = SimpleNamespace(provider=OpenAIOAuthProvider(creds))
    cli._build_slash_registry().dispatch(ctx, f"/models set {model} openai")

    assert isinstance(ctx.provider, OpenAIOAuthProvider)
    cfg = hconfig.load_harness_config()
    assert cfg["auth"] == "codex"
    assert cfg["preferred_model"] == model
    assert "preferred_provider" not in cfg

    configure(default_model="old-default")
    cli._resolve_default_model(None)
    resolution, boot_provider = cli._resolve_auth_or_die("auto")
    boot_provider = cli._apply_boot_model(
        boot_provider, user_explicit=None, auth_source=resolution.source,
    )
    assert isinstance(boot_provider, OpenAIOAuthProvider)
    assert get_config().default_model == model

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=(
            'data: {"type":"response.output_text.delta","delta":"ok"}\n\n'
            'data: {"type":"response.completed","response":{"status":"completed",'
            '"output_text":"ok","usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
        ))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        ctx.provider._client = client
        result = await ctx.provider.complete(
            messages=[{"role": "user", "content": "hello"}], model=get_config().default_model,
        )
    assert result.text == "ok"
    assert len(requests) == 1
    assert str(requests[0].url) == auth.CHATGPT_BACKEND_BASE + "/responses"
    assert requests[0].headers["authorization"] == "Bearer test-access"
    assert json.loads(requests[0].content)["model"] == model


def test_boot_saved_openai_catalog_route_uses_subscription(env, monkeypatch) -> None:
    from voss.harness.providers import OpenAIOAuthProvider

    creds = auth.CodexCreds(None, "test-access", "test-refresh", "test-account", "ChatGPT")
    monkeypatch.setattr(auth, "load_codex", lambda: creds)
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog({"openai": {
        "name": "OpenAI", "env": ["OPENAI_API_KEY"],
        "models": {"gpt-6.1-sol": {"id": "gpt-6.1-sol", "name": "GPT-6.1 Sol"}},
    }}))
    hconfig.set_preferred_routed("gpt-6.1-sol", "openai")

    provider = cli._apply_boot_model(object(), user_explicit=None, auth_source="env-openai")

    assert isinstance(provider, OpenAIOAuthProvider)
    assert cli._provider_label_for_runtime(provider) == "Codex"
    assert get_config().default_model == "gpt-6.1-sol"

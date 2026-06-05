"""P0 tests for the models.dev catalog parser + cache (no network)."""
from __future__ import annotations

import json

import pytest

from voss.harness import model_catalog as mc

# Minimal slice mirroring the live models.dev shape (pinned 2026-06).
RAW = {
    "anthropic": {
        "id": "anthropic",
        "name": "Anthropic",
        "env": ["ANTHROPIC_API_KEY"],
        "api": None,
        "models": {
            "claude-sonnet-4-5": {
                "id": "claude-sonnet-4-5",
                "name": "Claude Sonnet 4.5",
                "tool_call": True,
                "cost": {"input": 3, "output": 15},
                "limit": {"context": 200000, "output": 64000},
            }
        },
    },
    "opencode": {
        "id": "opencode",
        "name": "OpenCode Zen",
        "env": ["OPENCODE_API_KEY"],
        "api": "https://opencode.ai/zen/v1",
        "models": {
            "claude-opus-4-5": {
                "id": "claude-opus-4-5",
                "name": "Claude Opus 4.5",
                "tool_call": True,
                "cost": {"input": 5, "output": 25},
                "limit": {"context": 200000, "output": 64000},
            },
            "mimo-v2-flash-free": {
                "id": "mimo-v2-flash-free",
                "name": "MiMo V2 Flash Free",
                "tool_call": True,
                "cost": {"input": 0, "output": 0, "cache_read": 0},
                "limit": {"context": 262144, "output": 65536},
            },
        },
    },
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
                "limit": {"context": 131072, "output": 131072},
            }
        },
    },
    # Not in TARGET_PROVIDERS — must be filtered out.
    "fireworks-ai": {
        "id": "fireworks-ai",
        "name": "Fireworks",
        "env": ["FIREWORKS_API_KEY"],
        "models": {"x": {"id": "x", "name": "X"}},
    },
}


def test_parse_filters_to_target_providers() -> None:
    groups = mc.parse_catalog(RAW)
    ids = [g.id for g in groups]
    assert "fireworks-ai" not in ids
    assert set(ids) == {"anthropic", "opencode", "ollama-cloud"}


def test_parse_preserves_target_order() -> None:
    groups = mc.parse_catalog(RAW)
    # TARGET_PROVIDERS order: anthropic, openai, opencode, opencode-go, ollama-cloud
    assert [g.id for g in groups] == ["anthropic", "opencode", "ollama-cloud"]


def test_provider_routing_fields() -> None:
    groups = {g.id: g for g in mc.parse_catalog(RAW)}
    zen = groups["opencode"]
    assert zen.label == "OpenCode Zen"
    assert zen.api_base == "https://opencode.ai/zen/v1"
    assert zen.env_key == "OPENCODE_API_KEY"
    assert groups["anthropic"].api_base is None  # native litellm prefix


def test_free_and_subscription_flags() -> None:
    by_id = {
        m.id: m for g in mc.parse_catalog(RAW) for m in g.models
    }
    assert by_id["mimo-v2-flash-free"].free is True
    assert by_id["mimo-v2-flash-free"].subscription is False
    assert by_id["claude-opus-4-5"].free is False
    assert by_id["gemma3:27b"].subscription is True  # cost is None
    assert by_id["gemma3:27b"].free is False


def test_model_entry_context_and_toolcall() -> None:
    by_id = {m.id: m for g in mc.parse_catalog(RAW) for m in g.models}
    assert by_id["claude-sonnet-4-5"].context == 200000
    assert by_id["claude-sonnet-4-5"].tool_call is True
    assert by_id["gemma3:27b"].tool_call is False


def test_parse_skips_provider_with_no_models() -> None:
    raw = {"opencode": {"name": "OpenCode Zen", "api": "x", "env": ["K"], "models": {}}}
    assert mc.parse_catalog(raw) == []


# ---------------------------------------------------------------------------
# fetch_raw: cache hit / miss / offline-fallback (injected http + clock)
# ---------------------------------------------------------------------------


def test_fetch_uses_fresh_cache_without_network(tmp_path) -> None:
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"fetched_at": 1000.0, "data": RAW}))
    calls = []

    def http(_url):
        calls.append(_url)
        return {}

    out = mc.fetch_raw(path=path, now=lambda: 1100.0, ttl=24 * 3600, http_get=http)
    assert out == RAW
    assert calls == []  # fresh cache → no network


def test_fetch_refreshes_stale_cache(tmp_path) -> None:
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"fetched_at": 0.0, "data": {"old": {}}}))
    fresh = {"anthropic": RAW["anthropic"]}

    out = mc.fetch_raw(
        path=path,
        now=lambda: 10**9,  # far future → cache is stale
        ttl=24 * 3600,
        http_get=lambda _u: fresh,
    )
    assert out == fresh
    # cache rewritten with fresh data
    assert json.loads(path.read_text())["data"] == fresh


def test_fetch_falls_back_to_stale_cache_on_network_failure(tmp_path) -> None:
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"fetched_at": 0.0, "data": RAW}))

    def boom(_url):
        raise OSError("offline")

    out = mc.fetch_raw(path=path, now=lambda: 10**9, ttl=1, http_get=boom)
    assert out == RAW  # stale beats nothing


def test_fetch_raises_when_no_cache_and_network_down(tmp_path) -> None:
    path = tmp_path / "missing.json"

    def boom(_url):
        raise OSError("offline")

    with pytest.raises(RuntimeError):
        mc.fetch_raw(path=path, now=lambda: 0.0, ttl=1, http_get=boom)


def test_load_catalog_end_to_end_with_injected_fetch(tmp_path) -> None:
    path = tmp_path / "models.json"
    groups = mc.load_catalog(path=path, now=lambda: 0.0, http_get=lambda _u: RAW)
    assert [g.id for g in groups] == ["anthropic", "opencode", "ollama-cloud"]

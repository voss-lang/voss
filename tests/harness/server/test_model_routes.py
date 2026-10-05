from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient

from voss.harness import auth, config, model_catalog, model_router
from voss.harness.claude_agent_provider import ClaudeAgentProvider
from voss.harness.providers import OpenAIOAuthProvider
from voss.harness.server import app as appmod
from voss.harness.server import models

TOKEN = "model-route-test"


@pytest.fixture
def client(monkeypatch, tmp_path):
    creds = auth.CodexCreds(None, "synthetic-access", "synthetic-refresh", "test", "ChatGPT")
    resolutions = {
        "claude": auth.Resolution("claude-agent", "test", cli_path=Path("/test/claude")),
        "codex": auth.Resolution("codex-oauth", "test", codex_oauth=creds),
    }
    monkeypatch.setattr(auth, "resolve", lambda mode: resolutions[mode])
    monkeypatch.setattr(auth, "load_codex_default_model", lambda: "gpt-6-astra")
    monkeypatch.setattr(appmod, "_resolve_provider", lambda _: (resolutions["claude"], object()))
    monkeypatch.setattr(model_catalog, "load_catalog", lambda: model_catalog.parse_catalog({
        "openai": {"name": "OpenAI", "env": ["OPENAI_API_KEY"], "models": {
            "gpt-6.1-sol": {"id": "gpt-6.1-sol", "name": "GPT 6.1", "tool_call": True},
            "image-only": {"id": "image-only", "name": "Image", "tool_call": False},
        }},
        "openrouter": {"name": "OpenRouter", "env": ["OPENROUTER_API_KEY"],
                       "npm": "@ai-sdk/openai-compatible", "api": "https://example.invalid/v1",
                       "models": {"vendor/model": {"id": "vendor/model", "name": "Routed", "tool_call": True}}},
    }))
    monkeypatch.setattr(model_router, "resolve_key", lambda _: None)
    monkeypatch.delenv("VOSS_SERVE_DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("VOSS_SERVE_DEFAULT_AUTH", raising=False)
    c = TestClient(appmod.create_app(TOKEN), headers={"Authorization": f"Bearer {TOKEN}"})
    response = c.post("/session", json={"cwd": str(tmp_path), "model": "claude-sonnet-5-5"})
    assert response.status_code == 201
    c.sid = response.json()["id"]
    c.session = c.app.state.sessions.get(c.sid)
    c.resolutions = resolutions
    return c


def switch(client, **body):
    return client.post(f"/session/{client.sid}/model", json=body)


def test_catalog_separates_subscription_and_api_credentials(client):
    response = client.get("/models")
    assert response.status_code == 200
    rows = response.json()["models"]
    assert any(m["id"] == "gpt-6.1-sol" and m["auth"] == "codex" and m["connected"] for m in rows)
    assert any(m["id"] == "gpt-6.1-sol" and m["auth"] == "api" and not m["connected"] for m in rows)
    assert not any(m["id"] == "image-only" for m in rows)
    assert "synthetic-access" not in response.text
    assert "synthetic-refresh" not in response.text
    assert client.get("/models", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post(f"/session/{client.sid}/model", json={"auth": "codex"},
                       headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_subscription_catalog_survives_offline_api_catalog(client, monkeypatch):
    monkeypatch.setattr(model_catalog, "load_catalog", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    response = client.get("/models").json()
    assert response["warning"]
    assert {m["auth"] for m in response["models"]} == {"claude", "codex"}
    assert switch(client, model="gpt-6.1-sol").status_code == 200


def test_model_switch_changes_provider_and_restores_default_on_restart(client, tmp_path):
    other = client.app.state.sessions.create(cwd=tmp_path, model="other", provider=object())
    response = switch(client, model="gpt-6.1-sol")
    assert response.status_code == 200, response.text
    assert response.json()["auth"] == "codex-oauth"
    assert response.json()["provider"] == "Codex"
    assert client.session.model == client.session.record.model == "gpt-6.1-sol"
    assert isinstance(client.session.provider, OpenAIOAuthProvider)
    assert other.model == "other"
    assert config.load_harness_config() == {"preferred_model": "gpt-6.1-sol", "auth": "codex"}
    restarted = TestClient(appmod.create_app(TOKEN), headers=client.headers)
    created = restarted.post("/session", json={"cwd": str(tmp_path)})
    assert created.status_code == 201, created.text
    restored = restarted.app.state.sessions.get(created.json()["id"])
    assert restored.model == "gpt-6.1-sol"
    assert isinstance(restored.provider, OpenAIOAuthProvider)
    response = switch(client, auth="claude")
    assert response.status_code == 200
    assert response.json()["model"] == "claude-sonnet-5-5"
    assert isinstance(client.session.provider, ClaudeAgentProvider)
    assert config.load_harness_config()["auth"] == "claude"


@pytest.mark.parametrize("mode,model", [("claude", "claude-sonnet-4-5"), ("codex", "gpt-5.4")])
def test_existing_defaults_remain_usable_outside_curated_picker(client, tmp_path, monkeypatch, mode, model):
    config.set_preferred_selection(model, mode, None)
    monkeypatch.setattr(model_catalog, "load_catalog", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    response = client.post("/session", json={"cwd": str(tmp_path)})
    assert response.status_code == 201, response.text
    restored = client.app.state.sessions.get(response.json()["id"])
    assert restored.model == model
    assert restored.auth == client.resolutions[mode].source


@pytest.mark.parametrize("body", [
    {"model": "missing"}, {"model": "gpt"}, {"model": "gpt-6.1-sol", "auth": "claude"},
    {"model": "gpt-6.1-sol", "auth": "api", "provider": "openai"},
])
def test_rejected_switch_leaves_session_and_defaults_unchanged(client, body):
    provider = client.session.provider
    response = switch(client, **body)
    assert response.status_code == 400, response.text
    assert client.session.provider is provider
    assert client.session.model == "claude-sonnet-5-5"
    assert config.load_harness_config() == {}


def test_subscription_never_falls_back_to_api_key(client):
    client.resolutions["codex"] = auth.Resolution("codex", "API key", openai_api_key="synthetic-key")
    response = switch(client, model="gpt-6.1-sol")
    assert response.status_code == 400
    assert "codex login" in response.text
    assert client.session.auth == "claude-agent"


def test_malformed_credentials_leave_selection_unchanged(client):
    client.resolutions["codex"].codex_oauth.auth_mode = 42
    response = switch(client, auth="codex")
    assert response.status_code == 400
    assert "codex login" in response.text
    assert "synthetic" not in response.text
    assert client.session.model == "claude-sonnet-5-5"
    assert config.load_harness_config() == {}


def test_provider_constructor_failure_is_reported_without_mutating(client, monkeypatch):
    monkeypatch.setattr(OpenAIOAuthProvider, "__init__", lambda *a: (_ for _ in ()).throw(RuntimeError("synthetic-access")))
    response = switch(client, auth="codex")
    assert response.status_code == 400
    assert "Could not initialize" in response.text
    assert "synthetic-access" not in response.text
    assert client.session.model == "claude-sonnet-5-5"
    assert config.load_harness_config() == {}


def test_failed_config_replace_preserves_old_file_and_session(client, monkeypatch):
    config.set_preferred_selection("claude-sonnet-5-5", "claude", None)
    previous = config.config_path().read_bytes()
    provider = client.session.provider
    monkeypatch.setattr(Path, "replace", lambda *a: (_ for _ in ()).throw(OSError("readonly")))
    response = switch(client, auth="codex")
    assert response.status_code == 500
    assert config.config_path().read_bytes() == previous
    assert client.session.provider is provider
    assert not client.session.busy


def test_explicit_api_route_restores_endpoint_and_model(client, monkeypatch, tmp_path):
    monkeypatch.setattr(model_router, "resolve_key", lambda _: "synthetic-key")
    response = switch(client, model="vendor/model", auth="api", provider="openrouter")
    assert response.status_code == 200, response.text
    assert response.json()["model"] == "openai/vendor/model"
    assert response.json()["provider"] == "OpenRouter"
    assert config.load_harness_config()["preferred_provider"] == "openrouter"
    restarted = TestClient(appmod.create_app(TOKEN), headers=client.headers)
    created = restarted.post("/session", json={"cwd": str(tmp_path)})
    restored = restarted.app.state.sessions.get(created.json()["id"])
    assert restored.model == "openai/vendor/model"
    assert restored.provider.voss_provider_id == "openrouter"
    assert switch(client, auth="codex").status_code == 200
    assert "preferred_provider" not in config.load_harness_config()


@pytest.mark.parametrize("selection", [
    {"model": "gpt-6.1-sol", "auth": "codex"},
    {"model": "vendor/model", "auth": "api", "provider": "openrouter"},
])
def test_resume_restores_session_route_after_default_changes(client, monkeypatch, tmp_path, selection):
    monkeypatch.setattr(model_router, "resolve_key", lambda _: "synthetic-key")
    assert switch(client, **selection).status_code == 200
    appmod.session_store.save(client.session.record, client.session.history)
    previous_model = client.session.model
    config.set_preferred_selection("claude-opus-5-5", "claude", None)
    restarted = TestClient(appmod.create_app(TOKEN), headers=client.headers)
    response = restarted.post("/session", json={"cwd": str(tmp_path), "resume": client.sid})
    assert response.status_code == 201, response.text
    restored = restarted.app.state.sessions.get(client.sid)
    assert restored.model == previous_model
    assert restored.auth == client.session.auth
    assert type(restored.provider) is type(client.session.provider)
    assert config.load_harness_config()["auth"] == "claude"


@pytest.mark.parametrize("selection", [
    {"model": "gpt-6.1-sol", "auth": "codex"},
    {"model": "vendor/model", "auth": "api", "provider": "openrouter"},
])
def test_saved_selection_contains_route_identifiers_without_credentials(client, monkeypatch, selection):
    monkeypatch.setattr(model_router, "resolve_key", lambda _: "synthetic-key")
    client.resolutions["codex"].codex_oauth.account_id = "synthetic-account"
    assert switch(client, **selection).status_code == 200
    text = appmod.session_store.save(client.session.record, client.session.history).read_text()
    saved = json.loads(text)
    assert saved["model_auth"] == selection["auth"]
    assert saved["model_provider"] == selection.get("provider")
    for forbidden in (
        "synthetic-key", "synthetic-access", "synthetic-refresh", "synthetic-account",
        '"provider"', '"credentials"', '"access_token"', '"refresh_token"',
        '"api_key"', '"Authorization"',
    ):
        assert forbidden not in text


def test_busy_session_rejects_selection(client):
    client.session.switching = True
    assert switch(client, auth="codex").status_code == 409
    assert client.post(f"/session/{client.sid}/message", json={"parts": [{"text": "hello"}]}).status_code == 409


async def test_next_turn_receives_selected_provider_and_model(client, monkeypatch):
    assert switch(client, model="gpt-6.1-sol").status_code == 200
    seen = {}

    async def run(text, **kwargs):
        seen.update(kwargs)
        raise RuntimeError("stop at synthetic provider boundary")

    monkeypatch.setattr(appmod, "run_turn", run)
    monkeypatch.setattr(appmod.session_store, "save", lambda *a: None)
    await appmod._run_turn(client.session, "run the task", "plan")
    assert seen["provider"] is client.session.provider
    assert seen["model"] == "gpt-6.1-sol"


async def test_inflight_turn_rejects_selection(client):
    client.session.task = asyncio.create_task(asyncio.sleep(60))
    try:
        assert switch(client, auth="codex").status_code == 409
    finally:
        client.session.task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await client.session.task


async def test_prompt_cannot_start_while_provider_is_being_constructed(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    prepare = models.prepare

    def delayed(*args):
        entered.set()
        assert release.wait(5)
        return prepare(*args)

    monkeypatch.setattr(models, "prepare", delayed)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app),
                                base_url="http://test", headers=client.headers) as api:
        pending = asyncio.create_task(api.post(f"/session/{client.sid}/model", json={"auth": "codex"}))
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            prompt = await api.post(f"/session/{client.sid}/message", json={"parts": [{"text": "hello"}]})
            second = await api.post(f"/session/{client.sid}/model", json={"auth": "claude"})
            assert prompt.status_code == second.status_code == 409
        finally:
            release.set()
        assert (await pending).status_code == 200
        assert not client.session.busy

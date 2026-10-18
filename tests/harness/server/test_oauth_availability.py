from __future__ import annotations

import asyncio
import base64
import json
import time
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from voss.harness import auth, oauth
from voss.harness.claude_agent_provider import ClaudeAgentProvider
from voss.harness.providers import OpenAIOAuthProvider
from voss.harness.server import app as appmod


def token(expiry):
    payload = base64.urlsafe_b64encode(json.dumps({"exp": expiry}).encode()).decode().rstrip("=")
    return "synthetic." + payload + ".signature"


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", SimpleNamespace(ClaudeAgentOptions=SimpleNamespace, query=lambda **kw: None))
    creds = {
        "claude": auth.AnthropicOAuthCreds("synthetic-claude-access", "synthetic-claude-refresh", int((time.time() + 3600) * 1000)),
        "codex": auth.CodexCreds("synthetic-conflicting-key", token(time.time() + 3600), "synthetic-refresh", "synthetic-account", "chatgpt", "synthetic-id"),
    }
    monkeypatch.setattr(auth, "load_anthropic_oauth", lambda: creds["claude"])
    monkeypatch.setattr(auth, "load_codex", lambda: creds["codex"])
    monkeypatch.setattr(auth, "detect_upstream_cli", lambda name: Path("/synthetic") / name)
    monkeypatch.setattr(auth, "load_codex_default_model", lambda: "gpt-6-astra")
    monkeypatch.setattr(oauth.config, "load_harness_config", lambda: {"auth": "codex", "preferred_model": "gpt-6-astra"})
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.setenv(key, "synthetic-forbidden-key")

    def forbidden(*args, **kwargs):
        raise AssertionError("managed execution used legacy authentication or refreshed global credentials")

    monkeypatch.setattr(auth, "resolve", forbidden)
    monkeypatch.setattr(auth, "refresh_codex", forbidden)
    monkeypatch.setattr(auth, "load_voss_creds", forbidden)
    monkeypatch.setattr(appmod, "_resolve_provider", forbidden)
    app = appmod.create_app("synthetic-transport", oauth_only=True)
    client = TestClient(app, headers={"Authorization": "Bearer synthetic-transport"})
    return creds, app, client


def test_metadata_checks_create_no_sessions_and_expose_no_credentials(setup, tmp_path):
    creds, app, client = setup
    result = client.get("/harnesses")
    assert result.status_code == 200
    assert all(row["available"] for row in result.json()["harnesses"])
    assert result.json()["selected_harness"] == "codex"
    assert all(row["check_scope"] == "local_metadata" for row in result.json()["harnesses"])
    assert "synthetic" not in result.text
    assert app.state.sessions.list() == []
    assert not list(tmp_path.iterdir())
    assert client.get("/harnesses", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert "harness.oauth-only.v1" in client.get("/capabilities").json()["capabilities"]
    assert {row["auth"] for row in client.get("/models").json()["models"]} == {"claude", "codex"}


@pytest.mark.parametrize("state,code", [("missing", "oauth_missing"), ("expired", "oauth_expired"), ("api", "oauth_required"), ("malformed", "check_failed"), ("failure", "check_failed")])
def test_unavailable_login_affects_only_its_harness(setup, monkeypatch, state, code):
    creds, app, client = setup
    if state == "missing":
        creds["codex"] = None
    elif state == "expired":
        creds["codex"].access_token = token(time.time() - 60)
    elif state == "api":
        creds["codex"].auth_mode = "ApiKey"
    elif state == "malformed":
        creds["codex"].access_token = "malformed"
    else:
        monkeypatch.setattr(auth, "load_codex", lambda: (_ for _ in ()).throw(RuntimeError("synthetic-private-detail")))
    response = client.post("/harness/preflight", json={"harness": "codex"})
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["code"] == code
    assert "synthetic" not in response.text
    assert client.post("/harness/preflight", json={"harness": "claude"}).json()["available"]
    launch = client.post("/session", json={"auth": "codex"})
    assert launch.status_code == 200
    assert launch.json()["status"] == "unavailable"
    assert app.state.sessions.list() == []


def test_saved_account_and_custom_routes_are_unavailable_without_mutating_defaults(setup):
    _, app, client = setup
    for body in ({"harness": "codex", "account_alias": "saved"}, {"harness": "custom"}, {"harness": "codex", "model": "claude-sonnet-5-5"}):
        result = client.post("/harness/preflight", json=body)
        assert result.status_code == 200
        assert not result.json()["available"]
    assert oauth.config.load_harness_config()["preferred_model"] == "gpt-6-astra"
    assert app.state.sessions.list() == []


def test_bound_providers_exclude_conflicting_api_authentication(setup):
    _, _, client = setup
    for mode in ("claude", "codex"):
        result, binding = oauth.prepare(oauth.PreflightBody(harness=mode))
        assert result.available
        if mode == "claude":
            options = binding.provider._make_options(system_prompt="", model=result.model, schema=None)
            assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == "synthetic-claude-access"
            assert options.env["ANTHROPIC_API_KEY"] == options.env["ANTHROPIC_AUTH_TOKEN"] == ""
            assert json.loads(options.settings)["forceLoginMethod"] == "claudeai"
            assert options.setting_sources == []
        else:
            assert binding.provider.creds.api_key is None
            assert binding.provider.creds.refresh_token is None
            assert binding.provider.base_url == auth.CHATGPT_BACKEND_BASE
            assert binding.provider.allow_refresh is False
    assert client.get("/doctor").status_code == 200


@pytest.mark.asyncio
async def test_auth_loss_before_launch_can_be_retried_but_recheck_never_starts_work(setup, monkeypatch):
    creds, app, client = setup
    original = creds["codex"]
    calls = []

    async def turn(session, text, mode):
        calls.append(session.id)
        session.turn_outcome = "done"

    monkeypatch.setattr(appmod, "_run_turn", turn)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=client.headers) as api:
        sid = (await api.post("/session", json={"auth": "codex"})).json()["id"]
        body = {"command_id": "one", "parts": [{"text": "do it"}]}
        creds["codex"] = None
        response = await api.post(f"/session/{sid}/message", json=body)
        assert response.json()["status"] == "unavailable"
        snapshot = (await api.get(f"/session/{sid}/task")).json()
        assert snapshot["phase"] == "waiting" and snapshot["outcome"] == "authentication_required"
        assert snapshot["run_id"] is None
        creds["codex"] = original
        assert (await api.post("/harness/preflight", json={"harness": "codex"})).json()["available"]
        assert calls == []
        assert (await api.post(f"/session/{sid}/message", json=body)).json()["status"] == "accepted"
        await app.state.sessions.get(sid).task
        assert len(calls) == 1
        assert (await api.get(f"/session/{sid}/task")).json()["phase"] == "completed"
    app.state.sessions.journal.close()


@pytest.mark.asyncio
async def test_revoked_oauth_waits_for_operator_without_retry_or_global_refresh(setup, monkeypatch):
    _, app, client = setup
    calls = []

    async def complete(self, **kwargs):
        calls.append("oauth")
        raise auth.OAuthRequired("sign in")

    async def turn(session, text, mode):
        await session.provider.complete(messages=[], model=session.model)

    monkeypatch.setattr(OpenAIOAuthProvider, "complete", complete)
    monkeypatch.setattr(appmod, "_run_turn", turn)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=client.headers) as api:
        sid = (await api.post("/session", json={"auth": "codex"})).json()["id"]
        await api.post(f"/session/{sid}/message", json={"parts": [{"text": "do it"}]})
        session = app.state.sessions.get(sid)
        await session.task
        snapshot = (await api.get(f"/session/{sid}/task")).json()
        assert snapshot["phase"] == "waiting" and snapshot["outcome"] == "authentication_required"
        assert snapshot["pending_actions"][0]["code"] == "oauth_rejected"
        for _ in range(2):
            with pytest.raises(auth.OAuthRequired):
                await session.provider.complete(messages=[], model=session.model)
        assert calls == ["oauth"]
        assert (await api.post(f"/session/{sid}/model", json={"auth": "api", "model": "gpt-6-astra"})).json()["status"] == "unavailable"
    app.state.sessions.journal.close()


@pytest.mark.parametrize("role", ["coordinator", "builder-1", "reviewer"])
def test_every_swarm_role_is_preflighted_before_persistence(setup, role):
    _, app, client = setup
    roster = [{"name": name, "auth_pref": "api" if name == role else "codex"} for name in ("coordinator", "builder-1", "reviewer")]
    response = client.post("/swarm", json={"goal": "synthetic", "roster": roster})
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert app.state.sessions.list() == []
    assert not list(Path.cwd().iterdir())


@pytest.mark.parametrize("agent,args,command", [("custom", [], "fake"), ("gemini", [], ""), ("codex", ["--config", "model_provider=other"], "")])
def test_unverified_launchers_cannot_bypass_oauth_policy(setup, agent, args, command):
    _, app, client = setup
    response = client.post("/swarm", json={"goal": "synthetic", "roster": [{"name": "coordinator", "auth_pref": "codex"}, {"name": "builder-1", "agent": agent, "args": args, "command": command}]})
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert app.state.sessions.list() == []


@pytest.mark.parametrize("harness", ["claude", "codex"])
def test_cli_invocations_isolate_oauth_and_remove_api_credentials(setup, monkeypatch, tmp_path, harness):
    captured = {}

    def spawn(argv, **kwargs):
        captured.update(argv=argv, **kwargs)
        if harness == "codex":
            auth_file = Path(kwargs["env"]["CODEX_HOME"]) / "auth.json"
            payload = json.loads(auth_file.read_text())
            assert payload["auth_mode"] == "chatgpt"
            assert "OPENAI_API_KEY" not in payload
            assert auth_file.stat().st_mode & 0o777 == 0o600
        return SimpleNamespace(wait=lambda timeout=None: 0)

    monkeypatch.setattr(oauth.subprocess, "Popen", spawn)
    _, binding = oauth.prepare(oauth.PreflightBody(harness=harness))
    handle = oauth.spawn_cli(binding, [harness, "exec", "synthetic task"], tmp_path)
    assert not any(key.endswith("_API_KEY") for key in captured["env"])
    assert "ANTHROPIC_AUTH_TOKEN" not in captured["env"]
    assert captured["start_new_session"]
    assert handle.wait() == 0
    if harness == "codex":
        assert not Path(captured["env"]["CODEX_HOME"]).exists()
        assert 'forced_login_method="chatgpt"' in captured["argv"]
    else:
        assert captured["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "synthetic-claude-access"
    assert oauth.os.environ["OPENAI_API_KEY"] == "synthetic-forbidden-key"


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("status", [401, 403])
async def test_oauth_rejection_makes_one_subscription_request_and_never_refreshes(setup, stream, status):
    creds, _, _ = setup
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.host == "chatgpt.com"
        assert request.headers["authorization"] == "Bearer " + creds["codex"].access_token
        assert "synthetic-forbidden-key" not in str(request.headers)
        return httpx.Response(status, json={"error": "synthetic-private-detail"})

    _, binding = oauth.prepare(oauth.PreflightBody(harness="codex"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        binding.provider._client = client
        for _ in range(2):
            with pytest.raises(auth.OAuthRequired):
                if stream:
                    async for _ in binding.stream(messages=[], model="gpt-6-astra"):
                        pass
                else:
                    await binding.complete(messages=[], model="gpt-6-astra")
    assert len(calls) == 1
    assert binding.blocked.code == "oauth_rejected"
    assert "synthetic-private-detail" not in binding.blocked.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["authentication", "process"])
async def test_claude_auth_failures_stop_dispatch_without_exposing_sdk_errors(setup, failure):
    calls = []

    async def query(**kwargs):
        calls.append(kwargs)
        if failure == "process":
            raise type("ProcessError", (RuntimeError,), {})("synthetic-private-detail")
        yield SimpleNamespace(error="authentication_failed")

    _, binding = oauth.prepare(oauth.PreflightBody(harness="claude"))
    binding.provider._query_fn = query
    for _ in range(2):
        with pytest.raises(auth.OAuthRequired):
            await binding.complete(messages=[], model=binding.availability.model)
    assert len(calls) == 1
    assert "synthetic-private-detail" not in binding.blocked.model_dump_json()


@pytest.mark.asyncio
async def test_swarm_rechecks_all_roles_and_only_explicit_run_recovers_before_acceptance(setup, monkeypatch):
    creds, app, client = setup
    original = creds["codex"]
    seeds = []
    from voss.harness import swarm_coordinator

    async def seed(*args, provider, **kwargs):
        seeds.append(provider)
        assert isinstance(provider, oauth.BoundProvider)
        assert provider.availability.harness == "codex"
        raise auth.OAuthRequired("synthetic stop")

    monkeypatch.setattr(swarm_coordinator, "seed_tasks", seed)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=client.headers) as api:
        created = (await api.post("/swarm", json={"goal": "synthetic", "roster": [
            {"name": name, "auth_pref": "codex"} for name in ("coordinator", "builder-1", "reviewer")
        ]})).json()
        swarm_id = created["id"]
        for name, binding in app.state.oauth_bindings[swarm_id].items():
            assert binding.provider.creds.api_key is None
            assert binding.provider.allow_refresh is False
        creds["codex"] = None
        result = await api.post(f"/swarm/{swarm_id}/run")
        assert result.json()["status"] == "unavailable"
        assert seeds == [] and swarm_id not in app.state.swarm_runs
        creds["codex"] = original
        await api.get("/harnesses")
        assert seeds == []
        accepted = (await api.post(f"/swarm/{swarm_id}/run")).json()
        assert accepted["status"] == "accepted"
        await app.state.swarm_runs[swarm_id]
        assert len(seeds) == 1
        assert (await api.post(f"/swarm/{swarm_id}/run")).json() == accepted
        assert len(seeds) == 1
    app.state.sessions.journal.close()


def test_login_change_prevents_cli_spawn_and_nonzero_exit_preserves_operator_state(setup, monkeypatch, tmp_path):
    creds, _, _ = setup
    _, binding = oauth.prepare(oauth.PreflightBody(harness="codex"))
    original = creds["codex"].access_token
    creds["codex"].access_token = token(time.time() + 7200)
    monkeypatch.setattr(oauth.subprocess, "Popen", lambda *a, **kw: pytest.fail("spawned with changed login"))
    with pytest.raises(auth.OAuthRequired):
        oauth.spawn_cli(binding, ["codex", "exec"], tmp_path)
    assert binding.blocked.code == "login_changed"
    creds["codex"].access_token = original
    _, binding = oauth.prepare(oauth.PreflightBody(harness="codex"))
    monkeypatch.setattr(oauth.subprocess, "Popen", lambda *a, **kw: SimpleNamespace(wait=lambda timeout=None: 1))
    handle = oauth.spawn_cli(binding, ["codex", "exec"], tmp_path)
    directory = Path(handle.directory.name)
    with pytest.raises(auth.OAuthRequired):
        handle.wait()
    assert not directory.exists()
    assert binding.blocked.code == "worker_unavailable"

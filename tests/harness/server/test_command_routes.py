from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from voss.harness.server import app as appmod, commands


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = appmod.create_app("test-commands")
    c = TestClient(app, headers={"Authorization": "Bearer test-commands"})
    c.session = app.state.sessions.create(cwd=tmp_path, model="synthetic", provider=object())
    return c


def execute(client, name, args=None):
    body = {"name": name}
    if args is not None:
        body["args"] = args
    return client.post(f"/session/{client.session.id}/command", json=body)


def test_catalog_requires_auth_and_does_not_discover_resources(client, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Opening the palette must not initialize resources")

    monkeypatch.setattr(commands, "make_toolset", unexpected)
    monkeypatch.setattr(commands, "default_skill_registry", unexpected)
    monkeypatch.setattr(commands, "default_subagent_registry", unexpected)
    response = client.get("/commands")
    assert response.status_code == 200
    assert {c["name"] for c in response.json()["commands"]} == {"/tools", "/skills", "/agents"}
    assert all(c["description"] for c in response.json()["commands"])
    assert client.get("/commands", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post(f"/session/{client.session.id}/command", json={"name": "/tools"},
                       headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_tools_lists_builtins_and_mcp_without_executing_or_indexing(client, monkeypatch):
    closed = []

    async def close():
        closed.append(True)

    async def attach(tools, cwd):
        assert cwd == client.session.cwd
        tools["mcp__demo__search"] = SimpleNamespace(description="Search synthetic documentation")
        return SimpleNamespace(aclose=close)

    monkeypatch.setattr(commands, "attach_mcp_tools", attach)
    before = set(client.session.cwd.rglob("*"))
    response = execute(client, "/tools")
    assert response.status_code == 200
    result = response.json()
    assert "fs_read — Read a UTF-8 text file" in result["stdout"]
    assert "mcp__demo__search — Search synthetic documentation" in result["stdout"]
    assert result["stderr"] == ""
    assert closed == [True]
    assert set(client.session.cwd.rglob("*")) == before
    assert client.session.history.turns == []
    assert client.session.record.runs == []
    assert client.session.queue.empty()


def test_skills_uses_existing_discovery_and_voss_precedence(client):
    for folder, description in [(".claude", "Claude description"), (".codex", "Codex description"),
                                (".voss", "Project override")]:
        path = client.session.cwd / folder / "skills" / "review-fixture" / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(f"---\nname: review-fixture\ndescription: {description}\n---\nPrivate instructions\n")
    response = execute(client, "/skills")
    assert response.status_code == 200
    output = response.json()["stdout"]
    assert "analyze" in output
    assert "review-fixture" in output and "Project override" in output
    assert "Claude description" not in output and "Codex description" not in output
    assert "Private instructions" not in output


def test_agents_lists_builtins_and_project_definitions_without_spawning(client):
    path = client.session.cwd / ".voss" / "agents" / "reviewer.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nid: reviewer\ndescription: Review synthetic migrations\n---\nPrivate role prompt\n")
    response = execute(client, "/agents")
    assert response.status_code == 200
    output = response.json()["stdout"]
    assert "explorer" in output and "worker" in output
    assert output.count("reviewer") == 1
    assert "Review synthetic migrations" in output
    assert "Private role prompt" not in output
    assert client.session.task is None


def test_dispatch_rejects_unknown_commands_and_reports_usage(client, monkeypatch):
    monkeypatch.setattr(commands, "_skills", lambda _: pytest.fail("Invalid arguments must not execute"))
    assert execute(client, "/skill", ["run", "demo"]).status_code == 400
    assert execute(client, "!echo demo").status_code == 400
    assert execute(client, "/skills", ["extra"]).json()["stderr"] == "usage: /skills"
    assert execute(client, "/skills", "wrong type").status_code == 422
    assert client.post("/session/missing/command", json={"name": "/agents"}).status_code == 404


@pytest.mark.asyncio
async def test_slow_discovery_does_not_block_other_server_requests(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def slow_skills(cwd):
        entered.set()
        assert release.wait(5)
        return "synthetic skill"

    monkeypatch.setattr(commands, "_skills", slow_skills)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url="http://test",
                                headers={"Authorization": "Bearer test-commands"}) as api:
        task = asyncio.create_task(api.post(f"/session/{client.session.id}/command", json={"name": "/skills"}))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            response = await asyncio.wait_for(api.get(f"/session/{client.session.id}"), 1)
            assert response.status_code == 200
            assert not task.done()
        finally:
            release.set()
            result = await task
        assert result.json()["stdout"] == "synthetic skill"

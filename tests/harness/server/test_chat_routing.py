from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from voss.harness.agent import Plan, TurnResult
from voss.harness.server import app as appmod
from voss_runtime.providers.base import ProviderResponse


class ChatProvider:
    def __init__(self):
        self.requests = []

    async def complete(self, **kwargs):
        self.requests.append(kwargs)
        return ProviderResponse("hello back", kwargs["model"], 20, 5, 0.002)


@pytest.fixture
def server(monkeypatch, tmp_path):
    provider = ChatProvider()
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (
        SimpleNamespace(source="env-openai", detail="synthetic"), provider,
    ))
    monkeypatch.setattr("voss.harness.cli._render_project_index_text", lambda *a, **kw: "")
    monkeypatch.setattr("voss.harness.cli._render_code_recall_text", lambda *a, **kw: "")
    app = appmod.create_app("test-chat")
    return app, provider, tmp_path


def client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": "Bearer test-chat"},
    )


async def session(api, app, cwd):
    result = await api.post("/session", json={"cwd": str(cwd)})
    assert result.status_code == 201, result.text
    return app.state.sessions.get(result.json()["id"])


async def send(api, s, text, mode="plan"):
    result = await api.post(f"/session/{s.id}/message", json={
        "parts": [{"text": text}], "mode": mode,
    })
    assert result.status_code == 202, result.text
    events = []
    while not events or events[-1].type != "session.idle":
        events.append(await asyncio.wait_for(s.queue.get(), 2))
    return events


def no_tools(*args, **kwargs):
    raise AssertionError("ambient chat initialized tools")


async def test_chat_uses_session_model_and_history_without_tools(server, monkeypatch):
    app, provider, cwd = server
    monkeypatch.setattr(appmod, "make_toolset", no_tools)
    async with client(app) as api:
        s = await session(api, app, cwd)
        s.model = "session-model"
        s.history.summary = "We are discussing terminal clients."
        s.history.add("My project is Atlas.", role="user")
        s.history.add("I will remember Atlas.", role="assistant")
        events = await send(api, s, "What did I call my project?")

        assert len(provider.requests) == 1
        request = provider.requests[0]
        assert request["model"] == "session-model"
        assert "tools" not in request
        assert "Atlas" in str(request["messages"])
        assert "terminal clients" in str(request["messages"])
        assert request["messages"][-1] == {"role": "user", "content": "What did I call my project?"}
        assert [e.text for e in events if e.type == "final"] == ["hello back"]
        assert all(e.phase == "ambient" for e in events if e.type == "status")
        assert any(e.type == "status" for e in events)
        assert not any(e.type in ("plan", "tool") for e in events)
        cost = (await api.get(f"/session/{s.id}/cost")).json()
        assert cost["total_usd"] == 0.002
        assert s.task is None


async def test_status_question_is_local_and_uses_session_selection(server, monkeypatch):
    app, provider, cwd = server
    monkeypatch.setattr(appmod, "make_toolset", no_tools)
    async with client(app) as api:
        s = await session(api, app, cwd)
        s.model = "selected-model"
        events = await send(api, s, "what model are you using?", mode="edit")
        answer = next(e.text for e in events if e.type == "final")
        assert "Model: selected-model" in answer
        assert "Provider: OpenAI" in answer
        assert "Permission mode: edit" in answer
        assert provider.requests == []
        assert s.history.last(2)[-1]["content"] == answer


@pytest.mark.parametrize("text,swarm", [("fix the test failure", False), ("hello", True)])
async def test_work_and_swarm_tasks_keep_agent_permissions(server, monkeypatch, text, swarm):
    app, provider, cwd = server
    seen = {}

    async def run(text, **kwargs):
        seen.update(kwargs)
        return TurnResult(Plan(rationale="test", steps=[], confidence=1), 1, "done", [], 0, None)

    monkeypatch.setattr(appmod, "run_turn", run)
    async with client(app) as api:
        s = await session(api, app, cwd)
        if swarm:
            s.swarm_id = "synthetic-swarm"
        events = await send(api, s, text, mode="edit")
        assert seen["permissions"].mode == "edit"
        assert seen["provider"] is provider
        assert provider.requests == []
        assert [e.phase for e in events if e.type == "status"] == ["run", "ambient"]


@pytest.mark.parametrize("text", ["hello", "run the tests"])
async def test_abort_and_failure_restore_idle_and_allow_next_message(server, monkeypatch, text):
    app, provider, cwd = server
    if text == "hello":
        monkeypatch.setattr(appmod, "make_toolset", no_tools)
    entered = asyncio.Event()

    async def blocked(**kwargs):
        entered.set()
        await asyncio.Event().wait()

    complete = provider.complete
    provider.complete = blocked

    async def blocked_run(text, **kwargs):
        await blocked()

    monkeypatch.setattr(appmod, "run_turn", blocked_run)
    async with client(app) as api:
        s = await session(api, app, cwd)
        await api.post(f"/session/{s.id}/message", json={"parts": [{"text": text}]})
        await asyncio.wait_for(entered.wait(), 2)
        task = s.task
        busy = await api.post(f"/session/{s.id}/message", json={"parts": [{"text": "hello"}]})
        assert busy.status_code == 409
        assert (await api.post(f"/session/{s.id}/abort")).status_code == 202
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not s.busy
        events = []
        while not s.queue.empty():
            events.append(s.queue.get_nowait())
        assert events[-1].type == "session.idle"
        assert [e.phase for e in events if e.type == "status"][-1] == "ambient"
        assert not any(e.type == "final" for e in events)

        async def failed(**kwargs):
            raise RuntimeError("synthetic provider failure")

        provider.complete = failed
        events = await send(api, s, "hello again")
        assert any("synthetic provider failure" in getattr(e, "text", "") for e in events)
        assert not s.busy
        provider.complete = complete
        events = await send(api, s, "hello once more")
        assert any(e.type == "final" for e in events)


async def test_resumed_chat_sees_saved_conversation_and_keeps_run_context(server, monkeypatch):
    app, provider, cwd = server
    make_toolset = appmod.make_toolset
    monkeypatch.setattr(appmod, "make_toolset", no_tools)
    async with client(app) as api:
        s = await session(api, app, cwd)
        s.record.runs.append({"goal": "fix Atlas", "cost_usd": 0.01})
        await send(api, s, "hello, my project is Atlas")
        await api.delete(f"/session/{s.id}")
        result = await api.post("/session", json={"cwd": str(cwd), "resume": s.id})
        assert result.status_code == 201, result.text
        resumed = app.state.sessions.get(s.id)
        await send(api, resumed, "what was my project called?")
        assert "Atlas" in str(provider.requests[-1]["messages"])
        assert resumed.prior_context is not None
        assert (await api.get(f"/session/{s.id}/cost")).json()["total_usd"] == 0.014

        monkeypatch.setattr(appmod, "make_toolset", make_toolset)
        seen = {}

        async def run(text, **kwargs):
            seen.update(kwargs)
            return TurnResult(Plan(rationale="test", steps=[], confidence=1), 1, "done", [], 0, None)

        monkeypatch.setattr(appmod, "run_turn", run)
        await send(api, resumed, "fix Atlas")
        assert seen["prior_context"][0]["goal"] == "fix Atlas"
        assert seen["history"] is resumed.history
        assert resumed.prior_context is None

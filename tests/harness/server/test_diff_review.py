from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from voss.harness.agent import Plan, TurnResult
from voss.harness.server import app as appmod
from voss.harness.server.diffs import DIFF_EVENT_MAX_BYTES, DiffReviewRenderer
from voss.harness.tools import make_toolset


@pytest.fixture
def server(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_resolve_provider", lambda pref: (
        SimpleNamespace(source="env-openai", detail="synthetic"), object(),
    ))
    monkeypatch.setattr("voss.harness.cli._render_project_index_text", lambda *a, **kw: "")
    monkeypatch.setattr("voss.harness.cli._render_code_recall_text", lambda *a, **kw: "")

    async def scoped(cwd, text, session_id, run, make_turn):
        return await make_turn({})

    async def no_mcp(*args, **kwargs):
        return None

    monkeypatch.setattr("voss.harness.cli._scoped_turn", scoped)
    monkeypatch.setattr(appmod, "attach_mcp_tools", no_mcp)
    monkeypatch.setattr(appmod, "make_toolset", lambda cwd, **kw: make_toolset(cwd, background_indexing=False, **kw))
    (tmp_path / "f.txt").write_text("alpha\nbeta\n")
    return appmod.create_app("test-diff"), tmp_path


def client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": "Bearer test-diff"},
    )


async def create(api, app, cwd, **kwargs):
    r = await api.post("/session", json={"cwd": str(cwd), **kwargs})
    assert r.status_code == 201, r.text
    return app.state.sessions.get(r.json()["id"])


async def event(s, kind):
    async with asyncio.timeout(3):
        while True:
            ev = await s.queue.get()
            if ev.type == kind:
                return ev


def edit(monkeypatch, *, batch=False, new="BETA"):
    results = []

    async def run(text, **kwargs):
        tools = kwargs["tools"]
        if batch:
            result = await tools["fs_edit_many"].invoke(
                path="f.txt", edits=[{"old": "alpha", "new": "ALPHA"}, {"old": "beta", "new": new}],
            )
        else:
            result = await tools["fs_edit"].invoke(path="f.txt", old="beta", new=new)
        results.append(result)
        return TurnResult(Plan(rationale="test", steps=[], confidence=1), 1, result, [], 0, None)

    monkeypatch.setattr(appmod, "run_turn", run)
    return results


async def start(api, s):
    r = await api.post(f"/session/{s.id}/message", json={"parts": [{"text": "fix f.txt"}], "mode": "edit"})
    assert r.status_code == 202, r.text


@pytest.mark.parametrize("batch,decisions,expected", [
    (False, ["accept"], "alpha\nBETA\n"),
    (False, ["reject"], "alpha\nbeta\n"),
    (False, ["skip"], "alpha\nbeta\n"),
    (False, [], "alpha\nbeta\n"),
    (True, ["accept", "accept"], "ALPHA\nBETA\n"),
    (True, ["accept", "reject"], "alpha\nbeta\n"),
    (True, ["skip", "accept"], "alpha\nbeta\n"),
    (True, [], "alpha\nbeta\n"),
])
async def test_review_before_write(server, monkeypatch, batch, decisions, expected):
    app, cwd = server
    edit(monkeypatch, batch=batch)
    async with client(app) as api:
        s = await create(api, app, cwd, review_diffs=True)
        await start(api, s)
        proposal = await event(s, "diff.proposed")
        assert (cwd / "f.txt").read_text() == "alpha\nbeta\n"
        assert proposal.hunks[-1].model_dump() == {"file": "f.txt", "start": 2, "lines": ["- beta", "+ BETA"]}
        assert len(proposal.hunks) == (2 if batch else 1)
        assert (await api.get(f"/session/{s.id}")).json()["busy"] is True
        r = await api.post(f"/session/{s.id}/diff", json={"id": proposal.id, "decisions": decisions})
        assert r.json()["status"] == "ok"
        assert (await event(s, "diff.resolved")).id == proposal.id
        await event(s, "session.idle")
        assert (cwd / "f.txt").read_text() == expected
        assert not s.pending_diffs
        assert not s.busy
        assert (await api.post(f"/session/{s.id}/diff", json={"id": proposal.id, "decisions": decisions})).json()["status"] == "stale"


async def test_invalid_or_cross_session_reply_cannot_approve(server, monkeypatch):
    app, cwd = server
    edit(monkeypatch, batch=True)
    async with client(app) as api:
        s = await create(api, app, cwd, review_diffs=True)
        other = await create(api, app, cwd)
        await start(api, s)
        proposal = await event(s, "diff.proposed")
        body = {"id": proposal.id, "decisions": ["accept", "accept"]}
        assert (await api.post(f"/session/{other.id}/diff", json=body)).json()["status"] == "stale"
        for decisions in (["accept"], ["accept", "accept", "accept"], ["yes", "accept"], None):
            r = await api.post(f"/session/{s.id}/diff", json={**body, "decisions": decisions})
            assert r.status_code == 422
            assert not s.pending_diffs[proposal.id].future.done()
            assert (cwd / "f.txt").read_text() == "alpha\nbeta\n"
        await api.post(f"/session/{s.id}/diff", json={**body, "decisions": []})
        await event(s, "session.idle")


@pytest.mark.parametrize("action", ["abort", "delete"])
async def test_cancel_turn_removes_pending_review_without_writing(server, monkeypatch, action):
    app, cwd = server
    edit(monkeypatch)
    async with client(app) as api:
        s = await create(api, app, cwd, review_diffs=True)
        await start(api, s)
        proposal = await event(s, "diff.proposed")
        task = s.task
        if action == "abort":
            assert (await api.post(f"/session/{s.id}/abort")).status_code == 202
        else:
            assert (await api.delete(f"/session/{s.id}")).status_code == 204
        with pytest.raises(asyncio.CancelledError):
            await task
        assert (await event(s, "diff.resolved")).id == proposal.id
        await event(s, "session.idle")
        assert not s.pending_diffs
        assert (cwd / "f.txt").read_text() == "alpha\nbeta\n"
        if action == "abort":
            await start(api, s)
            again = await event(s, "diff.proposed")
            assert again.id != proposal.id
            await api.post(f"/session/{s.id}/diff", json={"id": again.id, "decisions": []})
            await event(s, "session.idle")


async def test_timeout_and_oversized_preview_fail_closed(server, monkeypatch):
    app, cwd = server
    show = DiffReviewRenderer.show_diff_modal

    async def fast_timeout(self, hunks, **kwargs):
        return await show(self, hunks, timeout_s=0.01)

    monkeypatch.setattr(DiffReviewRenderer, "show_diff_modal", fast_timeout)
    results = edit(monkeypatch)
    async with client(app) as api:
        s = await create(api, app, cwd, review_diffs=True)
        await start(api, s)
        proposal = await event(s, "diff.proposed")
        await event(s, "diff.resolved")
        await event(s, "session.idle")
        assert "denied" in results[-1]
        assert not s.pending_diffs
        assert (await api.post(f"/session/{s.id}/diff", json={"id": proposal.id, "decisions": ["accept"]})).json()["status"] == "stale"
        results = edit(monkeypatch, new="x" * DIFF_EVENT_MAX_BYTES)
        await start(api, s)
        assert "too large" in (await event(s, "warning")).message
        await event(s, "session.idle")
        assert "denied" in results[-1]
        assert not s.pending_diffs
        assert (cwd / "f.txt").read_text() == "alpha\nbeta\n"


@pytest.mark.parametrize("batch", [False, True])
@pytest.mark.parametrize("change", ["replace", "delete"])
async def test_changes_during_review_are_not_overwritten(server, monkeypatch, batch, change):
    app, cwd = server
    results = edit(monkeypatch, batch=batch)
    async with client(app) as api:
        s = await create(api, app, cwd, review_diffs=True)
        await start(api, s)
        proposal = await event(s, "diff.proposed")
        p = cwd / "f.txt"
        if change == "replace":
            p.write_text("external edit\n")
        else:
            p.unlink()
        await api.post(f"/session/{s.id}/diff", json={"id": proposal.id, "decisions": ["accept"] * len(proposal.hunks)})
        await event(s, "session.idle")
        assert "file changed during review" in results[-1]
        assert p.read_text() == "external edit\n" if change == "replace" else not p.exists()


async def test_old_clients_keep_behavior_and_resuming_can_opt_in(server, monkeypatch):
    app, cwd = server
    results = edit(monkeypatch)
    async with client(app) as api:
        s = await create(api, app, cwd)
        assert not s.review_diffs
        await start(api, s)
        await event(s, "session.idle")
        assert results[-1].startswith("edited")
        assert (cwd / "f.txt").read_text() == "alpha\nBETA\n"
        await api.delete(f"/session/{s.id}")
        resumed = await create(api, app, cwd, resume=s.id, review_diffs=True)
        assert resumed.review_diffs
        assert resumed.id == s.id


async def test_sse_disconnect_cancels_pending_edit(server, monkeypatch):
    app, cwd = server
    edit(monkeypatch)
    async with client(app) as api:
        s = await create(api, app, cwd, review_diffs=True)
        await start(api, s)
        task = s.task
        received, disconnected = asyncio.Event(), asyncio.Event()

        async def receive():
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if b"diff.proposed" in message.get("body", b""):
                received.set()

        scope = {
            "type": "http", "method": "GET", "http_version": "1.1",
            "path": f"/session/{s.id}/events", "query_string": b"",
            "headers": [(b"authorization", b"Bearer test-diff")],
            "scheme": "http", "server": ("test", 80), "client": ("test", 1234),
            "root_path": "",
        }
        stream = asyncio.create_task(app(scope, receive, send))
        try:
            await asyncio.wait_for(received.wait(), 3)
        finally:
            disconnected.set()
            await asyncio.wait_for(stream, 3)
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not s.pending_diffs
        assert (cwd / "f.txt").read_text() == "alpha\nbeta\n"

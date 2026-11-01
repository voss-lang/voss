from __future__ import annotations

import asyncio
import threading
from contextlib import contextmanager
from dataclasses import asdict
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from voss.harness.server import app as appmod, commands
from voss.harness import session as session_store
from voss.harness.memory_store import MemoryStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = appmod.create_app("test-commands")
    from voss.harness.server.task_journal import TaskJournal
    app.state.sessions.journal = TaskJournal(tmp_path.parent / (tmp_path.name + "-tasks.sqlite3"))
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
    monkeypatch.setattr(commands, "open_memory_store", unexpected)
    response = client.get("/commands")
    assert response.status_code == 200
    assert {c["name"] for c in response.json()["commands"]} == {
        "/tools", "/skills", "/agents", "/symbol", "/refs", "/refresh",
        "/probable", "/btrace", "/vdiff", "/budget", "/why",
        "/save-session", "/save", "/forget",
    }
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


def test_save_session_persists_current_history_name_model_and_cost(client):
    s = client.session
    s.history.add("synthetic prompt")
    s.history.add("synthetic answer", role="assistant")
    s.model = "selected-model"
    s.record.model_auth = "codex"
    s.record.total_cost_usd = 1.25
    s.record.runs.append({"cost_usd": 1.25, "judgments_cost_usd": 0.25})
    assert not session_store.session_path(s.id, s.cwd).exists()

    result = execute(client, "/save-session", ["Named", "conversation"]).json()
    assert result["stderr"] == "" and result["stdout"].startswith("saved: ")
    saved, history = session_store.load(s.id, cwd=s.cwd)
    assert saved.name == "Named conversation"
    assert saved.model == "selected-model" and saved.model_auth == "codex"
    assert saved.total_cost_usd == 1.25 and saved.judgments_cost_usd == 0.25
    assert history.last(10) == s.history.last(10)
    assert client.get(f"/session/{s.id}").json()["title"] == saved.name
    assert client.get("/sessions/saved", params={"cwd": str(s.cwd)}).json()["sessions"][0]["name"] == saved.name
    s.history.add("another turn")
    assert execute(client, "/save-session").json()["stderr"] == ""
    saved, history = session_store.load(s.id, cwd=s.cwd)
    assert saved.name == "Named conversation" and len(history.turns) == 3
    assert s.queue.empty() and s.task is None


def test_save_session_preserves_cost_from_older_sessions_without_run_records(client):
    client.session.record.total_cost_usd = 4.25
    assert client.session.record.runs == []
    assert execute(client, "/save-session").json()["stderr"] == ""
    saved, _ = session_store.load(client.session.id, cwd=client.session.cwd)
    assert saved.total_cost_usd == 4.25


def test_failed_save_session_keeps_name_and_releases_busy_state(client, monkeypatch):
    record, title = client.session.record, client.session.title

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(session_store, "save", fail)
    result = execute(client, "/save-session", ["new name"]).json()
    assert result["stderr"] == "/save-session failed: disk full"
    assert result["stdout"] == ""
    assert client.session.record is record and client.session.title == title
    assert not client.session.busy


def test_save_and_forget_use_local_memory_without_renaming_conversation(client, monkeypatch):
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda _: None)
    name = client.session.record.name
    result = execute(client, "/save", ["synthetic", "note"]).json()
    assert result["stderr"] == ""
    path = client.session.cwd / result["stdout"].removeprefix("note saved: ")
    assert path.is_file() and "synthetic note" in path.read_text()
    assert client.session.id in path.read_text()
    assert client.session.record.name == name
    assert execute(client, "/forget", ["note:*", "--yes"]).json()["stdout"] == "tombstoned: 1 entries"
    assert client.session.memory_store.recall("synthetic", source="notes") == []
    assert execute(client, "/forget", ["note:missing", "--yes"]).json()["stdout"] == "tombstoned: 0 entries"
    assert client.session.history.turns == [] and client.session.queue.empty()


@pytest.mark.parametrize("name,args", [
    ("/save", []), ("/save", [" "]), ("/save-session", [" "]),
    ("/forget", []), ("/forget", ["*"]), ("/forget", ["*", "--no"]),
    ("/forget", ["*", "--yes", "extra"]), ("/forget", [" ", "--yes"]),
])
def test_invalid_memory_commands_do_not_open_store_or_save(client, monkeypatch, name, args):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid command must not access storage")

    monkeypatch.setattr(commands, "open_memory_store", unexpected)
    monkeypatch.setattr(session_store, "save", unexpected)
    result = execute(client, name, args).json()
    assert result["stdout"] == "" and result["stderr"].startswith("usage: ")
    assert not client.session.busy


def test_memory_commands_honor_configured_remote_backend(client, monkeypatch):
    from tests.harness.test_memory_gateway import FakeRemoteClient
    from voss.harness.memory_gateway import MemoryApiClient

    config = client.session.cwd / ".voss" / "config.yml"
    config.parent.mkdir()
    config.write_text("memory:\n  retained_backend: laravel\n  service_project: demo\n")
    remote = FakeRemoteClient()
    monkeypatch.setattr(MemoryApiClient, "from_env", classmethod(lambda cls: remote))
    result = execute(client, "/save", ["synthetic remote note"]).json()
    assert result["stdout"] == "note saved: memory:demo:new-1"
    assert remote.created[0]["body"] == "synthetic remote note"
    assert remote.created[0]["provenance"]["session_id"] == client.session.id
    assert not list((client.session.cwd / ".voss" / "memory" / "notes").glob("*.md"))
    assert execute(client, "/forget", ["memory:demo:m1"]).json()["stderr"]
    assert execute(client, "/forget", ["*", "--yes"]).json()["stderr"].startswith("/forget failed:")
    assert remote.deleted == []
    assert execute(client, "/forget", ["memory:demo:m1", "--yes"]).json()["stdout"] == "tombstoned: 1 entries"
    assert remote.deleted[0]["id"] == "m1" and remote.deleted[0]["expected_revision"] == 1


def test_memory_backend_error_is_reported_without_success_or_local_fallback(client):
    config = client.session.cwd / ".voss" / "config.yml"
    config.parent.mkdir()
    config.write_text("memory:\n  retained_backend: laravel\n")
    result = execute(client, "/save", ["synthetic note"]).json()
    assert result["stdout"] == "" and "memory.service_project is required" in result["stderr"]
    assert not (config.parent / "memory").exists()
    assert not client.session.busy


def test_save_reports_lock_contention_without_claiming_a_note_was_saved(client, monkeypatch):
    @contextmanager
    def busy_lock(*args):
        yield None

    monkeypatch.setattr(MemoryStore, "_lock", busy_lock)
    result = execute(client, "/save", ["synthetic note"]).json()
    assert result["stdout"] == "" and result["stderr"] == "/save failed: memory store is busy; retry"
    assert not list((client.session.cwd / ".voss" / "memory" / "notes").glob("*.md"))
    assert not client.session.busy


@pytest.mark.parametrize("name,args", [
    ("/save-session", []), ("/save", ["note"]), ("/forget", ["*", "--yes"]),
])
def test_memory_mutations_reject_busy_session(client, name, args):
    client.session.switching = True
    assert execute(client, name, args).status_code == 409
    assert not list(client.session.cwd.rglob("*"))


@pytest.mark.asyncio
async def test_save_session_blocks_conflicting_work_without_blocking_reads(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    save = session_store.save

    def slow_save(*args):
        entered.set()
        assert release.wait(5)
        return save(*args)

    monkeypatch.setattr(session_store, "save", slow_save)
    path = f"/session/{client.session.id}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url="http://test",
                                headers={"Authorization": "Bearer test-commands"}) as api:
        task = asyncio.create_task(api.post(path + "/command", json={"name": "/save-session"}))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            response = await asyncio.wait_for(api.get(path), 1)
            assert response.json()["busy"]
            for suffix, body in [
                ("/command", {"name": "/save", "args": ["note"]}),
                ("/command", {"name": "/budget", "args": ["5"]}),
                ("/clear", {}), ("/message", {"parts": [{"type": "text", "text": "new turn"}]}),
                ("/model", {"model": "other"}),
            ]:
                assert (await api.post(path + suffix, json=body)).status_code == 409
        finally:
            release.set()
            result = await task
        assert result.json()["stderr"] == ""
        assert not (await api.get(path)).json()["busy"]


@pytest.mark.asyncio
async def test_cancelled_save_stays_busy_until_storage_finishes(client, monkeypatch):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    save = session_store.save

    def slow_save(*args):
        entered.set()
        assert release.wait(5)
        try:
            return save(*args)
        finally:
            finished.set()

    monkeypatch.setattr(session_store, "save", slow_save)
    path = f"/session/{client.session.id}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url="http://test",
                                headers={"Authorization": "Bearer test-commands"}) as api:
        request = asyncio.create_task(api.post(path + "/command", json={"name": "/save-session"}))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            assert (await api.get(path)).json()["busy"]
            assert (await api.post(path + "/clear")).status_code == 409
            assert (await api.post(path + "/command", json={"name": "/save", "args": ["note"]})).status_code == 409
        finally:
            release.set()
            assert await asyncio.to_thread(finished.wait, 2)
            await asyncio.wait_for(client.session.command_task, 2)
        assert (await api.post(path + "/command", json={"name": "/save-session"})).status_code == 200


def test_budget_reports_session_spending_and_can_be_cleared(client):
    client.session.record.runs.append({"cost_usd": 1.25, "judgments_cost_usd": 0.25})
    assert execute(client, "/budget").json()["stdout"] == "  budget: unbounded"
    assert execute(client, "/budget", ["$5.00"]).json()["stdout"] == "  budget: $5.00 (used $1.5000)"
    assert execute(client, "/budget").json()["stdout"] == "  budget: $5.00 (used $1.5000)"
    cost = client.get(f"/session/{client.session.id}/cost").json()
    assert cost["budget_usd"] == 5.0
    assert cost["total_usd"] == 1.5
    assert "already over budget" in execute(client, "/budget", ["1"]).json()["stdout"]
    assert execute(client, "/budget", ["0"]).json()["stdout"] == "  budget: cleared (unbounded)"
    assert execute(client, "/budget").json()["stdout"] == "  budget: unbounded"
    assert client.get(f"/session/{client.session.id}/cost").json()["budget_usd"] is None
    assert client.session.history.turns == []
    assert client.session.queue.empty()
    assert not list(client.session.cwd.rglob("*"))


@pytest.mark.parametrize("args", [["bad"], ["-1"], ["nan"], ["inf"], ["-inf"], ["1e309"], ["1", "2"]])
def test_invalid_budget_keeps_previous_setting(client, args):
    assert execute(client, "/budget", ["5"]).status_code == 200
    result = execute(client, "/budget", args).json()
    assert result["stderr"]
    assert result["stdout"] == ""
    assert execute(client, "/budget").json()["stdout"] == "  budget: $5.00 (used $0.0000)"


def test_budget_is_scoped_to_active_session_and_cannot_change_while_busy(client):
    execute(client, "/budget", ["5"])
    other = client.app.state.sessions.create(cwd=client.session.cwd, model="synthetic", provider=object())
    response = client.post(f"/session/{other.id}/command", json={"name": "/budget"})
    assert response.json()["stdout"] == "  budget: unbounded"
    client.session.switching = True
    assert execute(client, "/budget", ["10"]).status_code == 409
    assert execute(client, "/budget", ["0"]).status_code == 409
    assert execute(client, "/budget").json()["stdout"] == "  budget: $5.00 (used $0.0000)"


def test_why_reports_no_plan_and_rejects_arguments(client):
    assert execute(client, "/why").json()["stderr"] == "no plan yet — run a turn first"
    assert execute(client, "/why", ["extra"]).json()["stderr"] == "usage: /why"


def recorded_run():
    from voss.harness.session import IterationRecord, RunRecord

    return asdict(RunRecord(
        id="synthetic-run", started_at="2026-10-10T00:00:00Z", ended_at="2026-10-10T00:00:01Z",
        decisions=[
            {"title": "choose parser", "body": "first decision body", "confidence": 0.82},
            {"title": "emit tests", "body": "second decision body", "confidence": 0.47},
        ],
        iterations=[IterationRecord(index=0, prompt_tokens=10, completion_tokens=5,
                                    cache_creation_input_tokens=3, cache_read_input_tokens=2,
                                    cost_usd=0.001, exit_reason="done")],
    ))


def test_inspectors_use_latest_current_run_without_saving_or_invoking_provider(client):
    from voss.harness.voss_inspect import render_budget_timeline, render_decision_sequence

    older = recorded_run()
    older["decisions"][0]["body"] = "obsolete decision"
    run = recorded_run()
    client.session.record.runs.extend([older, run])
    before = {p: p.read_bytes() for p in client.session.cwd.rglob("*") if p.is_file()}
    for name, title, expected in [
        ("/probable", "Probable decision", render_decision_sequence(run)),
        ("/btrace", "Budget trace", render_budget_timeline(run)),
    ]:
        response = execute(client, name)
        assert response.status_code == 200
        result = response.json()
        assert result["stderr"] == ""
        assert result["stdout"] == expected
        assert result["inspection"] == {"title": title, "text": expected}
        assert "obsolete decision" not in result["stdout"]
    assert {p: p.read_bytes() for p in client.session.cwd.rglob("*") if p.is_file()} == before
    assert client.session.record.runs == [older, run]
    assert client.session.history.turns == []
    assert client.session.queue.empty()
    assert client.session.task is None


def test_inspectors_read_saved_session_by_id_prefix_or_name(client):
    from voss.harness import session as session_store

    saved = client.app.state.sessions.create(cwd=client.session.cwd, model="stub", provider=object(), title="saved run")
    saved.record.runs.append(recorded_run())
    path = session_store.save(saved.record, saved.history)
    before = path.read_bytes()
    for target in (saved.id[:8], "saved run"):
        result = execute(client, "/probable", [target, "--decision", "1"]).json()
        assert result["stderr"] == ""
        assert "second decision body" in result["stdout"]
        assert "first decision body" not in result["stdout"]
        assert "confidence: 0.47" in result["stdout"]
        assert "Recorded budget timeline" in execute(client, "/btrace", [target]).json()["stdout"]
    assert path.read_bytes() == before
    assert execute(client, "/probable", [saved.id, "--decision", "99"]).json()["stderr"].startswith("/probable failed:")


@pytest.mark.parametrize("name", ["/probable", "/btrace"])
def test_inspectors_report_empty_and_missing_sessions(client, name):
    result = execute(client, name).json()
    assert result["inspection"]["text"] == "No recorded runs. Run a task first."
    result = execute(client, name, ["missing-session"]).json()
    assert result["inspection"] is None
    assert "no session" in result["stderr"]
    run = recorded_run()
    run["decisions"], run["iterations"] = [], []
    client.session.record.runs.append(run)
    expected = "No recorded decisions." if name == "/probable" else "No recorded budget timeline."
    assert execute(client, name).json()["inspection"]["text"] == expected


def test_inspectors_reject_legacy_session_from_another_workspace(client, tmp_path):
    from voss.harness import session as session_store

    other = client.app.state.sessions.create(cwd=tmp_path / "other", model="stub", provider=object())
    other.record.runs.append(recorded_run())
    path = session_store.save(other.record, other.history)
    legacy = session_store.legacy_state_dir()
    legacy.mkdir(parents=True, exist_ok=True)
    path.rename(legacy / path.name)
    result = execute(client, "/probable", [other.id]).json()
    assert result["stdout"] == "" and result["inspection"] is None
    assert "different workspace" in result["stderr"]


@pytest.mark.parametrize(("name", "args"), [
    ("/probable", ["--decision"]), ("/probable", ["--decision", "bad"]),
    ("/probable", ["--decision", "-1"]), ("/probable", ["--decision", "0", "--decision", "1"]),
    ("/probable", ["one", "two"]), ("/probable", [""]), ("/probable", ["--unknown"]),
    ("/btrace", ["one", "two"]), ("/btrace", ["--decision", "0"]),
    ("/vdiff", []), ("/vdiff", ["one.voss", "two.voss"]), ("/vdiff", [" "]),
])
def test_inspector_usage_errors_do_not_open_a_panel(client, name, args):
    result = execute(client, name, args).json()
    assert result["stderr"]
    assert result["stdout"] == "" and result["inspection"] is None


def test_vdiff_compiles_preview_without_changing_workspace(client):
    source = client.session.cwd / "simple.voss"
    source.write_text('fn greet(name: string) -> string {\n    return "hello " + name\n}\n')
    before = {p: p.read_bytes() for p in client.session.cwd.rglob("*") if p.is_file()}
    result = execute(client, "/vdiff", ["simple.voss"]).json()
    assert result["stderr"] == ""
    assert "fn greet" in result["stdout"] and "def greet" in result["stdout"]
    assert "generated in memory" in result["stdout"]
    assert result["inspection"] == {"title": "Voss / Python", "text": result["stdout"]}
    assert {p: p.read_bytes() for p in client.session.cwd.rglob("*") if p.is_file()} == before


def test_vdiff_reports_invalid_source_and_rejects_workspace_escape(client, tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.voss"
    outside.write_text('fn outside() -> string { return "outside fixture" }')
    (tmp_path / "link.voss").symlink_to(outside)
    (tmp_path / "broken.voss").write_text("fn broken(")
    (tmp_path / "wrong.py").write_text("print('fixture')")
    (tmp_path / "directory.voss").mkdir()
    for path in ("missing.voss", "broken.voss", "wrong.py", "directory.voss", "link.voss", str(outside), "../" + outside.name):
        response = execute(client, "/vdiff", [path])
        assert response.status_code == 200
        result = response.json()
        assert result["stdout"] == "" and result["inspection"] is None
        assert result["stderr"].startswith("/vdiff failed:")


def test_vdiff_reads_cached_harness_output_but_rejects_external_cache(client, tmp_path):
    source = tmp_path / "voss" / "harness" / "agent" / "sample.voss"
    source.parent.mkdir(parents=True)
    source.write_text('fn sample() -> string { return "fixture" }')
    cached = tmp_path / ".voss-cache" / "harness" / "sample.py"
    cached.parent.mkdir(parents=True)
    cached.write_text("def sample(): return 'cached fixture'\n")
    args = [str(source.relative_to(tmp_path))]
    result = execute(client, "/vdiff", args).json()
    assert "cached fixture" in result["stdout"]
    assert "Generated Python: .voss-cache/harness/sample.py" in result["stdout"]
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    cached.rename(outside)
    cached.symlink_to(outside)
    result = execute(client, "/vdiff", args).json()
    assert "cached artifact escapes cwd" in result["stderr"]
    assert result["inspection"] is None and result["stdout"] == ""


@pytest.mark.asyncio
async def test_inspection_keeps_server_responsive(client, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    inspect = commands._inspect

    def slow_inspect(*args):
        entered.set()
        assert release.wait(5)
        return inspect(*args)

    monkeypatch.setattr(commands, "_inspect", slow_inspect)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url="http://test",
                                headers={"Authorization": "Bearer test-commands"}) as api:
        task = asyncio.create_task(api.post(f"/session/{client.session.id}/command", json={"name": "/btrace"}))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            response = await asyncio.wait_for(api.get(f"/session/{client.session.id}"), 1)
            assert response.status_code == 200
            assert not task.done()
        finally:
            release.set()
            result = await task
        assert result.json()["inspection"]["title"] == "Budget trace"


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


def test_code_commands_find_source_lines_and_refresh_changed_files(client, monkeypatch):
    monkeypatch.setattr("voss.harness.code.lsp_registry.is_lsp_available", lambda: False)
    path = client.session.cwd / "app.py"
    path.write_text("def sample_entry():\n    return 1\n\nsample_entry()\n")
    result = execute(client, "/symbol", ["sample_entry"]).json()
    assert result["stderr"] == ""
    assert result["code"] == {
        "query": "/symbol sample_entry", "truncated": False,
        "items": [{"file": "app.py", "line": 1, "name": "sample_entry", "language": "python",
                   "source": "index", "snippet": "def sample_entry():"}],
    }
    refs = execute(client, "/refs", ["sample_entry"]).json()["code"]["items"]
    assert [(r["line"], r["source"]) for r in refs] == [(1, "regex"), (4, "regex")]
    assert refs[1]["snippet"] == "sample_entry()"

    path.write_text("def replacement(): pass\n")
    refreshed = execute(client, "/refresh").json()
    assert refreshed["stdout"] == "refreshed code index: 1 files, 1 symbols"
    assert execute(client, "/symbol", ["sample_entry"]).json()["code"]["items"] == []
    assert execute(client, "/symbol", ["replacement"]).json()["code"]["items"][0]["line"] == 1
    assert path.read_text() == "def replacement(): pass\n"
    assert client.session.history.turns == []
    assert client.session.record.runs == []
    assert client.session.queue.empty()


@pytest.mark.parametrize(("name", "args"), [
    ("/symbol", []), ("/symbol", ["a", "b"]), ("/refs", [""]),
    ("/refs", ["--help"]), ("/refresh", ["extra"]),
])
def test_code_command_usage_does_not_build_an_index(client, name, args):
    response = execute(client, name, args)
    assert response.status_code == 200
    assert response.json()["stderr"].startswith(f"usage: {name}")
    assert not (client.session.cwd / ".voss-cache").exists()


@pytest.mark.parametrize("git_workspace", [False, True])
def test_code_results_are_bounded_and_skip_external_symlinks(client, tmp_path, monkeypatch, git_workspace):
    if git_workspace:
        (client.session.cwd / ".git").mkdir()
        monkeypatch.setattr("subprocess.check_output", lambda *a, **kw: "many.py\nexternal.py\n")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("def outside_only(): pass\n")
    (client.session.cwd / "external.py").symlink_to(outside)
    (client.session.cwd / "many.py").write_text("\n".join(f"def sample_{n:02d}(): pass" for n in range(60)))
    result = execute(client, "/symbol", ["sample_"]).json()["code"]
    assert len(result["items"]) == 50 and result["truncated"]
    assert execute(client, "/symbol", ["outside_only"]).json()["code"]["items"] == []


def test_lsp_references_use_one_based_lines_and_close_the_client(client, monkeypatch, tmp_path):
    from voss.harness.code.lsp import create_lsp_client
    from voss.harness.code.lsp_registry import LspRegistry

    path = client.session.cwd / "space name.py"
    path.write_text("def sample_entry(): pass\n\nsample_entry()\n")
    closed = []

    async def send_request(method, params=None):
        if method == "shutdown":
            closed.append(True)
            return
        assert method == "textDocument/references"
        assert params["position"]["line"] == 0
        return [
            {"uri": target.as_uri(), "range": {"start": {"line": 2, "character": 0}}}
            for target in (path, tmp_path.parent / "external.py")
        ]

    async def send_notification(method, params=None):
        assert method == "exit"

    async def adapter_for(registry, language):
        adapter = create_lsp_client(language)
        adapter._initialized = True
        adapter._client = SimpleNamespace(send_request=send_request, send_notification=send_notification)
        registry._clients[language] = adapter
        return adapter

    monkeypatch.setattr(LspRegistry, "get_adapter", adapter_for)
    result = execute(client, "/refs", ["sample_entry"]).json()["code"]["items"]
    assert len(result) == 1
    assert result[0]["file"] == "space name.py" and result[0]["line"] == 3
    assert result[0]["snippet"] == "sample_entry()" and result[0]["source"] == "lsp"
    assert closed == [True]


@pytest.mark.asyncio
async def test_refresh_keeps_server_responsive(client, monkeypatch):
    from voss.harness.code import index

    entered, release = threading.Event(), threading.Event()
    build = index.build_index

    def slow_build(cwd):
        entered.set()
        assert release.wait(5)
        return build(cwd)

    monkeypatch.setattr(index, "build_index", slow_build)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url="http://test",
                                headers={"Authorization": "Bearer test-commands"}) as api:
        task = asyncio.create_task(api.post(f"/session/{client.session.id}/command", json={"name": "/refresh"}))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            response = await asyncio.wait_for(api.get(f"/session/{client.session.id}"), 1)
            assert response.status_code == 200
            assert not task.done()
        finally:
            release.set()
            result = await task
        assert result.json()["stdout"].startswith("refreshed code index:")

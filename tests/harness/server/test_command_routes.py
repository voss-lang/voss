from __future__ import annotations

import asyncio
import threading
from dataclasses import asdict
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
    assert {c["name"] for c in response.json()["commands"]} == {
        "/tools", "/skills", "/agents", "/symbol", "/refs", "/refresh",
        "/probable", "/btrace", "/vdiff",
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

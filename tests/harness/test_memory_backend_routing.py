from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from types import SimpleNamespace

import click
import pytest
from fastapi.testclient import TestClient

from voss.harness import cli, memory_cli
from voss.harness.server import app as appmod
from voss.harness.tools import attach_memory_tools


def test_remote_save_does_not_block_the_agent_event_loop(tmp_path: Path) -> None:
    caller_thread = threading.get_ident()

    class RemoteStore:
        def write_note(self, text, *, session_id):
            assert threading.get_ident() != caller_thread
            assert text == "Use the existing component pattern"
            return SimpleNamespace(name="memory:demo:note-id")

    tools = {}
    attach_memory_tools(tools, store=RemoteStore(), session_id="synthetic-session")
    result = asyncio.run(tools["memory_remember"].invoke(text="Use the existing component pattern"))
    assert result == "remembered: memory:demo:note-id"
    assert not (tmp_path / ".voss").exists()


def test_remote_save_failure_is_not_reported_as_remembered() -> None:
    class UnavailableStore:
        def write_note(self, text, *, session_id):
            raise RuntimeError("Memory service unavailable")

    tools = {}
    attach_memory_tools(tools, store=UnavailableStore(), session_id="synthetic-session")
    result = asyncio.run(tools["memory_remember"].invoke(text="A synthetic note"))
    assert result.startswith("<error:")
    assert "remembered:" not in result


def test_pinned_memory_failure_cannot_silently_drop_constraints(tmp_path: Path) -> None:
    def run_turn(*, pinned_memory_text=""):
        pass

    class UnavailableStore:
        def render_pinned_memory_text(self, *, model):
            raise RuntimeError("Memory service unavailable")

    with pytest.raises(RuntimeError, match="Memory service unavailable"):
        cli._pinned_memory_kwargs(run_turn, tmp_path, model="synthetic", store=UnavailableStore())


def test_laravel_admin_command_cannot_mutate_old_project_files(tmp_path: Path, monkeypatch) -> None:
    legacy_note = tmp_path / ".voss" / "memory" / "notes" / "old.md"
    legacy_note.parent.mkdir(parents=True)
    legacy_note.write_text("Synthetic legacy note")
    monkeypatch.setattr(memory_cli, "open_memory_store", lambda cwd: object())
    with pytest.raises(click.ClickException, match="not yet available"):
        memory_cli._legacy_project_store(tmp_path)
    assert legacy_note.read_text() == "Synthetic legacy note"


def test_fastapi_reports_unavailable_memory_without_backend_details(tmp_path: Path, monkeypatch) -> None:
    class UnavailableStore:
        def summary(self):
            raise RuntimeError("internal connection details")

    monkeypatch.setattr(appmod, "open_memory_store", lambda cwd: UnavailableStore())
    client = TestClient(appmod.create_app("synthetic-client-authorization"))
    response = client.get(
        "/memory", params={"cwd": str(tmp_path)},
        headers={"Authorization": "Bearer synthetic-client-authorization"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Memory backend unavailable"}


@pytest.mark.asyncio
async def test_server_stops_before_model_call_when_remote_pins_are_unavailable(tmp_path, monkeypatch):
    class UnavailableStore:
        def render_pinned_memory_text(self, *, model):
            raise RuntimeError("Memory service unavailable")

    async def unexpected_turn(*args, **kwargs):
        pytest.fail("Model must not run without configured memory constraints")

    monkeypatch.setattr(appmod, "open_memory_store", lambda cwd: UnavailableStore())
    monkeypatch.setattr(appmod, "run_turn", unexpected_turn)
    monkeypatch.setattr(appmod.session_store, "save", lambda *args: None)
    app = appmod.create_app("synthetic-client-authorization")
    session = app.state.sessions.create(cwd=tmp_path, model="synthetic", provider=object())

    await appmod._run_turn(session, "Synthetic task", "plan")

    events = []
    while not session.queue.empty():
        events.append(session.queue.get_nowait())
    assert any("Memory service unavailable" in str(event) for event in events)
    assert events[-1].type == "session.idle"


@pytest.mark.parametrize("response", [{}, {"data": [None]}, {"data": [], "next_cursor": 42}])
def test_malformed_pin_response_cannot_appear_as_empty_memory(tmp_path, response):
    from voss.harness.memory_gateway import MemoryGateway, MemoryGatewayError
    from voss.harness.memory_store import MemoryStore

    remote = SimpleNamespace(list_memories=lambda *args, **kwargs: response)
    gateway = MemoryGateway(MemoryStore(tmp_path), remote, "synthetic-project")
    with pytest.raises(MemoryGatewayError):
        gateway.render_pinned_memory_text(model="synthetic")

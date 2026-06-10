"""E3-04: the surfaces suite loads and dispatches offline (no creds, no model)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import voss.eval.runner as runner_mod
from voss.eval.runner import (
    _drive_cli_chat,
    _drive_cli_do,
    _drive_cli_edit,
    _drive_serve,
    _drive_task,
)
from voss.eval.suite import TaskSpec, load_suite

EXPECTED_SURFACES = {
    "01-do-add-function": "cli:do",
    "02-chat-explain": "cli:chat",
    "03-edit-add-method": "cli:edit",
    "04-serve-write-file": "serve",
    "05-serve-permission-allow": "serve",
    "06-serve-permission-deny": "serve",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _surfaces_root() -> Path:
    return _repo_root() / "tests" / "eval" / "surfaces"


def test_surfaces_suite_loads_all() -> None:
    tasks = load_suite(_surfaces_root(), suite="surfaces")
    ids = [task_id for task_id, _ in tasks]

    assert ids == sorted(EXPECTED_SURFACES)
    for task_id, spec in tasks:
        assert spec.surface == EXPECTED_SURFACES[task_id]
        assert spec.checks != [], f"{task_id} must have at least one check"


def test_surface_dispatch_routes(monkeypatch, tmp_path: Path) -> None:
    # Fictional-API guard: the real driver symbols must exist before patching.
    assert all(
        callable(f) for f in (_drive_cli_do, _drive_cli_chat, _drive_cli_edit, _drive_serve)
    )

    calls: list[str] = []

    def _record(name: str):
        async def _fake(spec, cwd, **kw):  # noqa: ANN001, ANN003
            calls.append(name)
            return f"final from {name}", None, False

        return _fake

    monkeypatch.setattr(runner_mod, "_drive_cli_do", _record("cli:do"))
    monkeypatch.setattr(runner_mod, "_drive_cli_chat", _record("cli:chat"))
    monkeypatch.setattr(runner_mod, "_drive_cli_edit", _record("cli:edit"))
    monkeypatch.setattr(runner_mod, "_drive_serve", _record("serve"))

    for surface in ("cli:do", "cli:chat", "cli:edit", "serve"):
        calls.clear()
        spec = TaskSpec(prompt="x", mode="plan", rubric="...", surface=surface)
        record, final, crash, capped = asyncio.run(
            _drive_task(
                "99-test", spec, cwd=tmp_path, provider=object(), model="__stub__"
            )
        )
        assert calls == [surface]
        assert crash is None
        assert final == f"final from {surface}"

    # internal must call NONE of the four drivers. The internal path needs a
    # real provider; make run_turn-side failure irrelevant by asserting only
    # on driver calls — a crash row from the stub object() provider is fine.
    calls.clear()
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")
    asyncio.run(
        _drive_task("99-test", spec, cwd=tmp_path, provider=object(), model="__stub__")
    )
    assert calls == []


def test_serve_deny_scenario_choice() -> None:
    tasks = dict(load_suite(_surfaces_root(), suite="surfaces"))
    spec = tasks["06-serve-permission-deny"]

    assert spec.surface == "serve"
    assert spec.permission_choice == "d"


def test_serve_basic_scenario_auto_mode() -> None:
    tasks = dict(load_suite(_surfaces_root(), suite="surfaces"))
    spec = tasks["04-serve-write-file"]

    assert spec.surface == "serve"
    assert spec.mode == "auto"

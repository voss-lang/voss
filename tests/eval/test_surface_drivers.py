"""E3 surface driver tests.

CLI drivers run under STUB mode here (D-10 — sitecustomize/StubProvider
injection is permitted in tests via the CliRunner env; the live drivers
themselves never inject it). The stub env reaches the driver subprocess by
monkeypatching voss.eval.runner._live_env for the cli:* tests only.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from tests.e2e.runner import CliRunner
from voss.eval.runner import (
    _consume_sse,
    _drive_cli_chat,
    _drive_cli_do,
    _drive_cli_edit,
    _drive_serve,
)
from voss.eval.suite import TaskSpec


@pytest.fixture
def stub_runner(tmp_path: Path) -> CliRunner:
    runner = CliRunner(project_root=tmp_path / "proj", state_home=tmp_path / "state")
    runner.project_root.mkdir(parents=True, exist_ok=True)
    return runner


@pytest.fixture
def stub_live_env(stub_runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """Point the drivers' env at the CliRunner stub env (tests only)."""
    monkeypatch.setattr(
        "voss.eval.runner._live_env", lambda cwd: stub_runner.env(VOSS_DEV="1")
    )
    return stub_runner


def test_cli_do_stub(stub_live_env: CliRunner) -> None:
    cwd = stub_live_env.project_root
    (cwd / "README.md").write_text("# seed\n")
    spec = TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="cli:do")

    final, crash_reason, capped = asyncio.run(_drive_cli_do(spec, cwd))

    assert crash_reason is None
    assert final
    assert capped is False


def test_cli_chat_stub(stub_live_env: CliRunner) -> None:
    cwd = stub_live_env.project_root
    (cwd / "README.md").write_text("# seed\n")
    spec = TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="cli:chat")

    final, crash_reason, capped = asyncio.run(_drive_cli_chat(spec, cwd))

    assert crash_reason is None
    assert final
    assert capped is False


def test_cli_edit_requires_target_file(tmp_path: Path) -> None:
    spec = TaskSpec(prompt="x", mode="edit", rubric="...", surface="cli:edit")

    final, crash_reason, capped = asyncio.run(_drive_cli_edit(spec, tmp_path))

    assert crash_reason is not None
    assert "target_file" in crash_reason
    assert final == ""


def test_cli_edit_stub(stub_live_env: CliRunner) -> None:
    cwd = stub_live_env.project_root
    (cwd / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    spec = TaskSpec(
        prompt="Describe calc.py.",
        mode="edit",
        rubric="...",
        surface="cli:edit",
        target_file="calc.py",
    )

    final, crash_reason, capped = asyncio.run(_drive_cli_edit(spec, cwd))

    assert crash_reason is None
    assert capped is False


# ---------------------------------------------------------------------------
# serve driver — FAKE_TURN integration + parser-level permission tests
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_turn_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env-only injection: _live_env's dict(os.environ) copy carries it into
    the spawned serve subprocess. Do NOT monkeypatch _live_env here."""
    monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")


def test_serve_stub(tmp_path: Path, fake_turn_env: None) -> None:
    """FAKE_TURN proves spawn → handshake → SSE-before-message → final →
    session.idle → teardown end-to-end offline (no provider, no creds)."""
    cwd = tmp_path / "proj"
    cwd.mkdir()
    spec = TaskSpec(prompt="hello", mode="plan", rubric="...", surface="serve")

    final, crash, capped = asyncio.run(_drive_serve(spec, cwd))

    assert crash is None
    assert "echo: hello" in final
    assert capped is False


class _FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeClient:
    """Records POSTs; serves a synthetic SSE line sequence."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.posts: list[tuple[str, dict | None]] = []

    def stream(self, method: str, url: str, **kw: object) -> _FakeStream:
        return _FakeStream(self._lines)

    async def post(self, url: str, **kw):  # noqa: ANN003
        self.posts.append((url, kw.get("json")))


def _permission_sse_lines() -> list[str]:
    return [
        "event: permission.updated",
        "data: " + json.dumps(
            {
                "v": 1,
                "type": "permission.updated",
                "id": "abcd1234",
                "tool_name": "fs_write",
                "args": {},
                "dimension": "tool",
            }
        ),
        "",
        ": ping",
        "event: final",
        'data: {"v": 1, "type": "final", "text": "synthetic final"}',
        "",
        "event: session.idle",
        'data: {"v": 1, "type": "session.idle"}',
        "",
    ]


def test_serve_permission_allow_parser() -> None:
    client = _FakeClient(_permission_sse_lines())

    final = asyncio.run(
        _consume_sse(
            client,
            "http://t",
            "sid1",
            {},
            permission_choice="a",
            message_body={"parts": [{"type": "text", "text": "x"}], "mode": "plan"},
        )
    )

    assert final == "synthetic final"
    assert (
        "http://t/session/sid1/permission",
        {"id": "abcd1234", "choice": "a"},
    ) in client.posts


def test_serve_permission_deny_parser() -> None:
    client = _FakeClient(_permission_sse_lines())

    final = asyncio.run(
        _consume_sse(
            client,
            "http://t",
            "sid1",
            {},
            permission_choice="d",
            message_body={"parts": [{"type": "text", "text": "x"}], "mode": "plan"},
        )
    )

    # Deny degrades without hanging: the loop still terminates on session.idle
    # (bounded by the synthetic stream) and the reply carried choice "d".
    assert final == "synthetic final"
    assert (
        "http://t/session/sid1/permission",
        {"id": "abcd1234", "choice": "d"},
    ) in client.posts


def test_serve_token_not_leaked(
    tmp_path: Path, fake_turn_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THREAT T-E3-08: force a post-handshake failure; crash_reason must not
    echo the bearer header or the handshake token."""
    cwd = tmp_path / "proj"
    cwd.mkdir()
    captured: dict[str, str] = {}

    async def _boom(self: httpx.AsyncClient, url: str, **kw):  # noqa: ANN003
        headers = kw.get("headers") or {}
        auth = headers.get("Authorization", "")
        captured["token"] = auth.removeprefix("Bearer ").strip()
        raise RuntimeError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "post", _boom)
    spec = TaskSpec(prompt="hello", mode="plan", rubric="...", surface="serve")

    final, crash, capped = asyncio.run(_drive_serve(spec, cwd))

    assert crash is not None
    assert "Bearer" not in crash
    assert captured["token"]
    assert captured["token"] not in crash
    assert final == ""

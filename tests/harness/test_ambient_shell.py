from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness import cli
from voss.harness import session as session_store
from voss.harness.agent import Plan, TurnResult
from voss_runtime import EpisodicMemory, configure
from voss_runtime.providers.base import ProviderResponse


@pytest.fixture(autouse=True)
def _reset_model():
    before = cli.get_config().default_model
    yield
    configure(default_model=before)


@pytest.mark.parametrize(
    "line",
    [
        "what model are you using?",
        "which auth path is active?",
        "status",
        "who are you?",
    ],
)
def test_status_questions_route_to_local_ambient(line: str) -> None:
    assert cli._ambient_route(line) == "local"


@pytest.mark.parametrize(
    "line",
    [
        "fix the model status bug",
        "implement ambient shell routing",
        "run tests for the harness",
        "can you refactor the CLI dispatch?",
    ],
)
def test_work_intent_routes_to_voss_run(line: str) -> None:
    assert cli._ambient_route(line) == "voss_run"


@pytest.mark.parametrize(
    "line",
    [
        "explain how auth resolution works",
        "why did the harness call itself Voss?",
        "summarize the CLI entry points",
    ],
)
def test_general_questions_remain_ambient(line: str) -> None:
    assert cli._ambient_route(line) == "ambient"


def test_ambient_status_answer_uses_harness_state() -> None:
    configure(default_model="gpt-5.5")
    ctx = SimpleNamespace(
        provider=SimpleNamespace(voss_provider_label="Codex"),
        gate=SimpleNamespace(mode="plan"),
    )

    out = cli._ambient_status_answer(ctx, auth_detail="codex-oauth — test")

    assert "Provider: Codex" in out
    assert "Model: gpt-5.5" in out
    assert "Phase: ambient" in out
    assert "Permission mode: plan" in out


class _FakeAmbientProvider:
    def __init__(self) -> None:
        self.messages = None
        self.model = None
        self.calls = 0

    async def complete(self, **kwargs):
        self.calls += 1
        self.messages = kwargs["messages"]
        self.model = kwargs["model"]
        return ProviderResponse(
            text="ambient answer",
            model=kwargs["model"],
            prompt_tokens=3,
            completion_tokens=2,
            cost_usd=0.001,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


class _RaisingProvider:
    calls = 0

    async def complete(self, **_kwargs):
        self.calls += 1
        raise AssertionError("ambient provider should not be called")

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


def _drive_plain_repl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    input_text: str,
    provider,
):
    record = session_store.SessionRecord.new(
        cwd=tmp_path,
        model=cli.get_config().default_model,
    )
    lines = iter(input_text.splitlines())
    monkeypatch.setattr("builtins.input", lambda *_: next(lines))
    monkeypatch.setattr(cli, "_git_status", lambda _cwd: "no git")
    monkeypatch.setattr(
        cli,
        "_render_project_index_text",
        lambda *_args, **_kwargs: "## Project Index\n- cli.py",
    )

    cli._run_repl(
        cwd=tmp_path,
        json_mode=False,
        mode="plan",
        history=EpisodicMemory(capacity=10),
        record=record,
        provider=provider,
        auth_detail="codex-oauth test",
        plain=True,
    )
    return record


@pytest.mark.asyncio
async def test_ambient_provider_prompt_is_not_voss_plan_loop(tmp_path: Path) -> None:
    configure(default_model="gpt-5.5")
    provider = _FakeAmbientProvider()
    ctx = SimpleNamespace(
        cwd=tmp_path,
        provider=provider,
        gate=SimpleNamespace(mode="plan"),
        history=EpisodicMemory(capacity=10),
        project_index_text="## Project Index\n- cli.py",
    )

    response = await cli._run_ambient_provider_turn("explain the CLI", ctx)

    assert response.text == "ambient answer"
    assert provider.model == "gpt-5.5"
    system = provider.messages[0]["content"]
    assert "ambient assistant inside the Voss shell" in system
    assert "Do not identify yourself as Voss" in system
    assert "Project summary" in system
    assert "You are Voss" not in system
    assert ctx.history.last(2)[0]["role"] == "user"
    assert ctx.history.last(2)[1]["role"] == "assistant"


def test_plain_repl_status_question_prints_local_answer_without_run_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure(default_model="gpt-5.5")
    resolve_calls = 0

    def fail_resolve(_cwd: Path):
        nonlocal resolve_calls
        resolve_calls += 1
        raise AssertionError("run_turn should not be resolved")

    monkeypatch.setattr(cli, "_resolve_run_turn", fail_resolve)
    provider = _RaisingProvider()

    record = _drive_plain_repl(
        monkeypatch,
        tmp_path,
        "what model are you using?\n/exit\n",
        provider,
    )

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "Provider:" in output
    assert "Model: gpt-5.5" in output
    assert "Phase: ambient" in output
    assert "Permission mode: plan" in output
    assert resolve_calls == 0
    assert provider.calls == 0
    assert record.runs == []


def test_plain_repl_general_question_uses_ambient_provider_without_run_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure(default_model="gpt-5.5")
    resolve_calls = 0

    def fail_resolve(_cwd: Path):
        nonlocal resolve_calls
        resolve_calls += 1
        raise AssertionError("run_turn should not be resolved")

    monkeypatch.setattr(cli, "_resolve_run_turn", fail_resolve)
    provider = _FakeAmbientProvider()

    record = _drive_plain_repl(
        monkeypatch,
        tmp_path,
        "explain how auth resolution works\n/exit\n",
        provider,
    )

    captured = capsys.readouterr()
    output = captured.out + captured.err
    system = provider.messages[0]["content"]
    assert "ambient answer" in output
    assert "ambient assistant inside the Voss shell" in system
    assert "Project summary" in system
    assert resolve_calls == 0
    assert provider.calls == 1
    assert record.runs == []


def test_plain_repl_work_intent_promotes_to_run_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure(default_model="gpt-5.5")
    captured_task = None

    async def fake_run_turn(task: str, **_kwargs):
        nonlocal captured_task
        captured_task = task
        return TurnResult(
            plan=Plan(rationale="promoted", steps=[], confidence=0.9),
            confidence=0.9,
            final="promoted run",
            tool_results=[],
            cost_usd=0.0,
            run=None,
        )

    monkeypatch.setattr(cli, "_resolve_run_turn", lambda _cwd: fake_run_turn)
    provider = _RaisingProvider()

    _drive_plain_repl(
        monkeypatch,
        tmp_path,
        "fix the model status bug\n/exit\n",
        provider,
    )

    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "promoted run" in output
    assert captured_task == "fix the model status bug"
    assert provider.calls == 0

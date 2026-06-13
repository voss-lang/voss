from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness import cli
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
        provider=object(),
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

    async def complete(self, **kwargs):
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

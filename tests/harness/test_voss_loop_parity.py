"""M4 D-11: same fixture, two backends, identical TurnResult.final + tool sequence."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from voss.harness.agent import Plan, ToolCall
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset
from voss_runtime import ProbableValue, get_config
from voss_runtime.providers.base import ProviderResponse


class FakeProvider:
    def __init__(self, plan: Plan):
        self.plan = plan
        self.calls: list[dict] = []

    async def complete(
        self,
        *,
        messages,
        model,
        response_format=None,
        tools=None,
        temperature=1.0,
        max_tokens=None,
        timeout=None,
    ) -> ProviderResponse:
        self.calls.append({"model": model, "messages": messages, "schema": response_format})
        prompt = messages[-1]["content"] if messages else ""
        if response_format is Plan:
            return ProviderResponse(
                text=self.plan.model_dump_json(),
                model=model,
                prompt_tokens=10,
                completion_tokens=10,
                cost_usd=0.0,
                raw={"fake": True},
                parsed=self.plan,
            )
        if prompt.startswith("Classify this coding task"):
            text = ProbableValue(value="inspect", confidence=0.95)
        elif "harness turn for this task" in prompt:
            text = ProbableValue(value=self.plan, confidence=self.plan.confidence)
        else:
            text = ""
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=10,
            completion_tokens=10,
            cost_usd=0.0,
            raw={"fake": True},
            parsed=None,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return 1


def _fixture_plan() -> Plan:
    return Plan(
        rationale="read the noop fixture",
        steps=[ToolCall(name="fs_read", args={"path": "fixture.md"})],
        confidence=0.95,
        final_when_done="contents: {{step_0}}",
    )


def _run(project: Path, run_turn, provider: FakeProvider):
    return asyncio.run(
        run_turn(
            "noop summary of fixture.md",
            tools=make_toolset(project),
            cwd=project,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=PermissionGate(auto_yes=True),
        )
    )


def _load_compiled_run_turn(project: Path):
    from voss.harness import cache as harness_cache

    harness_cache.assert_fresh(project)
    loop_py = project / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    spec = importlib.util.spec_from_file_location(
        "voss_compiled_harness_loop_test",
        loop_py,
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_turn


def test_python_and_compiled_backends_agree(
    parity_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from voss.harness.agent import run_turn as python_run_turn
    from voss_runtime import providers

    plan = _fixture_plan()
    python_provider = FakeProvider(plan)
    compiled_provider = FakeProvider(plan)
    monkeypatch.setitem(
        providers._registry,
        get_config().default_model,
        compiled_provider,
    )

    compiled_run_turn = _load_compiled_run_turn(parity_project)
    py_result = _run(parity_project, python_run_turn, python_provider)
    voss_result = _run(parity_project, compiled_run_turn, compiled_provider)

    assert py_result.final == voss_result.final
    assert [s.name for s in py_result.plan.steps] == [
        s.name for s in voss_result.plan.steps
    ]
    assert [s.args for s in py_result.plan.steps] == [
        s.args for s in voss_result.plan.steps
    ]

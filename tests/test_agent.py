from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from voss_runtime import AgentHandle, ProviderError, StubProvider, VossAgent, gather, tool
from voss_runtime.providers import register
from voss_runtime.providers.stub import StubProvider as StubProviderClass


class ReportModel(BaseModel):
    content: str
    score: int


class FailingProvider(StubProviderClass):
    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        raise ProviderError("provider is down")


async def test_default_agent_subclass_with_system_prompt_returns_stub_text():
    provider = StubProvider(default_response="hello from stub")
    register("agent-text-model", provider)

    class EchoAgent(VossAgent):
        system_prompt = "You echo politely."
        model = "agent-text-model"

    result = await EchoAgent().run("hello")

    assert result == "hello from stub"
    assert provider.calls[0]["messages"] == [
        {"role": "system", "content": "You echo politely."},
        {"role": "user", "content": "hello"},
    ]


async def test_spawn_returns_handle_and_result_yields_value():
    class ImmediateAgent(VossAgent):
        async def run(self, value: str) -> str:
            return f"done:{value}"

    handle = ImmediateAgent().spawn("work")

    assert isinstance(handle, AgentHandle)
    assert isinstance(handle.task, asyncio.Task)
    assert await handle.result() == "done:work"


async def test_gather_preserves_input_order_and_failed_slots_are_none():
    class DelayAgent(VossAgent):
        async def run(self, value: str, delay: float = 0.0):
            await asyncio.sleep(delay)
            if value == "fail":
                raise ValueError("boom")
            return value

    agent = DelayAgent()
    handles = [
        agent.spawn("first", 0.02),
        agent.spawn("second", 0.0),
        agent.spawn("fail", 0.01),
    ]

    assert await gather(handles) == ["first", "second", None]


async def test_gather_timeout_returns_none_and_cancels_underlying_task():
    class SlowAgent(VossAgent):
        async def run(self):
            await asyncio.sleep(10)
            return "late"

    handle = SlowAgent().spawn()

    assert await gather([handle], timeout=0.01) == [None]
    assert handle.task.cancelled()


async def test_structured_return_type_uses_pydantic_response_format():
    provider = StubProvider(default_response={"content": "parsed", "score": 7})
    register("agent-structured-model", provider)

    class ReportAgent(VossAgent):
        model = "agent-structured-model"
        return_type = ReportModel

    result = await ReportAgent().run("make report")

    assert result == ReportModel(content="parsed", score=7)
    assert provider.calls[0]["response_format"] is ReportModel


async def test_retries_are_exhausted_then_provider_error_raises():
    provider = FailingProvider()
    register("agent-failing-model", provider)

    class FailingAgent(VossAgent):
        model = "agent-failing-model"
        retries = 2

    with pytest.raises(ProviderError):
        await FailingAgent().run("try")

    assert len(provider.calls) == 3


async def test_agent_tool_schemas_reach_provider_call_history():
    @tool
    def search(query: str, max_results: int = 5) -> str:
        """Search for a query."""
        return f"{query}:{max_results}"

    provider = StubProvider(default_response="used tool schema")
    register("agent-tools-model", provider)

    class ToolAgent(VossAgent):
        model = "agent-tools-model"
        tools = [search]

    assert await ToolAgent().run("find docs") == "used tool schema"
    assert provider.calls[0]["tools"] == [search.schema()]

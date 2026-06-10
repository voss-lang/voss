"""Packing integration at the agent replay chokepoint.

VOPT-06 (--no-pack byte-identity, cached-prefix preservation) and the
VOPT-03 steady-state cache half, driven through _run_turn_exec with the
FakeStreamingProvider double from test_agent_loop.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from voss.harness import telemetry
from voss.harness.agent import Plan, _run_turn_exec
from voss.harness.providers import (
    Done,
    ParsedPlan,
    ProviderStreamEvent,
    TextDelta,
    Usage,
)
from voss.harness.tools import ToolEntry
from voss_runtime.tools import ToolDescriptor


def _make_tool(name: str, result: str) -> ToolEntry:
    async def _impl() -> str:
        return result

    desc = ToolDescriptor(
        name=name,
        description=name,
        parameters={"type": "object", "properties": {}, "required": []},
        func=_impl,
    )
    return ToolEntry(descriptor=desc, is_mutating=False, group="fs")


def _make_plan(
    *,
    steps: list[dict] | None = None,
    confidence: float = 0.9,
    final_when_done: str = "",
    rationale: str = "do thing",
    open_question: str | None = None,
) -> Plan:
    from voss.harness.agent import ToolCall

    step_objs = [ToolCall(**s) for s in (steps or [])]
    return Plan(
        rationale=rationale,
        steps=step_objs,
        confidence=confidence,
        final_when_done=final_when_done,
        open_question=open_question,
    )


@dataclass
class FakeStreamingProvider:
    """Async-iterable provider double that scripts one stream per call."""

    scripts: list[list[ProviderStreamEvent]]
    stream_calls: list[dict] = field(default_factory=list)
    complete_calls: list[dict] = field(default_factory=list)
    record_run_return: Any = None
    _stream_index: int = 0

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        script = self.scripts[self._stream_index]
        self._stream_index += 1

        async def _gen():
            for ev in script:
                yield ev

        return _gen()

    async def complete(self, **kwargs):
        self.complete_calls.append(kwargs)
        from voss_runtime.providers.base import ProviderResponse

        return ProviderResponse(
            text="",
            model=kwargs.get("model", "stub"),
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=0.0,
            raw={},
            parsed=self.record_run_return,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)


@dataclass
class RecordingRenderer:
    deltas: list[str] = field(default_factory=list)
    finalize_calls: list[dict] = field(default_factory=list)
    plan_calls: list[Any] = field(default_factory=list)
    thinking_calls: list[str] = field(default_factory=list)
    tool_calls: list[tuple] = field(default_factory=list)
    clarify_calls: list[tuple[str, float]] = field(default_factory=list)
    final_calls: list[tuple] = field(default_factory=list)
    status_calls: list[dict] = field(default_factory=list)

    def banner(self, **kw): pass
    def show_user(self, task): pass
    def show_thinking(self, label): self.thinking_calls.append(label)
    def show_plan(self, plan, *, cost_usd): self.plan_calls.append(plan)
    def show_tool_call(self, name, args, summary, state):
        self.tool_calls.append((name, args, summary, state))
    def show_clarify(self, question, confidence):
        self.clarify_calls.append((question, confidence))
    def show_final(self, text, *, confidence, cost_usd):
        self.final_calls.append((text, confidence, cost_usd))
    def stream_delta(self, text):
        self.deltas.append(text)
    def finalize_stream(self, *, role, confidence=None, cost_usd=None, timestamp=None,
                        accumulated_text=None):
        self.finalize_calls.append(
            {"role": role, "confidence": confidence, "cost_usd": cost_usd,
             "timestamp": timestamp, "accumulated_text": accumulated_text}
        )
    def status(self, **kw): self.status_calls.append(kw)
    def show_cognition(self, **kw): pass
    def show_cognition_overflow(self, **kw): pass
    def show_warning(self, msg): pass


def _script(
    *, plan: Plan, prompt_tokens=10, completion_tokens=5, cache_read=0
) -> list[ProviderStreamEvent]:
    return [
        TextDelta(text="..."),
        ParsedPlan(plan=plan),
        Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.001,
            cache_read_input_tokens=cache_read,
        ),
        Done(stop_reason="end_turn"),
    ]


@pytest.fixture(autouse=True)
def _reset_telemetry():
    telemetry.begin_turn()
    yield
    telemetry.clear_turn()


@pytest.fixture(autouse=True)
def _reset_runtime():
    from voss_runtime._config import reset_config

    reset_config()
    yield
    reset_config()


def _tool_plan() -> Plan:
    return _make_plan(
        steps=[{"name": "fs_read", "args": {}, "why": "look"}],
        confidence=0.7,
        final_when_done="",
    )


def _done_plan() -> Plan:
    return _make_plan(steps=[], confidence=0.9, final_when_done="all set")


async def _run_short(tmp_path: Path, *, packing_enabled: bool, cache_read: int = 0):
    """3-iteration run (2 tool iters + done) — stays under recent_full_k=8."""
    provider = FakeStreamingProvider(
        scripts=[
            _script(plan=_tool_plan(), cache_read=cache_read),
            _script(plan=_tool_plan(), cache_read=cache_read),
            _script(plan=_done_plan(), cache_read=cache_read),
        ]
    )
    result = await _run_turn_exec(
        "do thing",
        tools={"fs_read": _make_tool("fs_read", "tool-result")},
        cwd=tmp_path,
        renderer=RecordingRenderer(),
        provider=provider,
        model="stub-model",
        session_id="packing-test-session",
        packing_enabled=packing_enabled,
    )
    return provider, result


@pytest.mark.asyncio
async def test_no_pack_byte_identical(tmp_path: Path) -> None:
    """VOPT-06: below-threshold run with packing on == packing off, byte-for-byte."""
    provider_off, _ = await _run_short(tmp_path, packing_enabled=False)
    provider_on, _ = await _run_short(tmp_path, packing_enabled=True)

    assert provider_on.stream_calls[-1]["messages"] == provider_off.stream_calls[-1]["messages"]


@pytest.mark.asyncio
async def test_cached_prefix_unchanged(tmp_path: Path) -> None:
    """VOPT-06: the T4 cached static prefix (sys_blocks) is untouched by packing."""
    provider_off, _ = await _run_short(tmp_path, packing_enabled=False)
    provider_on, _ = await _run_short(tmp_path, packing_enabled=True)

    on_prefix = provider_on.stream_calls[-1]["messages"][0]["content"]
    off_prefix = provider_off.stream_calls[-1]["messages"][0]["content"]
    assert on_prefix == off_prefix


@pytest.mark.asyncio
async def test_cache_coherence_steady_state(tmp_path: Path) -> None:
    """VOPT-03 integration: with packing on, steady-state iters keep cache reads hot."""
    from voss_runtime import configure

    configure(max_iterations=12)  # default cap is 8; _reset_runtime restores
    provider = FakeStreamingProvider(
        scripts=[_script(plan=_tool_plan(), cache_read=200) for _ in range(9)]
        + [_script(plan=_done_plan(), cache_read=200)]
    )
    result = await _run_turn_exec(
        "do thing",
        tools={"fs_read": _make_tool("fs_read", "tool-result")},
        cwd=tmp_path,
        renderer=RecordingRenderer(),
        provider=provider,
        model="stub-model",
        packing_enabled=True,
    )

    assert result.run is not None
    assert result.run.iteration_count == 10
    steady = result.run.iterations[3:]
    assert all(it.cache_read_input_tokens > 0 for it in steady)


@pytest.mark.asyncio
async def test_env_no_pack_ledger_method_is_no_pack(tmp_path: Path, monkeypatch) -> None:
    """VOPT-05/06: env-disabled packing is labeled no-pack in the ledger."""
    monkeypatch.setenv("VOSS_NO_PACK", "1")

    await _run_short(tmp_path, packing_enabled=True)

    ledger = (
        tmp_path
        / ".voss"
        / "sessions"
        / "packing-test-session"
        / "token-savings.jsonl"
    )
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line]
    assert rows
    assert {row["method"] for row in rows} == {"no-pack"}

"""T1-05 Task 2a: _run_turn_exec rewritten as iteration while-loop.

Covers ITER-01/02/05/06 acceptance via scripted FakeStreamingProvider +
RecordingRenderer doubles. Tests are sync-only in shape (using
asyncio.run / pytest-asyncio) and do NOT depend on any real provider,
TUI app, or git state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

import voss.harness.agent as agent_mod
from voss.harness import telemetry
from voss.harness.agent import Plan, _run_turn_exec
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
    return ToolEntry(descriptor=desc, is_mutating=False)
from voss.harness.providers import (
    Done,
    ParsedPlan,
    ProviderStreamEvent,
    TextDelta,
    Usage,
)


def _message_content_text(content) -> str:
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return str(content or "")


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


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
        # _record_run_call uses complete() for the closing semantics call.
        # Return None-shaped sentinel via a SimpleNamespace-ish object.
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


def _done_script(
    *, plan: Plan, prompt_tokens=10, completion_tokens=5
) -> list[ProviderStreamEvent]:
    return [
        TextDelta(text="..."),
        ParsedPlan(plan=plan),
        Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.001,
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_done_exit_after_one_planning_iter(tmp_path: Path) -> None:
    iter_done = _make_plan(
        steps=[], confidence=0.9, final_when_done="all set",
    )
    provider = FakeStreamingProvider(scripts=[_done_script(plan=iter_done)])
    renderer = RecordingRenderer()

    result = await _run_turn_exec(
        "do thing",
        tools={},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
    )

    assert result.run is not None
    assert result.run.iteration_count == 1
    assert result.run.exit_reason == "done"
    assert len(result.run.iterations) == 1
    assert result.final == "all set"


@pytest.mark.asyncio
async def test_done_after_two_iters_with_tool_step(tmp_path: Path) -> None:
    tool = _make_tool("fs_read", "tool-result")

    iter_0 = _make_plan(
        steps=[{"name": "fs_read", "args": {}, "why": "look"}],
        confidence=0.7,
        final_when_done="",
    )
    iter_1 = _make_plan(
        steps=[], confidence=0.85, final_when_done="done now",
    )
    provider = FakeStreamingProvider(
        scripts=[_done_script(plan=iter_0), _done_script(plan=iter_1)]
    )
    renderer = RecordingRenderer()

    result = await _run_turn_exec(
        "do thing",
        tools={"fs_read": tool},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
    )

    assert result.run.iteration_count == 2
    assert result.run.exit_reason == "done"
    # Iter 1's messages replay iter 0's plan + tool results.
    iter1_msgs = provider.stream_calls[1]["messages"]
    flat = "\n".join(_message_content_text(m.get("content", "")) for m in iter1_msgs)
    assert "Tool results for iteration 0:" in flat
    # Assistant replay carries iter 0's rationale.
    assert "do thing" in flat or "look" in flat


@pytest.mark.asyncio
async def test_max_iter_cap_returns_halted_string(
    tmp_path: Path, monkeypatch
) -> None:
    from voss_runtime._config import configure

    configure(max_iterations=3)

    never_done = _make_plan(
        steps=[], confidence=0.9, final_when_done="",
        # final_when_done EMPTY → _is_done_plan returns False, loop continues.
    )
    # Use a non-done plan: needs steps with no actual tools to execute fast.
    # Simpler: empty steps + empty final → not done → loop continues until cap.
    # But empty steps + empty final means no work each iter.
    provider = FakeStreamingProvider(
        scripts=[_done_script(plan=never_done)] * 3
    )
    renderer = RecordingRenderer()

    result = await _run_turn_exec(
        "do thing",
        tools={},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
    )

    assert result.run.exit_reason == "max-iter"
    assert result.run.iteration_count == 3
    assert "halted: max-iter" in result.final


@pytest.mark.asyncio
async def test_budget_exit_returns_halted_budget(
    tmp_path: Path, monkeypatch
) -> None:
    never_done = _make_plan(
        steps=[], confidence=0.9, final_when_done="",
    )
    # Each iter's Usage reports 1_000_000 tokens, so after iter 0 the
    # ContextScope.tokens_used will not actually go up (Usage events only
    # update local accumulators, not ctx.tokens_used). Instead, inflate
    # ctx via monkeypatch: patch ContextScope to set tokens_used directly.
    provider = FakeStreamingProvider(
        scripts=[_done_script(plan=never_done)] * 8
    )

    # Patch ContextScope to set tokens_used >= token_budget after first iter.
    from voss_runtime import context as _ctx_mod

    real_aenter = _ctx_mod.ContextScope.__aenter__
    inflate_counter = {"n": 0}

    async def _inflate_aenter(self):
        # Each call to __aenter__ is once per turn; the inflation happens
        # inside the loop instead. We patch the property after first yield.
        return await real_aenter(self)

    # Simpler approach: zero out budget so any tokens_used >= 0 triggers
    # exhaustion. The loop checks `ctx.token_budget and ctx.tokens_used >=
    # ctx.token_budget`. Setting token_budget=0 short-circuits via the
    # truthiness check. We want exhaustion, so use budget=1 and bump
    # ctx.tokens_used to >=1 via a side-effect patch on _is_done_plan.
    real_is_done = agent_mod._is_done_plan

    def patched_is_done(plan):
        # Smuggle: every call to _is_done_plan happens once per iter just
        # after the stream consumes; inflate ctx after the first call.
        result = real_is_done(plan)
        return result

    # Cleanest: hook _build_iter_rider to inflate ctx via the live frame.
    # Skip the indirection — patch ContextScope.token_budget to 1 and
    # update tokens_used via _serialize_iter_for_replay side-effect.
    renderer = RecordingRenderer()

    # Direct approach: monkeypatch the loop's ctx check by setting
    # ctx.token_budget=1 + ctx.tokens_used=1 mid-loop via patched
    # _build_iter_rider which receives ctx implicitly... it does not.
    # Instead expose a tokens-inflate hook on ContextScope.
    real_build = agent_mod._build_iter_rider

    def inflating_build(**kw):
        # On second iter, walk the frame to find the live ctx and inflate.
        import sys
        frame = sys._getframe(1)
        ctx = frame.f_locals.get("ctx")
        if ctx is not None and kw.get("index", 0) >= 1:
            ctx.tokens_used = ctx.token_budget + 1
        return real_build(**kw)

    monkeypatch.setattr(agent_mod, "_build_iter_rider", inflating_build)

    result = await _run_turn_exec(
        "do thing",
        tools={},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
        token_budget=1000,
    )

    assert result.run.exit_reason == "budget"
    assert "halted: budget" in result.final


@pytest.mark.asyncio
async def test_confidence_gate_only_on_terminating_iter(tmp_path: Path) -> None:
    tool = _make_tool("fs_read", "ok")

    iter_0 = _make_plan(
        steps=[{"name": "fs_read", "args": {}, "why": "x"}],
        confidence=0.40,
        final_when_done="",
    )
    iter_1 = _make_plan(
        steps=[{"name": "fs_read", "args": {}, "why": "y"}],
        confidence=0.40,
        final_when_done="",
    )
    iter_2 = _make_plan(
        steps=[], confidence=0.80, final_when_done="the answer",
    )
    provider = FakeStreamingProvider(scripts=[
        _done_script(plan=iter_0),
        _done_script(plan=iter_1),
        _done_script(plan=iter_2),
    ])
    renderer = RecordingRenderer()

    result = await _run_turn_exec(
        "do thing",
        tools={"fs_read": tool},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
        confidence_threshold=0.60,
    )

    assert result.run.exit_reason == "done"
    assert result.final == "the answer"
    # Clarify was NOT triggered mid-loop.
    assert renderer.clarify_calls == []


@pytest.mark.asyncio
async def test_confidence_gate_clarifies_on_low_done_iter(tmp_path: Path) -> None:
    plan = _make_plan(
        steps=[],
        confidence=0.30,
        final_when_done="(tentative answer)",
        open_question="what did you mean by X?",
    )
    provider = FakeStreamingProvider(scripts=[_done_script(plan=plan)])
    renderer = RecordingRenderer()

    result = await _run_turn_exec(
        "do thing",
        tools={},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
        confidence_threshold=0.60,
    )

    assert result.run is None
    assert renderer.clarify_calls == [("what did you mean by X?", 0.30)]
    meta = telemetry._turn_meta.get() or {}
    assert meta.get("outcome") == "clarify"
    assert meta.get("iteration_count") == 1


@pytest.mark.asyncio
async def test_renderer_does_not_render_plan_phase_deltas(tmp_path: Path) -> None:
    # Plan-phase TextDeltas carry the structured-output JSON (some providers
    # stream the schema body as text by contract). The loop must NOT render
    # them — doing so leaked raw {"rationale":...} into the chat. It still
    # finalizes the (empty) stream and surfaces the parsed plan / final answer.
    plan = _make_plan(steps=[], confidence=0.9, final_when_done="ok")
    script = [
        TextDelta(text="hel"),
        TextDelta(text="lo"),
        ParsedPlan(plan=plan),
        Usage(prompt_tokens=10, completion_tokens=5, cost_usd=0.001),
        Done(stop_reason="end_turn"),
    ]
    provider = FakeStreamingProvider(scripts=[script])
    renderer = RecordingRenderer()

    await _run_turn_exec(
        "x",
        tools={},
        cwd=tmp_path,
        renderer=renderer,
        provider=provider,
        model="stub-model",
    )

    assert renderer.deltas == []
    assert len(renderer.finalize_calls) == 1
    assert renderer.finalize_calls[0]["role"] == "assistant"
    assert renderer.finalize_calls[0]["accumulated_text"] is None
    assert renderer.finalize_calls[0]["confidence"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_iteration_telemetry_events_emitted(tmp_path: Path, monkeypatch) -> None:
    captured: list[tuple[str, dict]] = []

    real_emit = telemetry.emit

    def fake_emit(event_type, level="info", *, data=None, **kw):
        captured.append((event_type, dict(data or {})))
        return real_emit(event_type, level, data=data, **kw)

    monkeypatch.setattr(telemetry, "emit", fake_emit)
    monkeypatch.setattr(agent_mod.telemetry, "emit", fake_emit)

    tool = _make_tool("fs_read", "ok")

    iter_0 = _make_plan(
        steps=[{"name": "fs_read", "args": {}, "why": "x"}],
        confidence=0.85,
        final_when_done="",
    )
    iter_1 = _make_plan(
        steps=[{"name": "fs_read", "args": {}, "why": "y"}],
        confidence=0.85,
        final_when_done="",
    )
    iter_2 = _make_plan(steps=[], confidence=0.9, final_when_done="done")
    provider = FakeStreamingProvider(scripts=[
        _done_script(plan=iter_0),
        _done_script(plan=iter_1),
        _done_script(plan=iter_2),
    ])

    await _run_turn_exec(
        "do thing",
        tools={"fs_read": tool},
        cwd=tmp_path,
        renderer=RecordingRenderer(),
        provider=provider,
        model="stub-model",
    )

    starts = [d for (t, d) in captured if t == "iteration.start"]
    ends = [d for (t, d) in captured if t == "iteration.end"]
    assert len(starts) == 3
    assert len(ends) == 3
    assert [d["iteration_index"] for d in ends] == [0, 1, 2]


@pytest.mark.asyncio
async def test_note_turn_carries_iteration_count_and_exit_reason(
    tmp_path: Path,
) -> None:
    plan = _make_plan(steps=[], confidence=0.9, final_when_done="ok")
    provider = FakeStreamingProvider(scripts=[_done_script(plan=plan)])

    await _run_turn_exec(
        "x",
        tools={},
        cwd=tmp_path,
        renderer=RecordingRenderer(),
        provider=provider,
        model="stub-model",
    )

    meta = telemetry._turn_meta.get() or {}
    assert meta.get("iteration_count") == 1
    assert meta.get("exit_reason") == "done"
    assert meta.get("outcome") == "complete"


def test_substitute_placeholders_is_gone() -> None:
    # Hard removal: agent module must not expose the function.
    assert not hasattr(agent_mod, "_substitute_placeholders")

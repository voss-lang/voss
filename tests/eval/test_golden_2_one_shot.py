"""T1 ITER-01 / SPEC criterion 11: M5 golden #2 rename-symbol completes one-shot.

Pre-T1 this multi-step coding task required the user to re-prompt because
the single-shot loop couldn't react to tool results. T1's iteration loop
fixes it. This test exercises the ACTUAL `voss/harness/agent.py` loop
(not a mock of `_run_turn_exec`) with a scripted streaming provider that
plays out a four-iteration rename flow and asserts a single `run_turn`
call completes the task.

Follow-up note (CONTEXT.md "M5 fixture compatibility = hard break"):
pre-T1 single-shot M5 golden fixtures will be re-recorded against the
new iteration semantics in a separate M5 follow-up. This stub-provider
test exists so phase T1 can ship without the fixture re-record blocking
the merge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from voss.harness.agent import Plan, ToolCall, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import (
    Done,
    ParsedPlan,
    ProviderStreamEvent,
    TextDelta,
    Usage,
)
from voss.harness.render import PlainRenderer
from voss.harness.tools import ToolEntry
from voss_runtime.tools import ToolDescriptor


def _mk_tool(name: str, result: str, *, mutating: bool = False) -> ToolEntry:
    async def _impl(**_kwargs) -> str:
        return result

    desc = ToolDescriptor(
        name=name,
        description=name,
        parameters={"type": "object", "properties": {}, "required": []},
        func=_impl,
    )
    return ToolEntry(descriptor=desc, is_mutating=mutating)


def _mk_plan(
    *,
    rationale: str,
    steps: list[dict] | None = None,
    final_when_done: str = "",
    confidence: float = 0.85,
) -> Plan:
    return Plan(
        rationale=rationale,
        steps=[ToolCall(**s) for s in (steps or [])],
        confidence=confidence,
        final_when_done=final_when_done,
    )


@dataclass
class _RenameProvider:
    """Scripts a 4-iter rename: grep → edits → run tests → done."""

    scripts: list[list[ProviderStreamEvent]]
    stream_calls: list[dict] = field(default_factory=list)
    _idx: int = 0

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        idx = self._idx
        self._idx += 1
        script = self.scripts[min(idx, len(self.scripts) - 1)]

        async def _gen():
            for ev in script:
                yield ev

        return _gen()

    async def complete(self, **kwargs):
        from voss_runtime.providers.base import ProviderResponse
        return ProviderResponse(
            text="", model=kwargs.get("model", "stub"),
            prompt_tokens=0, completion_tokens=0, cost_usd=0.0,
            raw={}, parsed=None,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        return 1


def _frame(plan: Plan) -> list[ProviderStreamEvent]:
    return [
        TextDelta(text="planning…"),
        ParsedPlan(plan=plan),
        Usage(prompt_tokens=20, completion_tokens=10, cost_usd=0.001),
        Done(stop_reason="end_turn"),
    ]


@pytest.mark.t1
@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_golden_2_rename_completes_in_one_run(tmp_path: Path) -> None:
    # Task string mirrors the M5 golden #2 scenario. Pre-T1 this required
    # multiple `voss do` invocations; T1's iteration loop completes it in one.
    task = "Rename FooBar to BarBaz across the repo and verify tests pass"

    iter0 = _mk_plan(
        rationale="Find all FooBar occurrences",
        steps=[
            {"name": "fs_grep", "args": {"pattern": "FooBar"}, "why": "scan"}
        ],
        final_when_done="",
    )
    iter1 = _mk_plan(
        rationale="Edit each occurrence",
        steps=[
            {"name": "fs_edit",
             "args": {"path": "src/foo.py", "old": "FooBar", "new": "BarBaz"},
             "why": "rename in foo.py"},
            {"name": "fs_edit",
             "args": {"path": "src/bar.py", "old": "FooBar", "new": "BarBaz"},
             "why": "rename in bar.py"},
        ],
        final_when_done="",
    )
    iter2 = _mk_plan(
        rationale="Run tests to verify",
        steps=[
            {"name": "shell_run", "args": {"cmd": "pytest"}, "why": "verify"}
        ],
        final_when_done="",
    )
    iter3 = _mk_plan(
        rationale="Rename complete + tests pass",
        steps=[],
        confidence=0.92,
        final_when_done=(
            "renamed FooBar to BarBaz across 3 occurrences; tests pass (5 passed)"
        ),
    )

    provider = _RenameProvider(scripts=[
        _frame(iter0), _frame(iter1), _frame(iter2), _frame(iter3),
    ])

    tools = {
        "fs_grep": _mk_tool(
            "fs_grep",
            "src/foo.py:10: class FooBar:\nsrc/foo.py:25: FooBar()\nsrc/bar.py:5: import FooBar",
        ),
        "fs_edit": _mk_tool("fs_edit", "edited", mutating=True),
        "shell_run": _mk_tool("shell_run", "[exit 0] 5 passed"),
    }

    # Single run_turn call — no user re-prompt.
    result = await run_turn(
        task,
        tools=tools,
        cwd=tmp_path,
        renderer=PlainRenderer(),
        provider=provider,
        permissions=PermissionGate(auto_yes=True),
    )

    # Exactly the four scripted iterations ran.
    assert result.run is not None
    assert result.run.iteration_count == 4, (
        f"expected 4 iters, got {result.run.iteration_count}"
    )
    assert result.run.exit_reason == "done"

    # User-visible final string carries both the rename + the test-pass signal.
    final_lower = result.final.lower()
    assert "renamed" in final_lower
    assert "pass" in final_lower or "ok" in final_lower

    # Streaming provider was invoked once per iteration; the helper records 4.
    assert len(provider.stream_calls) == 4

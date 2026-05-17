"""T2-03 / PAR-02: per-step PermissionGate.check preserved inside batches.

The partition scheduler dispatches read-only steps in parallel under
asyncio.gather, but PermissionGate.check MUST still fire once per step
(M1 D-06 / SPEC Constraint 7). This test confirms no caching / skipping
happens just because steps run concurrently.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import pytest

from voss.harness.agent import ToolCall, _run_step_loop
from voss.harness.permissions import PermissionGate
from voss.harness.tools import ToolEntry
from voss_runtime._config import reset_config
from voss_runtime.tools import ToolDescriptor


@dataclass
class _Render:
    tool_calls: list = field(default_factory=list)

    def show_tool_call(self, *a, **kw): self.tool_calls.append(a)
    def show_thinking(self, *a, **kw): pass
    def show_plan(self, *a, **kw): pass
    def show_clarify(self, *a, **kw): pass
    def show_final(self, *a, **kw): pass
    def stream_delta(self, *a, **kw): pass
    def finalize_stream(self, **kw): pass
    def status(self, **kw): pass
    def show_cognition(self, **kw): pass
    def show_cognition_overflow(self, **kw): pass
    def show_warning(self, *a, **kw): pass


def _mk_tool(name: str, *, is_mutating: bool) -> ToolEntry:
    async def _impl() -> str:
        await asyncio.sleep(0.005)
        return f"ok:{name}"

    desc = ToolDescriptor(
        name=name,
        description=name,
        parameters={"type": "object", "properties": {}, "required": []},
        func=_impl,
    )
    return ToolEntry(descriptor=desc, is_mutating=is_mutating)


def _steps(*names: str) -> list[ToolCall]:
    return [ToolCall(name=n, args={}, why="") for n in names]


@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_config()
    yield
    reset_config()


@pytest.mark.asyncio
async def test_per_step_check_preserved_in_multi_step_read_batch() -> None:
    """3 reads in one parallel batch → gate.check fires exactly 3 times."""
    invocations: list[tuple[str, dict]] = []

    def _recorder(tool_name: str, args: dict, is_mutating: bool) -> tuple[bool, str]:
        invocations.append((tool_name, dict(args)))
        return True, "auto"

    gate = PermissionGate(auto_yes=True)
    # Wrap gate.check so we can count invocations without altering decisions.
    original_check = gate.check

    def _wrapped(tool_name, args, *, is_mutating=False, is_network=False):
        _recorder(tool_name, args, is_mutating)
        return original_check(tool_name, args, is_mutating=is_mutating, is_network=is_network)

    gate.check = _wrapped  # type: ignore[method-assign]

    tools = {n: _mk_tool(n, is_mutating=False) for n in ("a", "b", "c")}
    await _run_step_loop(_steps("a", "b", "c"), tools, gate, _Render())

    assert [name for name, _ in invocations] == ["a", "b", "c"]
    assert len(invocations) == 3


@pytest.mark.asyncio
async def test_per_step_check_preserved_for_write_singletons() -> None:
    """2 writes → 2 singleton dispatches → gate.check fires exactly 2 times."""
    invocations: list[str] = []
    gate = PermissionGate(auto_yes=True)
    original_check = gate.check

    def _wrapped(tool_name, args, *, is_mutating=False, is_network=False):
        invocations.append(tool_name)
        return original_check(tool_name, args, is_mutating=is_mutating, is_network=is_network)

    gate.check = _wrapped  # type: ignore[method-assign]
    tools = {n: _mk_tool(n, is_mutating=True) for n in ("w1", "w2")}
    await _run_step_loop(_steps("w1", "w2"), tools, gate, _Render())
    assert invocations == ["w1", "w2"]


@pytest.mark.asyncio
async def test_per_step_check_denies_one_step_in_batch_others_still_run() -> None:
    """Mid-batch denial surfaces as `<denied: ...>` for that slot only."""
    gate = PermissionGate(auto_yes=True)
    original_check = gate.check

    def _wrapped(tool_name, args, *, is_mutating=False, is_network=False):
        if tool_name == "b":
            return False, "test-denied"
        return original_check(tool_name, args, is_mutating=is_mutating, is_network=is_network)

    gate.check = _wrapped  # type: ignore[method-assign]
    tools = {n: _mk_tool(n, is_mutating=False) for n in ("a", "b", "c")}
    results = await _run_step_loop(_steps("a", "b", "c"), tools, gate, _Render())
    assert results[0] == "ok:a"
    assert results[1] == "<denied: test-denied>"
    assert results[2] == "ok:c"

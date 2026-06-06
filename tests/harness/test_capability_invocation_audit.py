"""V1-04: capability-invocation audit (CAP-08) + deterministic stub fixture (CAP-10).

No live LLM / MCP / network — everything is in-memory + stubbed.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from voss.harness.agent import _invoke_step_with_gate
from voss.harness.permissions import PermissionGate
from voss.harness.recorder import RunRecorder
from voss.harness.tools import ToolEntry
from voss_runtime import ToolDescriptor


# ---- Task 1: RunRecorder.observe_capability -------------------------------


def test_recorder_observe_capability() -> None:
    rec = RunRecorder.start()
    rec.observe_capability(
        "fs_write",
        "fs",
        {"path": "x", "content": "y"},
        is_mutating=True,
        is_network=False,
        audit_behavior="full",
        ok=True,
    )
    assert len(rec.capability_invocations) == 1
    ev = rec.capability_invocations[0]
    assert ev["name"] == "fs_write"
    assert ev["group"] == "fs"
    assert ev["is_mutating"] is True
    assert ev["is_network"] is False
    assert ev["ok"] is True
    assert ev["args"] is not None  # redacted args present


def test_metadata_only_omits_args() -> None:
    rec = RunRecorder.start()
    rec.observe_capability(
        "secret_tool",
        "review",
        {"token": "supersecret"},
        is_mutating=True,
        is_network=False,
        audit_behavior="metadata_only",
        ok=True,
    )
    ev = rec.capability_invocations[0]
    assert ev["args"] is None  # no raw args leaked


def test_observe_capability_never_raises_on_bad_args() -> None:
    rec = RunRecorder.start()
    rec.observe_capability(
        "x", "fs", None, is_mutating=False, is_network=False, ok=True  # type: ignore[arg-type]
    )
    assert len(rec.capability_invocations) == 1


def test_finalize_forwards_capability_invocations(tmp_path) -> None:
    rec = RunRecorder.start()
    rec.observe_capability("fs_read", "fs", {"path": "a"}, is_mutating=False, is_network=False, ok=True)
    record = rec.finalize(tmp_path, cost_usd=0.0, exit_reason="done")
    assert len(record.capability_invocations) == 1
    assert record.capability_invocations[0]["name"] == "fs_read"


# ---- Task 2: CAP-10 deterministic stub fixture at the agent site -----------


class _NullRenderer:
    def show_tool_call(self, *a, **k):
        return None


def _entry(name: str, *, is_mutating: bool, result: str = "RESULT") -> ToolEntry:
    async def invoke(**kwargs):
        return result

    desc = ToolDescriptor(
        name=name,
        description="stub",
        parameters={"type": "object", "properties": {}, "required": []},
        func=invoke,
    )
    return ToolEntry(descriptor=desc, is_mutating=is_mutating, group="fs", scope_requirements=("fs",))


def test_invocation_audited_on_success() -> None:
    tools = {"stub_read": _entry("stub_read", is_mutating=False)}
    gate = PermissionGate(mode="auto", auto_yes=True)
    rec = RunRecorder.start()
    step = SimpleNamespace(name="stub_read", args={"path": "x"})
    out = asyncio.run(_invoke_step_with_gate(step, tools, gate, _NullRenderer(), rec))
    assert out == "RESULT"
    assert len(rec.capability_invocations) == 1
    ev = rec.capability_invocations[0]
    assert ev["name"] == "stub_read" and ev["group"] == "fs" and ev["ok"] is True


def test_invocation_audited_on_denial() -> None:
    tools = {"stub_write": _entry("stub_write", is_mutating=True)}
    gate = PermissionGate(mode="plan", auto_yes=True)  # plan denies mutating
    rec = RunRecorder.start()
    step = SimpleNamespace(name="stub_write", args={"path": "x", "content": "y"})
    out = asyncio.run(_invoke_step_with_gate(step, tools, gate, _NullRenderer(), rec))
    assert out.startswith("<denied:")
    assert len(rec.capability_invocations) == 1
    assert rec.capability_invocations[0]["ok"] is False


def test_existing_observe_still_runs_on_success() -> None:
    # additive: the legacy observe path (inspected/changed tracking) still fires
    tools = {"fs_read": _entry("fs_read", is_mutating=False, result="data")}
    gate = PermissionGate(mode="auto", auto_yes=True)
    rec = RunRecorder.start()
    step = SimpleNamespace(name="fs_read", args={"path": "tracked.py"})
    asyncio.run(_invoke_step_with_gate(step, tools, gate, _NullRenderer(), rec))
    assert "tracked.py" in rec.inspected  # legacy observe() preserved
    assert len(rec.capability_invocations) == 1

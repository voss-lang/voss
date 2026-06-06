"""V1-01: ToolEntry capability metadata (CAP-01/02/03/06).

Task 1 covers the extended ToolEntry schema + nine-group constant.
Task 2 adds registry-wide + attach-helper completeness coverage.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.tools import CAPABILITY_GROUPS, ToolEntry, make_toolset


class _StubDescriptor:
    def __init__(self, name: str = "stub") -> None:
        self.name = name
        self.description = "stub tool"
        self.parameters = {"type": "object", "properties": {}, "required": []}

    def invoke(self, **kw):  # pragma: no cover - not exercised here
        return ""


def _entry(**kw) -> ToolEntry:
    base = dict(descriptor=_StubDescriptor(), is_mutating=False, group="fs")
    base.update(kw)
    return ToolEntry(**base)


# ---- Task 1: schema ---------------------------------------------------------


def test_capability_groups_exact_nine() -> None:
    assert tuple(CAPABILITY_GROUPS) == (
        "fs",
        "git",
        "test",
        "shell",
        "net",
        "code",
        "memory",
        "review",
        "mcp",
    )


def test_unknown_group_raises_valueerror() -> None:
    with pytest.raises(ValueError):
        _entry(group="bogus")


def test_missing_group_raises_typeerror() -> None:
    with pytest.raises(TypeError):
        ToolEntry(descriptor=_StubDescriptor(), is_mutating=False)


def test_bad_scope_requirement_raises() -> None:
    with pytest.raises(ValueError):
        _entry(scope_requirements=("fs", "nope"))


def test_bad_audit_behavior_raises() -> None:
    with pytest.raises(ValueError):
        _entry(audit_behavior="loud")


def test_defaults_stateful_false_audit_full() -> None:
    e = _entry()
    assert e.is_stateful is False
    assert e.audit_behavior == "full"
    assert e.scope_requirements == ()
    assert e.output_schema is None
    assert e.is_network is False


def test_capability_dict_shape() -> None:
    e = _entry(group="net", is_network=True, scope_requirements=("net",))
    cap = e.capability_dict()
    assert set(cap) == {
        "name",
        "description",
        "input_schema",
        "output_schema",
        "is_mutating",
        "is_network",
        "group",
        "scope_requirements",
        "audit_behavior",
        "is_stateful",
    }
    assert cap["input_schema"] == e.parameters
    assert cap["group"] == "net"
    assert cap["is_network"] is True
    assert cap["scope_requirements"] == ["net"]  # list, not tuple


# ---- Task 2: registry-wide + attach-helper completeness ---------------------

_ALLOWED_AUDIT = {"full", "redact_args", "metadata_only"}


def test_make_toolset_all_entries_tagged(tmp_path: Path) -> None:
    tools = make_toolset(tmp_path)
    for name, entry in tools.items():
        assert entry.group in CAPABILITY_GROUPS, f"{name} bad group {entry.group!r}"
        for s in entry.scope_requirements:
            assert s in CAPABILITY_GROUPS, f"{name} bad scope {s!r}"
        assert entry.audit_behavior in _ALLOWED_AUDIT, f"{name} bad audit"
    # anchors
    assert tools["fs_write"].group == "fs" and tools["fs_write"].is_mutating is True
    assert tools["git_diff"].group == "git" and tools["git_diff"].is_mutating is False
    assert tools["web_fetch"].group == "net" and tools["web_fetch"].is_network is True


def test_attach_helpers_tag_every_entry(tmp_path: Path, monkeypatch) -> None:
    from voss.harness import multiagent, subagents
    from voss.harness.tools import attach_memory_tools
    from voss.harness.memory_store import MemoryStore

    # memory tools
    tools: dict = {}
    attach_memory_tools(
        tools, store=MemoryStore(tmp_path).bind(session_id="s"), session_id="s"
    )
    # subagent_run + task
    monkeypatch.setattr(subagents, "build_role_provider", lambda *a, **k: None, raising=False)
    from voss.harness import roles

    monkeypatch.setattr(roles, "build_role_provider", lambda *a, **k: None)
    subagents.attach_subagent_tool(
        tools,
        registry=object(),
        cwd=tmp_path,
        renderer=object(),
        provider="p",
        model=lambda: "m",
        gate=object(),
        cognition=None,
    )
    # multiagent fan-out
    multiagent.attach_multiagent_tools(
        tools,
        registry=object(),
        cwd=tmp_path,
        renderer=object(),
        provider="p",
        model=lambda: "m",
        gate=object(),
        cognition=None,
    )
    for name in (
        "memory_recall",
        "memory_remember",
        "subagent_run",
        "task",
        "subagent_spawn",
        "subagent_steer",
        "subagent_status",
        "subagent_gather",
    ):
        assert name in tools, f"{name} not attached"
        assert tools[name].group in CAPABILITY_GROUPS, f"{name} untagged"

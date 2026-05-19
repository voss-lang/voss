from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from voss.harness.mcp.server_tools import (
    DEFAULT_LOW_LEVEL_TOOLS,
    build_tool_descriptors,
    build_tool_dispatch,
)
from voss.harness.permissions import PermissionGate
from voss.harness.skill_registry import default_skill_registry
from voss.harness.tools import make_toolset


DEFAULT_SKILL_IDS = {
    "add-test",
    "analyze",
    "audit-cognition",
    "port-py-to-voss",
    "rename-symbol",
    "summarize-diff",
    "voss-lint-as-skill",
}

MUTATING_SKILL_IDS = {
    "add-test",
    "analyze",
    "port-py-to-voss",
    "rename-symbol",
}


def _tools_and_registry(tmp_path):
    return make_toolset(tmp_path), default_skill_registry()


def _descriptor_by_name(descriptors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {descriptor["name"]: descriptor for descriptor in descriptors}


def test_default_surface_advertises_six_low_level_and_seven_skills(tmp_path) -> None:
    tools, registry = _tools_and_registry(tmp_path)

    descriptors = build_tool_descriptors(tools, registry, None)
    names = {descriptor["name"] for descriptor in descriptors}

    assert set(DEFAULT_LOW_LEVEL_TOOLS).issubset(names)
    assert DEFAULT_SKILL_IDS.issubset(names)
    assert len(descriptors) == 13


def test_destructive_hint_mirrors_is_mutating(tmp_path) -> None:
    tools, registry = _tools_and_registry(tmp_path)

    descriptors = _descriptor_by_name(build_tool_descriptors(tools, registry, None))

    destructive_count = 0
    for name in DEFAULT_LOW_LEVEL_TOOLS:
        hint = descriptors[name]["annotations"]["destructiveHint"]
        assert hint is tools[name].is_mutating
        destructive_count += int(hint)
    for skill_id in registry.ids():
        skill = registry.get(skill_id)
        assert skill is not None
        hint = descriptors[skill_id]["annotations"]["destructiveHint"]
        assert hint is skill.mutating
        destructive_count += int(hint)
    assert destructive_count == 4


def test_unknown_tool_or_skill_raises_mcp_config_error(tmp_path) -> None:
    from voss.harness.mcp.config import McpConfigError, McpServerExposureConfig

    tools, registry = _tools_and_registry(tmp_path)

    with pytest.raises(McpConfigError, match="unknown tool: does_not_exist"):
        build_tool_descriptors(
            tools,
            registry,
            McpServerExposureConfig(exposed_tools=["fs_read", "does_not_exist"]),
        )
    with pytest.raises(McpConfigError, match="unknown skill: does-not-exist"):
        build_tool_descriptors(
            tools,
            registry,
            McpServerExposureConfig(exposed_skills=["voss-lint-as-skill", "does-not-exist"]),
        )


@pytest.mark.asyncio
async def test_dispatch_plan_mode_denies_every_mutating_skill(tmp_path) -> None:
    tools, registry = _tools_and_registry(tmp_path)
    skill_dispatch = AsyncMock(return_value="should not be called")
    dispatch = build_tool_dispatch(
        tools, registry, skill_dispatch, PermissionGate(mode="plan")
    )

    for name in sorted(MUTATING_SKILL_IDS):
        result = await dispatch(name, {"args": []})
        assert result["isError"] is True
        assert result["content"][0]["text"] == "denied by mode plan"
    skill_dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_auto_mode_runs_read_only_tool(tmp_path) -> None:
    dummy = tmp_path / "dummy.txt"
    dummy.write_text("hello")
    tools, registry = _tools_and_registry(tmp_path)
    dispatch = build_tool_dispatch(
        tools, registry, None, PermissionGate(auto_yes=True)
    )

    result = await dispatch("fs_read", {"path": "dummy.txt"})

    assert result["isError"] is False
    assert result["content"][0]["text"] == "hello"


@pytest.mark.asyncio
async def test_dispatch_skill_returns_unwired_error_when_dispatch_is_none(tmp_path) -> None:
    tools, registry = _tools_and_registry(tmp_path)
    dispatch = build_tool_dispatch(
        tools, registry, None, PermissionGate(auto_yes=True)
    )

    result = await dispatch("voss-lint-as-skill", {"args": ["."]})

    assert result["isError"] is True
    assert "skill dispatch not wired" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_dispatch_tool_exception_converts_to_iserror_envelope(tmp_path) -> None:
    tools, registry = _tools_and_registry(tmp_path)
    dispatch = build_tool_dispatch(
        tools, registry, None, PermissionGate(auto_yes=True)
    )

    missing = await dispatch("fs_read", {"path": "no/such/file.txt"})
    assert missing["isError"] is False
    assert missing["content"][0]["text"].startswith("<error: not found:")

    class BoomTool:
        is_mutating = False
        is_network = False

        async def invoke(self, **kwargs: Any) -> str:
            raise RuntimeError("boom")

    patched_tools = dict(tools)
    patched_tools["boom"] = BoomTool()
    dispatch = build_tool_dispatch(
        patched_tools, registry, None, PermissionGate(auto_yes=True)
    )

    raised = await dispatch("boom", {})

    assert raised["isError"] is True
    assert "boom" in raised["content"][0]["text"]


def test_unknown_call_returns_unknown_tool_envelope(tmp_path) -> None:
    tools, registry = _tools_and_registry(tmp_path)
    dispatch = build_tool_dispatch(
        tools, registry, None, PermissionGate(auto_yes=True)
    )

    result = asyncio.run(dispatch("nope", {}))

    assert result["isError"] is True
    assert "unknown tool: nope" in result["content"][0]["text"]

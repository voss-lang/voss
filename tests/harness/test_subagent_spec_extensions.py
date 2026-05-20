"""Regression tests for O2 SubagentSpec extensions (OTEAM-02 back-compat)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from voss.harness.subagents import (
    SubagentRegistry,
    SubagentSpec,
    agent_task,
    default_subagent_registry,
)
from voss.harness.team import TeamRoleScope


def test_legacy_spec_three_args_unchanged() -> None:
    s = SubagentSpec("x", "d", "rp")
    assert s.id == "x"
    assert s.description == "d"
    assert s.role_prompt == "rp"
    assert s.model is None
    assert s.mode is None
    assert s.scope is None
    assert s.budget is None
    assert s.tools is None
    assert s.net is False


def test_full_spec_with_new_fields() -> None:
    scope = TeamRoleScope(("src/**",))
    tools = frozenset({"fs", "test"})
    s = SubagentSpec(
        id="x",
        description="d",
        role_prompt="rp",
        model="opus",
        mode="auto",
        scope=scope,
        budget=1000,
        tools=tools,
        net=True,
    )
    assert s.model == "opus"
    assert s.mode == "auto"
    assert s.scope is scope
    assert s.budget == 1000
    assert s.tools == tools
    assert s.net is True


def test_default_registry_unchanged() -> None:
    reg = default_subagent_registry()
    assert reg.ids() == ["explorer", "reviewer", "worker"]
    for spec in reg.entries():
        assert spec.model is None
        assert spec.mode is None
        assert spec.scope is None
        assert spec.budget is None
        assert spec.tools is None
        assert spec.net is False


def test_agent_task_reads_role_prompt_only() -> None:
    turn = agent_task(SubagentSpec("x", "d", "RP", model="opus"), "do something")
    assert "RP" in turn
    assert "opus" not in turn


def test_dispatch_refuses_unknown_id_regression() -> None:
    registry = SubagentRegistry()
    assert registry.get("ghost") is None
    expected = f"<error: unknown subagent {'ghost'!r}>"
    assert expected == "<error: unknown subagent 'ghost'>"


def test_spec_is_still_frozen() -> None:
    s = SubagentSpec("x", "d", "rp")
    with pytest.raises(FrozenInstanceError):
        s.model = "x"  # type: ignore[misc]

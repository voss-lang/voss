"""Wave 0 scaffold for NET-04 mcp scope gating. Bodies land in T3-07."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from voss.harness.cognition_schemas import PermissionsConfig


def test_default_plan_scope() -> None:
    assert PermissionsConfig.model_validate({}).mcp == {}
    assert PermissionsConfig.model_validate({"mcp": {"filesystem": "plan"}}).mcp == {
        "filesystem": "plan"
    }


def test_edit_scope() -> None:
    assert PermissionsConfig.model_validate({"mcp": {"filesystem": "edit"}}).mcp == {
        "filesystem": "edit"
    }
    with pytest.raises(ValidationError):
        PermissionsConfig.model_validate({"mcp": {"filesystem": "delete"}})

    config = PermissionsConfig.model_validate(
        {"tool_policy": {"allow": [], "deny": []}, "mcp": {"x": "auto"}}
    )
    assert config.tool_policy.allow == []
    assert config.tool_policy.deny == []
    assert config.mcp == {"x": "auto"}


def test_scope_denial() -> None:
    pytest.skip("pending T3-07 — placeholder created by T3-01")


def test_auto_does_not_override_scope() -> None:
    pytest.skip("pending T3-07 — placeholder created by T3-01")

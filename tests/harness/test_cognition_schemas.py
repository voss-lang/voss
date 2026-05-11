"""COG-03 strict YAML schema validation (Wave 1 — M2-01)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from voss.harness.cognition_schemas import (
    ConstraintRule,
    ConstraintsConfig,
    PathScope,
    PermissionsConfig,
    ValidationCommand,
    ValidationConfig,
)


def test_constraints_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ConstraintsConfig.model_validate({"rules": [], "stray_key": 1})


def test_permissions_layered_with_gate() -> None:
    c = PermissionsConfig.model_validate(
        {
            "tool_policy": {"allow": ["fs_read"], "deny": ["shell_run"]},
            "path_scopes": [{"glob": "src/**", "modes": ["plan", "edit"]}],
        }
    )
    assert c.tool_policy.deny == ["shell_run"]
    assert c.path_scopes[0].modes == ["plan", "edit"]

    # Extra invariant: invalid mode literal rejected.
    with pytest.raises(ValidationError):
        PathScope(glob="a", modes=["unknown"])


def test_validation_on_enum() -> None:
    ok = ValidationConfig.model_validate(
        {"commands": [{"name": "tests", "run": "pytest", "on": ["save", "post_run"]}]}
    )
    assert ok.commands[0].on == ["save", "post_run"]

    with pytest.raises(ValidationError):
        ValidationCommand.model_validate({"name": "x", "run": "y", "on": ["invalid"]})

    # Extra invariant: max_file_size_lines must be > 0.
    with pytest.raises(ValidationError):
        ConstraintRule(max_file_size_lines=0)

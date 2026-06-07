"""OTEAM-07: per-role PermissionGate compilation from SubagentSpec."""

from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.cognition_schemas import PermissionsConfig, SafetyConfig
from voss.harness.edit_scope import EditScope
from voss.harness.permissions import PermissionGate, PermissionStore
from voss.harness.skill.scope import _min_mode as scope_min_mode
from voss.harness.subagents import SubagentSpec
import voss.harness.team as team_mod
from voss.harness.team import gate_for_role


def test_gate_for_role_caps_mode() -> None:
    base = PermissionGate(mode="edit")
    spec = SubagentSpec("r", "d", "rp", mode="plan")
    g = gate_for_role(spec, base)
    assert g.mode == "plan"


def test_gate_for_role_never_expands_mode() -> None:
    base = PermissionGate(mode="edit")
    spec = SubagentSpec("r", "d", "rp", mode="auto")
    g = gate_for_role(spec, base)
    assert g.mode == "edit"


def test_gate_for_role_inherits_base_mode_when_spec_mode_none() -> None:
    base = PermissionGate(mode="edit")
    spec = SubagentSpec("r", "d", "rp", mode=None)
    g = gate_for_role(spec, base)
    assert g.mode == "edit"


def test_gate_for_role_preserves_project_policy() -> None:
    policy = PermissionsConfig()
    base = PermissionGate(mode="edit", project_policy=policy)
    spec = SubagentSpec("r", "d", "rp")
    g = gate_for_role(spec, base)
    assert g.project_policy is policy


def test_gate_for_role_preserves_safety_policy() -> None:
    policy = SafetyConfig.model_validate({"runbooks": [{"name": "rb", "steps": ["s"]}]})
    base = PermissionGate(mode="edit", safety_policy=policy)
    spec = SubagentSpec("r", "d", "rp")
    g = gate_for_role(spec, base)
    assert g.safety_policy is policy


def test_gate_for_role_sets_safety_actor_role_and_tier() -> None:
    base = PermissionGate(mode="auto", auto_yes=True)
    spec = SubagentSpec("backend", "Backend", "rp", model="cheap")
    g = gate_for_role(spec, base)
    assert g.safety_actor is not None
    assert g.safety_actor.role == "backend"
    assert g.safety_actor.model_tier == "cheap"


def test_gate_for_role_subagent_never_prompts() -> None:
    base = PermissionGate(mode="edit", auto_yes=False)
    spec = SubagentSpec("r", "d", "rp")
    g = gate_for_role(spec, base)
    assert g.auto_yes is True


def test_gate_for_role_does_not_inherit_store_or_edit_scope() -> None:
    store = PermissionStore(cwd=Path("."))
    esc = EditScope(cwd=Path("."))
    base = PermissionGate(mode="edit", store=store, edit_scope=esc)
    spec = SubagentSpec("r", "d", "rp")
    g = gate_for_role(spec, base)
    assert g.store is None
    assert g.edit_scope is None


def test_gate_for_role_uses_min_mode_from_skill_scope() -> None:
    assert team_mod._min_mode is scope_min_mode


@pytest.mark.parametrize(
    ("m1", "m2", "expected"),
    [
        ("plan", "plan", "plan"),
        ("plan", "edit", "plan"),
        ("plan", "auto", "plan"),
        ("edit", "plan", "plan"),
        ("edit", "edit", "edit"),
        ("edit", "auto", "edit"),
        ("auto", "plan", "plan"),
        ("auto", "edit", "edit"),
        ("auto", "auto", "auto"),
    ],
)
def test_min_mode_truth_table(
    m1: str, m2: str, expected: str
) -> None:
    assert team_mod._min_mode(m1, m2) == expected  # type: ignore[arg-type]

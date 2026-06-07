"""V12-04: safety policy inheritance through EM-derived role gates.

Proves derived ``gate_for_role()`` gates carry the same safety policy as the
base harness gate, attach role/model-tier actor context for weak-model scaffold
rules, and route factory-only operations identically at the gate layer.
"""
from __future__ import annotations

import pytest

from voss.harness.cognition_schemas import SafetyConfig
from voss.harness.config import get_model_tiers
from voss.harness.em import EMBoardHandle
from voss.harness.permissions import PermissionGate
from voss.harness.subagents import SubagentSpec
from voss.harness.team import _model_tier_for_spec, gate_for_role

FORBIDDEN_METHODS = {
    "set_ceiling",
    "set_p",
    "set_budget",
    "extend_budget",
    "register_role",
    "register_agent",
    "mutate_team_config",
}


def _scaffold_policy() -> SafetyConfig:
    return SafetyConfig.model_validate(
        {
            "runbooks": [{"name": "scaffold-rb", "steps": ["step1"]}],
            "weak_model_scaffolds": [
                {"model_tiers": ["cheap"], "pattern": "*", "runbook": "scaffold-rb"},
                {"model_tiers": ["fast"], "pattern": "*", "runbook": "scaffold-rb"},
            ],
        }
    )


def _factory_policy() -> SafetyConfig:
    return SafetyConfig.model_validate(
        {
            "runbooks": [{"name": "prod-deploy", "steps": ["plan", "apply"]}],
            "factory_only_operations": [
                {
                    "id": "git-push",
                    "tool": "shell_run",
                    "pattern": "git push *",
                    "runbook": "prod-deploy",
                    "classes": ["deploy"],
                }
            ],
        }
    )


def _base_with_policy(policy: SafetyConfig) -> PermissionGate:
    return PermissionGate(mode="auto", auto_yes=True, safety_policy=policy)


class TestSafetyPolicyObjectIdentity:
    """Derived role gates share the base safety policy object."""

    def test_gate_for_role_preserves_safety_policy_identity(self) -> None:
        policy = _scaffold_policy()
        base = _base_with_policy(policy)
        spec = SubagentSpec("backend", "d", "rp", model="cheap")
        role_gate = gate_for_role(spec, base)
        assert role_gate.safety_policy is policy

    def test_gate_for_role_preserves_safety_confirm_fn(self) -> None:
        policy = _scaffold_policy()
        calls: list[str] = []

        def confirm(_req: object) -> str:
            calls.append("called")
            return ""

        base = PermissionGate(
            mode="auto",
            auto_yes=True,
            safety_policy=policy,
            safety_confirm_fn=confirm,
        )
        spec = SubagentSpec("backend", "d", "rp", model="cheap")
        role_gate = gate_for_role(spec, base)
        assert role_gate.safety_confirm_fn is confirm

    def test_role_gate_does_not_inherit_base_safety_actor(self) -> None:
        from voss.harness.safety import SafetyActorContext

        policy = _scaffold_policy()
        base_actor = SafetyActorContext(role="em", model_tier="strong")
        base = PermissionGate(
            mode="auto",
            auto_yes=True,
            safety_policy=policy,
            safety_actor=base_actor,
        )
        spec = SubagentSpec("backend", "d", "rp", model="cheap")
        role_gate = gate_for_role(spec, base)
        assert role_gate.safety_actor is not base_actor
        assert role_gate.safety_actor.role == "backend"
        assert role_gate.safety_actor.model_tier == "cheap"


class TestWeakModelScaffoldViaRoleGate:
    """Weak-model scaffold rules key off derived gate actor context."""

    @pytest.mark.parametrize("tier", ["cheap", "fast"])
    def test_cheap_or_fast_tier_triggers_weak_model_scaffold(self, tier: str) -> None:
        policy = _scaffold_policy()
        base = _base_with_policy(policy)
        spec = SubagentSpec("backend", "d", "rp", model=tier)
        role_gate = gate_for_role(spec, base)
        allowed, why = role_gate.check(
            "fs_write", {"path": "src/x.py", "content": "y"}, is_mutating=True
        )
        assert allowed is False
        assert "scaffold" in why

    def test_strong_tier_does_not_trigger_weak_model_scaffold(self) -> None:
        policy = _scaffold_policy()
        base = _base_with_policy(policy)
        spec = SubagentSpec("architect", "d", "rp", model="strong")
        role_gate = gate_for_role(spec, base)
        allowed, _ = role_gate.check(
            "fs_write", {"path": "src/x.py", "content": "y"}, is_mutating=True
        )
        assert allowed is True

    def test_builtin_role_defaults_infer_cheap_tier(self) -> None:
        policy = _scaffold_policy()
        base = _base_with_policy(policy)
        spec = SubagentSpec("backend", "d", "rp")  # no explicit model
        assert _model_tier_for_spec(spec) == "cheap"
        role_gate = gate_for_role(spec, base)
        allowed, why = role_gate.check(
            "fs_write", {"path": "src/x.py", "content": "y"}, is_mutating=True
        )
        assert allowed is False
        assert "scaffold" in why

    def test_resolved_model_id_reverse_lookup_yields_tier(self) -> None:
        haiku = get_model_tiers()["cheap"]
        spec = SubagentSpec("custom", "d", "rp", model=haiku)
        assert _model_tier_for_spec(spec) in {"cheap", "fast"}


class TestFactoryOnlyRoutingParity:
    """Factory-only operation routing works on derived role gates."""

    def test_factory_only_operation_blocked_on_role_gate(self) -> None:
        policy = _factory_policy()
        base = _base_with_policy(policy)
        spec = SubagentSpec("backend", "d", "rp", model="cheap")
        role_gate = gate_for_role(spec, base)
        allowed, why = role_gate.check(
            "shell_run", {"cmd": "git push origin main"}, is_mutating=True
        )
        assert allowed is False
        assert "runbook 'prod-deploy'" in why
        assert "direct execution blocked" in why

    def test_base_and_role_gate_share_factory_decision(self) -> None:
        policy = _factory_policy()
        base = _base_with_policy(policy)
        spec = SubagentSpec("backend", "d", "rp", model="cheap")
        role_gate = gate_for_role(spec, base)
        args = {"cmd": "git push origin main"}
        base_ok, base_why = base.check("shell_run", args, is_mutating=True)
        role_ok, role_why = role_gate.check("shell_run", args, is_mutating=True)
        assert base_ok == role_ok is False
        assert base_why == role_why


class TestEMCageUnchanged:
    """V12 must not add EM mutation APIs."""

    def test_forbidden_methods_absent_on_em_board_handle(self, make_handle) -> None:
        handle = make_handle()
        public = {m for m in dir(handle) if not m.startswith("_")}
        overlap = public & FORBIDDEN_METHODS
        assert overlap == set(), f"cage breach: {overlap}"

    def test_getattr_raises_for_forbidden(self, make_handle) -> None:
        handle = make_handle()
        for name in FORBIDDEN_METHODS:
            with pytest.raises(AttributeError):
                getattr(handle, name)

    def test_em_board_handle_is_not_subclass_mutation_surface(self) -> None:
        assert not hasattr(EMBoardHandle, "set_ceiling")
        assert not hasattr(EMBoardHandle, "mutate_team_config")

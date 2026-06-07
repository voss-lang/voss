"""V12-02 runtime safety gate: confirmation + factory routing in PermissionGate.

Covers VSAFE-01/02/03/06 at the gate layer. The gate is exercised directly with
injected confirmation functions — no real stdin/TTY.
"""
from __future__ import annotations

from voss.harness.cognition_schemas import SafetyConfig
from voss.harness.permissions import PermissionGate
from voss.harness.safety import SafetyActorContext, SafetyConfirmRequest


def _policy() -> SafetyConfig:
    return SafetyConfig.model_validate(
        {
            "runbooks": [
                {"name": "prod-deploy", "steps": ["plan", "apply"]},
                {"name": "empty-rb"},  # declared but no procedure
            ],
            "pipelines": [{"name": "fast-path"}],
            "factory_only_paths": [
                {
                    "id": "prod-paths",
                    "glob": "infra/prod/**",
                    "runbook": "prod-deploy",
                    "classes": ["prod", "irreversible"],
                }
            ],
            "factory_only_operations": [
                {
                    "id": "git-push",
                    "tool": "shell_run",
                    "pattern": "git push *",
                    "runbook": "prod-deploy",
                    "classes": ["deploy"],
                },
                {
                    "id": "rm-rf",
                    "tool": "shell_run",
                    "pattern": "rm -rf *",
                    "runbook": "empty-rb",
                    "classes": ["delete"],
                },
            ],
            "latency_pipelines": [
                {"id": "quote", "tool": "shell_run", "pattern": "quote *", "pipeline": "fast-path"}
            ],
        }
    )


_IRREVERSIBLE = ("fs_write", {"path": "infra/prod/app.yml", "content": "x"})


# --- VSAFE-01: irreversible confirmation ------------------------------------


def test_auto_yes_does_not_bypass_irreversible_confirmation() -> None:
    # auto_yes True + no confirmation available (non-interactive) → DENY.
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    allowed, why = gate.check(*_IRREVERSIBLE, is_mutating=True)
    assert allowed is False
    assert "confirmation" in why


def test_matching_confirmation_allows_irreversible_to_proceed() -> None:
    def confirm(req: SafetyConfirmRequest) -> str:
        return req.exact_action  # echo exact action verbatim

    gate = PermissionGate(
        mode="auto", auto_yes=True, safety_policy=_policy(), safety_confirm_fn=confirm
    )
    allowed, why = gate.check(*_IRREVERSIBLE, is_mutating=True)
    assert allowed is True


def test_non_matching_confirmation_denies_with_safety_reason() -> None:
    def confirm(req: SafetyConfirmRequest) -> str:
        return "yes"  # wrong — not the exact action

    gate = PermissionGate(
        mode="auto", auto_yes=True, safety_policy=_policy(), safety_confirm_fn=confirm
    )
    allowed, why = gate.check(*_IRREVERSIBLE, is_mutating=True)
    assert allowed is False
    assert "safety" in why
    assert "exact action" in why


def test_confirmation_request_carries_risk_and_exact_action() -> None:
    captured: list[SafetyConfirmRequest] = []

    def confirm(req: SafetyConfirmRequest) -> str:
        captured.append(req)
        return req.exact_action

    gate = PermissionGate(
        mode="auto", auto_yes=True, safety_policy=_policy(), safety_confirm_fn=confirm
    )
    gate.check(*_IRREVERSIBLE, is_mutating=True)
    assert captured, "confirmation fn was not called"
    req = captured[0]
    assert req.exact_action == "infra/prod/app.yml"
    assert "Irreversible" in req.risk_summary


# --- VSAFE-02: dangerous-operation runbook routing --------------------------


def test_dangerous_operation_routed_to_runbook_blocks_direct_execution() -> None:
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    allowed, why = gate.check(
        "shell_run", {"cmd": "git push origin main"}, is_mutating=True
    )
    assert allowed is False
    assert "runbook 'prod-deploy'" in why
    assert "direct execution blocked" in why


def test_runbook_without_procedure_denies_before_invocation() -> None:
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    allowed, why = gate.check("shell_run", {"cmd": "rm -rf /tmp/x"}, is_mutating=True)
    assert allowed is False
    assert "no defined procedure" in why


# --- VSAFE-03: latency fixed pipeline ---------------------------------------


def test_latency_critical_routes_to_fixed_pipeline_only_when_configured() -> None:
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    hit_ok, hit_why = gate.check("shell_run", {"cmd": "quote AAPL"})
    assert hit_ok is False
    assert "fixed pipeline 'fast-path'" in hit_why
    # An unconfigured op stays on the normal path (auto + auto_yes → allowed).
    miss_ok, _ = gate.check("shell_run", {"cmd": "echo hi"})
    assert miss_ok is True


# --- Normal-path preservation (additive) ------------------------------------


def test_unclassified_operations_unchanged_without_safety_policy() -> None:
    gate = PermissionGate(mode="auto", auto_yes=True)  # no safety_policy
    assert gate.check("shell_run", {"cmd": "git push origin main"}, is_mutating=True)[0] is True
    assert gate.check("fs_read", {"path": "README.md"})[0] is True


def test_unclassified_operations_unchanged_with_safety_policy() -> None:
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    # A path outside any factory glob + a command outside any pattern → normal.
    assert gate.check("fs_read", {"path": "README.md"})[0] is True
    assert gate.check("shell_run", {"cmd": "echo hi"})[0] is True


def test_project_policy_deny_still_wins_over_safety_overlay() -> None:
    from voss.harness.cognition_schemas import PermissionsConfig

    pol = PermissionsConfig.model_validate({"tool_policy": {"deny": ["shell_run"]}})
    gate = PermissionGate(
        mode="auto", auto_yes=True, project_policy=pol, safety_policy=_policy()
    )
    allowed, why = gate.check("shell_run", {"cmd": "git push origin main"}, is_mutating=True)
    assert allowed is False
    assert "permissions.yml" in why  # project deny precedence preserved


def test_weak_model_scaffold_blocks_direct_execution() -> None:
    policy = SafetyConfig.model_validate(
        {
            "runbooks": [{"name": "scaffold-rb", "steps": ["step1"]}],
            "weak_model_scaffolds": [
                {"model_tiers": ["cheap"], "pattern": "*", "runbook": "scaffold-rb"}
            ],
        }
    )
    cheap = PermissionGate(
        mode="auto",
        auto_yes=True,
        safety_policy=policy,
        safety_actor=SafetyActorContext(role="backend", model_tier="cheap"),
    )
    allowed, why = cheap.check("fs_write", {"path": "src/x.py", "content": "y"}, is_mutating=True)
    assert allowed is False
    assert "scaffold" in why
    # A strong actor is exempt → normal path.
    strong = PermissionGate(
        mode="auto",
        auto_yes=True,
        safety_policy=policy,
        safety_actor=SafetyActorContext(role="backend", model_tier="strong"),
    )
    assert strong.check("fs_write", {"path": "src/x.py", "content": "y"}, is_mutating=True)[0] is True

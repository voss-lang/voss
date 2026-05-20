"""OTEAM-03: per-role net cage — compile_team → gate_for_role + tool filter (integration)."""

from __future__ import annotations

from pathlib import Path

import pytest

from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.cognition_schemas import PermissionsConfig, ToolPolicy
from voss.harness.permissions import PermissionGate, PermissionStore
from voss.harness.team import compile_team, filter_toolset_for_role, gate_for_role
from voss.harness.tools import make_toolset
from voss_runtime._config import get_config, reset_config

_STRAWMAN = (
    Path(__file__).resolve().parents[1] / "parser" / "examples" / "team_strawman.voss"
)


def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)


def _only_team(prog) -> TeamDecl:
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_config()
    yield
    reset_config()


@pytest.fixture
def strawman_registry():
    src = _STRAWMAN.read_text(encoding="utf-8")
    prog = _prog(src, str(_STRAWMAN))
    td = _only_team(prog)
    _cfg, registry = compile_team(td)
    return registry


def _set_process_allow_net(value: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    """Match Task 3 plan: patch process config without replacing the singleton."""
    monkeypatch.setattr(get_config(), "allow_net", value)


def _permissive_base(tmp_path: Path) -> PermissionGate:
    return PermissionGate(mode="edit", store=PermissionStore(cwd=tmp_path), auto_yes=True)


def test_ai_role_gate_grants_net_when_process_allows(
    strawman_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_process_allow_net(True, monkeypatch)
    spec = strawman_registry.get("ai")
    assert spec is not None
    gate = gate_for_role(spec, _permissive_base(tmp_path))
    allowed, _why = gate.check(
        "web_fetch",
        {"url": "https://example.com"},
        is_mutating=False,
        is_network=True,
    )
    assert allowed is True


def test_ai_role_gate_grants_net_even_when_process_disallows(
    strawman_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_process_allow_net(False, monkeypatch)
    spec = strawman_registry.get("ai")
    assert spec is not None
    gate = gate_for_role(spec, _permissive_base(tmp_path))
    allowed, why = gate.check(
        "web_fetch",
        {"url": "https://example.com"},
        is_mutating=False,
        is_network=True,
    )
    assert allowed is True
    assert why == "auto"


def test_backend_role_gate_denies_net_even_when_process_allows(
    strawman_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_process_allow_net(True, monkeypatch)
    spec = strawman_registry.get("backend")
    assert spec is not None
    gate = gate_for_role(spec, _permissive_base(tmp_path))
    allowed, why = gate.check(
        "web_fetch",
        {"url": "https://example.com"},
        is_mutating=False,
        is_network=True,
    )
    assert allowed is False
    assert why == "net disabled for this role (per-gate override)"


def test_engineer_roles_all_lack_net(
    strawman_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_process_allow_net(True, monkeypatch)
    base = _permissive_base(tmp_path)
    for role_id in ("backend", "frontend", "ui"):
        spec = strawman_registry.get(role_id)
        assert spec is not None
        gate = gate_for_role(spec, base)
        allowed, why = gate.check(
            "web_fetch",
            {"url": "https://example.com"},
            is_mutating=False,
            is_network=True,
        )
        assert allowed is False
        assert why == "net disabled for this role (per-gate override)"


def test_em_gate_inherits_base(
    strawman_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EM strawman has no net in tools; gate denies web_fetch like other non-net roles."""
    _set_process_allow_net(True, monkeypatch)
    spec = strawman_registry.get("em")
    assert spec is not None
    assert spec.net is False
    base = _permissive_base(tmp_path)
    gate = gate_for_role(spec, base)
    # Mode caps: EM auto vs base edit → edit
    assert gate.mode == "edit"
    allowed, why = gate.check(
        "web_fetch",
        {"url": "https://example.com"},
        is_mutating=False,
        is_network=True,
    )
    assert allowed is False
    assert why == "net disabled for this role (per-gate override)"


def test_filtered_toolset_for_ai_role_includes_web_fetch(
    strawman_registry, tmp_path: Path
) -> None:
    spec = strawman_registry.get("ai")
    assert spec is not None
    full = make_toolset(tmp_path, renderer=None, net=None)
    filtered = filter_toolset_for_role(spec, full)
    assert "web_fetch" in filtered


def test_filtered_toolset_for_backend_role_excludes_web_fetch(
    strawman_registry, tmp_path: Path
) -> None:
    spec = strawman_registry.get("backend")
    assert spec is not None
    full = make_toolset(tmp_path, renderer=None, net=None)
    filtered = filter_toolset_for_role(spec, full)
    assert "web_fetch" not in filtered


def test_project_policy_deny_overrides_ai_role_net(
    strawman_registry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_process_allow_net(True, monkeypatch)
    spec = strawman_registry.get("ai")
    assert spec is not None
    base = PermissionGate(
        mode="edit",
        store=PermissionStore(cwd=tmp_path),
        auto_yes=True,
        project_policy=PermissionsConfig(tool_policy=ToolPolicy(deny=["web_fetch"])),
    )
    gate = gate_for_role(spec, base)
    allowed, why = gate.check(
        "web_fetch",
        {"url": "https://example.com"},
        is_mutating=False,
        is_network=True,
    )
    assert allowed is False
    assert "denied by .voss/permissions.yml" in why

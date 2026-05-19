"""RED/GREEN tests for SKILL-04 (Scope and permission gates)."""
from __future__ import annotations

import pytest
from voss.harness.permissions import PermissionGate


def test_out_of_scope_blocked() -> None:
    """SKILL-04: Out-of-scope operations like writing or network are blocked."""
    try:
        from voss.harness.skill.scope import ScopeSpec, scoped_gate
    except ImportError as e:
        pytest.fail(f"RED: missing scope module ({e})")

    # A read-only scope, fs="cwd", net=False
    spec = ScopeSpec(tools="read-only", fs="cwd", net=False)
    base_gate = PermissionGate(mode="auto", auto_yes=True)
    gate = scoped_gate(spec, base_gate)

    # fs_write is a mutating tool, should be blocked by read-only scope
    allowed, reason = gate.check("fs_write", ["file.txt", "content"], is_mutating=True)
    assert not allowed
    assert "scope" in reason.lower() or "read-only" in reason.lower() or "plan" in reason.lower()

    # Network access should be blocked
    allowed, reason = gate.check("http_request", ["http://example.com"], is_network=True)
    assert not allowed
    assert "network" in reason.lower() or "scope" in reason.lower() or "net" in reason.lower()


def test_in_scope_allowed() -> None:
    """SKILL-04: In-scope operations like read-only file reads are permitted."""
    try:
        from voss.harness.skill.scope import ScopeSpec, scoped_gate
    except ImportError as e:
        pytest.fail(f"RED: missing scope module ({e})")

    spec = ScopeSpec(tools="read-only", fs="cwd", net=False)
    base_gate = PermissionGate(mode="auto", auto_yes=True)
    gate = scoped_gate(spec, base_gate)

    # fs_read is non-mutating and in-scope, should be allowed
    allowed, reason = gate.check("fs_read", ["file.txt"], is_mutating=False)
    assert allowed
    assert reason == "ok" or reason == "auto"

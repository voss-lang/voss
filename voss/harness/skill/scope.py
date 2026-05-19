"""Permission scoping and PermissionGate integration for third-party skills.

Converts manifest scopes into the existing harness PermissionGate mode axis.
Confinement is enforced by mapping tools to existing Mode tiers (plan, edit, auto)
and running the skill subprocess with allow_net=ScopeSpec.net.

Direct Python calls (e.g. open(), urllib.request) executed inside a skill's .voss
subprocess are NOT sandboxed (OS-level sandboxing is deferred). Gate-confinement
restricts harness tool calls only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from voss.harness.permissions import PermissionGate

if TYPE_CHECKING:
    from voss.harness.permissions import Mode


@dataclass(frozen=True)
class ScopeSpec:
    """Declared execution scope from the skill manifest."""
    tools: str = "read-only"  # "read-only" | "mutating" | "all"
    fs: str = "cwd"          # "cwd" | "none"
    net: bool = False


def scope_spec_from_manifest(raw: dict) -> ScopeSpec:
    """Parse raw manifest dictionary to extract ScopeSpec defensively.
    
    Undeclared, unrecognized, or malformed values default-deny to read-only cwd no-net.
    """
    if not isinstance(raw, dict):
        return ScopeSpec()
    scopes = raw.get("scopes")
    if not isinstance(scopes, dict):
        return ScopeSpec()

    tools = str(scopes.get("tools", "read-only")).strip()
    if tools not in ("read-only", "mutating", "all"):
        tools = "read-only"

    fs = str(scopes.get("fs", "cwd")).strip()
    if fs not in ("cwd", "none"):
        fs = "cwd"

    net = scopes.get("net", False)
    if not isinstance(net, bool):
        net = False

    return ScopeSpec(tools=tools, fs=fs, net=net)


def scope_to_mode(tools_value: str) -> Mode:
    """Map tool scope strings to existing Mode literal tiers.
    
    "read-only" -> "plan"
    "mutating" -> "edit"
    "all"       -> "auto"
    unrecognized -> "plan" (default-deny)
    """
    val = str(tools_value).strip()
    if val == "read-only":
        return "plan"
    if val == "mutating":
        return "edit"
    if val == "all":
        return "auto"
    return "plan"


def _min_mode(m1: Mode, m2: Mode) -> Mode:
    """Return the tighter (more restrictive) mode of the two."""
    order = {"plan": 0, "edit": 1, "auto": 2}
    v1 = order.get(m1, 0)
    v2 = order.get(m2, 0)
    return m1 if v1 <= v2 else m2


def scoped_gate(spec: ScopeSpec, base_gate: PermissionGate) -> PermissionGate:
    """Return a new PermissionGate capped by the declared tools scope.
    
    Capped mode = min(base_gate.mode, scope_to_mode(spec.tools)).
    Ensures third-party skills never prompt (auto_yes=True) and never persist
    always-allow decisions (store=None).
    """
    effective_mode = _min_mode(base_gate.mode, scope_to_mode(spec.tools))
    return PermissionGate(
        mode=effective_mode,
        auto_yes=True,
        store=None,
        project_policy=base_gate.project_policy,
    )

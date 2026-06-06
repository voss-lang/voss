"""V1-03: MCP capability unification — default-deny mutability, gate-on-mutation
parity, and scoped net bucket (CAP-07/09, D-02)."""
from __future__ import annotations

import sys
from types import SimpleNamespace

from voss.harness.mcp.registry import _is_mutating_from_descriptor, register_mcp_tools
from voss.harness.permissions import PermissionGate
from voss.harness.rate_limit import TokenBucket


def _tool(name: str, annotations: dict | None = None) -> dict:
    d: dict = {"name": name, "inputSchema": {"type": "object"}}
    if annotations is not None:
        d["annotations"] = annotations
    return d


def _register(tools: list[dict]):
    config = SimpleNamespace(servers=["srv"])
    client = SimpleNamespace(_tools_cache={"srv": tools})
    return register_mcp_tools(config, {}, client)


# ---- Task 1: default-deny mutability + metadata tagging --------------------


def test_no_annotations_is_mutating() -> None:
    assert _is_mutating_from_descriptor(_tool("x")) is True


def test_readonly_hint_not_mutating() -> None:
    assert _is_mutating_from_descriptor(_tool("x", {"readOnlyHint": True})) is False


def test_destructive_false_without_readonly_still_mutating() -> None:
    # default-deny: destructiveHint=False alone does NOT make it read-only
    assert _is_mutating_from_descriptor(_tool("x", {"destructiveHint": False})) is True


def test_register_tags_capability_metadata() -> None:
    entries = _register(
        [_tool("do_thing"), _tool("read_thing", {"readOnlyHint": True})]
    )
    assert set(entries) == {"srv__do_thing", "srv__read_thing"}
    for e in entries.values():
        assert e.group == "mcp"
        assert "mcp" in e.scope_requirements
        assert "net" in e.scope_requirements
        assert e.is_network is True
        assert e.audit_behavior == "full"
        assert e.is_stateful is False
    assert entries["srv__do_thing"].is_mutating is True
    assert entries["srv__read_thing"].is_mutating is False


# ---- Task 2: gate-on-mutation parity --------------------------------------


def test_mutating_mcp_prompts_in_edit(monkeypatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    calls: list = []

    def prompt_fn(name, args):
        calls.append(name)
        return "a"  # allow once

    gate = PermissionGate(mode="edit", auto_yes=False, prompt_fn=prompt_fn, allow_net=True)
    allowed, why = gate.check("srv__do_thing", {}, is_mutating=True, is_network=True)
    assert allowed is True  # user approved
    assert calls == ["srv__do_thing"]  # prompt actually fired


def test_readonly_mcp_no_mutation_prompt_in_edit(monkeypatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    calls: list = []

    def prompt_fn(name, args):
        calls.append(name)
        return "a"

    gate = PermissionGate(mode="edit", auto_yes=False, prompt_fn=prompt_fn, allow_net=True)
    allowed, why = gate.check("srv__read_thing", {}, is_mutating=False, is_network=True)
    assert allowed is True
    assert calls == []  # no prompt for a read-only MCP capability


# ---- Task 2: scoped net bucket (no blanket __ bypass) ----------------------


def test_configured_mcp_bucket_is_honored() -> None:
    from voss.harness.net import NetSession

    session = NetSession()
    # Inject a 1-token bucket for an MCP-namespaced name. With the old blanket
    # `if "__" in name: return True, 0.0` bypass, the second acquire would still
    # be allowed; now the bucket is consulted and the second is throttled.
    session._buckets["srv__do_thing"] = TokenBucket(rate_per_min=1, burst=1)
    first_ok, _ = session.acquire("srv__do_thing")
    second_ok, wait = session.acquire("srv__do_thing")
    assert first_ok is True
    assert second_ok is False  # bucket consulted, not blanket-bypassed
    assert wait > 0.0

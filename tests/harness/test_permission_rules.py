"""H5.1 — wildcard / per-command permission rules."""

from __future__ import annotations

from voss.harness.cognition_schemas import PermissionsConfig
from voss.harness.permissions import PermissionGate, match_permission_rules


def test_matcher_exact_wildcard_and_specificity():
    assert match_permission_rules({"fs_write": "deny"}, "fs_write", {}) == "deny"
    assert match_permission_rules({"*": "ask"}, "fs_read", {}) == "ask"
    # a specific tool key wins over "*"
    assert match_permission_rules({"*": "deny", "fs_read": "allow"}, "fs_read", {}) == "allow"
    assert match_permission_rules({}, "fs_read", {}) is None
    assert match_permission_rules(None, "fs_read", {}) is None


def test_matcher_per_command_last_match_wins():
    rules = {"shell_run": {"*": "ask", "git *": "allow", "git push *": "deny"}}
    assert match_permission_rules(rules, "shell_run", {"cmd": "git status"}) == "allow"
    assert match_permission_rules(rules, "shell_run", {"cmd": "git push origin"}) == "deny"
    assert match_permission_rules(rules, "shell_run", {"cmd": "ls -la"}) == "ask"


def test_deny_rule_blocks_even_in_auto_mode():
    g = PermissionGate(
        mode="auto", project_policy=PermissionsConfig(rules={"fs_write": "deny"})
    )
    ok, why = g.check("fs_write", {"path": "x"}, is_mutating=True)
    assert ok is False
    assert "rule" in why


def test_allow_rule_skips_prompt_in_edit_mode():
    calls = {"n": 0}

    def pf(tool, args):
        calls["n"] += 1
        return "d"

    g = PermissionGate(
        mode="edit",
        auto_yes=False,
        prompt_fn=pf,
        project_policy=PermissionsConfig(rules={"fs_write": "allow"}),
    )
    ok, why = g.check("fs_write", {"path": "x"}, is_mutating=True)
    assert ok is True
    assert "rule" in why
    assert calls["n"] == 0  # allow short-circuited the prompt


def test_ask_rule_forces_prompt_over_auto_yes():
    def pf(tool, args):
        return "d"  # user denies

    g = PermissionGate(
        mode="auto",
        auto_yes=True,
        prompt_fn=pf,
        project_policy=PermissionsConfig(rules={"shell_run": {"*": "ask"}}),
    )
    ok, _why = g.check("shell_run", {"cmd": "ls"}, is_mutating=False)
    assert ok is False  # ask forced a prompt despite auto_yes; pf denied


def test_no_rules_preserves_existing_behaviour():
    # empty rules -> matcher returns None; gate behaves as before (auto allows).
    g = PermissionGate(mode="auto", project_policy=PermissionsConfig())
    ok, _ = g.check("fs_read", {"path": "x"})
    assert ok is True

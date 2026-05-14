"""Permission gate matrix: 3 modes × 3 mutating tools.

Asserts the `mode_allows` contract directly. End-to-end coverage via
`voss do` would require driving the stubbed planner to emit specific tool
calls per mode — fingerprint-keyed stub responses make that brittle. The
unit contract is the source of truth; this matrix test pins it.

Truth table (voss/harness/permissions.py:mode_allows):

           | fs_write | fs_edit | shell_run
    plan   |   deny   |  deny   |   deny
    edit   |   allow  |  allow  |   deny
    auto   |   allow  |  allow  |   allow
"""
from __future__ import annotations

import pytest

from voss.harness.permissions import mode_allows


EXPECTED = {
    ("plan", "fs_write"): False,
    ("plan", "fs_edit"): False,
    ("plan", "shell_run"): False,
    ("edit", "fs_write"): True,
    ("edit", "fs_edit"): True,
    ("edit", "shell_run"): False,
    ("auto", "fs_write"): True,
    ("auto", "fs_edit"): True,
    ("auto", "shell_run"): True,
}


MUTATING_TOOLS = ("fs_write", "fs_edit", "shell_run")


@pytest.mark.parametrize("mode", ("plan", "edit", "auto"))
@pytest.mark.parametrize("tool", MUTATING_TOOLS)
def test_mode_allows_matrix(mode: str, tool: str) -> None:
    allowed, reason = mode_allows(mode, tool, is_mutating=True)
    expected = EXPECTED[(mode, tool)]
    assert allowed is expected, (
        f"mode={mode!r} tool={tool!r}: got allowed={allowed} reason={reason!r}; "
        f"expected {expected}"
    )


@pytest.mark.parametrize("mode", ("plan", "edit", "auto"))
def test_mode_allows_read_only(mode: str) -> None:
    """Read-only tools (is_mutating=False) are always allowed."""
    for tool in ("fs_read", "fs_glob", "fs_grep", "git_status", "voss_check"):
        allowed, _ = mode_allows(mode, tool, is_mutating=False)
        assert allowed, f"read-only {tool!r} denied under mode={mode!r}"


def test_mode_allows_returns_reason_on_deny() -> None:
    """Reason string must mention the mode that denied so logs make sense."""
    allowed, reason = mode_allows("plan", "fs_write", is_mutating=True)
    assert not allowed
    assert "plan" in reason, reason

    allowed, reason = mode_allows("edit", "shell_run", is_mutating=True)
    assert not allowed
    assert "edit" in reason, reason

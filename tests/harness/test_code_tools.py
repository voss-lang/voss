"""Basic registration tests for M10-04 code intelligence tools."""

from pathlib import Path

from voss.harness.tools import make_toolset


def test_code_tools_are_registered_and_readonly():
    tools = make_toolset(Path.cwd())
    for name in ("code_search", "find_definition", "find_references", "code_refresh"):
        assert name in tools, f"Missing tool: {name}"
        entry = tools[name]
        assert entry.is_mutating is False, f"{name} must be read-only"
        assert entry.is_network is False, f"{name} must not be network"


def test_code_tools_do_not_increase_mutating_count():
    # The test_tools.py has hard counts; this wave only adds read-only tools
    tools = make_toolset(Path.cwd())
    mutating = [n for n, e in tools.items() if e.is_mutating]
    # We don't assert exact number here to avoid fragility; the main test_tools does the count
    assert "code_search" not in mutating

"""Pinning test: subagent recursion has no depth guard.

`voss.harness.subagents.run_subagent` calls `run_turn`, which can dispatch
the `subagent_run` tool, which loops back through `run_subagent`. There is
currently no depth counter or `max_depth` parameter — recursion is bounded
only by Python's stack (default ~1000 frames). A malicious or buggy plan
that always emits `subagent_run` will OOM/RecursionError.

This test pins the gap. If a guard is added (e.g. a `depth` kwarg on
`run_subagent` or a module-level `MAX_DEPTH` constant), update the
assertions below to verify the guard fires.

Follow-up issue: add `max_depth` (default 5) to run_subagent + a clear
"subagent depth exceeded" error path.
"""
from __future__ import annotations

import inspect

from voss.harness import subagents


def test_run_subagent_has_no_depth_parameter() -> None:
    """run_subagent signature does not take a depth / max_depth kwarg."""
    sig = inspect.signature(subagents.run_subagent)
    params = set(sig.parameters)
    assert "depth" not in params, (
        "run_subagent now takes a depth param — update this test and "
        "drop the follow-up issue."
    )
    assert "max_depth" not in params


def test_no_module_level_depth_constant() -> None:
    """No MAX_DEPTH / DEPTH_LIMIT constant exists in the subagents module."""
    for attr in ("MAX_DEPTH", "DEPTH_LIMIT", "RECURSION_LIMIT"):
        assert not hasattr(subagents, attr), (
            f"subagents.{attr} now exists — update this test to verify "
            f"it is consulted by run_subagent."
        )


def test_subagent_tool_marked_mutating() -> None:
    """subagent_run is mutating (it can spawn writes via child run_turn).

    This is the only existing safeguard: under mode=plan the planner cannot
    invoke subagent_run because mode_allows denies mutating tools. Under
    mode=edit / auto, recursion is unbounded — hence the follow-up issue.
    """
    from voss.harness.permissions import mode_allows

    allowed_plan, _ = mode_allows("plan", "subagent_run", is_mutating=True)
    assert not allowed_plan, "plan mode unexpectedly allows subagent_run"

    allowed_edit, _ = mode_allows("edit", "subagent_run", is_mutating=True)
    assert allowed_edit, "edit mode unexpectedly denies subagent_run"

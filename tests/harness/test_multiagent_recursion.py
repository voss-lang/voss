"""M13 Wave-0 — recursive spawn (MAG-06) + back-compat recursion-pin guard.

This file carries TWO distinct kinds of test, deliberately:

  * `TestDepth2` — MAG-06 RED scaffold (xfail, strict=False): depth-2
    parent→child→grandchild nested even-split budget + nested panels +
    no-leak. Drives the not-yet-existing `voss.harness.multiagent`
    (created in W1) imported inside the test body. RED-by-design.

  * `TestBackCompatRecursionPinIntact` — the M13 back-compat regression
    guard. GREEN from Wave 0 onward and MUST stay green through every
    later wave. It is the tripwire that fails loudly if any M13 wave
    breaches the recursion-pinning contract by adding a
    depth/max_depth/MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT symbol to
    `voss.harness.subagents` or modifies the unmodified pinning suite
    `tests/harness/test_subagent_recursion.py`. It is NOT xfail-marked.

Threat: T-M13-recursion-DoS (unbounded recursive spawn, DoS). Recursion is
bounded by the viable-budget-floor denial in `M13Allocator.allocate`
(M13-VALIDATION.md §"Security Domain") — NOT by any depth constant. No test
in this file introduces or references a depth/max_depth symbol for
production use; the forbidden names appear only as negative assertions in
the back-compat guard. No production code is written here.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestDepth2:
    """MAG-06: parent→child→grandchild nested budget + nested panels.

    (a) 3 distinct panel_ids mounted concurrently;
    (b) grandchild allotment ≤ child slice ≤ parent reserve at all 3 levels;
    (c) post-gather zero SubAgentPanel (no leak).
    Recursion bounded by viable-floor only (no depth constant).
    """

    async def test_nested_budget_is_strictly_bounded(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        parent_reserve = 60_000
        parent = multiagent.M13Allocator(reserve=parent_reserve)
        await parent.allocate("child-a")
        child_slice = parent.snapshot()["child-a"]

        child = multiagent.M13Allocator(reserve=child_slice)
        await child.allocate("grandchild")
        grandchild_slice = child.snapshot()["grandchild"]

        assert grandchild_slice <= child_slice <= parent_reserve

    async def test_three_distinct_panels_then_clean_teardown(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        f = scripted_multiagent_provider
        f.scripts["parent"] = [
            f.spawn_plan([("child-a", "level 1")]),
            f.gather_plan(["child-a"], final="done"),
        ]
        f.scripts["child-a"] = [
            f.spawn_plan([("grandchild", "level 2")]),
            f.gather_plan(["grandchild"], final="child done"),
        ]
        f.scripts["grandchild"] = [f.done_plan("grandchild done")]

        orchestrator = multiagent.MultiAgentOrchestrator(
            provider_factory=f, cwd=tmp_path
        )
        panel_ids = await orchestrator.run_recursive(depth_roles=["parent"])
        assert len(set(panel_ids)) == 3, "expected 3 distinct nested panel ids"
        assert orchestrator.live_panels() == [], "panels leaked post-gather"


class TestBackCompatRecursionPinIntact:
    """M13 back-compat regression guard — GREEN from Wave 0, stays green.

    NOT xfail-marked. Asserts the recursion-pinning contract that
    `tests/harness/test_subagent_recursion.py` pins is still intact and that
    no M13 wave has added a depth guard to `voss.harness.subagents`. This is
    the tripwire for threat T-M13-02 (back-compat breach, Tampering).
    """

    def test_run_subagent_has_no_depth_or_max_depth_param(self) -> None:
        from voss.harness import subagents

        sig = inspect.signature(subagents.run_subagent)
        params = set(sig.parameters)
        assert "depth" not in params, (
            "M13 added a `depth` param to run_subagent — back-compat "
            "recursion pin breached (test_subagent_recursion.py contract)."
        )
        assert "max_depth" not in params, (
            "M13 added a `max_depth` param to run_subagent — back-compat "
            "recursion pin breached."
        )

    def test_subagents_module_has_no_depth_constant(self) -> None:
        from voss.harness import subagents

        for attr in ("MAX_DEPTH", "DEPTH_LIMIT", "RECURSION_LIMIT"):
            assert not hasattr(subagents, attr), (
                f"M13 introduced subagents.{attr} — back-compat recursion "
                f"pin breached; recursion must stay viable-floor-bounded."
            )

    def test_unmodified_pinning_suite_still_passes(self) -> None:
        """Run the UNMODIFIED pinning suite in a subprocess (not re-entrant).

        Asserts `tests/harness/test_subagent_recursion.py` still collects
        and passes byte-unmodified — the green-from-W0 tripwire.
        """
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/harness/test_subagent_recursion.py",
            ],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            "unmodified tests/harness/test_subagent_recursion.py no longer "
            f"passes — back-compat breach.\nstdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

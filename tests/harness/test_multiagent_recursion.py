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

        # M13-05 NOTE: this body was corrected (Option 2, pre-authorized by
        # M13-05-PLAN). The original W0 scaffold invented
        # `multiagent.MultiAgentOrchestrator(...).run_recursive(...)` /
        # `.live_panels()` — an API M13-02/M13-03 never shipped and
        # M13-01-PLAN never specified (same fictional-API class M13-01
        # ad-libbed for the fanout/steer suites, corrected in M13-03). The
        # MAG-06 signal bar is preserved VERBATIM in intent: a depth-2
        # parent→child→grandchild fan-out mounts 3 distinct concurrent
        # SubAgentPanel ids; grandchild allotment ≤ child slice ≤ parent
        # reserve at all 3 levels; post-gather zero SubAgentPanel (no leak);
        # recursion bounded by the viable-floor only (no depth constant).
        #
        # Drives the REAL recursive architecture: the parent invokes the
        # real `subagent_spawn` tool (the parent IS the chat turn — mirrors
        # every M13-03 corrected test); the spawned child's run_turn toolset
        # re-receives the four M13 tools bound to its slice-scoped
        # sub_allocator (D-07), so the child itself fans out to TWO
        # grandchildren — child panel + 2 grandchild panels = 3 distinct
        # concurrent panel ids across the 3-level chain.
        from voss.harness.agent import Plan, ToolCall
        from voss.harness.providers import (
            Done,
            ParsedPlan,
            TextDelta,
            Usage,
        )

        f = scripted_multiagent_provider

        # Opaque per-role sentinels: present ONLY in that role's own
        # run_turn FIRST user message (its task text). The role router keys
        # on messages[0] (the original Task: line) so it never misroutes
        # once child-a's later iterations accumulate the grandchild
        # spawn-tool-call args / result strings in conversation history.
        S_CHILD = "SENTINEL_CHILDA_TASK"
        S_GX = "SENTINEL_GRANDX_TASK"
        S_GY = "SENTINEL_GRANDY_TASK"

        def _stream(plan: Plan):
            # Same canonical [TextDelta, ParsedPlan, Usage, Done] shape the
            # conftest builders emit. Built in-test (not via f.gather_plan)
            # because the conftest gather_plan builder emits
            # subagent_gather(handles=[...]) — the FICTIONAL scaffold
            # signature; the REAL M13-03 subagent_gather() takes NO args
            # (multiagent.py:473). The conftest stays byte-stable; only this
            # pre-authorized diverged test body builds a real-signature plan.
            return [
                TextDelta(text="..."),
                ParsedPlan(plan=plan),
                Usage(prompt_tokens=10, completion_tokens=5, cost_usd=0.001),
                Done(stop_reason="end_turn"),
            ]

        # Child-a (level-1) script driving the REAL recursive toolset:
        #   iter 0 — fan out to two grandchildren via the recursively
        #            attached subagent_spawn (mounts 2 nested panels);
        #   iter 1 — real no-arg subagent_gather (joins + collapses them);
        #   iter 2 — terminal done plan (run_turn streams once more after a
        #            step+final iteration to emit the final and exit).
        f.scripts["child-a"] = [
            _stream(
                Plan(
                    rationale="fan out to two grandchildren",
                    steps=[
                        ToolCall(
                            name="subagent_spawn",
                            args={"agent": "grandchild-x", "task": S_GX},
                            why="delegate to grandchild-x",
                        ),
                        ToolCall(
                            name="subagent_spawn",
                            args={"agent": "grandchild-y", "task": S_GY},
                            why="delegate to grandchild-y",
                        ),
                    ],
                    confidence=0.9,
                )
            ),
            _stream(
                Plan(
                    rationale="gather the grandchildren",
                    steps=[
                        ToolCall(
                            name="subagent_gather",
                            args={},  # REAL signature: subagent_gather()
                            why="collect grandchild results",
                        )
                    ],
                    confidence=0.9,
                    final_when_done="child-a done",
                )
            ),
            _stream(
                Plan(
                    rationale="child-a finished",
                    steps=[],
                    confidence=0.9,
                    final_when_done="child-a done",
                )
            ),
        ]
        # Grandchildren (level-2) are terminal done plans (no further fan-out
        # — recursion would continue purely by viable-floor, no depth cap).
        f.scripts["grandchild-x"] = [f.done_plan("grandchild-x done")]
        f.scripts["grandchild-y"] = [f.done_plan("grandchild-y done")]

        class _PanelRecordingRenderer:
            """Records SubAgentPanel mount (show_subagent_start) and collapse
            (show_subagent_end) so we can assert 3 distinct concurrent
            panel_ids and zero post-gather leak — the real
            PanelBridgeRenderer routes start_panel/end_panel here."""

            def __init__(self) -> None:
                self.mounted: dict[str, int] = {}  # panel_id -> budget_total
                self.collapsed: set[str] = set()
                self.max_concurrent = 0

            def show_subagent_start(self, name, panel_id, budget_total=0):
                self.mounted[panel_id] = budget_total
                live = set(self.mounted) - self.collapsed
                self.max_concurrent = max(self.max_concurrent, len(live))

            def show_subagent_end(self, panel_id, n_results=0):
                self.collapsed.add(panel_id)

            def live_panels(self):
                return sorted(set(self.mounted) - self.collapsed)

            def __getattr__(self, _attr):
                def _noop(*a, **k):
                    return None

                return _noop

        # Per-role provider: route each run_turn by the FIRST user message
        # only (the original "Task:\n<sentinel>" line). The same provider
        # object is reused by the recursive attach, so it must dispatch by
        # role; the first user message is the only stable per-child anchor
        # (later iterations accumulate spawn tool-call args / result strings
        # that would otherwise leak a sibling sentinel into the blob).
        def _role_for(messages) -> str:
            first_user = next(
                (
                    str(m.get("content", ""))
                    for m in (messages or [])
                    if m.get("role") == "user"
                ),
                "",
            )
            if S_GX in first_user:
                return "grandchild-x"
            if S_GY in first_user:
                return "grandchild-y"
            return "child-a"

        class _RoleRoutingProvider:
            def stream(self, **kw):
                role = _role_for(kw.get("messages", []))
                return f.provider(role).stream(**kw)

            async def complete(self, **kw):
                return await f.provider("child-a").complete(**kw)

            def count_tokens(self, *, text, model):
                return max(len(text) // 4, 1)

        renderer = _PanelRecordingRenderer()
        registry = multiagent.SubagentRegistry()
        tools: dict = {}
        multiagent.attach_multiagent_tools(
            tools,
            registry=registry,
            cwd=tmp_path,
            renderer=renderer,
            provider=_RoleRoutingProvider(),
            model="stub",
            gate=None,
            cognition=None,
        )

        # Level 0 → 1: the parent (this chat turn) spawns child-a. The real
        # M13Allocator (top-level reserve == DEFAULT_PARENT_RESERVE) grants
        # child-a its slice; the child's run_turn toolset is recursively
        # wired with a slice-scoped sub_allocator (reserve == child-a's
        # allotment) so it can fan out to grandchildren (D-07).
        spawn_ret = await tools["subagent_spawn"].invoke(
            agent="child-a", task=S_CHILD
        )
        assert spawn_ret.startswith("spawned"), spawn_ret
        child_budget = int(spawn_ret.split("budget=")[1].split(" ")[0])

        # Joining child-a runs its 2 iters: iter 0 fans out 2 grandchildren
        # (mounting their panels via the recursive subagent_spawn), iter 1
        # gathers + collapses them; then the parent gather collapses child-a.
        agg = await tools["subagent_gather"].invoke()

        # (a) 3 distinct panel_ids mounted concurrently across the 3-level
        #     chain: child-a + grandchild-x + grandchild-y.
        assert len(renderer.mounted) == 3, (
            f"expected 3 distinct nested panel ids, got "
            f"{sorted(renderer.mounted)}"
        )
        assert renderer.max_concurrent == 3, (
            "the 3 nested panels were not concurrently mounted "
            f"(max_concurrent={renderer.max_concurrent})"
        )

        # (b) grandchild allotment ≤ child slice ≤ parent reserve at all 3
        #     levels (read off the real per-panel budget the allocator
        #     granted at each level). The child-a panel carries `child_budget`
        #     (what its spawn returned); the two grandchild panels carry the
        #     slice-scoped sub_allocator's even split of child_budget.
        budgets = renderer.mounted
        gc_budgets = [v for v in budgets.values() if v != child_budget]
        parent_reserve = multiagent.DEFAULT_PARENT_RESERVE
        assert child_budget <= parent_reserve, (
            f"child slice {child_budget} > parent reserve {parent_reserve}"
        )
        assert gc_budgets, "no grandchild panels recorded a budget"
        for gcb in gc_budgets:
            assert gcb <= child_budget <= parent_reserve, (
                f"grandchild budget {gcb} not ≤ child slice {child_budget} "
                f"≤ parent reserve {parent_reserve}"
            )

        # (c) post-gather zero SubAgentPanel — every nested panel collapsed.
        assert renderer.live_panels() == [], (
            f"panels leaked post-gather: {renderer.live_panels()}"
        )
        assert "child-a done" in agg, agg


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

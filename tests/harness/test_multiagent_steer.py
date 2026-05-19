"""M13 Wave-0 RED scaffold — autonomous-parent course-correction (MAG-05).

Pins MAG-05 from M13-VALIDATION.md: a scripted parent injects a mid-run
correction into a still-running child via `subagent_steer`; the child stub
BRANCHES on injected-guidance presence and emits a different `final` when
steered. The WITH-correction child output must differ from the
no-correction control.

Threat: T-M13-mis-steer (steer to wrong/finished child, Tampering) —
M13-VALIDATION.md §"Security Domain". `ChildRegistry.get(handle)` validates;
steering a `done` child is a no-op.

RESEARCH Pitfall 2 (cited): a child that decides "done" before the
`agent.py:830` steer-inbox drain never consumes a pending steer — so the
child MUST be scripted for ≥2 iterations for the drain to be observably
hit. The scripts below give the child two iterations on purpose.

Wave-0 discipline: `voss.harness.multiagent` does NOT exist yet; it is
imported inside the test body, and the class is `xfail(strict=False)` so
this runs RED-by-design (xfail) — never green, never errored at collection.
No production code is written here.
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestCorrectionChangesBehavior:
    """MAG-05: WITH-correction child output != no-correction control.

    Threat T-M13-mis-steer: parent→running-child only; the steer is
    consumed at the ≥2-iteration drain seam (RESEARCH Pitfall 2).
    """

    async def test_steered_child_diverges_from_control(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        f = scripted_multiagent_provider

        # Control child: 2 iterations, no steer → baseline final.
        f.scripts["child-control"] = [
            f.done_plan("", rationale="control iter 0 (not yet done)"),
            f.done_plan("CONTROL-RESULT", rationale="control iter 1 done"),
        ]
        # Steered child: 2 iterations; branches on injected guidance presence.
        f.scripts["child-steered"] = [
            f.done_plan("", rationale="steered iter 0 (awaiting guidance)"),
            f.done_plan("STEERED-RESULT", rationale="steered iter 1 corrected"),
        ]
        f.scripts["parent"] = [
            f.spawn_plan([("child-steered", "do the task")]),
            f.steer_plan("child-steered", "actually, do it differently"),
            f.gather_plan(["child-steered"], final="merged"),
        ]

        orchestrator = multiagent.MultiAgentOrchestrator(
            provider_factory=f, cwd=tmp_path
        )
        control = await orchestrator.run_child(
            "child-control", "do the task", steer=None
        )
        steered = await orchestrator.run_child(
            "child-steered",
            "do the task",
            steer="actually, do it differently",
        )

        assert steered != control, (
            "steered child output did not diverge from the no-correction "
            "control — correction was not observably applied"
        )

    async def test_steer_to_finished_child_is_noop(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        registry = multiagent.ChildRegistry()
        registry.register("child-a")
        registry.release("child-a")  # child is now done
        accepted = registry.steer("child-a", "too late")
        assert accepted is False, "steering a finished child must be a no-op"

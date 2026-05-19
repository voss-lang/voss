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


class _NullRenderer:
    """No-op renderer: every Renderer-protocol call the child run_turn makes
    is swallowed (no show_subagent_* so the PanelBridgeRenderer hasattr
    guards exercise their no-base-method path)."""

    def __getattr__(self, _attr):
        def _noop(*a, **k):
            return None

        return _noop


class _StubProvider:
    """Routes the single `child-a` script for the no-op test (the steered
    child here is never actually run before it is gathered)."""

    def __init__(self, factory):
        self._f = factory

    def stream(self, **kw):
        return self._f.provider("child-a").stream(**kw)

    async def complete(self, **kw):
        return await self._f.provider("child-a").complete(**kw)

    def count_tokens(self, *, text, model):
        return max(len(text) // 4, 1)


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestCorrectionChangesBehavior:
    """MAG-05: WITH-correction child output != no-correction control.

    Drives the REAL M13-03 architecture: `attach_multiagent_tools` ->
    `subagent_spawn` launches a detached child whose run_turn carries the
    per-child `steer_inbox` queue; `subagent_steer` enqueues guidance; the
    child is scripted for ≥2 iterations so the agent.py:830 drain fires and
    injects the guidance as a synthetic next-iteration user message; the
    child provider BRANCHES on the `[steering from parent agent]` marker
    appearing in its `messages` and emits a divergent `final`. The
    no-correction control runs the same child WITHOUT subagent_steer.

    M13-01 NOTE: this body was corrected (Option 2) — the original scaffold
    invented `multiagent.MultiAgentOrchestrator(...).run_child(...)` and
    `ChildRegistry.register/release/steer`, an API M13-02 never shipped and
    M13-01-PLAN never specified. The MAG-05 signal bar (WITH-correction
    output != no-correction control, ≥2-iteration drain consumption,
    T-M13-mis-steer no-op) is preserved verbatim in intent.
    """

    async def _run_one(
        self, multiagent, tmp_path, f, role: str, *, steer: str | None
    ) -> str:
        """Spawn `role` via the real subagent_spawn tool, optionally steer it
        mid-run, then gather. Returns this child's aggregated result line."""

        # Iter 0: empty steps + empty final -> NOT _is_done_plan -> loop
        # continues -> agent.py:830 drain fires. Iter 1: branch on the
        # injected steering marker present in the rebuilt `messages`.
        STEER_MARK = "[steering from parent agent]"

        class _BranchingProvider:
            def __init__(self, base):
                self._base = base
                self._i = 0

            def stream(self, **kw):
                i = self._i
                self._i += 1
                if i == 0:
                    return self._base.stream(**kw)  # not-done iter 0
                # Iteration >=1: did the parent steer land in `messages`?
                msgs = kw.get("messages", [])
                steered = any(
                    STEER_MARK in str(m.get("content", "")) for m in msgs
                )
                final = "STEERED-RESULT" if steered else "BASELINE-RESULT"
                stream = f.done_plan(final, rationale=f"iter {i} {final}")

                async def _gen():
                    for ev in stream:
                        yield ev

                return _gen()

            async def complete(self, **kw):
                return await self._base.complete(**kw)

            def count_tokens(self, *, text, model):
                return max(len(text) // 4, 1)

        f.scripts[role] = [f.done_plan("", rationale=f"{role} iter 0")]
        branching = _BranchingProvider(f.provider(role))

        class _Prov:
            def stream(self, **kw):
                return branching.stream(**kw)

            async def complete(self, **kw):
                return await branching.complete(**kw)

            def count_tokens(self, *, text, model):
                return max(len(text) // 4, 1)

        registry = multiagent.SubagentRegistry()
        tools: dict = {}
        multiagent.attach_multiagent_tools(
            tools,
            registry=registry,
            cwd=tmp_path,
            renderer=_NullRenderer(),
            provider=_Prov(),
            model="stub",
            gate=None,
            cognition=None,
        )
        spawn_ret = await tools["subagent_spawn"].invoke(
            agent=role, task="do the task"
        )
        handle = spawn_ret.split("handle=")[1].split(" ")[0]
        if steer is not None:
            # No await/yield between spawn and steer: the child task is
            # scheduled by create_task but has not run yet, so the steer
            # lands in its queue BEFORE its iter-0 loop boundary (the
            # agent.py:830 drain), guaranteeing deterministic consumption.
            steer_ret = await tools["subagent_steer"].invoke(
                handle=handle, guidance=steer
            )
            assert steer_ret == f"steered {handle}", steer_ret
        agg = await tools["subagent_gather"].invoke()
        return agg

    async def test_steered_child_diverges_from_control(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        f = scripted_multiagent_provider

        control = await self._run_one(
            multiagent, tmp_path, f, "child-control", steer=None
        )
        steered = await self._run_one(
            multiagent,
            tmp_path,
            f,
            "child-steered",
            steer="actually, do it differently",
        )

        assert "BASELINE-RESULT" in control, control
        assert "STEERED-RESULT" in steered, steered
        assert steered != control, (
            "steered child output did not diverge from the no-correction "
            "control — correction was not observably applied"
        )

    async def test_steer_to_finished_child_is_noop(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        # Real API: subagent_steer (the M13-03 tool) is the steer surface;
        # ChildRegistry has no register/release/steer. A steer to a `done`
        # child must be a benign no-op string (never raise) — T-M13-mis-steer.
        registry = multiagent.SubagentRegistry()
        tools: dict = {}
        multiagent.attach_multiagent_tools(
            tools,
            registry=registry,
            cwd=tmp_path,
            renderer=_NullRenderer(),
            provider=_StubProvider(scripted_multiagent_provider),
            model="stub",
            gate=None,
            cognition=None,
        )
        # Unknown handle -> benign no-op (never raises).
        unknown = await tools["subagent_steer"].invoke(
            handle="does-not-exist", guidance="too late"
        )
        assert unknown.startswith("<no-op:"), unknown

        # Spawn a child, gather it (now done), then steer -> no-op.
        f = scripted_multiagent_provider
        f.scripts["child-a"] = [f.done_plan("A-DONE", rationale="child a")]
        spawn_ret = await tools["subagent_spawn"].invoke(
            agent="child-a", task="do a"
        )
        handle = spawn_ret.split("handle=")[1].split(" ")[0]
        await tools["subagent_gather"].invoke()
        late = await tools["subagent_steer"].invoke(
            handle=handle, guidance="too late"
        )
        assert late == f"<no-op: child {handle} already finished>", late

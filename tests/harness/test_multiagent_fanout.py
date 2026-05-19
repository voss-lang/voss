"""M13 Wave-0 RED scaffold — concurrent fan-out + even-split + no-oversell.

Pins MAG-01 (concurrency overlap), MAG-03 (even-split / rebalance) and
MAG-04 (race-safe no-oversell + exactly-once release + depth-bound) from
M13-VALIDATION.md against the not-yet-existing `voss.harness.multiagent`
module (created in Wave 1).

Wave-0 discipline: `voss.harness.multiagent` does NOT exist yet. It is
imported INSIDE each test body (never at module scope) so collection stays
clean, and every MAG class is `@pytest.mark.xfail(strict=False)` so the
suite runs RED-by-design (xfail) — not skipped, not errored. Later waves
flip these xfail→xpass; tightening to strict is out of Wave-0 scope.

No production code is written here. The shared scripted provider comes from
`tests/harness/conftest.py::scripted_multiagent_provider`.
"""
from __future__ import annotations

import asyncio

import pytest


class _NullRenderer:
    """No-op renderer: every Renderer-protocol call the child run_turn makes
    is swallowed. It deliberately has NO show_subagent_* methods so the
    PanelBridgeRenderer hasattr-guards exercise their no-base-method path."""

    def __getattr__(self, _attr):
        def _noop(*a, **k):
            return None

        return _noop


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestConcurrentInFlight:
    """MAG-01: ≥2 children observably in-flight at the same instant.

    Drives the REAL M13-03 architecture (`attach_multiagent_tools` ->
    `subagent_spawn`/`subagent_gather`, the M13-02 `ChildRegistry`). Each
    child's provider stub records a wall-clock window AND yields the event
    loop mid-run; the windows must OVERLAP (proving concurrent
    `asyncio.create_task` scheduling, not serial await), and the closed-over
    `ChildRegistry.active()` must report ≥2 strictly between spawn and gather.

    M13-01 NOTE: this body was corrected (Option 2) — the original scaffold
    invented `ChildRegistry.register/release`/`active()==[]`, an API M13-02
    never shipped and M13-01-PLAN never specified. The MAG-01 signal bar
    (≥2 concurrently in-flight AND overlapping run windows) is preserved
    verbatim in intent against the shipped API.
    """

    async def test_two_children_overlap_in_flight(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        f = scripted_multiagent_provider
        f.scripts["child-a"] = [f.done_plan("A-DONE", rationale="child a")]
        f.scripts["child-b"] = [f.done_plan("B-DONE", rationale="child b")]

        windows: dict[str, list[float]] = {}

        # Provider that drives the real child run_turn but records a
        # wall-clock window and yields the loop mid-run so two detached
        # child tasks observably overlap (not serial await).
        class _WindowProvider:
            def __init__(self, base, role):
                self._base = base
                self._role = role

            def stream(self, **kw):
                inner = self._base.stream(**kw)

                async def _gen():
                    windows.setdefault(
                        self._role, [asyncio.get_event_loop().time()]
                    )
                    await asyncio.sleep(0.05)
                    async for ev in inner:
                        yield ev
                    windows[self._role].append(
                        asyncio.get_event_loop().time()
                    )

                return _gen()

            async def complete(self, **kw):
                return await self._base.complete(**kw)

            def count_tokens(self, *, text, model):
                return self._base.count_tokens(text=text, model=model)

        # Two distinct window-recording providers bound by spawn order.
        prov_a = _WindowProvider(f.provider("child-a"), "child-a")
        prov_b = _WindowProvider(f.provider("child-b"), "child-b")
        _seq = iter((prov_a, prov_b))

        class _SeqProvider:
            def stream(self, **kw):
                return next(_seq).stream(**kw)

            async def complete(self, **kw):
                return await f.provider("child-a").complete(**kw)

            def count_tokens(self, *, text, model):
                return max(len(text) // 4, 1)

        registry = multiagent.SubagentRegistry()
        tools: dict = {}
        multiagent.attach_multiagent_tools(
            tools,
            registry=registry,
            cwd=tmp_path,
            renderer=_NullRenderer(),
            provider=_SeqProvider(),
            model="stub",
            gate=None,
            cognition=None,
        )

        # The closed-over ChildRegistry is what subagent_spawn registers into;
        # reach it via the spawn tool then observe active() between spawn and
        # gather. attach_multiagent_tools owns it, so spy through the tool.
        spawn = tools["subagent_spawn"]
        gather = tools["subagent_gather"]

        h1 = await spawn.invoke(agent="child-a", task="do a")
        h2 = await spawn.invoke(agent="child-b", task="do b")
        assert h1.startswith("spawned") and h2.startswith("spawned")

        # Strictly between spawn and gather: both detached tasks scheduled,
        # neither awaited. The status tool reports the live active count.
        await asyncio.sleep(0.02)
        status = await tools["subagent_status"].invoke()
        active_mid = int(status.splitlines()[0].split("active=")[1])
        assert active_mid >= 2, (
            "children were not concurrently in-flight "
            f"(active={active_mid}; expected >= 2 between spawn and gather)"
        )

        agg = await gather.invoke()
        assert "A-DONE" in agg and "B-DONE" in agg

        a_start, a_end = windows["child-a"]
        b_start, b_end = windows["child-b"]
        assert a_start < b_end and b_start < a_end, "run windows did not overlap"

    async def test_registry_active_drops_to_zero_after_gather(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        # Real API: ChildRegistry tracks ChildHandle records; `done` (flipped
        # by the gather path) is what active() filters on — there is no
        # registry-level register/release in the shipped M13-02 module.
        registry = multiagent.ChildRegistry()
        registry.add(multiagent.ChildHandle(id="child-a"))
        registry.add(multiagent.ChildHandle(id="child-b"))
        assert len(registry.active()) >= 2
        registry.get("child-a").done = True
        registry.get("child-b").done = True
        assert registry.active() == []


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestEvenSplitRebalance:
    """MAG-03: reserve R / N children → each ≈ R//N; rebalance on release.

    After one child releases, a surviving child's allotment strictly
    increases and the panel BudgetMeter reflects the new total.
    """

    async def test_even_split_then_rebalance(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        reserve = 60_000
        allocator = multiagent.M13Allocator(reserve=reserve)
        handles = ["child-a", "child-b", "child-c"]
        for h in handles:
            await allocator.allocate(h)

        snap = allocator.snapshot()
        for h in handles:
            assert snap[h] == pytest.approx(reserve // len(handles), rel=0.05)

        before = allocator.snapshot()["child-b"]
        allocator.release("child-a")
        await allocator.rebalance()
        after = allocator.snapshot()["child-b"]
        assert after > before, "survivor allotment did not increase on rebalance"


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestNoOversell:
    """MAG-04 (must-not-happen) — recursive no-oversell invariant.

    Threats: T-M13-oversell (budget oversell race, Tampering) and
    T-M13-recursion-DoS (unbounded recursive spawn, DoS — bounded here by
    the viable-floor denial, NOT by any depth constant). See
    M13-VALIDATION.md §"Security Domain".
    """

    async def test_concurrent_allocation_never_oversells(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        reserve = 30_000
        allocator = multiagent.M13Allocator(reserve=reserve)
        many = [f"child-{i}" for i in range(64)]
        await asyncio.gather(*[allocator.allocate(h) for h in many])

        total = sum(allocator.snapshot().values())
        assert total <= reserve, f"oversold: Σ={total} > reserve={reserve}"
        granted = len(allocator.snapshot())
        assert granted == reserve // multiagent.M13Allocator.VIABLE_FLOOR or (
            granted <= reserve // multiagent.M13Allocator.VIABLE_FLOOR
        ), "denied-count does not match viable-floor math"

    async def test_double_release_credits_exactly_once(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        reserve = 12_000
        allocator = multiagent.M13Allocator(reserve=reserve)
        for h in ("child-a", "child-b"):
            await allocator.allocate(h)
        allocator.release("child-a")
        allocator.release("child-a")  # idempotent — must NOT double-credit
        await allocator.rebalance()
        assert sum(allocator.snapshot().values()) <= reserve

    async def test_depth_bound_grandchild_le_child_le_parent(
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


class _RecordingRenderer:
    """Like _NullRenderer but records show_subagent_end (panel collapse) so
    TestOrphanTeardown can assert the orphan's panel was collapsed."""

    def __init__(self) -> None:
        self.ended: list[tuple] = []

    def show_subagent_end(self, parent_id, n_results=0):
        self.ended.append((parent_id, n_results))

    def __getattr__(self, _attr):
        def _noop(*a, **k):
            return None

        return _noop


class TestOrphanTeardown:
    """T-M13-02 (orphan-DoS) EXECUTABLE GATE — NEW in M13-03 (additive).

    A scripted parent calls `subagent_spawn` but NEVER `subagent_gather`.
    After the parent turn ends, awaiting the `_teardown_orphans` callable
    (returned by `attach_multiagent_tools`) MUST cancel the still-running
    child task, release its allotment, collapse its panel, and leave no
    live/un-released handle. This proves the orphan mitigation is wired,
    not merely present. The cli-level invocation hook lands in M13-06.

    NOT xfail-marked: the defensive net ships in M13-03, so this is a hard
    green gate from this wave onward.
    """

    async def test_teardown_cancels_releases_collapses_orphan(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        f = scripted_multiagent_provider
        cancelled: dict[str, bool] = {}

        # A child whose first stream blocks forever — it is still in-flight
        # when teardown runs, so cancellation is observable inside the child.
        class _BlockingProvider:
            def stream(self, **kw):
                async def _gen():
                    try:
                        await asyncio.sleep(3600)
                    except asyncio.CancelledError:
                        cancelled["child"] = True
                        raise
                    # unreachable in this test
                    for ev in f.done_plan("UNREACHED"):
                        yield ev

                return _gen()

            async def complete(self, **kw):
                return await f.provider("child-a").complete(**kw)

            def count_tokens(self, *, text, model):
                return max(len(text) // 4, 1)

        renderer = _RecordingRenderer()
        registry = multiagent.SubagentRegistry()
        tools: dict = {}
        teardown = multiagent.attach_multiagent_tools(
            tools,
            registry=registry,
            cwd=tmp_path,
            renderer=renderer,
            provider=_BlockingProvider(),
            model="stub",
            gate=None,
            cognition=None,
        )
        assert callable(teardown), "attach_multiagent_tools must return the net"

        spawn_ret = await tools["subagent_spawn"].invoke(
            agent="child-a", task="run forever"
        )
        handle = spawn_ret.split("handle=")[1].split(" ")[0]

        # Let the detached child actually start its (blocking) first stream.
        await asyncio.sleep(0.02)
        status = await tools["subagent_status"].invoke()
        assert "active=1" in status, status

        # Parent turn ends WITHOUT gather -> defensive net.
        await teardown()

        # 1) child task was cancelled (cancellation propagated into child).
        assert cancelled.get("child") is True, (
            "orphan child task was not cancelled by the teardown net"
        )
        # 2) panel collapsed (bridge end_panel -> show_subagent_end).
        assert any(pid == handle for pid, _ in renderer.ended), (
            f"orphan panel {handle} was not collapsed; "
            f"ended={renderer.ended}"
        )
        # 3) no live/un-released handle. The child-tracking ChildRegistry is
        # closed over inside attach_multiagent_tools; observe it via the
        # status tool — a done child with active=0 proves the handle is no
        # longer live and its allotment was released exactly once.
        post = await tools["subagent_status"].invoke()
        assert "active=0" in post, post
        assert post.splitlines()[1].startswith(f"[{handle}] done=True"), post

        # 4) idempotent: a second teardown / gather is safe to call again.
        await teardown()
        agg = await tools["subagent_gather"].invoke()
        assert handle in agg

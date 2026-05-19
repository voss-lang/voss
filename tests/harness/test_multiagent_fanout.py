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


@pytest.mark.xfail(
    reason="W1 voss.harness.multiagent not yet implemented",
    raises=(ImportError, AttributeError, AssertionError),
    strict=False,
)
class TestConcurrentInFlight:
    """MAG-01: ≥2 children observably in-flight at the same instant.

    Each child stub records a wall-clock window; the windows must OVERLAP
    (proving concurrent scheduling, not serial await), and
    `ChildRegistry.active()` must report ≥2 between spawn and gather.
    """

    async def test_two_children_overlap_in_flight(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        registry = multiagent.ChildRegistry()
        windows: dict[str, list[float]] = {}

        async def _child(handle: str) -> None:
            windows[handle] = [asyncio.get_event_loop().time()]
            registry.register(handle)
            await asyncio.sleep(0.05)
            registry.release(handle)
            windows[handle].append(asyncio.get_event_loop().time())

        spawn = asyncio.gather(_child("child-a"), _child("child-b"))
        await asyncio.sleep(0.02)
        active_mid = registry.active()
        await spawn

        assert len(active_mid) >= 2, "children were not concurrently in-flight"
        a_start, a_end = windows["child-a"]
        b_start, b_end = windows["child-b"]
        assert a_start < b_end and b_start < a_end, "run windows did not overlap"

    async def test_registry_active_drops_to_zero_after_gather(
        self, tmp_path, scripted_multiagent_provider
    ) -> None:
        from voss.harness import multiagent

        registry = multiagent.ChildRegistry()
        registry.register("child-a")
        registry.register("child-b")
        assert len(registry.active()) >= 2
        registry.release("child-a")
        registry.release("child-b")
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

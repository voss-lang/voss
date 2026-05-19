"""M13 multi-agent-in-chat foundation — in-memory, chat-turn-scoped.

This module is the pure, unit-testable core every later M13 wave builds on:
the `M13Allocator` (even-split-of-reserve budget allocator with an
`asyncio.Lock` race-safe check-and-allocate, idempotent exactly-once
`release`, and a viable-floor spawn denial that bounds recursion WITHOUT a
depth constant), plus the `ChildHandle` dataclass and `ChildRegistry`
in-memory child tracker.

It is a NEW module so `voss/harness/subagents.py` stays byte-stable and the
`tests/harness/test_subagent_recursion.py` pinning test remains green. The
allocator is LIFTED (copied, not imported) from O1-PATTERNS Pattern 2 — there
is intentionally NO import of `voss/harness/session_tree.py` or any other O1
module. O1 owns persistence; M13 keeps the registry/handle purely in memory
(M13-CONTEXT D-02: no disk, no global singleton).

────────────────────────────────────────────────────────────────────────────
RESEARCH Open Question A1 — resolved in-module (M13-RESEARCH "Reserve source")
────────────────────────────────────────────────────────────────────────────
Chat does not pass a parent budget today: the chat `run_turn` call
(cli.py:1695) passes NO `token_budget`, so `_run_turn_exec` falls back to the
DEFAULT signature default — verbatim, `voss/harness/agent.py` line 419:

    token_budget: int = 60_000

(`async def run_turn(...)` signature; VERIFIED this plan). The parent turn is
therefore wrapped in `ContextScope(token_budget=60_000, ...)` (agent.py:580).
There is no per-spawn budget anywhere in chat today. M13 must INVENT the
reserve (M13-CONTEXT D-05: "a parent reserve is carved"). The two constants
below are the Claude's-discretion resolution of A1 (CONTEXT "Claude's
Discretion": exact viable-budget-floor threshold is a sensible default that
must bound recursion); both cite the agent.py:419 `token_budget: int = 60_000`
anchor.

NOTE: no `depth` / `max_depth` / `MAX_DEPTH` / `DEPTH_LIMIT` /
`RECURSION_LIMIT` identifier appears anywhere in this module by design
(M13-RESEARCH line 442; preserves `test_subagent_recursion.py`). Recursion is
bounded ONLY by the viable-floor `None` return in `M13Allocator.allocate`.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

# OQ-A1 resolution constants (Claude's discretion; agent.py:419 anchor) ──────

#: Synthetic parent reserve. Half of the chat parent's effective working
#: budget: the chat `run_turn` call (cli.py:1695) passes no `token_budget`,
#: so `_run_turn_exec` uses the default ``token_budget: int = 60_000`` at
#: agent.py:419. M13 carves DEFAULT_PARENT_RESERVE from that 60_000, leaving
#: the parent ~30_000 for its own orchestration turn (D-05: "a parent reserve
#: is carved").
DEFAULT_PARENT_RESERVE: int = 30_000

#: Minimum allotment that still funds >=1 child iteration; must be
#: < reserve // expected_fanout so a first/second spawn is allowed but
#: unbounded recursion is denied. With DEFAULT_PARENT_RESERVE=30_000 this
#: allows up to floor(30_000/2_000)=15 concurrent first-level children before
#: denial; in the recursive case a child's sub-allocator reserve = that
#: child's allotment (D-07, slice-scoped), so depth is bounded naturally
#: without any depth/max_depth constant (M13-RESEARCH line 442; preserves
#: test_subagent_recursion.py — which only pins the agent.py:419-fed
#: subagents.py module, not this one).
DEFAULT_VIABLE_FLOOR: int = 2_000


class M13Allocator:
    """Even-split-of-reserve, in-memory, chat-turn-scoped budget allocator.

    NOT the O1 ``SessionTreeManager`` — LIFTED (copied, not imported) from
    O1-PATTERNS Pattern 2. The ``asyncio.Lock`` is what makes the
    check-and-allocate atomic on the single asyncio loop (children are
    ``create_task`` coroutines on it); ``asyncio.Lock`` not ``threading.Lock``
    (M13-RESEARCH line 307 — a thread lock would deadlock the loop).

    Invariant (asserted by ``TestNoOversell``): at all times, including under
    racing ``asyncio.gather`` allocations and double ``release``,
    ``sum(snapshot().values()) <= reserve``.

    Recursion bound: ``allocate`` returns ``None`` once the even slice falls
    below :attr:`VIABLE_FLOOR`. A child's sub-allocator is constructed with
    ``reserve = child_allotment`` (D-07, slice-scoped); each level only ever
    divides its OWN reserve, so the per-level invariant compounds to a global
    one and recursion terminates without any depth/max_depth constant.
    """

    #: Class-level viable floor (the recursion bound). Read off the class by
    #: ``TestNoOversell`` as ``M13Allocator.VIABLE_FLOOR``; also surfaced
    #: per-instance via the :attr:`viable_floor` property so a recursive
    #: sub-allocator can read it back (D-07).
    VIABLE_FLOOR: int = DEFAULT_VIABLE_FLOOR

    def __init__(self, *, reserve: int) -> None:
        self._reserve = reserve
        self._active: dict[str, int] = {}            # handle -> current allotment
        self._lock = asyncio.Lock()                  # D-06 single-loop guard
        self._credited_finished: set[str] = set()    # exactly-once rebalance guard

    @property
    def viable_floor(self) -> int:
        """The recursion-bound floor (the recursive sub-allocator reads this
        back per D-07)."""
        return self.VIABLE_FLOOR

    async def allocate(self, handle: str) -> int | None:
        """Race-safe check-and-allocate. Returns the granted allotment, or
        ``None`` when the even slice would fall below the viable floor (the
        D-07 denial — this, and only this, bounds recursion)."""
        async with self._lock:                       # D-06 race-safe check-and-allocate
            n = len(self._active) + 1                # include the new child
            even = self._reserve // n
            if even < self.VIABLE_FLOOR:             # D-07 viable-floor -> bounds recursion
                return None                          # caller emits <denied: ...>
            self._active[handle] = even
            self._rebalance_locked()                 # even-split existing too
            return self._active[handle]

    def release(self, handle: str) -> None:
        """Mark a finished child's slice free. Idempotent: a second
        ``release`` for the same handle is a no-op (MAG-04 exactly-once — the
        must-not-happen double-credit guard). The freed slice is folded into
        survivors on the next :meth:`rebalance` (or immediately here)."""
        if handle in self._credited_finished:        # MAG-04 exactly-once
            return
        self._credited_finished.add(handle)
        self._active.pop(handle, None)
        self._rebalance_locked()                      # freed slice -> survivors

    async def rebalance(self) -> None:
        """Re-even-split the reserve across the currently-active handles.

        Public async entry point (the locked ``TestEvenSplitRebalance`` /
        ``TestNoOversell`` call ``await allocator.rebalance()`` after a
        synchronous ``release``). Lock-guarded for parity with
        :meth:`allocate` under racing callers."""
        async with self._lock:
            self._rebalance_locked()

    def _rebalance_locked(self) -> None:
        """Even-split the reserve across active handles. Caller already holds
        (or does not need) the lock — the name encodes the precondition; do
        NOT re-acquire ``self._lock`` here."""
        if not self._active:
            return
        even = self._reserve // len(self._active)
        for h in self._active:
            self._active[h] = even
        # INVARIANT: sum(self._active.values()) == even * len <= reserve

    def snapshot(self) -> dict[str, int]:
        """Defensive copy of the live handle -> allotment map (consumed later
        by the panel BudgetMeter ticks)."""
        return dict(self._active)


@dataclass
class ChildHandle:
    """In-memory record of one spawned child, keyed by :attr:`id`.

    Mirrors the ``SubagentSpec`` dataclass idiom (subagents.py:22-27) but is
    NOT ``frozen`` — ``done``/``result`` mutate over the child's lifetime.
    """

    #: ``uuid.uuid4().hex[:12]`` handle (also the ``panel_id``, RESEARCH
    #: Pattern 1).
    id: str
    #: The detached ``asyncio.Task`` running the child ``run_turn`` (typed
    #: ``Any`` so M13-02 imports/awaits nothing; M13-03 populates it).
    task: Any = None
    #: Budget slice received from ``M13Allocator.allocate``.
    allotment: int = 0
    #: Lifecycle flag flipped by the gather path.
    done: bool = False
    #: Aggregated child output, set on completion by the gather path.
    result: str | None = None
    #: M13-03 ADDITIVE (D-03): per-child steer inbox. The parent enqueues
    #: ``subagent_steer`` guidance here; the child ``run_turn`` drains it at
    #: its loop boundary (agent.py:830). Defaulted so M13-02's 5-field
    #: construction stays valid; populated by ``subagent_spawn``.
    queue: Any = None
    #: M13-03 ADDITIVE: the ``SubAgentPanel`` parent_id (== :attr:`id`).
    panel_id: str = ""
    #: M13-03 ADDITIVE (D-07, slice-scoped): an optional per-child
    #: sub-allocator (``reserve = allotment``) the recursive wave (M13-05)
    #: hands children of children; unused by first-level fan-out here.
    sub_allocator: Any = None


class ChildRegistry:
    """Thin in-memory map of child id -> :class:`ChildHandle`, scoped to one
    chat turn (a fresh instance per fan-out; no disk, no global singleton —
    M13-CONTEXT D-02; O1 owns persistence)."""

    def __init__(self) -> None:
        self._children: dict[str, ChildHandle] = {}

    def add(self, handle: ChildHandle) -> None:
        self._children[handle.id] = handle

    def get(self, handle_id: str) -> ChildHandle | None:
        """Lookup by id; ``None`` for unknown ids (the future
        ``subagent_steer`` validates the target via this — steer to an
        unknown/finished child must be a no-op, T-M13 mis-steer)."""
        return self._children.get(handle_id)

    def active(self) -> list[ChildHandle]:
        """Handles whose ``done is False`` (the MAG-01 concurrency-overlap
        proof spies this; >=2 between spawn and gather)."""
        return [h for h in self._children.values() if h.done is False]

    def all(self) -> list[ChildHandle]:
        """Every handle regardless of ``done`` (the gather path iterates
        this)."""
        return list(self._children.values())


def new_handle_id() -> str:
    """Mint a child handle id with the project-wide scheme
    (``uuid.uuid4().hex[:12]`` — matches RunRecorder/SessionRecord,
    O1-PATTERNS lines 110-120). M13-03 mints ids via this helper so the
    scheme stays consistent; do NOT inline ``uuid.uuid4()`` at call sites."""
    return uuid.uuid4().hex[:12]

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


# ════════════════════════════════════════════════════════════════════════════
# M13-03 Wave 2A — non-blocking fan-out tools, panel bridge, attach entry,
# defensive orphan-teardown net. EXTENDS this M13-02 module (no recreation of
# M13Allocator / ChildHandle / ChildRegistry above; stdlib + in-repo only).
# ════════════════════════════════════════════════════════════════════════════

from pathlib import Path  # noqa: E402  (in-repo, additive — Analog A param shape)
from typing import Callable  # noqa: E402

from voss_runtime import EpisodicMemory, tool  # noqa: E402

from .agent import run_turn  # noqa: E402
from .permissions import PermissionGate  # noqa: E402
from .subagents import SubagentRegistry, agent_task  # noqa: E402
from .tools import ToolEntry, make_toolset  # noqa: E402


class PanelBridgeRenderer:
    """RESEARCH Pattern 4 — a thin renderer wrapper that pins a child's render
    calls to ONE ``SubAgentPanel`` (``panel_id``) and otherwise transparently
    delegates the full Renderer protocol to the base renderer so the child's
    ``run_turn`` drives it unchanged.

    Children are ``asyncio.create_task`` coroutines on the app's event loop
    (NOT threads): the base renderer's existing ``_post`` already handles
    main-thread vs off-loop posting (T-M13-05 — no ``to_thread``/``Thread``).
    """

    def __init__(self, base: Any, *, panel_id: str) -> None:
        self._base = base
        self._panel_id = panel_id

    def start_panel(self, *, name: str, budget_total: int) -> None:
        if hasattr(self._base, "show_subagent_start"):
            self._base.show_subagent_start(name, self._panel_id, budget_total)

    def step(self, line: str, used: int) -> None:
        # Calls the existing renderer.py:203 method name (the dead seam); the
        # renderer.py wiring itself is M13-04's TUI track, NOT touched here.
        if hasattr(self._base, "show_subagent_progress"):
            self._base.show_subagent_progress(self._panel_id, line, used)

    def end_panel(self, n_results: int = 1) -> None:
        if hasattr(self._base, "show_subagent_end"):
            self._base.show_subagent_end(self._panel_id, n_results)

    def __getattr__(self, attr: str) -> Any:
        # Everything not overridden above (the full Renderer protocol the
        # child run_turn calls) delegates to the base renderer unchanged.
        return getattr(self._base, attr)


def attach_multiagent_tools(
    tools: dict[str, ToolEntry],
    *,
    registry: SubagentRegistry,
    cwd: Path,
    renderer: Any,
    provider: Any,
    model: str | Callable[[], str],
    gate: PermissionGate,
    cognition: Any = None,
) -> Callable[[], Any]:
    """Analog A — register the four non-blocking M13 fan-out tools.

    SAME parameter list as ``subagents.attach_subagent_tool``. Closes over a
    fresh chat-turn-scoped :class:`ChildRegistry` + :class:`M13Allocator`
    (constructed with the M13-02 OQ-A1 ``DEFAULT_PARENT_RESERVE`` reserve;
    the viable floor is M13Allocator's ``VIABLE_FLOOR`` class attr) and the
    base renderer. Returns the ``_teardown_orphans`` callable so the cli wave
    (M13-06) can invoke it at chat-turn exit; ``subagent_gather`` is itself
    idempotently re-callable as a second safety net.

    Tool names are FINAL and distinct from ``SPAWN_TOOL_NAME="subagent_run"``
    (the back-compat anchor, not shadowed): ``subagent_spawn`` /
    ``subagent_steer`` / ``subagent_status`` / ``subagent_gather``.
    """
    base_renderer = renderer
    child_registry = ChildRegistry()
    # OQ-A1 reserve consumed from M13-02 (DEFAULT_PARENT_RESERVE=30_000);
    # the viable floor is M13Allocator.VIABLE_FLOOR (== DEFAULT_VIABLE_FLOOR
    # == 2_000), a class attr — M13Allocator takes ONLY reserve= (real API).
    allocator = M13Allocator(reserve=DEFAULT_PARENT_RESERVE)
    # handle id -> PanelBridgeRenderer (so gather/teardown can end_panel even
    # though M13-02's ChildHandle dataclass has no bridge field).
    bridges: dict[str, PanelBridgeRenderer] = {}

    def _resolve_task(agent: str, task: str) -> str:
        # Reuse the registered subagent role framing when the agent id is a
        # known SubagentSpec; else fall back to the raw task string.
        spec = registry.get(agent) if registry is not None else None
        return agent_task(spec, task) if spec is not None else task

    @tool(
        name="subagent_spawn",
        description=(
            "Spawn a sub-agent on a bounded task as a DETACHED concurrent "
            "child and return its handle immediately (does NOT wait for the "
            "child). Spawn several, then call subagent_gather once to collect "
            "all results. Returns '<denied: ...>' if the remaining budget is "
            "below the viable floor (no child is created)."
        ),
    )
    async def subagent_spawn(agent: str, task: str) -> str:
        handle = new_handle_id()
        allotment = await allocator.allocate(handle)
        if allotment is None:
            return (
                f"<denied: budget below viable floor — cannot spawn {agent!r}>"
            )
        queue: asyncio.Queue = asyncio.Queue()
        panel_id = handle
        bridge = PanelBridgeRenderer(base_renderer, panel_id=panel_id)
        bridge.start_panel(name=agent, budget_total=allotment)
        bridges[handle] = bridge
        picked_model = model() if callable(model) else model
        child_tools = make_toolset(cwd, renderer=bridge)
        coro = run_turn(
            _resolve_task(agent, task),
            tools=child_tools,
            cwd=cwd,
            renderer=bridge,
            model=picked_model,
            provider=provider,
            history=EpisodicMemory(capacity=20),
            permissions=gate,
            cognition=cognition,
            token_budget=allotment,
            steer_inbox=queue,
        )
        # RESEARCH Pattern 1 — the INVERSION of subagents.py:92 `await
        # run_turn(...)`: schedule, do NOT await the child here.
        t = asyncio.create_task(coro)
        child_registry.add(
            ChildHandle(
                id=handle,
                task=t,
                allotment=allotment,
                queue=queue,
                panel_id=panel_id,
                sub_allocator=M13Allocator(reserve=allotment),
            )
        )
        # Pitfall 1: the return string makes the pending-gather obligation
        # explicit so the parent LLM actually gathers.
        return (
            f"spawned {agent} handle={handle} budget={allotment} — "
            f"call subagent_gather when ready"
        )

    @tool(
        name="subagent_steer",
        description=(
            "Inject a mid-run course-correction into a still-running child by "
            "handle. NOTE: a steer only affects a child that runs another "
            "iteration; a child that has already decided it is done will not "
            "consume it. Unknown/finished handles are a safe no-op (no error)."
        ),
    )
    async def subagent_steer(handle: str, guidance: str) -> str:
        h = child_registry.get(handle)
        if h is None:  # T-M13-01 mis-steer — validate, never raise
            return f"<no-op: unknown handle {handle!r}>"
        if h.done:  # steer to a done child = no-op (D-04 / Pitfall 2)
            return f"<no-op: child {handle} already finished>"
        h.queue.put_nowait(guidance)
        return f"steered {handle}"

    @tool(
        name="subagent_status",
        description=(
            "Read-only status of spawned children: per-handle done flag, "
            "result, and current budget allotment. Pass a handle for one "
            "child, or omit to summarize all."
        ),
    )
    async def subagent_status(handle: str | None = None) -> str:
        snap = allocator.snapshot()
        if handle is not None:
            h = child_registry.get(handle)
            if h is None:
                return f"<no-op: unknown handle {handle!r}>"
            return (
                f"[{h.id}] done={h.done} allotment={snap.get(h.id, h.allotment)} "
                f"result={h.result!r}"
            )
        children = child_registry.all()
        active = len(child_registry.active())
        lines = [f"children={len(children)} active={active}"]
        for h in children:
            lines.append(
                f"[{h.id}] done={h.done} "
                f"allotment={snap.get(h.id, h.allotment)}"
            )
        return "\n".join(lines)

    @tool(
        name="subagent_gather",
        description=(
            "Join ALL outstanding spawned children concurrently, release each "
            "budget allotment, collapse each panel, and return every child's "
            "result aggregated into this turn. Idempotent: safe to call again."
        ),
    )
    async def subagent_gather() -> str:
        handles = child_registry.all()
        pending = [h for h in handles if h.task is not None and not h.done]
        tasks = [h.task for h in pending]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
        for h, r in zip(pending, results):
            allocator.release(h.id)  # sync release (real API) ...
            await allocator.rebalance()  # ... then async rebalance (MAG-04)
            if isinstance(r, Exception):
                h.done = True
                h.result = h.result or f"<error: {r}>"
            else:
                h.done = True
                h.result = h.result or (
                    r.final if hasattr(r, "final") else str(r)
                )
            br = bridges.get(h.id)
            if br is not None:
                br.end_panel(1)  # -> app.collapse_subagent (M9-08 restore)
        lines = [f"[{h.id}] {h.result}" for h in child_registry.all()]
        return "Aggregated sub-agent results:\n" + "\n".join(lines)

    async def _teardown_orphans() -> None:
        """Pitfall 1 / T-M13-02 — defensive net: cancel + release + collapse
        every un-gathered, not-finished child so no task/panel leaks if the
        parent turn exits without ``subagent_gather``. The cli-level
        invocation hook (chat-turn-exit) lands in M13-06; this is the
        callable it will invoke."""
        for h in child_registry.all():
            if h.done:
                continue
            t = h.task
            finished = t is not None and t.done()
            if t is not None and not finished:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
            allocator.release(h.id)
            await allocator.rebalance()
            h.done = True
            h.result = h.result or "<orphan: cancelled at parent turn exit>"
            br = bridges.get(h.id)
            if br is not None:
                br.end_panel(1)

    tools["subagent_spawn"] = ToolEntry(
        descriptor=subagent_spawn, is_mutating=True
    )
    tools["subagent_steer"] = ToolEntry(
        descriptor=subagent_steer, is_mutating=True
    )
    tools["subagent_status"] = ToolEntry(
        descriptor=subagent_status, is_mutating=False
    )
    tools["subagent_gather"] = ToolEntry(
        descriptor=subagent_gather, is_mutating=True
    )
    return _teardown_orphans

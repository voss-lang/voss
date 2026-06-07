"""Multi-agent-in-chat fan-out tools — V4-persisted (V8 VMAG-10/UNIFY/07/ROOT).

The four non-blocking fan-out tools (`subagent_spawn`/`steer`/`status`/`gather`),
the `ChildHandle` dataclass, the `ChildRegistry` in-memory child tracker, and the
`PanelBridgeRenderer`. V8 unified the budget+persistence backend onto the V4
`SessionTreeManager` (the prior in-memory even-split allocator was removed):
every spawn allocates a persisted `SessionTreeNode` child of the level's node,
and recursion builds a per-node child manager (reserve = `VIABLE_FLOOR`) so each
level divides only its own node's envelope. The chat-root manager is owned and
injected by `cli.py`.

Budget constants `DEFAULT_PARENT_RESERVE` (30_000, the chat-root reserve, sourced
from agent.py's `token_budget: int = 60_000` chat default) and `VIABLE_FLOOR`
(2_000) live here. No recursion-depth ceiling constant appears anywhere —
recursion is bounded SOLELY by the viable-floor denial in `subagent_spawn`
(budget-structural, preserves `test_subagent_recursion.py`).
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

#: V8 alias used by the inline even-split denial in ``subagent_spawn``. A
#: budget floor (the recursion bound) — NOT a depth constant; it stays in this
#: module and never appears in subagents.py (V8-RESEARCH Pitfall 6).
VIABLE_FLOOR: int = DEFAULT_VIABLE_FLOOR


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
    #: Budget slice (the child node's envelope limit) granted at spawn.
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
    #: DEPRECATED in V8 (kept only for positional back-compat; always set to
    #: None at construction). The recursive sub-allocator is now a per-node V4
    #: ``SessionTreeManager`` built in ``subagent_spawn``, not stored here.
    sub_allocator: Any = None
    #: V8 ADDITIVE: the persisted V4 ``SessionTreeNode`` for this child, used to
    #: ``finalize_node`` on gather/teardown. Last field (positional back-compat).
    node: Any = None


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
# Non-blocking fan-out tools, panel bridge, attach entry, defensive
# orphan-teardown net (extends the ChildHandle / ChildRegistry above;
# stdlib + in-repo only).
# ════════════════════════════════════════════════════════════════════════════

from pathlib import Path  # noqa: E402  (in-repo, additive — Analog A param shape)
from typing import Callable  # noqa: E402

from voss_runtime import EpisodicMemory, tool  # noqa: E402

from .agent import run_turn  # noqa: E402
from .permissions import PermissionGate  # noqa: E402
from .session_tree import (  # noqa: E402
    BudgetAllocationError,
    SessionTreeManager,
    SessionTreeNode,
    finalize_node,
)
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
    node_manager: SessionTreeManager | None = None,
) -> Callable[[], Any]:
    """Analog A — register the four non-blocking fan-out tools (V8 V4-backed).

    SAME parameter list as ``subagents.attach_subagent_tool``, plus the
    keyword-only ``node_manager`` — the V4 :class:`SessionTreeManager` that
    governs budget AND persistence for THIS nesting level. Closes over a fresh
    chat-turn-scoped :class:`ChildRegistry` and the base renderer.

    Each ``subagent_spawn`` allocates a persisted child node via
    ``node_manager.allocate_child`` and, for recursion, builds a per-node child
    ``SessionTreeManager`` (``reserve = VIABLE_FLOOR``) which it injects as the
    recursive ``node_manager=``. Every level only ever divides its OWN node's
    envelope, so the no-oversell invariant holds structurally and recursion is
    bounded SOLELY by the viable-floor denial (no depth/max_depth constant).
    The chat-root manager is owned and injected by ``cli.py`` — there is no
    in-module construction; ``node_manager`` is required in practice.

    Returns the ``_teardown_orphans`` callable so the cli can invoke it at
    chat-turn exit; ``subagent_gather`` is itself idempotently re-callable as a
    second safety net.

    Tool names are FINAL and distinct from ``SPAWN_TOOL_NAME="subagent_run"``
    (the back-compat anchor, not shadowed): ``subagent_spawn`` /
    ``subagent_steer`` / ``subagent_status`` / ``subagent_gather``.
    """
    base_renderer = renderer
    child_registry = ChildRegistry()
    # V4-backed default when no manager is injected (e.g. a direct
    # attach without a chat root). cli.py injects the real session-scoped
    # chat-root manager; this fallback keeps the tool surface usable
    # standalone. This is a real persisted V4 root, not the removed
    # in-memory even-split allocator.
    if node_manager is None:
        node_manager = SessionTreeManager(
            SessionTreeNode.create_root(cwd=cwd, limit=60_000),
            reserve=DEFAULT_PARENT_RESERVE,
            cwd=cwd,
        )
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
        # Inline even-split over the V4 node envelope. Compute the allotment
        # under the manager lock (Pitfall 1 — but do NOT hold it across the
        # allocate_child / create_task below).
        async with node_manager._lock:
            active_children = [
                c for c in node_manager._children if c.terminal_state is None
            ]
            allocated = sum(c.envelope["limit"] for c in active_children)
            available = (
                node_manager._root.envelope["limit"]
                - node_manager._reserve
                - allocated
            )
            # Divide by active+2 (not active+1) so the new child takes only a
            # SHARE of `available`, leaving headroom for further siblings. V4
            # node limits are immutable (unlike M13's rebalancing allocator), so
            # a greedy `// (active+1)` would let the first child swallow the
            # whole envelope and deny every later sibling. Reserving headroom
            # lets multiple sequential children coexist while no-oversell
            # (allocate_child's BudgetAllocationError) and the viable-floor
            # denial still hold.
            n = len(active_children) + 2
            allotment = available // n
        if allotment < VIABLE_FLOOR:  # viable-floor denial -> bounds recursion
            return (
                f"<denied: budget below viable floor — cannot spawn {agent!r}>"
            )
        # OUTSIDE the lock: allocate the persisted node. allocate_child re-checks
        # under its own lock and raises BudgetAllocationError — the authoritative
        # guard against the TOCTOU window (Pitfall 1).
        try:
            child_node = await node_manager.allocate_child(
                allotment, scope="chat", role=agent
            )
        except BudgetAllocationError as exc:
            return f"<denied: {exc}>"
        # Use the persisted node id as the handle so registry lookups, panel
        # keying, and finalize_node all align on one id.
        handle = child_node.id
        queue: asyncio.Queue = asyncio.Queue()
        panel_id = handle
        bridge = PanelBridgeRenderer(base_renderer, panel_id=panel_id)
        bridge.start_panel(name=agent, budget_total=allotment)
        bridges[handle] = bridge
        picked_model = model() if callable(model) else model
        child_tools = make_toolset(cwd, renderer=bridge)
        # Per-node recursion (Pitfall 5): the child becomes a parent via its OWN
        # V4 manager rooted at child_node (reserve == VIABLE_FLOOR), injected as
        # the recursive node_manager=. Each level divides only its own node's
        # envelope; grandchildren persist under child_node.id. Recursion is
        # bounded SOLELY by the viable-floor denial — no depth constant.
        child_manager = SessionTreeManager(
            child_node, reserve=VIABLE_FLOOR, cwd=cwd
        )
        attach_multiagent_tools(
            child_tools,
            registry=registry,
            cwd=cwd,
            renderer=bridge,
            provider=provider,
            model=model,
            gate=gate,
            cognition=cognition,
            node_manager=child_manager,
        )
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
                sub_allocator=None,
                node=child_node,
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
        snap = {c.id: c.envelope["limit"] for c in node_manager._children}
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
            if isinstance(r, Exception):
                h.done = True
                h.result = h.result or f"<error: {r}>"
                if h.node is not None:
                    finalize_node(
                        h.node, exit_reason="error", final=h.result, cwd=cwd
                    )
            else:
                h.done = True
                h.result = h.result or (
                    r.final if hasattr(r, "final") else str(r)
                )
                if h.node is not None:
                    finalize_node(
                        h.node, exit_reason="done", final=h.result, cwd=cwd
                    )
            node_manager.release_child(h.id)  # free budget for reallocation
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
            h.done = True
            h.result = h.result or "<orphan: cancelled at parent turn exit>"
            if h.node is not None:
                finalize_node(
                    h.node, exit_reason="interrupt", final=h.result, cwd=cwd
                )
            node_manager.release_child(h.id)
            br = bridges.get(h.id)
            if br is not None:
                br.end_panel(1)

    tools["subagent_spawn"] = ToolEntry(
        descriptor=subagent_spawn, is_mutating=True, group="review", scope_requirements=("review",)
    )
    tools["subagent_steer"] = ToolEntry(
        descriptor=subagent_steer, is_mutating=True, group="review", scope_requirements=("review",), is_stateful=True
    )
    tools["subagent_status"] = ToolEntry(
        descriptor=subagent_status, is_mutating=False, group="review", scope_requirements=("review",), is_stateful=True
    )
    tools["subagent_gather"] = ToolEntry(
        descriptor=subagent_gather, is_mutating=True, group="review", scope_requirements=("review",), is_stateful=True
    )
    return _teardown_orphans

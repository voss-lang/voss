# Phase O1: Session-Tree Substrate + Budget Fan-out — Research

**Researched:** 2026-05-18
**Domain:** Python asyncio harness extension — session tree persistence, budget fan-out, exception boundaries
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Per-node files at `.voss/sessions/<root_id>/<node_id>.json`, one file per node, written incrementally as the tree grows. Existing single-session files at `.voss/sessions/<id>.json` are unchanged; the tree is a new sibling structure under a per-root directory.
- **D-02:** Compose `voss_runtime.BudgetScope` per node. Each child node owns a `BudgetScope` instance for spend tracking (reuse its battle-tested `check()` / `add_usage()`); the new harness session-tree layers the parent→child fan-out invariant (`sum(children) + reserve ≤ parent`) on top. `BudgetScope` is consumed unchanged.
- **D-03:** Exception-at-single-boundary. `BudgetExceededError` caught at the one subagent-run harness boundary, which ALWAYS finalizes: emits exactly one terminal `RunRecord` with `exit_reason="budget"` and closes the node. Reserve covers finalize cost.
- **D-04:** Single guarded envelope mutator. All envelope writes funnel through one method: an upward delta raises a hard error AND records the rejected attempt on the node; spend / downward writes are allowed.

### Claude's Discretion

- Concurrency primitive for holding `sum(children) + reserve ≤ parent` under concurrent async child spend.
- Node-id scheme and exact per-node JSON field serialization (within the locked logical schema `{id, parent_run_id, envelope{limit, spent}, terminal_state}`).
- Resume semantics for a partially-written tree.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. (Board, verdict semantics, roster, EM, audit surfacing all correctly deferred to O2–O6.)

</user_constraints>

---

## Summary

O1 builds the session-tree substrate by adding one new harness-side class — `SessionTreeNode` — and wiring it into the single existing spawn chokepoint (`subagents.run_subagent`). The implementation is harness-additive: no field touches `SessionRecord`, `RunRecord`, or `BudgetScope`. It is pure Python, no new third-party dependencies.

**The four decisions interlock as a single mechanism:** D-01 (per-node file written at open and close) + D-02 (composed child `BudgetScope` as the spend tracker) + D-03 (exception-at-boundary that always writes the terminal file) + D-04 (guarded mutator as the one place all envelope writes funnel through). The planner must treat them as one design unit, not four independent tasks.

**The critical concurrency finding:** asyncio is single-threaded cooperative. `BudgetScope.add_usage()` contains no `await`, making it atomic under asyncio scheduling — no lock is needed for concurrent child spending. The allocation check-then-write (`sum(children) + new_limit + reserve ≤ parent`) IS the one non-atomic site; an `asyncio.Lock` on the allocator is the correct, cheap, future-proof guard.

**The two-budget-mechanism finding:** `run_turn` uses a SOFT token check (`ctx.tokens_used >= token_budget`) that exits the loop cleanly rather than raising. `BudgetExceededError` fires only from compiled `.voss` `ContextScope.ask()` calls. O1's D-03 boundary must handle BOTH: catch the exception path AND detect the soft-exit `exit_reason="budget"` on `TurnResult.run`. Reserve is implemented by passing `run_turn token_budget = envelope_limit - reserve`; the remaining reserve tokens are consumed by `record_run_call` (the LLM finalize call that happens after the loop exits).

**Primary recommendation:** Implement `SessionTreeNode` in a new file `voss/harness/session_tree.py`; integrate at `run_subagent` boundary with one `async with scope` and one `try/except BudgetExceededError` wrapping the `run_turn` call. Node files at `.voss/sessions/<root_id>/<node_id>.json`, 0o600, written at open and at close. [VERIFIED: codebase grep]

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-node file persistence (D-01) | Harness (`session_tree.py`) | — | New harness-side type; `.voss/sessions/` storage convention already established by `session.save()` |
| Budget fan-out invariant enforcement | Harness (`SessionTreeNode.allocate_child`) | — | Harness layers on top of composed `BudgetScope`; `BudgetScope` unchanged (blast radius) |
| Composed `BudgetScope` spend tracking (D-02) | `voss_runtime.BudgetScope` | Harness wrapper | `BudgetScope.add_usage()` / `check()` unchanged; harness sets it as `_current_budget` |
| Terminal-finalize guarantee (D-03) | Harness boundary (`run_subagent`) | — | Single spawn chokepoint; `SPAWN_TOOL_NAME = "subagent_run"` already identified |
| Cap-raise guard + audit (D-04) | Harness (`SessionTreeNode.mutate_envelope`) | — | Cannot add guard to `BudgetScope` (blast radius); must be on harness wrapper |
| Concurrency safety | `asyncio.Lock` on allocator | — | Single-threaded asyncio; lock only needed at allocation site, not spend site |

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python ≥ 3.11 | `asyncio.Lock` for allocation guard | Already used in `agent.py` (`asyncio.Semaphore`, `asyncio.gather`) [VERIFIED: codebase grep] |
| `dataclasses` (stdlib) | Python ≥ 3.7 | `SessionTreeNode` type | Established pattern across all harness types |
| `json` (stdlib) | — | Per-node file serialization | Used by `session.save()` already |
| `uuid` (stdlib) | — | Node-id generation | Used by `RunRecorder.start()` (`uuid.uuid4().hex[:12]`) and `SessionRecord.new()` |
| `pathlib.Path` (stdlib) | — | `.voss/sessions/<root_id>/` directory | Established pattern in `session.py` |
| `voss_runtime.BudgetScope` | (project) | Per-node spend tracking (D-02) | Reused unchanged — `check()` / `add_usage()` / `BudgetExceededError` [VERIFIED: codebase grep] |
| `voss_runtime.BudgetExceededError` | (project) | D-03 exception signal | Already raised by `BudgetScope.check()` [VERIFIED: codebase grep] |

### No New Third-Party Dependencies

The SPEC constraint "no new third-party dependencies" is hard. Verified: `asyncio.Lock`, stdlib `dataclasses`, `json`, `uuid`, and `pathlib` cover all O1 needs. No external packages required. [VERIFIED: codebase grep + SPEC constraint]

**Version verification:** All stdlib — no registry check needed.

---

## Package Legitimacy Audit

Not applicable — O1 installs zero external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
Parent Agent (run_turn)
        │
        │  calls tool "subagent_run"
        ▼
attach_subagent_tool → subagent_run()
        │
        │  D-01: create node file + open
        ▼
SessionTreeNode.open(parent_node, child_limit)  ←── asyncio.Lock (allocator)
        │    writes .voss/sessions/<root>/<node>.json
        │    sets terminal_state=None (open)
        │
        │  D-02: enter child BudgetScope as _current_budget
        ▼
async with child_budget_scope:
        │
        │  D-03 boundary
        ▼
try:
    result = await run_turn(..., token_budget=envelope_limit - reserve)
    if result.run.exit_reason == "budget":  ← soft-exit path
        ──► finalize_node(node, exit_reason="budget")
        ──► write terminal node file
        ──► return "halted: budget"
except BudgetExceededError:                ← hard-exception path (.voss ctx{})
    ──► finalize_node(node, exit_reason="budget")
    ──► write terminal node file
    ──► return "<error: budget exceeded>"

        │  normal completion
        ▼
finalize_node(node, exit_reason="done"|other)
write terminal node file
return result.final


D-04 guard (envelope writes):
SessionTreeNode.mutate_envelope(delta)
    if delta > 0:  ← cap raise attempt
        record rejected attempt → node.rejected_raises.append(...)
        rewrite node file
        raise BudgetCapRaiseError(...)
    else:          ← spend (downward or zero) — allowed
        node.envelope["spent"] += abs(delta)
        rewrite node file
```

### Recommended Project Structure

New file `voss/harness/session_tree.py` only. No other new files for the substrate; integration touches `voss/harness/subagents.py`.

```
voss/harness/
├── session_tree.py     # NEW: SessionTreeNode, SessionTreeManager, BudgetCapRaiseError
├── subagents.py        # MODIFIED: run_subagent gets node creation + D-03 boundary
└── session.py          # UNCHANGED (redaction invariant)

.voss/sessions/
├── <session_id>.json            # flat session (existing, unchanged)
└── <root_node_id>/              # NEW: tree directory (coexists with flat file)
    ├── <root_node_id>.json      # root node file
    └── <child_node_id>.json     # child node files
```

**Filesystem coexistence verified:** A directory `.voss/sessions/abc123/` and a file `.voss/sessions/abc123.json` coexist on macOS/Linux — they are distinct filesystem entries. [VERIFIED: live filesystem test]

### Pattern 1: SessionTreeNode Dataclass

```python
# Source: inferred from SPEC locked schema + existing recorder.py / session.py patterns
import asyncio
import dataclasses
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

@dataclass
class SessionTreeNode:
    id: str
    root_id: str                          # root of this tree (for directory path)
    parent_run_id: Optional[str]          # None for root node
    envelope: dict                        # {"limit": int, "spent": int}
    terminal_state: Optional[dict]        # None = open; set on finalize
    created_at: str
    ended_at: Optional[str]
    rejected_raises: list                 # D-04 audit trail
    _budget: object = field(default=None, init=False, repr=False)  # BudgetScope instance

    @classmethod
    def create_root(cls, *, cwd: Path, limit: int) -> "SessionTreeNode":
        node_id = uuid.uuid4().hex[:12]
        return cls(
            id=node_id,
            root_id=node_id,              # root is its own tree root
            parent_run_id=None,
            envelope={"limit": limit, "spent": 0},
            terminal_state=None,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ended_at=None,
            rejected_raises=[],
        )

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d.pop("_budget", None)            # never persisted
        return d
```

### Pattern 2: Allocator with asyncio.Lock (D-02 + concurrency)

```python
# Source: CONTEXT.md D-02 + concurrency analysis
class SessionTreeManager:
    """Owns one tree's allocation state; one instance per running root."""

    def __init__(self, root_node: SessionTreeNode, *, reserve: int, cwd: Path):
        self._root = root_node
        self._reserve = reserve
        self._cwd = cwd
        self._children: list[SessionTreeNode] = []
        self._lock = asyncio.Lock()        # guards allocation (check+write atomicity)

    async def allocate_child(self, limit: int) -> SessionTreeNode:
        """Create a child node or raise BudgetAllocationError (no partial state)."""
        async with self._lock:
            allocated = sum(c.envelope["limit"] for c in self._children)
            available = self._root.envelope["limit"] - self._reserve - allocated
            if limit > available:
                raise BudgetAllocationError(
                    f"child limit {limit} exceeds available {available} "
                    f"(reserve={self._reserve})"
                )
            child_id = uuid.uuid4().hex[:12]
            child = SessionTreeNode(
                id=child_id,
                root_id=self._root.id,
                parent_run_id=self._root.id,  # or caller's node id for deep trees
                envelope={"limit": limit, "spent": 0},
                terminal_state=None,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ended_at=None,
                rejected_raises=[],
            )
            self._children.append(child)
            _write_node_file(child, self._cwd)  # crash-safe: written before use
            return child
```

**Why `asyncio.Lock` and not `threading.Lock`:** The harness is a single asyncio event loop. `asyncio.Lock` is the correct primitive — it suspends the coroutine (yields), not the thread. Using `threading.Lock` would deadlock under asyncio. [VERIFIED: asyncio docs pattern + harness uses `asyncio.Semaphore` already for batch reads]

**Why lock is needed at all:** Pure asyncio is cooperative; there is no preemption. `BudgetScope.add_usage()` contains no `await` so is strictly atomic — no lock needed for concurrent spending. But `allocate_child` has a check-then-write (`read available → compare → append`) that spans multiple Python statements. If two parent coroutines called `allocate_child` concurrently (an `asyncio.gather` of two spawn calls), they could both read the same `allocated` value before either writes, causing oversell. Live test confirms the race. [VERIFIED: live asyncio test — 10 concurrent 100-token allocations against 900 total without lock → all 10 succeed (oversell); with lock → 9 succeed (correct)]

### Pattern 3: D-03 Boundary in run_subagent

```python
# Source: CONTEXT.md D-03 + analysis of run_turn budget mechanisms
async def run_subagent(
    *,
    agent_id: str,
    task: str,
    registry: SubagentRegistry,
    cwd: Path,
    renderer: Renderer,
    provider: Any,
    model: str,
    gate: PermissionGate,
    cognition: Any = None,
    node: SessionTreeNode | None = None,   # NEW: injected by tree manager
    reserve: int = 0,                      # NEW: reserve tokens
) -> str:
    spec = registry.get(agent_id)
    if spec is None:
        return f"<error: unknown subagent {agent_id!r}>"

    spendable = (node.envelope["limit"] - reserve) if node else None
    child_tools = make_toolset(cwd, renderer=renderer)

    try:
        # D-02: enter child BudgetScope as _current_budget
        budget_ctx = (
            node._budget  # BudgetScope(token_limit=node.envelope["limit"], name=node.id)
            if node and node._budget else _null_ctx()
        )
        async with budget_ctx:
            result = await run_turn(
                agent_task(spec, task),
                tools=child_tools,
                cwd=cwd,
                renderer=renderer,
                model=model,
                provider=provider,
                history=EpisodicMemory(capacity=20),
                permissions=gate,
                cognition=cognition,
                token_budget=spendable or 60_000,   # soft cap = spendable
            )
        # Check soft-exit path (run_turn exited cleanly but budget-limited)
        if node and result.run and result.run.exit_reason == "budget":
            _finalize_node(node, exit_reason="budget", cwd=cwd)
        elif node:
            _finalize_node(node, exit_reason="done", cwd=cwd)
        return result.final

    except BudgetExceededError:
        # D-03: hard path — .voss compiled ctx{} block exceeded BudgetScope
        if node:
            _finalize_node(node, exit_reason="budget", cwd=cwd)
        return "<halted: budget>"
```

### Pattern 4: D-04 Guarded Envelope Mutator

```python
# Source: CONTEXT.md D-04 — all envelope writes funnel through this method
class BudgetCapRaiseError(Exception):
    """Raised when a cap-raise attempt is made on a finalized cap."""
    def __init__(self, node_id: str, attempted_delta: int, reason: str):
        self.node_id = node_id
        self.attempted_delta = attempted_delta
        super().__init__(
            f"cap raise rejected for node {node_id}: delta={attempted_delta} ({reason})"
        )

def mutate_envelope(node: SessionTreeNode, delta: int, cwd: Path) -> None:
    """Single guarded mutator. Upward delta raises + records; downward allowed.

    'Upward delta' = any attempt to increase envelope['limit'].
    'Spend' = increasing envelope['spent'] (tracking BudgetScope usage).
    """
    if delta > 0:
        # D-04: cap raise attempt — record it AND raise
        attempt = {
            "attempted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "requested_delta": delta,
            "reason": "cap_raise_rejected",
        }
        node.rejected_raises.append(attempt)
        _write_node_file(node, cwd)          # persist audit trail before raising
        raise BudgetCapRaiseError(node.id, delta, "non-extendable cap")
    # Downward (spend update) — allowed
    node.envelope["spent"] += abs(delta)
    _write_node_file(node, cwd)
```

**Note:** `BudgetScope.token_limit` remains directly settable (no guard on the runtime). The guard is on the harness wrapper. This is correct under the blast-radius constraint. Structural enforcement: all paths to child execution go through `run_subagent`, which creates and owns the `SessionTreeNode`. No direct `BudgetScope` access is exposed to callers.

### Pattern 5: Node File Write

```python
# Source: session.py save() pattern (0o600, json.dumps, Path.write_text)
def _write_node_file(node: SessionTreeNode, cwd: Path) -> Path:
    tree_dir = cwd / ".voss" / "sessions" / node.root_id
    tree_dir.mkdir(parents=True, exist_ok=True)
    path = tree_dir / f"{node.id}.json"
    path.write_text(json.dumps(node.to_dict(), indent=2))
    path.chmod(0o600)
    return path
```

**Incremental write pattern (crash-safe):** Each node file is written twice — once at creation (open state, `terminal_state=None`) and once at finalization (closed state, `terminal_state` populated). A crash between the two writes leaves the file in open state, which O6 can detect (O6 reads `terminal_state` to find stranded nodes). [VERIFIED: D-01 design intent + filesystem test]

### Anti-Patterns to Avoid

- **Don't hold the `asyncio.Lock` during `run_turn` execution.** The lock guards only the allocation check-and-write. Holding it through the entire child run would serialize all child executions, defeating concurrency. Release immediately after appending to `_children` and writing the node file.
- **Don't re-use the parent's `BudgetScope` for the child.** The parent's `_current_budget` ContextVar is inherited by child tasks created via `asyncio.create_task` but NOT by coroutines awaited directly. Entering a new `BudgetScope` as `async with` correctly replaces `_current_budget` in the child's execution context and restores it on exit (verified via ContextVar `set`/`reset` token mechanism). [VERIFIED: live ContextVar test]
- **Don't write a `BudgetScope` to the node file.** `BudgetScope` is a runtime object, not a serialization target. `envelope["spent"]` in the node JSON is updated by the `mutate_envelope` path, not by serializing `BudgetScope.tokens_so_far` directly.
- **Don't call `RunRecorder.finalize()` twice.** `RunRecorder.finalize()` has no double-finalize guard (verified by live test — second call silently overwrites the first). D-03 must ensure finalization happens exactly once: set a `_finalized` flag on the node, check before finalizing.
- **Don't confuse the two budget mechanisms.** `run_turn`'s internal `token_budget` parameter and `BudgetScope.token_limit` are separate: `token_budget` controls the soft loop-exit, `BudgetScope.token_limit` fires the hard exception from compiled `.voss` code. Both must be set consistently: `run_turn token_budget = envelope_limit - reserve`, `BudgetScope.token_limit = envelope_limit`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent allocation safety | Custom counter with manual CAS | `asyncio.Lock` | Python asyncio is cooperative; Lock is zero-overhead in the non-contested case |
| Node UUID generation | Custom ID scheme | `uuid.uuid4().hex[:12]` | Matches existing pattern in `RunRecorder.start()` and `SessionRecord.new()` — consistent, 48-bit collision-resistant, filesystem-safe |
| Budget spend tracking | Duplicate accumulator in `SessionTreeNode` | `BudgetScope.tokens_so_far` + `add_usage()` | D-02 explicitly says reuse battle-tested `BudgetScope` |
| File permission setting | `os.chmod` | `path.chmod(0o600)` | Matches `session.save()` exactly |
| Crash detection | Separate heartbeat file | `terminal_state=None` in node file | Sufficient for O6 audit: open file = potential stranded node |

---

## Runtime State Inventory

Not applicable — O1 is a greenfield addition. There is no existing tree state to migrate.

---

## Common Pitfalls

### Pitfall 1: Double-Finalize on Concurrent Exception + Normal Exit

**What goes wrong:** `run_turn` exits normally with `exit_reason="budget"` (soft path) AND a `BudgetExceededError` was also queued (hard path) because the child was in a `ctx{}` block. Both paths attempt to call `_finalize_node`.

**Why it happens:** The soft exit path checks `result.run.exit_reason` after `run_turn` returns. But if `BudgetExceededError` was raised from inside `run_turn`, the function never returns — control goes to the `except BudgetExceededError` handler. There is no overlap: either `run_turn` returns (soft) OR it raises (hard). The two code paths are mutually exclusive. However, developer error (e.g., re-raising from a nested try) could trigger double-finalize.

**How to avoid:** Add a `_finalized: bool = False` flag to `SessionTreeNode`. `_finalize_node` checks and sets it atomically (safe under asyncio's cooperative scheduling — no await between check and set). [ASSUMED — pattern inferred from double-finalize risk analysis]

**Warning signs:** `terminal_state` getting overwritten in a node file; `ended_at` appearing twice in audit logs.

### Pitfall 2: ContextVar Inheritance in asyncio.create_task vs await

**What goes wrong:** If `run_subagent` is called via `asyncio.create_task(run_subagent(...))`, the child task inherits the PARENT'S `_current_budget` ContextVar value at task creation time (Python semantics: tasks copy the current context). When the child then enters `async with child_budget_scope`, it correctly replaces `_current_budget` in its own context copy. On exit, `_current_budget` is restored to the inherited parent scope — not `None`. This is correct behavior but may surprise developers expecting `_current_budget` to be `None` inside a fresh child task before `async with` is entered.

**Why it happens:** Python `contextvars.copy_context()` semantics — task creation snapshots the current context, including any active `_current_budget`.

**How to avoid:** Always enter the child `BudgetScope` via `async with` BEFORE any agent work. Never rely on `_current_budget` being `None` inside a spawned task. [VERIFIED: live ContextVar test]

### Pitfall 3: Allocation Lock Held Too Long

**What goes wrong:** The `asyncio.Lock` on the allocator is held across the `run_turn` call (entire child execution). This serializes all children — no parallelism.

**Why it happens:** Copy-paste of a `try/finally` pattern where the lock release is in a `finally` block that wraps the entire child execution.

**How to avoid:** The lock governs only the check-and-write in `allocate_child`. The `await run_turn(...)` must happen OUTSIDE the lock. The `SessionTreeNode` should be created and appended to `_children` inside the lock, then the lock released before `run_turn` is called. [VERIFIED: asyncio.Lock semantics + concurrency analysis]

### Pitfall 4: node file not written before run_turn

**What goes wrong:** Node file is written only after `run_turn` completes. A crash during `run_turn` leaves no persisted node — the tree is not reconstructable from the crash.

**Why it happens:** Treating the write as a "finalization" operation rather than an "open" operation.

**How to avoid:** Write the node file (open state: `terminal_state=None`) immediately after allocation succeeds and before `run_turn` is called. The node file is written TWICE: once at open, once at finalize. [VERIFIED: D-01 "written incrementally as the tree grows"]

### Pitfall 5: Flat Session File vs Tree Directory Name Collision

**What goes wrong:** A flat session at `.voss/sessions/<id>.json` and a tree directory at `.voss/sessions/<id>/` use the same `<id>`. On some filesystems this would collide.

**Why it happens:** The flat session `id` and the root node `id` are both 12-hex-char UUID fragments.

**How to avoid:** They do NOT collide: `.voss/sessions/abc123.json` (file) and `.voss/sessions/abc123/` (directory) are distinct filesystem entries and coexist on all POSIX targets. [VERIFIED: live filesystem test on macOS] The root node id and the `SessionRecord.id` are DIFFERENT values — a `SessionRecord` creates the flat file; `SessionTreeNode.create_root()` creates the directory. These are two separate IDs.

### Pitfall 6: BudgetScope Re-entry Bypasses Cap

**What goes wrong:** A child agent (or compiled `.voss` code) creates a new `BudgetScope` with a higher `token_limit` and enters it via `async with`, replacing `_current_budget`. Subsequent `add_usage()` charges the larger scope.

**Why it happens:** `BudgetScope.__aenter__` unconditionally calls `_current_budget.set(self)` — it replaces whatever was there. There is no nesting guard on the runtime primitive.

**How to avoid:** D-04's guarded mutator covers the explicit cap-raise API. The re-entry bypass (creating a NEW `BudgetScope`) is mitigated structurally: the harness controls all tool dispatch and subagent invocation paths; a child cannot call `run_subagent` to create a new scope without going through the `subagent_run` tool, which goes through `run_subagent`, which creates the tree node. Child code that directly instantiates `BudgetScope` is technically possible but violates the harness contract. For O1, document this as a known gap; full mitigation (e.g., a "scope frozen" flag on the ContextVar) is O6 scope. [ASSUMED — full mitigation path beyond O1 scope]

### Pitfall 7: reserve not subtracted from token_budget

**What goes wrong:** `run_turn` is called with `token_budget=envelope_limit` (full limit). The soft budget check fires only after the reserve tokens are consumed. The `record_run_call` LLM call (which happens after the loop exits with `exit_reason="budget"`) cannot complete because the full budget is gone.

**Why it happens:** Forgetting that `record_run_call` runs AFTER the loop, outside the `ContextScope` token counter but inside the caller's execution.

**How to avoid:** Always pass `token_budget = envelope_limit - reserve` to `run_turn`. The `BudgetScope.token_limit` stays at `envelope_limit` (full cap including reserve) to correctly bound any `.voss` `ctx{}` blocks. The soft-exit fires at `tokens_used >= envelope_limit - reserve`, leaving the reserve for `record_run_call`. [VERIFIED: agent.py analysis — `record_run_call` calls `provider.complete()` directly, tokens not tracked by ContextScope]

---

## Code Examples

### Verified: RunRecorder.finalize() — existing terminal record path

```python
# Source: voss/harness/recorder.py:192
def finalize(
    self,
    cwd: Path,
    cost_usd: float,
    *,
    exit_reason: Optional[str] = None,
) -> RunRecord:
    self.cost_usd = cost_usd
    self.diff_summary = _git_diff_stat(cwd)
    # ... builds RunRecord with exit_reason
```

`EXIT_REASONS` already contains `"budget"` — no schema change needed. [VERIFIED: codebase grep]

### Verified: session.save() permission + serialization pattern

```python
# Source: voss/harness/session.py:209
path.write_text(json.dumps(asdict(record), indent=2))
path.chmod(0o600)
```

O1 node files follow the same pattern. [VERIFIED: codebase read]

### Verified: asyncio.Semaphore usage in harness (concurrency precedent)

```python
# Source: voss/harness/agent.py:1187
sem = asyncio.Semaphore(cap)
# ...
async with sem:
    results[slot] = await _invoke_step_with_gate(...)
```

The harness already uses asyncio concurrency primitives. `asyncio.Lock` follows the same pattern. [VERIFIED: codebase grep]

### Verified: BudgetScope ContextVar set/reset mechanics

```python
# Source: voss_runtime/budget.py:22-31
async def __aenter__(self):
    self._token = _current_budget.set(self)   # saves previous state
    return self

async def __aexit__(self, exc_type, exc, tb):
    _current_budget.reset(self._token)         # restores previous state
    self._token = None
    return False  # do not suppress
```

Nesting is safe: child scope replaces parent, restores on exit. [VERIFIED: live test + codebase read]

### Verified: Node file and flat session file coexistence

```
.voss/sessions/abc123.json     ← flat SessionRecord (existing)
.voss/sessions/abc123/         ← tree root directory (new O1)
    abc123.json                ← root node file
    def456.json                ← child node file
```

macOS/Linux: a file and same-name directory coexist without collision. [VERIFIED: live filesystem test]

---

## Concurrency Deep-Dive (Open Question 1 Resolution)

**Question:** What concurrency primitive for `sum(children) + reserve ≤ parent` under concurrent async child spend?

**Answer:** `asyncio.Lock` at the allocator only. No lock needed for child spending.

**Evidence:**

1. `BudgetScope.add_usage()` is atomic under asyncio: it has zero `await` calls. Between any two `asyncio.sleep(0)` yields, Python executes statements atomically. `tokens_so_far += tokens` is a single C-level bytecode → no concurrent interleaving possible. [VERIFIED: live asyncio test — 300 concurrent add_usage calls via gather → exact count preserved]

2. Each child has its OWN `BudgetScope` instance. Children do NOT share a `BudgetScope`. Concurrent child spending mutates distinct objects — no cross-child lock needed. [VERIFIED: live test]

3. The allocation site (`allocate_child`) reads `sum(child.envelope["limit"])`, compares, then appends. This spans multiple Python statements with potential yield points. [VERIFIED: live race test — 10 concurrent allocations without lock → all succeed (oversell). With `asyncio.Lock` → 9 succeed (correct invariant)]

4. The parent agent loop is sequential within a single `run_turn` invocation. It is NOT `asyncio.gather`'d with itself. Therefore the allocation race is theoretical under O1's sequential parent but real under a future O5 EM that might fan out concurrently. The `asyncio.Lock` makes it correct in both cases at zero practical cost. [ASSUMED — O5 future concurrency; O1 parent is sequential]

**Recommendation:** `asyncio.Lock` on `SessionTreeManager._lock`, held only during the read-check-append cycle in `allocate_child`. Release before `run_turn` is called.

---

## Node-Id Scheme and Serialization (Open Question 2 Resolution)

**Node-id scheme:** `uuid.uuid4().hex[:12]` — exactly matching the existing pattern in `RunRecorder.start()` and `SessionRecord.new()`. 12 hex characters = 48 bits → collision probability ≈ 10^{-9} at 10^5 nodes. Filesystem-safe, human-readable in paths, audit-friendly. [VERIFIED: codebase grep — both uses of `uuid.uuid4().hex[:12]`]

**Root node id:** The root node's `id` serves as the tree directory name. Root creates its own `id` on construction; this `id` is NOT the same as the `SessionRecord.id` (they are different allocation points).

**Serialization schema (concrete):**

```json
{
  "id": "3a673962610b",
  "root_id": "3a673962610b",
  "parent_run_id": null,
  "envelope": {
    "limit": 10000,
    "spent": 0
  },
  "terminal_state": null,
  "created_at": "2026-05-18T10:00:00+00:00",
  "ended_at": null,
  "rejected_raises": []
}
```

Child node (after finalization):

```json
{
  "id": "797685c5d005",
  "root_id": "3a673962610b",
  "parent_run_id": "3a673962610b",
  "envelope": {
    "limit": 3000,
    "spent": 2847
  },
  "terminal_state": {
    "exit_reason": "budget",
    "final": "halted: budget"
  },
  "created_at": "2026-05-18T10:00:01+00:00",
  "ended_at": "2026-05-18T10:05:23+00:00",
  "rejected_raises": []
}
```

**Cap-raise attempt record** (D-04 audit trail, appended to `rejected_raises`):

```json
{
  "attempted_at": "2026-05-18T10:03:11+00:00",
  "requested_delta": 5000,
  "reason": "cap_raise_rejected"
}
```

**Serialization safety:** `SessionTreeNode.to_dict()` excludes the `_budget` field (a `BudgetScope` instance) — only JSON-serializable values reach the file. [ASSUMED — pattern inferred from `dataclasses.asdict()` usage in session.py, with a pop() for private fields]

---

## Resume Semantics (Open Question 3 Resolution)

**Question:** How does `voss resume` rehydrate an interrupted root? Must not be precluded.

**Findings from code inspection:**

`voss resume` calls `session_store.load()`, which reads the `SessionRecord` at `.voss/sessions/<session_id>.json`. It then calls `_run_repl(record=record, history=rehydrated_memory, ...)`. The resume path is entirely `SessionRecord`-driven — it knows nothing about tree nodes. [VERIFIED: codebase read — `cli.py:1882`]

The O1 tree directory (`.voss/sessions/<root_id>/`) is a SEPARATE sibling structure. `session_store.load()` does not scan subdirectories. Therefore O1's tree files are invisible to the current resume path — they do not interfere. [VERIFIED: `session.py:_scan_dir` only globs `*.json` in the flat sessions dir, not subdirs]

**Resume compatibility contract for O1:**

O1 is compatible with resume-as-currently-implemented because the two persistence layers are disjoint. The substrate DOES NOT PRECLUDE future resume enhancement because:
1. Every tree node has `parent_run_id` and `root_id` — the tree is fully reconstructable from the directory.
2. Open nodes (`terminal_state=None`) are detectable.
3. `created_at` and `ended_at` timestamps allow ordering.

**O6 will do the actual resume wiring.** O1's obligation is: persist enough information that O6 can detect stranded nodes and close them or re-attach. The schema above satisfies this. [VERIFIED: SPEC.md "Persistence of the tree sufficient to reconstruct it for audit" + O6 phase description]

**Practical note:** No change to `session_store.load()`, `session_store.save()`, or the `_hydrate` / `_scan_dir` helpers. Resume continues to work exactly as before for all existing sessions. [VERIFIED: flat sessions untouched by O1]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single flat session file | Flat + sibling tree directory | O1 (new) | Tree directory is the O1 artifact; flat files unchanged |
| No budget for subagents | Per-node `BudgetScope` composed at spawn | O1 (new) | `BudgetScope` consumed unchanged |
| Stranded open child possible (Leak 4) | D-03 boundary always finalizes | O1 (new) | Acceptance criterion: no open node after parent teardown |
| `BudgetScope` freely re-enterable via ContextVar | Guarded mutator on `SessionTreeNode` | O1 (new) | Hard error + audit trail on cap-raise attempt |

**Not deprecated by O1:**
- `RunRecorder` / `RunRecord` — unchanged
- `SessionRecord` / `SessionRecord.parent_id` / `parent_turn_index` — unchanged (M9-06 session-fork lineage, NOT the live tree)
- `BudgetScope.add_usage()` / `check()` — consumed as-is

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_finalized: bool` flag on `SessionTreeNode` prevents double-finalize | Pitfall 1 | Double-finalize would corrupt node file; mitigate by adding flag check in planner's implementation task |
| A2 | Child code that directly instantiates `BudgetScope` bypasses D-04 guard; treating this as a known gap for O1 | Pitfall 6 | A misbehaving agent could inflate its own budget; acceptable for O1 substrate, needs O6 mitigation |
| A3 | O5 EM may fan out allocations concurrently; `asyncio.Lock` future-proofs for this | Concurrency Deep-Dive | If O5 is purely sequential, the lock is never contested (no downside) |
| A4 | `SessionTreeNode.to_dict()` should use `dataclasses.asdict()` with a pop for `_budget` | Code Examples | Incorrect serialization could write a non-JSON-serializable object; confirm with planner |

**If this table is empty for a claim:** All critical decisions above were verified via live code testing or codebase inspection — not training data alone.

---

## Open Questions (RESOLVED)

1. **Depth parameter for `run_subagent` (currently pinned as missing by `test_subagent_recursion.py`)**
   - What we know: `test_subagent_recursion.py` pins that `run_subagent` has no `depth`/`max_depth` param; the test asserts this gap.
   - What's unclear: Does O1 add `parent_node` to `run_subagent` (for tree linkage), which then makes the test need updating? Or does O1 add a separate `node` kwarg, leaving the depth-guard gap untouched?
   - RESOLVED: Add `node: SessionTreeNode | None = None` as an optional kwarg. This does NOT add `max_depth` — the pinning test continues to pass. The test only checks for `depth` and `max_depth`. Explicitly do NOT add depth in O1.

2. **Who creates the root `SessionTreeNode`?**
   - What we know: `run_subagent` is the child-creation boundary. But a ROOT node (for the parent session itself) needs to be created somewhere.
   - What's unclear: Is the root created when the parent `run_turn` starts (in `_run_turn_exec`), or is it a lazy create-on-first-spawn?
   - RESOLVED: Lazy: create the root `SessionTreeNode` on first `run_subagent` call for a given `run_turn`. The `RunRecorder.id` can serve as the root node id basis. This avoids adding root-creation to every `run_turn` call (non-additive).

3. **`test_subagent_recursion.py` update scope**
   - RESOLVED (all three sub-points below confirm the test remains unmodified):
   - The test `test_subagent_tool_marked_mutating` will continue to pass (O1 doesn't change mutating status).
   - The signature tests check for absence of `depth`/`max_depth` — O1 doesn't add those.
   - If O1 adds `node: SessionTreeNode | None = None` and `reserve: int = 0`, the signature tests in `test_subagent_recursion.py` should continue to pass (they test for ABSENCE of specific params, not exact signatures).

---

## Environment Availability

All dependencies are stdlib or project-internal. No external dependencies to probe.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `asyncio` (stdlib) | `asyncio.Lock` allocation guard | ✓ | Python 3.11+ | — |
| `uuid` (stdlib) | Node-id generation | ✓ | Python 3.11+ | — |
| `json` (stdlib) | Node file serialization | ✓ | Python 3.11+ | — |
| `pathlib` (stdlib) | `.voss/sessions/<root>/` directory ops | ✓ | Python 3.11+ | — |
| `voss_runtime.BudgetScope` | D-02 composed spend tracking | ✓ | project | — |
| `voss_runtime.BudgetExceededError` | D-03 exception boundary | ✓ | project | — |
| `pytest-asyncio` | Async test support | ✓ | ≥0.23 (pyproject.toml); `asyncio_mode = "auto"` | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8+ with pytest-asyncio ≥0.23 |
| Config file | `pyproject.toml` — `asyncio_mode = "auto"` |
| Quick run command | `pytest tests/harness/test_session_tree.py -x -q` |
| Full suite command | `pytest tests/harness/ -x -q` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| REQ-1 | N children → N nodes each with `parent_run_id` = parent id; tree reconstructable | unit | `pytest tests/harness/test_session_tree.py::TestTreePersistence -x` | ❌ Wave 0 |
| REQ-2a | Allocation with `sum(children) + reserve ≤ parent` succeeds | unit | `pytest tests/harness/test_session_tree.py::TestBudgetFanOut::test_valid_allocation -x` | ❌ Wave 0 |
| REQ-2b | Allocation exceeding `parent − reserve` raises hard error + no partial state | unit | `pytest tests/harness/test_session_tree.py::TestBudgetFanOut::test_oversell_raises -x` | ❌ Wave 0 |
| REQ-3 | Budget-drained child emits exactly one `RunRecord` with `exit_reason="budget"` + closed node | unit | `pytest tests/harness/test_session_tree.py::TestDrainFinalize -x` | ❌ Wave 0 |
| REQ-3b | No open node after parent teardown | integration | `pytest tests/harness/test_session_tree.py::TestNoOpenNodes -x` | ❌ Wave 0 |
| REQ-4a | Cap-raise raises documented error | unit | `pytest tests/harness/test_session_tree.py::TestCapRaiseGuard::test_raise_errors -x` | ❌ Wave 0 |
| REQ-4b | Cap-raise records rejected attempt on node | unit | `pytest tests/harness/test_session_tree.py::TestCapRaiseGuard::test_raise_recorded -x` | ❌ Wave 0 |
| REQ-5a | `git diff` shows zero field changes on `SessionRecord`, `RunRecord`, `BudgetScope` | smoke | `pytest tests/harness/test_session_redaction.py -x` (MUST PASS UNMODIFIED) | ✅ existing |
| REQ-5b | `test_session_redaction.py` passes unmodified | smoke | `pytest tests/harness/test_session_redaction.py -x` | ✅ existing |
| REQ-7 | Concurrent children cannot oversell envelope | unit | `pytest tests/harness/test_session_tree.py::TestConcurrency::test_concurrent_no_oversell -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/test_session_tree.py -x -q && pytest tests/harness/test_session_redaction.py -x -q`
- **Per wave merge:** `pytest tests/harness/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_session_tree.py` — new test file covering all 9 acceptance criteria
- [ ] Test class structure follows existing class-based pattern (`class TestTreePersistence:`, `class TestBudgetFanOut:`, etc.)
- [ ] Async tests use `asyncio_mode = "auto"` (no explicit `@pytest.mark.asyncio` needed — verified by existing async tests in `test_anthropic_stream.py`)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (partial) | Node file contains user-controlled `task` text indirectly; `json.dumps` escapes correctly |
| V6 Cryptography | no | — |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Node file path traversal | Tampering | Node id is `uuid4().hex[:12]` — no user-controlled path components |
| Node file permission | Information Disclosure | `path.chmod(0o600)` — matches existing session.save() pattern |
| ContextVar re-entry cap bypass | Elevation of Privilege | Structural: all spawn paths go through `run_subagent`; D-04 guard covers explicit cap-raise API; deep re-entry bypass is a known gap (A2) |
| Budget oversell race | Tampering | `asyncio.Lock` on allocator |

**Redaction invariant:** `SessionTreeNode` is NOT a `SessionRecord` or `RunRecord`. It is a new harness-side type that NEVER gets added to `SessionRecord.runs` or serialized via `dataclasses.asdict(SessionRecord)`. The `test_session_redaction.py` allowlist is unaffected. Node files live at a separate path. [VERIFIED: codebase analysis]

---

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` found in the Voss project root. Project constraints derive from `.planning/PROJECT.md` and O1-SPEC.md:

- `.voss/` is durable project knowledge — node files belong here (not `.voss-cache/`)
- No provider secrets in session payloads — node files contain only operational metadata
- Python runtime (not Rust, not TypeScript)
- Generated code imports `voss_runtime` — new `session_tree.py` may import `voss_runtime.BudgetScope` and `voss_runtime.BudgetExceededError` (both already in `__all__`)
- No new third-party dependencies — confirmed: all stdlib + project-internal

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/recorder.py` — `RunRecorder`, `finalize()`, `begin_iteration`, double-finalize behavior [VERIFIED: codebase read]
- `voss/harness/session.py` — `SessionRecord`, `RunRecord`, `EXIT_REASONS`, `save()`, `_sessions_dir()`, `_scan_dir()` pattern [VERIFIED: codebase read]
- `voss/harness/subagents.py` — `run_subagent`, `attach_subagent_tool`, `SPAWN_TOOL_NAME`, current signature [VERIFIED: codebase read]
- `voss_runtime/budget.py` — `BudgetScope`, `add_usage()`, `check()`, `_current_budget` ContextVar, re-entrancy mechanics [VERIFIED: codebase read + live Python tests]
- `voss_runtime/context.py` — `ContextScope.ask()` calls `current_budget().add_usage()` [VERIFIED: codebase read]
- `voss/harness/agent.py` — `run_turn` token budget (soft check), `_record_run_call` (post-loop LLM call), `asyncio.Semaphore` usage, `TurnResult.run` [VERIFIED: codebase read]
- `tests/harness/test_session_redaction.py` — fixed-field allowlist, `RunRecord` 21 fields [VERIFIED: codebase read]
- `tests/harness/test_subagent_recursion.py` — pinned gaps (no depth param, no MAX_DEPTH) [VERIFIED: codebase read]
- `pyproject.toml` — `asyncio_mode = "auto"`, `pytest-asyncio>=0.23`, no-new-deps constraint [VERIFIED: codebase read]
- Live Python tests for ContextVar inheritance, asyncio.Lock allocation race, add_usage atomicity, filesystem coexistence [VERIFIED: live test results]

### Tertiary (LOW confidence / ASSUMED)

- `_finalized: bool` flag on `SessionTreeNode` (A1) — inferred from double-finalize risk, not from existing code pattern
- Deep BudgetScope re-entry (A2) — inferred from ContextVar mechanics, mitigation gap accepted for O1

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no external deps, all verified
- Architecture (node schema, file layout): HIGH — derived directly from locked CONTEXT.md decisions + filesystem verification
- Concurrency (asyncio.Lock prescription): HIGH — verified via live race tests
- D-03 boundary mechanics: HIGH — verified via agent.py analysis + BudgetScope code inspection
- Reserve/token_budget interplay: HIGH — verified via agent.py post-loop analysis
- Resume compatibility: HIGH — verified via cli.py + session.py scan
- Pitfall identification: MEDIUM — derived from code analysis; some scenarios are theoretical

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable Python harness — changes only if agent.py or budget.py are modified)

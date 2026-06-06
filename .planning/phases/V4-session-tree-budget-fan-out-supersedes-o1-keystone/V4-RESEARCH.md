# Phase V4: Session Tree + Budget Fan-out (supersedes O1 — KEYSTONE) — Research

**Researched:** 2026-06-06
**Domain:** Python asyncio harness extension — pre-emptive spend guard, all-reason finalize wiring, scope/role schema, CLI subgroup, consolidated JSON export
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from V4-CONTEXT.md)

### Locked Decisions

- **Delta-only on shipped O1.** Verify/regress TREE-01..06; build only the gaps (enforcement, finalize wiring, scope/role, CLI, export). O1 marked superseded/absorbed (bookkeeping); O1 artifacts retained as reference design.
- **Pre-emptive spend guard (VTREE-04 — keystone).** A node refuses to **begin** an iteration/call when `spent >= limit` — halts **before** the breaching spend, finalizes `exit_reason="budget"`. Guard does not predict per-call cost; enforcement is at the iteration/call boundary. Keep existing `allocate_child` invariant. Guard correctness under concurrent child spend — reuse `asyncio.Lock`, no oversell race.
- **Always-finalize (VTREE-07).** Guarantee `finalize_node` works for ALL `EXIT_REASONS`. Wire so **error, timeout, and budget** termination paths each emit exactly one terminal node. `killed`/`blocked` emitters deferred to V5/V7.
- **Scope + role metadata (VTREE-08).** Add `scope` + `role` to `SessionTreeNode` — additive, nullable. Populate at spawn when available; null when unknown. Full population via V7 EM dispatch (later). Both present in the export.
- **CLI (VTREE-09).** `voss session tree <root_id>` reads persisted nodes, prints tree: id, parent, envelope limit/spent, terminal_state, scope, role. Exits 0 for known root; non-zero + stderr for unknown.
- **Export (VTREE-10).** API + reachable via CLI: single JSON object per `root_id` — all nodes, parent linkage, envelopes, terminal states, scope/role. Round-trips the persisted tree. ADE rendering deferred to V11.
- **Depth-1 only.** No recursive multi-level fan-out (child-of-child) in V4 — recursion to V8 (MAG-07).
- **Schema freeze (carried from O1).** No field added/removed on `SessionRecord`, `RunRecord`, or `voss_runtime.BudgetScope`. `tests/harness/test_session_redaction.py` must pass **unmodified**.
- **No new third-party dependencies.** All stdlib + project-internal.
- **Tests follow `tests/harness/` conventions** — pytest, class-based, `asyncio_mode = "auto"`, no new deps.

### Claude's Discretion

- Exact placement/shape of the pre-emptive guard call site within the iteration loop (subagent/harness boundary).
- Internal structure of the export function and CLI rendering format (tree-print style).
- Test organization within `tests/harness/` conventions.
- How `scope` is derived from allocation context.

### Deferred Ideas (OUT OF SCOPE)

- Recursive multi-level fan-out (child-of-child) — V8 (MAG-07).
- ADE rendering of the tree — V11.
- Full scope/role population via EM dispatch — V7.
- `killed`/`blocked` terminal emitters — V5/V7.
- Board columns/WIP/gates/verdicts — V5; reviewers — V6.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VTREE-01 | `SessionTreeNode` persists + round-trips; extended additively with `scope`/`role` | Existing shipped implementation verified; additive extension pattern in `_hydrate_node` documented |
| VTREE-02 | `SessionTreeManager` verified + extended for spend-guard + export hooks | Existing `allocate_child`/`get_node`/`_lock` verified functional; extension points identified |
| VTREE-03 | Persistence: N children → N node files; tree reconstructable from disk alone | Existing `_write_node_file` / `.voss/sessions/<root>/<node>.json` pattern verified |
| VTREE-04 | Fan-out invariant holds + pre-emptive spend guard: node cannot begin a call when `spent >= limit` | Guard insertion point in `run_subagent` identified; `asyncio.Lock` coverage confirmed; corrected pattern documented |
| VTREE-05 | Non-extendable cap (verify): `BudgetCapRaiseError` on `delta > 0` | Already implemented and tested; verify-only |
| VTREE-06 | Rejected-raise audit (verify): `rejected_raises[]` appended + persisted on rejection | Already implemented and tested; verify-only |
| VTREE-07 | Always-finalize: `finalize_node` works for ALL `EXIT_REASONS`; error/timeout/budget paths each emit exactly one terminal node | Gap in current `run_subagent`: only `BudgetExceededError` + budget soft-exit caught; bare `Exception` + `asyncio.TimeoutError` not handled; `try/except/finally` pattern documented |
| VTREE-08 | `scope` + `role` additive nullable fields on `SessionTreeNode`; populated at spawn when available | `_hydrate_node` setdefault back-compat pattern confirmed; V3 spec absent today so `role=None` at spawn; `scope` from allocation context — planner's discretion |
| VTREE-09 | `voss session tree <root_id>` CLI: exits 0 + tree print for known root; non-zero + stderr for unknown | Click subgroup pattern confirmed; `session_group` does NOT yet exist (conflict analysis performed); new `session_group` + `tree` subcommand pattern documented |
| VTREE-10 | Consolidated JSON export: one JSON object per `root_id` aggregating all per-node files; round-trips | Per-node file layout confirmed; aggregation via `glob("*.json")` + `_hydrate_node` pattern; export API + CLI wiring documented |

</phase_requirements>

---

## Summary

V4 is a delta on a fully shipped O1 substrate (`voss/harness/session_tree.py`, 192 lines). The five gaps are: (1) a pre-emptive spend guard that blocks a subagent call at the iteration boundary when `spent >= limit`, (2) wiring error/timeout/budget termination paths to always-finalize, (3) additive `scope`/`role` nullable fields on `SessionTreeNode`, (4) a `voss session tree <root_id>` CLI subcommand, and (5) a consolidated JSON export API + CLI hook.

The keystone correctness fix (VTREE-04) has a specific integration point: the guard must be inserted at the top of `run_subagent`, **before** `async with scope:` and before any spend-incurring call. The existing `asyncio.Lock` in `SessionTreeManager.allocate_child` guards allocation (no-oversell); V4 adds a per-node envelope check at call entry. Because `asyncio.Lock` is only held during allocation (not during `run_turn`), the guard check itself is not under the lock — but the check is a simple read (`spent >= limit`) on the node's own envelope before the call, which is safe under asyncio's cooperative scheduling (no preemption between the check and the call start that would interleave another coroutine's spend on the same node).

The always-finalize gap (VTREE-07) is a missing `except Exception` + `except asyncio.TimeoutError` branch in `run_subagent`. The current implementation catches only `BudgetExceededError`. A `try/except/finally` boundary that calls `finalize_node` in the `finally` block (relying on `_finalized` idempotence) is the cleanest pattern. The `_finalized` flag is already on `SessionTreeNode` and `finalize_node` checks it — so a `finally: finalize_node(node, exit_reason=..., cwd=cwd)` pattern is safe.

The CLI gap (VTREE-09/10) uses Click's `@click.group` + `@group.command` pattern, consistent with `inspect_group`, `skill_group`, `principles_group` and others. A new `session_group` is needed (there is currently only a flat `sessions_cmd` list command, NOT a `session` group). The group is added to `AGENT_COMMANDS` and registered via the existing `register()` function.

**Primary recommendation:** Insert the pre-emptive guard at the top of `run_subagent` (before `async with scope:`), add a `try/except Exception/finally` shell for VTREE-07, extend `SessionTreeNode` additively for VTREE-08, add a `@click.group("session")` with a `tree` subcommand for VTREE-09, and add `export_tree(root_id, cwd)` as a pure function callable from both the API and the CLI for VTREE-10.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pre-emptive spend guard (VTREE-04) | `voss/harness/subagents.py` — `run_subagent` | `voss/harness/session_tree.py` — `SessionTreeNode.envelope` | Guard lives at the one call boundary that all subagent execution goes through; envelope state lives on the node |
| All-reason finalize wiring (VTREE-07) | `voss/harness/subagents.py` — `run_subagent` try/finally | `voss/harness/session_tree.py` — `finalize_node` | `run_subagent` is the single spawn boundary; `finalize_node` is already idempotent |
| Scope/role node metadata (VTREE-08) | `voss/harness/session_tree.py` — `SessionTreeNode` + `_hydrate_node` | `voss/harness/subagents.py` — `allocate_child` call site | Schema lives on the node; population happens at spawn in subagents or manager |
| `voss session tree` CLI (VTREE-09) | `voss/harness/cli.py` — new `session_group` | `voss/harness/session_tree.py` — `export_tree` | CLI module owns command registration; tree reading is a `session_tree.py` function |
| Consolidated JSON export (VTREE-10) | `voss/harness/session_tree.py` — new `export_tree` function | `voss/harness/cli.py` | Pure function in `session_tree.py`; CLI calls it; reachable independently |
| Fan-out invariant (VTREE-02/04) | `SessionTreeManager.allocate_child` + `asyncio.Lock` | — | Already shipped; lock guards check-then-append; no change needed |
| Schema freeze / redaction invariant | `tests/harness/test_session_redaction.py` (gate) | `session.py` | No `SessionRecord`/`RunRecord`/`BudgetScope` field changes |

---

## Standard Stack

### Core (no new dependencies — all shipped or stdlib)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.11+ | `asyncio.Lock` for allocation guard | Already used; existing pattern [VERIFIED: subagents.py, session_tree.py] |
| `dataclasses` (stdlib) | Python 3.11+ | `SessionTreeNode` field extension | Existing pattern for all harness types [VERIFIED: session_tree.py] |
| `json` (stdlib) | — | Node file serialization + export | Existing pattern [VERIFIED: session_tree.py] |
| `pathlib.Path` (stdlib) | — | `.voss/sessions/<root>/` glob + node reading | Existing pattern [VERIFIED: session_tree.py `_write_node_file`] |
| `click` (project dep) | ≥8.0 | CLI subgroup + command | Existing pattern; all CLI commands use click [VERIFIED: cli.py] |
| `voss.harness.session.EXIT_REASONS` | (project) | Validate `exit_reason` in `finalize_node` | Already imported in `session_tree.py` [VERIFIED: session_tree.py line 17] |

### No New Third-Party Dependencies

SPEC constraint: hard. Verified: all V4 needs are covered by stdlib + existing project deps. [VERIFIED: codebase inspection]

---

## Package Legitimacy Audit

Not applicable — V4 installs zero external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
run_subagent(node, reserve, ...)
         │
         │ [VTREE-04 PRE-EMPTIVE GUARD — NEW V4]
         │ if node and node.envelope["spent"] >= node.envelope["limit"]:
         │     finalize_node(node, exit_reason="budget")
         │     return "<halted: budget — envelope exhausted>"
         │
         │ spendable = node.envelope["limit"] - reserve (if node)
         ▼
try:
    async with scope (BudgetScope or nullcontext):
        result = await run_turn(..., token_budget=spendable)
    ┌─────────────────────────────────────────────────────┐
    │ Soft-exit path: result.run.exit_reason == "budget"  │─→ finalize(budget)
    │ Normal path: exit_reason != "budget"                │─→ finalize(done)
    └─────────────────────────────────────────────────────┘
except BudgetExceededError:         [already wired in O1]
    finalize_node(exit_reason="budget")
except Exception as exc:            [NEW V4 — VTREE-07]
    finalize_node(exit_reason="error")
    re-raise (or return error envelope)
except asyncio.TimeoutError:        [NEW V4 — VTREE-07]
    finalize_node(exit_reason="timeout")
finally:                            [safety net — VTREE-07]
    if node and not node._finalized:
        finalize_node(exit_reason="error")  # fallback for uncaught paths

─────────────────────────────────────────────────────────────

SessionTreeNode (V4 schema — additive)
    id, root_id, parent_run_id
    envelope: {limit, spent}
    terminal_state: {exit_reason, final} | None
    created_at, ended_at
    rejected_raises[]
    transitions[], retry_notes[]    [O3 additions]
    scope: str | None               [NEW V4 — VTREE-08]
    role: str | None                [NEW V4 — VTREE-08]

─────────────────────────────────────────────────────────────

export_tree(root_id, cwd) → dict    [NEW V4 — VTREE-10]
    glob(".voss/sessions/<root_id>/*.json")
    _hydrate_node(data) for each file
    return {"root_id": ..., "nodes": [...]}

─────────────────────────────────────────────────────────────

CLI: voss session tree <root_id>    [NEW V4 — VTREE-09]
    → calls export_tree()
    → known root: print tree, exit 0
    → unknown root: stderr message, exit 1
```

### Recommended Project Structure

Only surgical additions to existing files:

```
voss/harness/
├── session_tree.py      # MODIFIED: add scope/role to SessionTreeNode,
│                        #   setdefault in _hydrate_node, add export_tree()
├── subagents.py         # MODIFIED: add pre-emptive guard at top of run_subagent,
│                        #   add except Exception + asyncio.TimeoutError + finally
└── cli.py               # MODIFIED: add session_group + tree_cmd, add to AGENT_COMMANDS

tests/harness/
└── test_session_tree.py # MODIFIED: add new test classes for V4 gaps
                         #   (guard, finalize-all-reasons, scope/role, export, CLI)
```

No new files required. (The planner may choose to split tests into a separate file — within discretion.)

---

## Focus Area 1: Pre-emptive Spend Guard (VTREE-04)

### Guard Insertion Point

The guard must sit at the **top of `run_subagent`** — specifically, immediately before `async with scope:` begins. This is the one call site where all subagent execution passes through. [VERIFIED: subagents.py lines 211–285]

Current `run_subagent` signature (already has `node` and `reserve`):
```python
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
    node: SessionTreeNode | None = None,
    reserve: int = 0,
) -> str:
```

**Guard placement (V4 addition — lines ~225–230 after the `spec is None` early return):**
```python
    # [VTREE-04] Pre-emptive spend guard: refuse to begin a call when envelope exhausted.
    if node is not None and node.envelope["spent"] >= node.envelope["limit"]:
        finalize_node(node, exit_reason="budget", final="<halted: budget — envelope exhausted>", cwd=cwd)
        return "<halted: budget — envelope exhausted>"
```

**Why here:** The guard is after the `spec is None` check (which is not a spend event) and before `async with scope:` (which enters the BudgetScope context). It halts before ANY spend can occur. [VERIFIED: subagents.py structure — lines 225–228 are the early-return guard for unknown agent; the spend boundary starts at line 235]

### Concurrency Analysis

**The guard check is safe without a lock.** Under asyncio's cooperative scheduling, no preemption happens between `node.envelope["spent"] >= node.envelope["limit"]` (the check) and returning (before any spend). A concurrent child's spend on the same node would require an `await` yield between the check and the return, which does not occur. [ASSUMED — based on asyncio cooperative scheduling analysis; the same reasoning verified for `add_usage()` atomicity in O1-RESEARCH.md]

**The allocator's `asyncio.Lock` guards over-allocation, not over-spending.** The lock in `allocate_child` prevents two parent coroutines from simultaneously allocating more children than the parent budget allows. It does NOT guard individual spend events on already-allocated children, because each child has its own envelope. The pre-emptive guard on a child's envelope is per-node and per-call — no cross-node locking needed. [VERIFIED: session_tree.py lines 165–192 — lock scope is allocation check-then-append only]

**Post-call spend via `mutate_envelope` remains unguarded at the mutex level.** `mutate_envelope(node, delta=-N, cwd=cwd)` (which increments `spent`) is called after `run_turn` completes. The guard fires BEFORE `run_turn`, so a concurrent sibling spending its own envelope does not race with this node's guard check. [ASSUMED — derived from the single-child-per-call asyncio execution model; concurrent siblings have distinct node objects]

**The pre-emptive semantic is coarse-grained by design.** The guard checks `spent >= limit` at call start — if `spent` equals exactly `limit` from a prior call, the next call is blocked. This may block even if the next call would use zero tokens (e.g., a trivially short response). The SPEC explicitly accepts this: "the guard does not predict exact per-call output cost." [VERIFIED: V4-SPEC.md line 47]

### Who Calls `mutate_envelope`?

Currently: `mutate_envelope` is only called from `tests/harness/test_session_tree.py` (directly in tests) and is exported for callers. It is NOT called inside `run_subagent` today — the iteration loop's token usage does not flow back through `mutate_envelope` automatically. The `run_turn` call uses `BudgetScope.add_usage()` internally to track soft-budget consumption. **V4 must decide: when does `spent` get updated on the node?**

The current code in `run_subagent` does NOT call `mutate_envelope` after `run_turn` — `spent` stays 0 unless the caller does it manually. The pre-emptive guard at `spent >= limit` will never fire unless something increments `spent`. The planner must wire `mutate_envelope(node, delta=-tokens_used, cwd=cwd)` after `run_turn` to update `node.envelope["spent"]` with the actual usage. The source of `tokens_used` is `result.run.iteration_total_prompt_tokens + result.run.iteration_total_completion_tokens` (or equivalent from `RunRecord`). [VERIFIED: subagents.py — no `mutate_envelope` call; session_tree.py — `mutate_envelope` is a standalone function]

**This is the critical wiring the pre-emptive guard depends on.** Without updating `spent` after each `run_turn`, the guard is inert.

---

## Focus Area 2: All-Reason Finalize Wiring (VTREE-07)

### Current State

`run_subagent` catches only `BudgetExceededError` (lines 277–285). All other exceptions propagate uncaught, leaving the node open (no `finalize_node` call). Error paths (network errors, provider errors, unexpected exceptions) and timeout paths (`asyncio.TimeoutError` from an outer timeout wrapper) both produce open nodes. [VERIFIED: subagents.py lines 235–285]

### All EXIT_REASONS in the Frozen Set

```python
# session.py line 74-76
EXIT_REASONS: frozenset[str] = frozenset(
    {"done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout", "killed"}
)
```
[VERIFIED: voss/harness/session.py lines 74–78]

V4 wires: `error` is NOT in `EXIT_REASONS`. Looking at the SPEC: "error, timeout, and budget termination paths each emit exactly one terminal node" — but `finalize_node` validates `exit_reason ∈ EXIT_REASONS`, which does NOT include `"error"`. **This is a gap to resolve.** Options:

1. Add `"error"` to `EXIT_REASONS` in `session.py` — additive frozenset change, no field change on any record.
2. Map exception paths to `"interrupt"` (already in `EXIT_REASONS`, semantically "abnormal termination").
3. Map exception paths to a new reason if `"error"` is added.

Option 1 is cleanest for clarity. Option 2 avoids touching `session.py`. The planner must decide — this is Claude's discretion. If `"error"` is not added, exception paths should finalize with `exit_reason="interrupt"`. [ASSUMED — the SPEC says "error" termination but does not mandate the string literal; `finalize_node` validates against `EXIT_REASONS`]

### Recommended try/except/finally Shape

```python
# run_subagent body (V4 addition):
    # [VTREE-04] Pre-emptive guard
    if node is not None and node.envelope["spent"] >= node.envelope["limit"]:
        finalize_node(node, exit_reason="budget", final="<halted: budget>", cwd=cwd)
        return "<halted: budget — envelope exhausted>"

    try:
        async with scope:
            result = await run_turn(...)
        # update spent from result
        if node:
            tokens_used = _extract_tokens(result)  # from RunRecord
            mutate_envelope(node, delta=-tokens_used, cwd=cwd)
        # check soft-exit
        if node and result.run and result.run.exit_reason == "budget":
            finalize_node(node, exit_reason="budget", final=result.final, cwd=cwd)
        elif node:
            finalize_node(node, exit_reason="done", final=result.final, cwd=cwd)
        return result.final

    except BudgetExceededError:
        if node:
            finalize_node(node, exit_reason="budget", final="<halted: budget>", cwd=cwd)
        return "<halted: budget>"

    except asyncio.TimeoutError:                        # [NEW V4 — VTREE-07]
        if node:
            finalize_node(node, exit_reason="timeout", final="<halted: timeout>", cwd=cwd)
        raise  # re-raise — caller decides whether to swallow

    except Exception as exc:                            # [NEW V4 — VTREE-07]
        if node:
            # "error" or "interrupt" depending on planner's EXIT_REASONS decision
            finalize_node(node, exit_reason="interrupt", final=f"<error: {exc}>", cwd=cwd)
        raise

    finally:                                            # [safety net — VTREE-07]
        if node and not node._finalized:
            finalize_node(node, exit_reason="interrupt", final="<uncaught>", cwd=cwd)
```

**The `finally` safety net:** Because `finalize_node` is idempotent (`_finalized` flag checked first), a `finally` block calling `finalize_node` is harmless if one of the `except` handlers already finalized. This guarantees no node is left open regardless of unexpected code paths. [VERIFIED: session_tree.py lines 105–123 — `if node._finalized: return`]

**`killed` and `blocked` are deferred.** The `finalize_node` function already accepts them (they are in `EXIT_REASONS`). V4 just proves the mechanism — V5/V7 wire the emitters. [VERIFIED: session.py EXIT_REASONS includes "killed"]

---

## Focus Area 3: Additive Scope/Role Schema (VTREE-08)

### SessionTreeNode Extension

Add two nullable fields **with defaults** so they remain optional at construction:

```python
@dataclass
class SessionTreeNode:
    id: str
    root_id: str
    parent_run_id: Optional[str]
    envelope: dict
    terminal_state: Optional[dict]
    created_at: str
    ended_at: Optional[str]
    rejected_raises: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    retry_notes: list = field(default_factory=list)
    # V4 VTREE-08: nullable metadata — populated at spawn when available.
    scope: Optional[str] = None
    role: Optional[str] = None
    _budget: Optional[BudgetScope] = field(default=None, init=False, repr=False)
    _finalized: bool = field(default=False, init=False, repr=False)
```

`scope` and `role` have `None` defaults so existing `create_root()` and child-creation in `allocate_child` continue to work without changes. [VERIFIED: session_tree.py dataclass field ordering rules — fields with defaults must come after fields without]

### Back-Compat `_hydrate_node` Update

Add two `setdefault` lines:

```python
def _hydrate_node(data: dict) -> SessionTreeNode:
    kept = {k: v for k, v in data.items() if k in _NODE_FIELDS}
    kept.setdefault("rejected_raises", [])
    kept.setdefault("transitions", [])
    kept.setdefault("retry_notes", [])
    kept.setdefault("scope", None)    # V4: pre-V4 files → null
    kept.setdefault("role", None)     # V4: pre-V4 files → null
    return SessionTreeNode(**kept)
```

`_NODE_FIELDS` is rebuilt from `dataclasses.fields(SessionTreeNode)` at module load, so once the fields are added to the dataclass, `_NODE_FIELDS` automatically includes them. [VERIFIED: session_tree.py lines 86 — `_NODE_FIELDS = {f.name for f in dataclasses.fields(SessionTreeNode)}`]

### Schema Key Impact on Existing Tests

`test_session_tree.py` line 26–40 defines `_NODE_JSON_KEYS` as a frozen set. Adding `scope` and `role` to `SessionTreeNode` means `to_dict()` will now include them, breaking `test_node_keys_exact` which asserts `set(root.to_dict().keys()) == _NODE_JSON_KEYS`. **The V4 plan must update `_NODE_JSON_KEYS` to include `"scope"` and `"role"`.**

This is expected — V4 is extending the node schema. The test correctly guards against accidental schema changes; V4's explicit schema extension requires updating the guard. [VERIFIED: test_session_tree.py lines 26–40, 172–177]

### Population at Spawn

**Where scope/role are available at spawn:**
- `SubagentSpec.scope: TeamRoleScope | None` — already a field on `SubagentSpec` (line 41 of `subagents.py`). This is the agent's scope.
- `SubagentSpec.model`, `SubagentSpec.role_prompt` — available but not a "role" in the VTREE-08 sense.
- No V3 spec shipped yet — `role` will be `None` at spawn in V4.

The `allocate_child` call in any future orchestrator could pass `scope=str(spec.scope)` and `role=None` at spawn. The planner must decide whether `allocate_child` gains `scope`/`role` kwargs or whether the caller sets them on the node after allocation. **Adding kwargs to `allocate_child` is cleaner and allows atomicity with persistence.** [ASSUMED — based on SubagentSpec structure; V3 spec absent so role=None in V4]

---

## Focus Area 4: `voss session tree` CLI (VTREE-09)

### Existing CLI Pattern

The CLI uses Click. Commands and groups are defined in `voss/harness/cli.py`, collected in `AGENT_COMMANDS` tuple, and registered via `register(group)` which is called from `voss/cli.py`. [VERIFIED: cli.py lines 3777–3813]

**Key observation: there is NO existing `session_group`.** There is only a flat `sessions_cmd` (line 2437) which lists sessions. `voss session tree` requires a NEW `session_group` with `sessions_cmd` demoted to be either a standalone command or a group subcommand.

**Option A: New `session_group`, `sessions_cmd` stays as-is (flat command).**
`voss sessions` keeps working; `voss session tree` is a new group. Both `sessions_cmd` and `session_group` in `AGENT_COMMANDS`. CLI now has both `voss sessions` (flat) and `voss session` (group). This is slightly inconsistent but non-breaking.

**Option B: New `session_group`, move `sessions_cmd` into it as `voss session list`.**
Clean taxonomy: `voss session list` / `voss session tree`. Breaks `voss sessions` (users lose the flat command). Breaking change — needs consideration.

**Recommended for V4: Option A** (non-breaking; adds new group alongside existing flat command). Option B is a larger refactor outside VTREE-09 scope.

### Concrete Pattern to Mirror (from `inspect_group`)

```python
# voss/harness/cli.py — analogous to lines 2757–2788

@click.group("session")
def session_group() -> None:
    """Inspect persisted session trees."""


@session_group.command("tree")
@click.argument("root_id")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON export.")
def session_tree_cmd(root_id: str, cwd_str: str, json_mode: bool) -> None:
    """Print the session tree for a root node."""
    from .session_tree import export_tree, SessionTreeNotFoundError
    cwd = Path(cwd_str).resolve()
    try:
        tree = export_tree(root_id, cwd)
    except SessionTreeNotFoundError:
        click.echo(f"<error: no tree found for root_id {root_id!r}>", err=True)
        raise click.exceptions.Exit(1)
    if json_mode:
        click.echo(json.dumps(tree, indent=2))
        return
    _print_tree(tree)  # helper — tree text rendering
```

Add `session_group` to `AGENT_COMMANDS` tuple. [VERIFIED: cli.py lines 3777–3813 — AGENT_COMMANDS tuple + register() pattern]

### Exit Code Semantics

Click uses `raise click.exceptions.Exit(1)` for non-zero exit. Printing to stderr is `click.echo(..., err=True)`. For an unknown root (no directory or no JSON files), the function should output a user-readable message to stderr and exit 1. [VERIFIED: cli.py line 2774 — `raise click.ClickException(str(exc))` which writes to stderr and exits 1; or direct `Exit(1)`]

---

## Focus Area 5: Consolidated JSON Export (VTREE-10)

### Per-Node File Layout (to aggregate from)

```
.voss/sessions/<root_id>/
├── <root_id>.json       # root node (parent_run_id = null)
├── <child_id>.json      # child node (parent_run_id = root_id)
└── <child_id>.json      # ...
```

Root identified by: `parent_run_id == null` OR `id == root_id`. [VERIFIED: session_tree.py lines 97–101, test_session_tree.py lines 43–57]

### Export Function Shape

```python
# voss/harness/session_tree.py

class SessionTreeNotFoundError(Exception):
    """Raised when no persisted tree exists for the given root_id."""


def export_tree(root_id: str, cwd: Path) -> dict:
    """Return a single JSON-serializable dict representing the full tree.

    Aggregates all per-node files at .voss/sessions/<root_id>/.
    Raises SessionTreeNotFoundError if the directory does not exist or is empty.
    """
    tree_dir = cwd / ".voss" / "sessions" / root_id
    if not tree_dir.is_dir():
        raise SessionTreeNotFoundError(root_id)
    nodes = []
    for path in sorted(tree_dir.glob("*.json")):
        data = json.loads(path.read_text())
        nodes.append(data)
    if not nodes:
        raise SessionTreeNotFoundError(root_id)
    return {
        "root_id": root_id,
        "nodes": nodes,
    }
```

**Round-trip property:** Each node dict in `nodes` is the exact JSON-serializable form already on disk. `_hydrate_node(node_dict)` round-trips it back to a `SessionTreeNode`. The export schema carries all required fields: id, root_id, parent_run_id, envelope, terminal_state, scope, role, created_at, ended_at, rejected_raises. [VERIFIED: session_tree.py `_write_node_file` → `to_dict()` → `json.dumps()` — the disk format IS the export format]

**Export is reachable via CLI** via `session_tree_cmd --json` or the non-JSON tree print. No separate `export` subcommand needed. [Per VTREE-10: "API + reachable via the CLI"]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent allocation safety | Custom CAS or per-node lock | `asyncio.Lock` (already on `SessionTreeManager`) | Already proven correct in O1; no new mechanism needed |
| Guard race condition | Per-call lock around check+return | Trust asyncio cooperative scheduling | `await` boundary exists only at `async with scope:` — guard check + return is atomic under asyncio |
| Node aggregation for export | Streaming parser, in-memory tree structure | `glob("*.json")` + `json.loads` | Files are already the canonical node store; no in-memory cache needed |
| CLI argument parsing | Manual `sys.argv` parsing | Click group/command pattern (existing) | All voss CLI uses Click; `inspect_group` is the direct analog |
| Back-compat hydration | Version numbers, migration scripts | `setdefault` in `_hydrate_node` | Established pattern: transitions/retry_notes added with `setdefault` in O3 |
| Exit reason validation | Custom validator | `EXIT_REASONS` frozenset (already checked in `finalize_node`) | `finalize_node` raises `ValueError` on invalid reason — behavior already tested |

**Key insight:** Every mechanism V4 needs already exists in the substrate. V4 is configuration + wiring of existing primitives, not new infrastructure.

---

## Common Pitfalls

### Pitfall 1: Guard Firing Before `spent` Is Ever Updated

**What goes wrong:** The guard checks `spent >= limit` but `mutate_envelope` is never called after `run_turn`, so `spent` stays 0 forever. The guard is dead code.

**Why it happens:** Currently `run_subagent` does not call `mutate_envelope` — it exists as a standalone API. The O1 design expected callers to update spent; V4 must wire the update inside `run_subagent`.

**How to avoid:** After `run_turn` returns (normal path), extract token usage from `result.run` (e.g., `iteration_total_prompt_tokens + iteration_total_completion_tokens`) and call `mutate_envelope(node, delta=-tokens_used, cwd=cwd)`. Do this BEFORE checking soft-exit. Handle `result.run is None` gracefully (no iteration completed → 0 tokens).

**Warning signs:** Tests for the guard pass with `spent=0` and `limit=0` but fail with realistic limits.

### Pitfall 2: `_NODE_JSON_KEYS` Test Breaks on scope/role Addition

**What goes wrong:** `TestSchemaIsolation.test_node_keys_exact` asserts exact key equality against `_NODE_JSON_KEYS = frozenset({...})`. Adding `scope` and `role` to `SessionTreeNode` makes `to_dict()` include them, breaking the assertion.

**Why it happens:** The test is a schema-lock guard, intentionally strict.

**How to avoid:** Update `_NODE_JSON_KEYS` in `test_session_tree.py` to include `"scope"` and `"role"` as part of V4. This is an expected, deliberate schema extension — the test update is the correct signal that the lock was broken intentionally.

### Pitfall 3: `finalize_node` Called Twice in the `finally` Branch

**What goes wrong:** An `except` handler calls `finalize_node`, then `finally` also calls it. Two disk writes occur, the second a no-op (because `_finalized=True`), but the `finally` path may use the wrong `exit_reason`.

**Why it happens:** `finally` always runs, including after `except`.

**How to avoid:** The `finally` block should guard: `if node and not node._finalized: finalize_node(...)`. `finalize_node` itself also checks `_finalized` (line 111–113 of `session_tree.py`), providing a double guard. [VERIFIED: session_tree.py lines 109–113]

### Pitfall 4: `attach_subagent_tool` Inner `subagent_run` Tool Bypasses the Guard

**What goes wrong:** The `@tool` closure `subagent_run` (lines 317–329 of `subagents.py`) calls `run_subagent` WITHOUT passing `node=`. The guard in `run_subagent` is `if node is not None and ...`. When `node=None`, the guard is skipped. Subagent calls from the tool dispatcher have no budget enforcement.

**Why it happens:** `attach_subagent_tool` builds the tool closure without access to a `SessionTreeNode`. The tree manager and node must be plumbed through to the tool closure.

**How to avoid:** V4's scope is the mechanism (the guard lives in `run_subagent`). Plumbing `node` through `attach_subagent_tool` is the V5/V7 integration work. For V4, the guard works when `run_subagent` is called directly with a `node`. The planner should document this gap explicitly — the tool-dispatched path is unguarded in V4 (same as O1).

### Pitfall 5: `asyncio.TimeoutError` Branch Exit Code

**What goes wrong:** `except asyncio.TimeoutError: finalize_node(..., exit_reason="timeout"); raise` — re-raising propagates the error to the caller. If the caller catches it and ignores it, the node is finalized but the outer run continues. If the caller doesn't catch it, the task terminates with an unhandled exception.

**Why it happens:** Timeout semantics are caller-defined; `run_subagent` doesn't know if the timeout should be silent or fatal.

**How to avoid:** Re-raise by default (same as the existing `except Exception` recommendation). Document the behavior in the function docstring. The VTREE-07 requirement is "exactly one terminal node" — which is satisfied even if the exception propagates.

### Pitfall 6: Export Reads Stale Files During Active Run

**What goes wrong:** `export_tree` reads all JSON files in the directory. If called during an active run (node not yet finalized, `terminal_state=None`), the export includes open nodes with no `ended_at`.

**Why it happens:** The export is a point-in-time snapshot of the filesystem.

**How to avoid:** This is correct behavior — open nodes have `terminal_state: null`, which is a valid export state (the tree is live). ADE rendering (V11) must handle `terminal_state: null`. No fix needed in V4.

---

## Code Examples

### Pre-emptive Guard Insertion (VTREE-04)

```python
# Source: V4 gap — inserted into voss/harness/subagents.py run_subagent body
# After the spec-not-found guard, before async with scope:

    spec = registry.get(agent_id)
    if spec is None:
        return f"<error: unknown subagent {agent_id!r}>"

    # [VTREE-04] Pre-emptive spend guard: refuse to start a call when envelope exhausted.
    if node is not None and node.envelope["spent"] >= node.envelope["limit"]:
        if not node._finalized:
            finalize_node(node, exit_reason="budget", final="<halted: budget — envelope exhausted>", cwd=cwd)
        return "<halted: budget — envelope exhausted>"

    spendable = (node.envelope["limit"] - reserve) if node else None
    # ... rest of function
```

### `_hydrate_node` Back-Compat Update (VTREE-08)

```python
# Source: session_tree.py _hydrate_node — V4 additive extension
def _hydrate_node(data: dict) -> SessionTreeNode:
    kept = {k: v for k, v in data.items() if k in _NODE_FIELDS}
    kept.setdefault("rejected_raises", [])
    kept.setdefault("transitions", [])
    kept.setdefault("retry_notes", [])
    kept.setdefault("scope", None)   # V4: pre-V4 node files → null
    kept.setdefault("role", None)    # V4: pre-V4 node files → null
    return SessionTreeNode(**kept)
```

### `allocate_child` with `scope`/`role` kwargs (VTREE-08)

```python
# Source: session_tree.py SessionTreeManager.allocate_child — V4 extension
    async def allocate_child(self, limit: int, *, scope: str | None = None, role: str | None = None) -> SessionTreeNode:
        async with self._lock:
            # ... existing allocation check ...
            child = SessionTreeNode(
                id=child_id,
                root_id=self._root.id,
                parent_run_id=self._root.id,
                envelope={"limit": limit, "spent": 0},
                terminal_state=None,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ended_at=None,
                rejected_raises=[],
                scope=scope,    # V4
                role=role,      # V4
            )
            self._children.append(child)
            _write_node_file(child, self._cwd)
            child._budget = BudgetScope(token_limit=limit, name=child.id)
            return child
```

### `session_group` Click Registration (VTREE-09)

```python
# Source: voss/harness/cli.py — mirror of inspect_group pattern (lines 2757–2788)
@click.group("session")
def session_group() -> None:
    """Inspect persisted session trees (VTREE-09)."""


@session_group.command("tree")
@click.argument("root_id")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="Machine-readable JSON export.")
def session_tree_cmd(root_id: str, cwd_str: str, json_mode: bool) -> None:
    """Show the session tree for a root node id."""
    import json as _json
    from .session_tree import SessionTreeNotFoundError, export_tree
    cwd = Path(cwd_str).resolve()
    try:
        tree = export_tree(root_id, cwd)
    except SessionTreeNotFoundError:
        click.echo(f"<error: no tree found for root_id {root_id!r}>", err=True)
        raise click.exceptions.Exit(1)
    if json_mode:
        click.echo(_json.dumps(tree, indent=2))
        return
    # Text tree rendering
    for node in tree["nodes"]:
        indent = "  " if node["parent_run_id"] else ""
        line = (
            f"{indent}{node['id']}  "
            f"parent={node['parent_run_id'] or '—'}  "
            f"limit={node['envelope']['limit']} spent={node['envelope']['spent']}  "
            f"state={node['terminal_state']['exit_reason'] if node['terminal_state'] else 'open'}  "
            f"scope={node.get('scope') or '—'}  role={node.get('role') or '—'}"
        )
        click.echo(line)
```

Add `session_group` to `AGENT_COMMANDS` tuple (after `sessions_cmd`). [VERIFIED: cli.py lines 3777–3813]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode = "auto") |
| Config file | `pyproject.toml` line 93: `asyncio_mode = "auto"` |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` |
| Redaction invariant gate | `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` |
| Full harness suite | `.venv/bin/python -m pytest tests/harness/ -x -q` |

**Python interpreter:** `.venv/bin/python` (bare `python3` lacks deps). [VERIFIED: memory voss-python-interpreter]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VTREE-01 | `scope`/`role` fields present in `to_dict()` and round-trip via `_hydrate_node`; pre-V4 files hydrate with `null` | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSchemaExtension -x` | ❌ new class |
| VTREE-01 | `_NODE_JSON_KEYS` updated to include `scope`/`role` | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSchemaIsolation::test_node_keys_exact -x` | ✅ existing (must update) |
| VTREE-02 | Existing manager tests regress green | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` | ✅ existing |
| VTREE-03 | Existing persistence tests regress green | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestTreePersistence -x` | ✅ existing |
| VTREE-04 | Node at `spent >= limit` cannot start a call (guard halts, returns budget envelope message, finalizes node) | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSpendGuard -x` | ❌ new class |
| VTREE-04 | Node after a call has `spent` incremented by actual token usage | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSpendGuard::test_spent_updated_after_call -x` | ❌ new test |
| VTREE-04 | Concurrent children cannot oversell parent (regression) | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestConcurrency -x` | ✅ existing |
| VTREE-05/06 | Cap-raise guard + rejected-raise audit (regression) | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestCapRaiseGuard -x` | ✅ existing |
| VTREE-07 | `finalize_node` accepts every EXIT_REASONS value | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestAllReasonsFinalize -x` | ❌ new class |
| VTREE-07 | Error path (bare Exception) → exactly one finalized node with `terminal_state` set | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestAllReasonsFinalize::test_error_path -x` | ❌ new test |
| VTREE-07 | Timeout path → exactly one finalized node with `exit_reason="timeout"` | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestAllReasonsFinalize::test_timeout_path -x` | ❌ new test |
| VTREE-07 | Budget path (both hard+soft) → exactly one finalized node | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestDrainFinalize -x` | ✅ existing |
| VTREE-07 | No node open after all-paths teardown | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestNoOpenNodes -x` | ✅ existing |
| VTREE-08 | Spawn with known scope/role persists them; spawn without → null | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSchemaExtension::test_scope_role_spawn -x` | ❌ new test |
| VTREE-08 | scope/role present in export | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestExport -x` | ❌ new class |
| VTREE-09 | `voss session tree <root_id>` exits 0 and prints tree for known root | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestCLI::test_known_root -x` | ❌ new class |
| VTREE-09 | `voss session tree <root_id>` exits non-zero + stderr for unknown root | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestCLI::test_unknown_root -x` | ❌ new test |
| VTREE-10 | Export returns one JSON object with all nodes + parent linkage + envelope + terminal_state + scope/role | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestExport::test_export_round_trips -x` | ❌ new test |
| VTREE-10 | Export raises on unknown root_id | unit | `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestExport::test_export_unknown_root -x` | ❌ new test |
| Schema freeze | `test_session_redaction.py` passes unmodified; no `SessionRecord`/`RunRecord`/`BudgetScope` field changes | smoke | `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` | ✅ MUST PASS UNMODIFIED |

### Concurrency Correctness Testing Pattern

To test the spend guard under concurrent children deterministically:

```python
# Approach: mock run_turn to record call order and inject spend
class TestSpendGuard:
    async def test_guard_blocks_when_envelope_exhausted(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(100)
        # Drive child to full spend
        mutate_envelope(child, delta=-100, cwd=tmp_path)
        assert child.envelope["spent"] == 100
        # Guard must block: mock run_subagent or call guard logic directly
        # Guard check: spent (100) >= limit (100) → True → block
        assert child.envelope["spent"] >= child.envelope["limit"]
        # Verify finalize would be called (test the guard logic, not full run_subagent)
        # For integration: mock run_turn and verify it is NOT called
```

Full integration test (mock `run_turn`):
- Patch `voss.harness.subagents.run_turn` with an `AsyncMock` that records calls.
- Call `run_subagent` with `node` at exhaustion.
- Assert `run_turn` mock was NOT called (guard fired before it).
- Assert `node._finalized is True` with `exit_reason="budget"`.

### Schema-Freeze Signal

```bash
# Verify zero field changes on frozen schemas:
git diff HEAD -- voss/harness/session.py | grep "^[+-]" | grep -E "SessionRecord|RunRecord" | grep -v "^---\|^+++"
# Should be empty (no field changes on frozen schemas).

# Redaction test passes unmodified:
.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q
```

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q && .venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ -x -q`
- **Phase gate:** Full harness suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test classes: `TestSpendGuard`, `TestAllReasonsFinalize`, `TestSchemaExtension`, `TestExport`, `TestCLI` — in `tests/harness/test_session_tree.py`
- [ ] Update `_NODE_JSON_KEYS` to include `"scope"` and `"role"` in existing `TestSchemaIsolation`
- [ ] `SessionTreeNotFoundError` exception class in `session_tree.py` (needed by CLI + export)
- [ ] Framework: already installed (`asyncio_mode = "auto"`, confirmed)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Post-hoc spend tracking only | Pre-emptive guard at call boundary | V4 | Budget becomes a real security boundary, not just a post-fact audit |
| Only `BudgetExceededError` caught | All exception paths finalize | V4 | No open nodes after any termination reason |
| No scope/role on nodes | Additive nullable `scope`/`role` fields | V4 | Foundation for V7 EM dispatch + ADE rendering |
| No tree CLI | `voss session tree <root_id>` | V4 | Tree inspectable without code |
| Per-node files only | Consolidated JSON export `export_tree()` | V4 | Machine-readable input for ADE (V11) |

**Still deferred from V4:**
- `killed`/`blocked` emitters → V5/V7 (mechanism proven by VTREE-07)
- ADE tree rendering → V11 (export data ships in V4)
- Recursive depth>1 → V8 (MAG-07)
- Full scope/role population via EM → V7

---

## Environment Availability

All dependencies are stdlib or project-internal.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `asyncio` (stdlib) | Pre-emptive guard + concurrency | ✓ | Python 3.11+ | — |
| `json` (stdlib) | Export + node files | ✓ | Python 3.11+ | — |
| `pathlib` (stdlib) | Node file glob + directory ops | ✓ | Python 3.11+ | — |
| `click` (project dep) | `session_group` CLI | ✓ | ≥8.0 (in pyproject.toml) | — |
| `pytest-asyncio` | Async tests | ✓ | `asyncio_mode = "auto"` in pyproject.toml line 93 | — |
| `.venv/bin/python` | Test runner | ✓ | Confirmed (memory voss-python-interpreter) | — |

**Missing dependencies with no fallback:** None.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | partial | Pre-emptive guard is a budget access control; budget = security boundary |
| V5 Input Validation | yes (minor) | `root_id` in CLI: `uuid4().hex[:12]` pattern — no user-controlled path traversal |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Budget oversell at allocation | Tampering | `asyncio.Lock` on `allocate_child` (existing, verified) |
| Budget oversell at spend (no pre-emptive guard) | Elevation of Privilege | V4 pre-emptive guard at `run_subagent` entry |
| Node file path traversal via `root_id` | Tampering | `root_id` is `uuid4().hex[:12]` — no user-controlled path components; glob is scoped to `.voss/sessions/<root_id>/` |
| Node file permission | Information Disclosure | `path.chmod(0o600)` — existing pattern unchanged |
| Open node after error termination (finalize gap) | Denial of Service (resource leak) | V4 `try/finally` finalize boundary |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Guard check `spent >= limit` is atomic under asyncio cooperative scheduling — no interleave risk between check and return | Focus Area 1 — Concurrency | If threading is introduced later, the guard would need a lock; safe under current asyncio-only model |
| A2 | `result.run.iteration_total_prompt_tokens + result.run.iteration_total_completion_tokens` is the correct token usage field to feed into `mutate_envelope` after `run_turn` | Focus Area 1 — Guard Insertion | If the field names differ in `RunRecord`, spent update would use wrong values; planner must verify against `RunRecord` fields in `test_session_redaction.py` line 109 |
| A3 | V3 spec is absent in today's codebase, so `role=None` at spawn in V4 | Focus Area 3 — scope/role | If a V3 spec format ships before V4 plan executes, `role` plumbing path changes |
| A4 | `"error"` should either be added to `EXIT_REASONS` or mapped to `"interrupt"` for exception-path finalization | Focus Area 2 — EXIT_REASONS | If neither approach is taken, `finalize_node` raises `ValueError` on exception paths — defeating VTREE-07 |
| A5 | `test_session_redaction.py` does NOT test `_NODE_JSON_KEYS` — updating that set in `test_session_tree.py` does not break the redaction test | Validation Architecture | Verified by reading `test_session_redaction.py` in full — it only tests `SessionRecord`, `RunRecord`, and `session.save()` paths, not `session_tree.py` |
| A6 | Option A for CLI (new `session_group` alongside existing flat `sessions_cmd`) is non-breaking | Focus Area 4 — CLI | If tooling depends on `voss session` not being a group today, this adds a group that was absent. Verified: no `session_group` exists today — no conflict |

---

## Open Questions

1. **What exit_reason string for exception paths?**
   - What we know: `EXIT_REASONS` = `{done, max-iter, budget, interrupt, batch-invariant, timeout, killed}`. No `"error"`.
   - What's unclear: Should `"error"` be added to `EXIT_REASONS`, or should exception paths use `"interrupt"` (semantically "abnormal termination")?
   - Recommendation: Add `"error"` to `EXIT_REASONS` for clarity (additive, no field change on any record). If adding to `session.py` feels too broad, use `"interrupt"` as a conservative fallback. Planner decides.

2. **Where does `mutate_envelope` get called to update `spent` after `run_turn`?**
   - What we know: `mutate_envelope` exists but is not called inside `run_subagent` today. The guard depends on `spent` being accurate.
   - What's unclear: Exact token count field(s) from `result.run` to use. `RunRecord` has `iteration_total_prompt_tokens` and `iteration_total_completion_tokens` (confirmed in `test_session_redaction.py` line 118).
   - Recommendation: `tokens_used = (result.run.iteration_total_prompt_tokens or 0) + (result.run.iteration_total_completion_tokens or 0)` when `result.run` is not None; `0` otherwise.

3. **Does the `finally` safety net re-raise or swallow?**
   - What we know: `except Exception as exc: ... raise` re-raises. `finally` always runs.
   - What's unclear: Should the outer caller of `run_subagent` (the `subagent_run` tool closure) see the exception?
   - Recommendation: Re-raise from `except Exception`. The tool dispatch layer in `attach_subagent_tool` wraps `run_subagent` in an `async def subagent_run(...)` tool function — propagating the exception causes the tool to return an error to the agent loop. Verify the agent loop handles tool errors gracefully (it does — tool errors become tool result strings).

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/session_tree.py` (192 lines) — shipped substrate, all fields, `finalize_node`, `mutate_envelope`, `_hydrate_node`, `SessionTreeManager` [VERIFIED: codebase read]
- `voss/harness/subagents.py` (370 lines) — `run_subagent` current body, `attach_subagent_tool` closure, `SPAWN_TOOL_NAME`, `SubagentSpec.scope` field [VERIFIED: codebase read]
- `voss/harness/cli.py` (3814 lines) — `AGENT_COMMANDS`, `register()`, `inspect_group` pattern, `session_group` absence confirmed, `principles_group` as recent analogous addition [VERIFIED: codebase read]
- `voss/harness/session.py` lines 74–78 — `EXIT_REASONS` frozenset with all 7 values [VERIFIED: codebase read]
- `tests/harness/test_session_tree.py` — all existing test classes, `_NODE_JSON_KEYS`, schema isolation patterns [VERIFIED: codebase read]
- `tests/harness/test_session_redaction.py` — `RunRecord` field count (24), `SessionRecord` schema, redaction guarantee [VERIFIED: codebase read]
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-RESEARCH.md` — prior verified research on asyncio.Lock, BudgetScope mechanics, D-03 boundary pattern [CITED: O1-RESEARCH.md]
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md` — file analogs, hydrate pattern, async test conventions [CITED: O1-PATTERNS.md]

### Tertiary (LOW confidence / ASSUMED)

- A1: asyncio cooperative scheduling makes the guard check atomic — derived from asyncio docs + O1 live test reasoning
- A2: `iteration_total_prompt_tokens` + `iteration_total_completion_tokens` as token source — derived from `RunRecord` field names in `test_session_redaction.py` line 118
- A4: `"error"` vs `"interrupt"` for exception paths — no precedent in codebase; planner decision

---

## Metadata

**Confidence breakdown:**
- Shipped substrate (VTREE-01..06): HIGH — all code read and verified
- Guard integration point (VTREE-04): HIGH — `run_subagent` body verified; guard placement unambiguous
- `mutate_envelope` spend update wiring: MEDIUM — token field names confirmed; exact call site is new code
- All-reason finalize (VTREE-07): HIGH — except/finally pattern; `_finalized` idempotence verified
- Scope/role schema (VTREE-08): HIGH — `_hydrate_node` setdefault pattern confirmed
- CLI registration (VTREE-09): HIGH — `inspect_group` / `principles_group` pattern confirmed; `session_group` absence confirmed
- Export function (VTREE-10): HIGH — `glob("*.json")` + `_hydrate_node` pattern confirmed against disk layout

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (stable Python harness; re-validate if `subagents.py`, `session_tree.py`, or `session.py` are modified before planning executes)

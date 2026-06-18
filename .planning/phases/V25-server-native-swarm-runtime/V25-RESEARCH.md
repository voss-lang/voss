# Phase V25: Server-Native Swarm Runtime — Research

**Researched:** 2026-06-17
**Domain:** Harness FastAPI server swarm coordination runtime
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01** — Coordinator is a full harness `ServerSession` (its own pane + model), not a one-shot call. It calls `POST /swarm/{id}/task` to seed tasks, emits `swarm.assign`, and can re-plan / gate mid-run as a first-class roster member.
- **D-02** — Single-coordinator topology (not peer-to-peer); max-6-concurrent-agents cap (user-overridable), carried from A13 D-02/D-12.
- **D-03** — V25 emits `swarm.*` SSE events as a first-class dedicated event plane; V24's `swarmReconcile` consumes them directly. NOT bent into existing RunData/board shapes.
- **D-04** — New append-only `events/*.jsonl` under `.voss/swarm/<id>/` as the truth-mirror. A13's `manifest.json` + `tasks/` + `results/` become an optional derived snapshot view rendered from the event log — not the source of truth. A13-01's Rust temp-rename writers + `swarmTypes.ts` are demoted to snapshot rendering, not deleted.
- **D-05** — Coordinator/builder/reviewer prompts live as versioned files in `voss/harness/swarm/prompts/`, git-tracked, generated per-run with task context injected. The coordinator prompt is seeded from BridgeSwarm's recovered coordinator playbook.

### Claude's Discretion
- Ownership policy injection mechanics (VSWARM-05): exact construction of the synthetic per-task `PermissionsConfig` attached to the session's `PermissionGate`.
- Event envelope schema (event id/type/actor/ts/payload shape) — constrained by VSWARM-01 (append-only, replayable) and D-03 (must satisfy V24 `swarmReconcile`).
- Spawn-gate `waiting` mechanics — new `ServerSession` state vs. lazy session creation on assign.

### Deferred Ideas (OUT OF SCOPE)
- V24 `swarmReconcile` swarm-event consumer (→ V24 backlog)
- voss-app swarm spawn UI / roster sidebar / launch modal (→ V24/voss-app)
- Coordinator decomposition-quality evals (→ E-track)
- V25 ↔ V5/V7 cage convergence (later, not this phase)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VSWARM-01 | SwarmStore + event log: server-side state + append-only JSONL mirror under `.voss/swarm/<id>/events/` | See Standard Stack / SwarmStore design section |
| VSWARM-02 | Swarm SSE event types: 5 new event types on existing SSE bus | See Architecture Patterns — SSE extension pattern |
| VSWARM-03 | /swarm REST endpoints: POST/GET with bearer-auth parity | See Architecture Patterns — route insertion pattern |
| VSWARM-04 | Spawn-gating: `waiting` state, zero turns until `swarm.assign` | See spawn-gate state machine section |
| VSWARM-05 | Server-enforced ownership at `PermissionGate` | See ownership injection section |
| VSWARM-06 | Ownership overlap validation in SwarmStore | See SwarmStore design section |
| VSWARM-07 | Memory-scoped recall injection per agent turn | See VSWARM-07 section |
| VSWARM-08 | Per-role model routing through `_resolve_provider` | See VSWARM-08 section |
| VSWARM-09 | `agent_registry` swarm columns + list-by-swarm query | See VSWARM-09 section |
| VSWARM-10 | Operator escalation + decision recording | See VSWARM-10 section |
| VSWARM-11 | Audit replay from `events/*.jsonl` | See VSWARM-11 section |
</phase_requirements>

---

## Summary

V25 builds a server-native multi-agent swarm runtime on top of an already-rich harness substrate. Every primitive it needs — multiplexed sessions, SSE event bus, file-write permission enforcement, semantic memory recall, per-pane agent registry, and provider routing — already ships and is cleanly extensible. The work is primarily **wiring**, not new infrastructure.

The harness has no swarm code today (confirmed by codebase inspection). `voss/harness/swarm_store.py` does not exist. There are no swarm SSE event types in `server/events.py`, no `/swarm` routes in `server/app.py`, and no swarm columns in `agent_registry.rs`. All 11 requirements are net-new additions to existing extension points.

Three specific engineering challenges warrant the planner's attention: (1) the spawn-gate mechanics require a new `waiting` flag on `ServerSession` and an `asyncio.Event` or `asyncio.Condition` that `_run_turn` blocks on before the first turn — this must be asyncio-native to avoid blocking the event loop; (2) the ownership-policy injection requires constructing a synthetic `PermissionsConfig` without using `model_config = STRICT` (which would reject construction from code), either by using `model_construct` or by building a `rules`-only dict via the existing `rules: dict[str,Any]` field; (3) the coordinator prompt template (D-05) must be authored from scratch because the BridgeSwarm coordinator playbook does not exist on disk anywhere in the Voss repo or SecondBrain (see Open Questions).

**Primary recommendation:** Start with SwarmStore + event-log (VSWARM-01) as Wave 0 foundation, since all other requirements flow through it. Build swarm SSE events and routes next (VSWARM-02/03), then spawn-gate + ownership (VSWARM-04/05), then recall injection + model routing + registry (VSWARM-07/08/09), then operator/audit (VSWARM-10/11). Gate on the 2-builder enforced integration test as the terminal acceptance bar.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SwarmStore (state + event log) | Python harness (server memory) | `.voss/swarm/` filesystem (audit) | State lives server-side; disk is append-only mirror |
| Swarm SSE event types | Python harness (server/events.py) | voss-app TS (swarmReconcile, V24 follow-up) | Event emission is server-side; rendering is V24 scope |
| /swarm REST endpoints | Python harness (server/app.py) | — | Same tier as all existing /session routes |
| Spawn-gating | Python harness (ServerSession + _run_turn) | — | Session lifecycle is entirely in-process asyncio |
| Ownership enforcement | Python harness (PermissionGate) | — | PermissionGate.check is the existing write chokepoint |
| Overlap validation | Python harness (SwarmStore) | — | Pure Python logic at task-creation time |
| Memory-scoped recall | Python harness (_run_turn augmentation) | — | Turn assembly already runs in _run_turn |
| Per-role model routing | Python harness (_resolve_provider) | — | Existing provider selection, no new router |
| Agent-registry binding | Rust (agent_registry.rs) | Python harness (spawn call) | Rust owns SQLite schema; harness calls Tauri command on spawn |
| Operator escalation | Python harness (existing /permission route) | — | Reuses the Future-based permission bridge already in ServerSession |
| Audit replay | Python reader (replay_swarm function) | — | Pure JSONL reader, no live server needed |
| Role-prompt templates | Python harness (voss/harness/swarm/prompts/) | — | Git-tracked Jinja templates rendered per-run |

---

## Standard Stack

### Core (all existing, no new dependencies)
| Library | Existing Version | Purpose | Notes |
|---------|-----------------|---------|-------|
| `fastapi` | already in harness | REST routes for /swarm | New routes added alongside /session |
| `pydantic` v2 | already in harness | SwarmStore models, event models | Use `BaseModel` with `model_config = ConfigDict(extra="ignore")` matching `_Base` |
| `sse_starlette` | already in harness | SSE delivery | New event types added to discriminated union |
| `asyncio` | stdlib | Spawn-gate, session.task, asyncio.Event | Native to harness loop |
| `portalocker` | already in harness | Advisory lock for JSONL append writes | Mirrors memory_store.py pattern |
| `pathlib.Path` | stdlib | `.voss/swarm/<id>/events/` directory | Mirrors session_store pattern |
| `rusqlite` (Rust) | already in agent_registry.rs | SQLite migration for swarm columns | ALTER TABLE ADD COLUMN pattern |

### No New Dependencies
V25 requires no new Python or Rust packages. [VERIFIED: direct codebase inspection] All required primitives are present. The package legitimacy audit is empty.

---

## Package Legitimacy Audit

> No new packages are installed in this phase. All dependencies are already in the harness venv and cargo workspace.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP Client / voss-app
       |
       | POST /swarm             POST /swarm/{id}/task
       | POST /swarm/{id}/message   GET /swarm/{id}
       v
  _BearerASGI middleware (existing, no change)
       |
       v
  app.py: /swarm route handlers (NEW)
       |
       +---> SwarmStore (NEW, in-process)
       |         |
       |         +---> append event to .voss/swarm/<id>/events/<seq>.jsonl (audit)
       |         |
       |         +---> validate ownedFiles overlap (VSWARM-06)
       |
       +---> SessionManager.create_waiting() — coordinator + builder sessions
       |              |
       |              | (spawn-gated: asyncio.Event blocks builders)
       |              v
       |         _run_turn (existing, lightly extended):
       |              |
       |              +-> PermissionGate(project_policy=swarm_ownership_policy)
       |              |
       |              +-> MemoryStore.recall(query, scope=task.ownedFiles)  (VSWARM-07)
       |              |
       |              +-> run_turn(model=role.model, provider=per_role_provider)
       |              |
       |              +-> EventBusRenderer.emit(SwarmAssign | SwarmWorkerDone | ...)
       |
       v
  GET /session/{id}/events  (SSE, existing route)
       |
       | swarm.assign -> unblocks waiting builder (asyncio.Event.set)
       | swarm.needs_operator -> surfaces via existing /permission endpoint
       v
  Client SSE subscriber (voss-app swarmReconcile, V24 follow-up)
```

### Recommended Project Structure

```
voss/harness/
├── swarm_store.py          # NEW: SwarmStore, Swarm, Task, Role models + JSONL event log
├── swarm/
│   ├── __init__.py         # NEW
│   ├── events.py           # NEW: SwarmEventLog writer (append-only JSONL)
│   └── prompts/
│       ├── coordinator.md  # NEW: coordinator role-prompt template (Jinja)
│       ├── builder.md      # NEW: builder role-prompt template (Jinja)
│       └── reviewer.md     # NEW: reviewer role-prompt template (Jinja)
└── server/
    ├── app.py              # MODIFY: add /swarm routes + SwarmManager import
    ├── events.py           # MODIFY: add 5 swarm event types + update AgentEvent union
    └── sessions.py         # MODIFY: add waiting flag + gate_event to ServerSession

crates/voss-app-core/src/
└── agent_registry.rs       # MODIFY: ALTER TABLE migration + list_by_swarm query + SwarmEntry

tests/harness/
└── test_swarm_store.py     # NEW: unit tests for SwarmStore, event-log replay, overlap validation
tests/harness/server/
└── test_swarm_routes.py    # NEW: route-level tests (auth, CRUD, 4xx overlap)
tests/
└── test_swarm_e2e.py       # NEW: 2-builder enforced integration test (SPEC acceptance bar)
```

### Pattern 1: Adding New SSE Event Types

**What:** Add new Pydantic event models to `server/events.py` and extend the `AgentEvent` union.
**When to use:** Any new event type flowing over the existing SSE bus.
**Example (from `server/events.py` existing pattern):**

```python
# Source: voss/harness/server/events.py (existing _Base pattern)
class SwarmAssign(_Base):
    type: Literal["swarm.assign"] = "swarm.assign"
    swarm_id: str
    task_id: str
    session_id: str       # builder session that owns this task
    owned_files: list[str]
    role: str

class SwarmWorkerDone(_Base):
    type: Literal["swarm.worker_done"] = "swarm.worker_done"
    swarm_id: str
    task_id: str
    session_id: str
    summary: str | None = None

class SwarmGate(_Base):
    type: Literal["swarm.gate"] = "swarm.gate"
    swarm_id: str
    task_id: str
    gate_type: str        # "ownership_denied" | "reviewer_reject"
    detail: str

class SwarmNeedsOperator(_Base):
    type: Literal["swarm.needs_operator"] = "swarm.needs_operator"
    swarm_id: str
    task_id: str
    session_id: str
    tool_name: str
    path: str | None = None  # the denied file path

class SwarmComplete(_Base):
    type: Literal["swarm.complete"] = "swarm.complete"
    swarm_id: str
    task_count: int
    summary: str | None = None

# Add to AgentEvent union:
AgentEvent = Annotated[
    Union[
        # ... existing 21 types ...
        SwarmAssign,
        SwarmWorkerDone,
        SwarmGate,
        SwarmNeedsOperator,
        SwarmComplete,
    ],
    Field(discriminator="type"),
]
```

**Emit via existing `EventBusRenderer.emit()`** which is already a server-only helper.

### Pattern 2: Adding Routes Alongside /session

**What:** Add `/swarm` routes inside `create_app()` in `server/app.py`.
**When to use:** New resource-level REST endpoints.
**Example (mirroring existing session route pattern):**

```python
# Source: voss/harness/server/app.py — route insertion pattern
swarm_mgr = SwarmStore(cwd=Path(".").resolve())
app.state.swarm_store = swarm_mgr

@app.post("/swarm", status_code=201)
async def create_swarm(body: CreateSwarmBody) -> dict:
    swarm = swarm_mgr.create(goal=body.goal, cwd=body.cwd or ".")
    return {"v": 1, "id": swarm.id}

@app.get("/swarm/{swarm_id}")
async def get_swarm(swarm_id: str) -> dict:
    s = swarm_mgr.get(swarm_id)
    if s is None:
        raise HTTPException(404, "swarm not found")
    return {"v": 1, "swarm": s.to_dict()}
```

Note: `_BearerASGI` at the ASGI layer (app.py:60-77) covers all routes automatically — no per-route auth decorator needed. [VERIFIED: direct source inspection]

### Pattern 3: Spawn-Gate — Blocking a Session Until `swarm.assign`

**What:** A `ServerSession` must run zero turns until the coordinator's `swarm.assign` for its task arrives. This is the deterministic replacement for BridgeSwarm's `+2s sleep` race.

**Decision (Claude's Discretion):** Use a new `gate_event: asyncio.Event | None` field on `ServerSession`. When `None`, the session behaves normally. When set (a swarm builder), `_run_turn` awaits `gate_event.wait()` before the first `run_turn(...)` call. The coordinator's `swarm.assign` emission sets the event via `loop.call_soon_threadsafe(gate_event.set)`.

**Mechanics:**

```python
# server/sessions.py — MODIFY ServerSession
@dataclass
class ServerSession:
    id: str
    cwd: Path
    model: str
    provider: Any
    record: session_store.SessionRecord
    history: EpisodicMemory
    queue: asyncio.Queue[Any] = field(default_factory=lambda: asyncio.Queue(maxsize=256))
    task: asyncio.Task | None = None
    pending: dict[str, Future] = field(default_factory=dict)
    title: str = ""
    prior_context: Any = None
    # V25: spawn-gate (VSWARM-04)
    gate_event: asyncio.Event | None = None   # None = ungated (normal); set = waiting builder
    swarm_id: str | None = None
    swarm_task_id: str | None = None
    swarm_owned_files: list[str] = field(default_factory=list)
    swarm_role: str | None = None
    # V25: per-session ownership policy (VSWARM-05)
    swarm_policy: "PermissionsConfig | None" = None

# server/app.py — _run_turn augmentation
async def _run_turn(session: ServerSession, text: str, mode: str) -> None:
    loop = asyncio.get_running_loop()
    renderer = EventBusRenderer(session.queue, session_id=session.id, loop=loop)

    # VSWARM-04: wait for swarm.assign before first turn
    if session.gate_event is not None:
        await session.gate_event.wait()

    # ... rest of existing _run_turn ...
    gate = PermissionGate(
        mode=mode,
        store=PermissionStore.load(session.cwd),
        auto_yes=False,
        project_policy=session.swarm_policy,   # VSWARM-05: inject ownership deny
    )
    # ...
```

The gate `asyncio.Event` is compatible with `asyncio.create_task` because `await gate_event.wait()` suspends the coroutine (yields control) rather than blocking the thread.

**The POST /swarm/{id}/message route for the coordinator** can call `session.gate_event.set()` on the appropriate builder sessions when it receives `swarm.assign` content from the coordinator's turn. The coordinator itself is an ungated session (`gate_event=None`).

### Pattern 4: Ownership Policy Injection (VSWARM-05)

**What:** Inject a per-task file-ownership deny policy into `PermissionGate` so writes outside `task.ownedFiles` return `(False, "denied by .voss/permissions.yml")`.

**Exact mechanism:** `PermissionGate.check` at line 233 evaluates `self.project_policy` first (the deny-wins layer, lines 288-295):

```python
# permissions.py:288-295 — the hook
if self.project_policy is not None:
    if tool_name in self.project_policy.tool_policy.deny:
        return False, "denied by .voss/permissions.yml"
    rule_decision = match_permission_rules(
        getattr(self.project_policy, "rules", None), tool_name, args
    )
    if rule_decision == "deny":
        return False, "denied by permission rule (.voss/permissions.yml)"
```

**PermissionsConfig** (`cognition_schemas.py:56-66`) uses `model_config = STRICT` (extra=forbid), so it can't be constructed with non-declared kwargs. But it can be constructed normally via field assignment. The `rules` field is `dict[str, Any]` which accepts `{tool_name: {path_pattern: "deny"}}`.

**Recommended construction:**

```python
# swarm_store.py — build ownership deny policy for a task
from ..cognition_schemas import PermissionsConfig, ToolPolicy

def _build_ownership_policy(owned_files: list[str]) -> PermissionsConfig:
    """Synthetic PermissionsConfig that denies fs_write/fs_edit to non-owned paths.

    Uses the existing rules dict (H5.1 wildcard pattern) to deny writes to
    any path NOT in owned_files. The deny-wins project-policy layer in
    PermissionGate._check_impl:288-295 evaluates this before mode/prompt.
    """
    # Build a deny-all rule for writes, then allow the owned paths.
    # Rules last-match-wins, so: deny * first, then allow owned.
    # For fs_edit/fs_write, args["path"] is the file path.
    rules: dict[str, Any] = {}
    for tool in ("fs_write", "fs_edit", "fs_edit_many"):
        tool_rules: dict[str, str] = {"*": "deny"}
        for f in owned_files:
            tool_rules[f] = "allow"
        rules[tool] = tool_rules
    return PermissionsConfig(rules=rules)
```

**Note on path normalization:** The `match_permission_rules` → `_decision_for` path uses `fnmatch(arg_str, pattern)`. The `arg_str` for write tools is `str(args.get("path", ""))` from `_rule_command_arg` (permissions.py:62-64). This is the path as passed to the tool call (relative to cwd). Owned files stored in SwarmStore must use the SAME relative-path form. This is a normalization pitfall (see Pitfalls section).

**When ownership is denied**, the `_check_impl` returns `(False, "denied by permission rule")`. The caller site in `agent.py:1424` receives this and the write does not occur. V25 needs to additionally emit `swarm.needs_operator` at that denial point. The cleanest place is in `_run_turn` — subclass or wrap `PermissionGate.check` to intercept denials and emit the event, or attach a denial callback to the session.

### Pattern 5: JSONL Event Log (VSWARM-01/11)

**What:** Append-only per-swarm event log that is the source of truth; state is rebuildable by replay.

**File layout:**
```
.voss/swarm/<swarm_id>/
├── events/
│   ├── 000001.jsonl    # one file per event (or one file per swarm, appended)
│   └── ...
├── tasks/              # A13-01 derived snapshot (written from event replay)
│   └── <task_id>.task.md
├── results/            # A13-01 derived snapshot
│   └── <task_id>.result.md
└── manifest.json       # A13-01 derived snapshot (mutable, NOT source of truth)
```

**Recommended JSONL approach:** One file per swarm (`events/events.jsonl`), appended with portalocker (mirroring `memory_store.py:write_turn` pattern). Create-exclusive semantics on first write; never rewrite.

**Event envelope schema (Claude's Discretion — recommended):**

```json
{
  "v": 1,
  "id": "evt_7f3a1b",
  "type": "swarm.assign",
  "swarm_id": "swarm-abc123",
  "ts": "2026-06-17T10:00:00Z",
  "actor": "session-xyz",
  "payload": {
    "task_id": "task-1",
    "session_id": "session-xyz",
    "owned_files": ["src/a.py"],
    "role": "builder"
  }
}
```

Fields: `v=1`, `id` (random 8-char hex), `type` (mirrors SSE event type), `swarm_id`, `ts` (UTC ISO), `actor` (session_id or "coordinator" or "operator"), `payload` (event-type-specific dict).

**Write discipline:** `swarm/events.py` writer must use atomic append (portalocker advisory lock + `with open(path, "a") as f: f.write(json.dumps(evt) + "\n")`). The `os.replace` temp-rename is for rewrites; for append-only logs, portalocker + open("a") is the correct pattern (same as `memory_store.py:write_turn`).

**Replay:** Load all lines, deserialize, sort by `ts` if needed, reconstruct task state by applying each transition event in order.

### Anti-Patterns to Avoid

- **Poll / sleep for spawn synchronization:** The entire point of V25 is eliminating BridgeSwarm's timing race. `asyncio.Event.wait()` is the correct primitive — zero CPU, deterministic.
- **Global SwarmStore per-app-instance:** The `SwarmStore` must be app-scoped (stored in `app.state.swarm_store`), not module-level global. Module globals survive across TestClient instances in pytest, which will cause cross-test state leakage.
- **Calling `PermissionsConfig(**kwargs)` with extra fields:** `STRICT` model_config means unknown fields raise `ValidationError`. Build via normal positional/keyword args using only declared fields.
- **Rewriting JSONL files in place:** The event log is append-only. Never use `path.write_text()` on an events file. Use `open("a")`.
- **Using `asyncio.to_thread` for gate_event.wait():** The spawn-gate must await in the asyncio coroutine directly (`await session.gate_event.wait()`). Using `to_thread` would block a thread-pool thread instead, which doesn't integrate with cancellation correctly.
- **Normalizing paths at read time:** Path normalization for the ownership deny check must happen at write time (when owned_files are stored), not at check time. The check uses fnmatch against the raw path argument, so stored paths must match exactly what the agent passes to `fs_write`/`fs_edit`.

---

## VSWARM-05: Ownership Enforcement — Construction Detail

**Current deny-wins layer (permissions.py:288-295):** Already checks `project_policy.tool_policy.deny` (tool-name level) then `project_policy.rules` (path-pattern level via `match_permission_rules`). The `rules` field accepts `{tool_name: {path_pattern: decision}}` sub-maps where last-match-wins within the sub-map.

**Synthetic policy construction:**
- `PermissionsConfig(rules={"fs_write": {"*": "deny", "src/a.py": "allow"}, "fs_edit": {...}})` — this works because `rules: dict[str, Any]` accepts any dict.
- Attach as `gate.project_policy = session.swarm_policy` in `_run_turn` before the first `run_turn` call.
- The gate's existing check order (project_policy deny first, then mode, then prompt) means the ownership deny fires before any permission prompt — correct behavior.

**Emitting `swarm.needs_operator` on denial:** `_run_turn` constructs the gate fresh each turn. To intercept denials and emit swarm events, either: (a) override `PermissionGate.check` with a subclass that calls `super().check()` and, on `(False, ...)` for write tools, emits the event via the renderer; or (b) wrap `gate.check` with a closure that does the same. Option (b) is simpler and avoids subclassing the permission gate. [ASSUMED — exact injection site is Claude's discretion per CONTEXT.md]

---

## VSWARM-07: Memory-Scoped Recall Injection

**Current state:** `_run_turn` in `server/app.py:221-232` already calls `_render_code_recall_text(session.cwd, text, session_id=session.id)` from `cli.py`. That function calls `svc.query(task_text, top_k=5)` against the semantic code index.

**`MemoryStore.recall` signature** (memory_store.py:605-611):
```python
def recall(self, query: str, *, top_k: int = 5, source: str | None = None) -> list[Hit]:
```
The `source` parameter filters by memory source type (turns, ledgers, decisions, conventions). There is **no `scope` / `ownedFiles` parameter today** — [ASSUMED: new `scope` parameter needs to be added, or filtering applied post-recall].

**Recommended approach:** Add an optional `scope: list[str] | None = None` parameter to `MemoryStore.recall`. When `scope` is non-empty, post-filter hits whose `locator` path component matches any of the owned files. For code-chunk hits, the locator is `code:<filepath>:<seq>` (V19 pattern from memory_store.py:line 45-54); extract the path component and check if it's in owned_files. For turn/ledger hits, pass through unchanged (they carry session context, not file paths).

**Alternative (simpler for Wave 1):** Add a `_render_swarm_recall_text(cwd, task_text, owned_files, session_id)` function in `swarm_store.py` that calls `MemoryStore.recall` and post-filters. This avoids modifying `MemoryStore.recall`'s signature, which has many callers. The injection into `_run_turn` for swarm sessions passes this text as the `code_recall_text` kwarg.

**Scout not spawned:** Default roster for a 2-builder swarm must have no scout agent. This is enforced in `SwarmStore.create()` — the roster builder must not include a scout role unless explicitly requested.

---

## VSWARM-08: Per-Role Model Routing

**`_resolve_provider` signature** (app.py:85-112):
```python
def _resolve_provider(preference: str) -> tuple[auth_mod.Resolution, Any]:
```
Takes an auth preference string (`"auto"`, `"claude-agent"`, `"codex-oauth"`, etc.) and returns a provider. [VERIFIED: direct source inspection]

**Routing mechanism:** Each `Role` in the SwarmStore carries a `model: str` field. When spawning a builder/coordinator/reviewer session, call `_resolve_provider(role.auth_pref)` to get the provider, then pass `model=role.model` to `SessionManager.create()`. The session's `model` field is used by `run_turn` (app.py:239 `model=session.model`).

**No new routing infrastructure needed.** The per-role model routing is simply: each swarm-spawned `ServerSession` has its own `model` and `provider` resolved at spawn time from the role spec.

---

## VSWARM-09: Agent-Registry Swarm Columns

**Current schema** (agent_registry.rs:92-108):
```sql
CREATE TABLE IF NOT EXISTS agent_sessions (
    pane_id    TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    cli_binary TEXT NOT NULL,
    cli_args   TEXT NOT NULL DEFAULT '[]',
    cwd        TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'active'
               CHECK(status IN ('active', 'stopped')),
    last_seen  INTEGER NOT NULL
);
```

**Required migration:**
```sql
ALTER TABLE agent_sessions ADD COLUMN swarm_id TEXT DEFAULT NULL;
ALTER TABLE agent_sessions ADD COLUMN role TEXT DEFAULT NULL;
ALTER TABLE agent_sessions ADD COLUMN owned_files TEXT DEFAULT NULL; -- JSON array string
```

**Migration approach:** SQLite `ALTER TABLE ADD COLUMN` is safe for `DEFAULT NULL` columns and does not require data copy. Add these three statements to `create_schema()` guarded by `IF NOT EXISTS`-equivalent — in SQLite, `ADD COLUMN` errors if the column already exists, so wrap in a migration helper or use `PRAGMA table_info` to check. [ASSUMED: standard SQLite migration pattern]

**New query — list by swarm_id:**
```rust
pub fn list_agents_by_swarm(
    conn: &Connection,
    swarm_id: &str,
) -> Result<Vec<AgentEntry>, AgentRegistryError>
```

**`AgentEntry` struct must gain three fields:**
```rust
pub swarm_id: Option<String>,
pub role: Option<String>,
pub owned_files: Option<String>,  // JSON array string, parse in TS
```
The IPC contract is `#[serde(rename_all = "camelCase")]` — existing TS `AgentEntry` interface must gain `swarmId`, `role`, `ownedFiles` as optional fields.

**Thin pane-binding on spawn:** When the harness spawns a swarm agent (via the existing Tauri `spawn_agent` command or equivalent), it must also call `register_agent` with the new swarm fields. Since V25 runtime is Python-side headless, the pane-binding is the Rust `register_agent` call with `swarm_id` populated. The test verifies via a GET /swarm/{id} that aggregates agent_registry rows. [ASSUMED: exact Tauri/Python boundary for pane spawn not verified — see Open Questions]

---

## VSWARM-10: Operator Escalation + Decision Recording

**Existing permission bridge** (app.py:137-168): `_install_server_permissions` installs `gate.prompt_fn` and `gate.scope_prompt_fn` that emit `permission.updated` events and block on a `concurrent.futures.Future`. The `POST /session/{id}/permission` route resolves the Future. This is the exact mechanism for swarm operator escalation.

**Extension for VSWARM-10:** When a write is denied at the ownership gate (VSWARM-05), instead of silently returning `(False, ...)` to the agent, the wrapper emits `swarm.needs_operator` on the SSE bus. The operator can then respond via the existing `POST /session/{session_id}/permission` endpoint (same path, same Future pattern).

**Decision recording (`.voss/decisions/*.md`):** After a reviewer reject or ownership gate resolution, write a markdown file to `.voss/decisions/`. Existing decisions live in `.voss/decisions/` (confirmed by codebase inspection: `ls /Users/benjaminmarks/Projects/Voss/.voss/decisions/`). The file format mirrors existing decisions:

```markdown
---
date: 2026-06-17
confidence: 0.8
related_session: abc123def456
swarm_id: swarm-xyz
task_id: task-1
gate_type: reviewer_reject
---

# Swarm Gate Decision

[description of what was rejected and why]
```

---

## VSWARM-11: Audit Replay

**Replay algorithm:**
1. Read all `*.jsonl` lines from `.voss/swarm/<id>/events/` in lexicographic order (filenames or line order preserve causality since timestamps are monotone).
2. Deserialize each event.
3. Apply to an in-memory state machine:
   - `swarm.create` → create Swarm record
   - `swarm.assign` → transition task from `open` → `assigned`
   - `swarm.worker_done` → transition task `assigned` → `done`
   - `swarm.gate` → record gate event on task
   - `swarm.complete` → mark swarm done

**Acceptance check:** After replay, every task's state transitions from `open → assigned → done` must appear in order with no gaps. The test asserts this by replaying a completed swarm and checking each task's transition sequence.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async permission prompt | custom callback system | existing `_install_server_permissions` pattern (app.py:137-168) | Already shipping, has timeout/Future machinery |
| File write denial | new tool interceptor | `PermissionGate.project_policy` deny-wins layer (permissions.py:207, 288-295) | Existing, tested, deny-wins is exactly the right semantic |
| Model routing per role | new provider registry | `_resolve_provider(preference)` (app.py:85-112) | Already handles all auth types |
| Semantic memory query | new search infrastructure | `MemoryStore.recall(query, top_k, source)` (memory_store.py:605) | Already BM25+chroma RRF fusion |
| Session token management | custom token counting | `_default_token_count` from `agent.py` | Already used by `_render_code_recall_text` |
| JSON append log | hand-rolled JSONL serializer | stdlib `json.dumps + "\n"` + portalocker lock | Pattern established in memory_store.py |
| SQLite migration | raw connection pool | `rusqlite` `execute_batch` in `create_schema` | Established pattern in agent_registry.rs:90-108 |

**Key insight:** Every non-trivial mechanism in V25 maps to an existing, tested, production path. The only genuine net-new code is the SwarmStore state machine and the JSONL event log.

---

## Runtime State Inventory

> This is a net-new feature phase, not a rename/refactor. No runtime state migration is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — SwarmStore is new | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

---

## Common Pitfalls

### Pitfall 1: Path Normalization for Ownership Deny Rules

**What goes wrong:** The `match_permission_rules` function in permissions.py uses `fnmatch(arg_str, pattern)` where `arg_str = str(args.get("path", ""))` is the raw path the agent passes to `fs_write`/`fs_edit`. If the coordinator stores `ownedFiles` as `["src/auth.py"]` but the agent calls `fs_edit(path="./src/auth.py")`, fnmatch fails.

**Why it happens:** Python tools receive paths as strings passed by the LLM, which may include `./`, absolute paths, or platform-specific separators.

**How to avoid:** Normalize all paths in SwarmStore at task-creation time AND in the tool call interceptor. Use `str(Path(p))` (strips `./`). Store ownedFiles as relative paths from cwd, normalized. Add a `jail_path`-like normalization step in the deny-rule match.

**Warning signs:** A builder whose task owns `src/a.py` gets denied when editing `./src/a.py`.

### Pitfall 2: asyncio.Event Not Initialized Before Task Launch

**What goes wrong:** `asyncio.Event()` must be created in the same event loop that will `await` it. Creating it outside an async context (e.g., at `SessionManager.create()` time on a thread) can bind it to a different loop.

**Why it happens:** `asyncio.Event()` in Python 3.10+ no longer binds to the running loop at creation, but early Python 3.9 versions did. Voss uses Python 3.13 (confirmed by `.venv/lib/python3.13`), so this is not a version concern — but the Event must still be created from within an async context to be safe.

**How to avoid:** Create `gate_event = asyncio.Event()` inside an `async` function (e.g., inside the `/swarm/{id}/task` route handler that creates the builder session), not in `SessionManager.create()`.

### Pitfall 3: SSE Queue Fan-Out for Multi-Session Swarms

**What goes wrong:** Each `ServerSession` has its own `asyncio.Queue`. A `swarm.assign` event emitted by the coordinator session's queue is NOT automatically delivered to builder sessions' queues.

**Why it happens:** The SSE bus is per-session, not broadcast. `EventBusRenderer` publishes to `session.queue`; the SSE endpoint `GET /session/{id}/events` drains that specific session's queue.

**How to avoid:** For VSWARM-02, emit swarm events on BOTH the coordinator's queue (for SSE subscribers watching the coordinator) AND on each affected builder's queue. `SwarmStore.emit_swarm_event(swarm_id, event)` should iterate the registered builder sessions and call `renderer.emit(ev)` on each. The spawn-gate unblock (`gate_event.set()`) must happen separately from queue delivery.

**Warning signs:** Builder sessions show no swarm events when the coordinator emits `swarm.assign`.

### Pitfall 4: `PermissionsConfig` STRICT model_config Rejects Construction

**What goes wrong:** `PermissionsConfig` uses `model_config = STRICT` which means `extra="forbid"`. Attempting to construct with fields not in the schema raises `ValidationError`.

**Why it happens:** The schema was designed for YAML deserialization, not programmatic construction.

**How to avoid:** Only use declared fields (`tool_policy`, `path_scopes`, `mcp`, `rules`). For the ownership-deny use case, only `rules` is needed. Construct as `PermissionsConfig(rules={...})` — all other fields have `Field(default_factory=...)`.

### Pitfall 5: `_BearerASGI` Ordering and CORS Preflight for New Routes

**What goes wrong:** If `/swarm` routes are added outside the `create_app()` closure, they won't be covered by `_BearerASGI`.

**Why it happens:** `_BearerASGI` is applied as ASGI middleware at the `create_app` level (app.py:325). It covers all routes on the app. Routes added after the app is created BUT inside the same `create_app` function are covered; routes added on a separate sub-app are not.

**How to avoid:** Define all `/swarm` routes inside `create_app()` in the same pattern as `/session` routes. [VERIFIED: app.py architecture studied]

### Pitfall 6: `asyncio.Queue` Maxsize 256 and Long-Running Swarms

**What goes wrong:** A builder session with `QUEUE_MAXSIZE = 256` (sessions.py:24) may drop events if the SSE consumer disconnects and reconnects during a long swarm run.

**Why it happens:** `EventBusRenderer._put` drops the oldest event when the queue is full (renderer.py:52-58). For swarm coordination events (unlike streaming deltas), a dropped `swarm.assign` could leave a builder permanently in `waiting` state.

**How to avoid:** Swarm coordination events (`swarm.assign`, `swarm.gate`, `swarm.complete`) must NOT be routed exclusively through the queue. The queue is for the SSE transport to the human observer; the spawn-gate unblock (`gate_event.set()`) must happen in-process synchronously, independent of queue state.

---

## Open Questions

### 1. BridgeSwarm Coordinator Playbook — Does it Exist on Disk?

**What we know:** V25-CONTEXT.md D-05 states "coordinator prompt is seeded from BridgeSwarm's recovered coordinator playbook." The V25-CONTEXT.md specifics section says "use as the starting template for `voss/harness/swarm/prompts/coordinator.md`."

**What's unclear:** A thorough search of the Voss repo, SecondBrain vault, and the `~/Projects` directory found **no file containing BridgeSwarm coordinator playbook text**. The search found only planning-doc references to the playbook but no actual playbook content. The teardown note in the ROADMAP says "Coordinator template was recovered" but this may refer to logical/semantic recovery (i.e., the coordinator's behavior can be reconstructed from the A13 CONTEXT.md design) rather than a literal file.

**Risk if wrong:** The coordinator prompt must be authored from scratch, not seeded from a recovered template. This is not a blocker — the coordinator prompt can be authored based on A13-CONTEXT.md's `Coordinator Flow` section — but the planner should not plan a "copy recovered playbook" task.

**Recommendation:** Flag in Wave 0: "Author coordinator.md from A13 coordinator flow spec (no recovered playbook found on disk). Builder.md and reviewer.md also authored fresh." [ASSUMED: playbook text does not exist on disk — confirmed by search]

### 2. Pane-Binding Mechanism for Headless Swarm (VSWARM-09)

**What we know:** `agent_registry.rs` stores per-pane agent sessions. V25 is verified headlessly without a running voss-app. The `register_agent` Rust function takes `pane_id` — but headless runs have no real pane.

**What's unclear:** How to satisfy VSWARM-09 ("swarm spawn applies a layout preset and registers each agent session against its pane") in a headless test environment. The test asserts registry rows carry `swarm_id`/`role`/`owned_files` — but a headless Python integration test can't call a Tauri command.

**Recommendation:** For headless acceptance, the Python harness should maintain a SwarmStore-side index of session→swarm/role/ownedFiles. The agent_registry.rs migration is for the voss-app pane-binding surface (V24 scope); the headless test verifies the Python-side index. The acceptance criterion reads "agent_registry rows carry..." — clarify with planner whether this means the Rust SQLite DB or a Python-side SwarmStore record. [ASSUMED: Python-side SwarmStore index satisfies the headless test; Rust migration is thin and may be deferred to when voss-app spawn is wired]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.13 | All harness code | ✓ | 3.13 (`.venv/lib/python3.13`) | — |
| FastAPI / sse_starlette | SSE + routes | ✓ | already in deps | — |
| portalocker | JSONL event log | ✓ | already in deps (memory_store.py) | stdlib file lock |
| rusqlite | agent_registry migration | ✓ | already in Cargo.toml | — |
| pytest + httpx | Tests | ✓ | confirmed by existing test_server_app.py | — |
| fastapi.testclient | Route tests | ✓ | TestClient used in existing tests | — |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (harness test suite) |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_swarm_store.py -x` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/ tests/test_swarm_e2e.py -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VSWARM-01 | SwarmStore state reconstructs from JSONL replay | unit | `pytest tests/harness/test_swarm_store.py::test_replay_reconstructs_state -x` | ❌ Wave 0 |
| VSWARM-01 | JSONL is append-only (no rewrite) | unit | `pytest tests/harness/test_swarm_store.py::test_event_log_append_only -x` | ❌ Wave 0 |
| VSWARM-02 | All 5 swarm SSE event types in queue | unit | `pytest tests/harness/test_swarm_routes.py::test_swarm_sse_event_types -x` | ❌ Wave 0 |
| VSWARM-03 | POST/GET /swarm auth + 401 | unit | `pytest tests/harness/server/test_swarm_routes.py::test_swarm_auth -x` | ❌ Wave 0 |
| VSWARM-04 | Builder runs zero turns until assign | unit | `pytest tests/harness/test_swarm_store.py::test_spawn_gate_zero_turns_before_assign -x` | ❌ Wave 0 |
| VSWARM-05 | Deny write outside owned file | unit | `pytest tests/harness/test_swarm_store.py::test_ownership_denies_non_owned_write -x` | ❌ Wave 0 |
| VSWARM-06 | Overlap validation 4xx | unit | `pytest tests/harness/server/test_swarm_routes.py::test_overlap_rejected -x` | ❌ Wave 0 |
| VSWARM-07 | Recall hits scoped to ownedFiles | unit | `pytest tests/harness/test_swarm_store.py::test_recall_scoped_to_owned_files -x` | ❌ Wave 0 |
| VSWARM-08 | 3-role swarm spawns distinct models | unit | `pytest tests/harness/server/test_swarm_routes.py::test_per_role_model_routing -x` | ❌ Wave 0 |
| VSWARM-09 | Registry rows carry swarm_id/role/owned_files | unit | `pytest tests/harness/test_swarm_store.py::test_agent_registry_swarm_columns -x` | ❌ Wave 0 |
| VSWARM-10 | Operator escalation via /permission | unit | `pytest tests/harness/server/test_swarm_routes.py::test_operator_escalation -x` | ❌ Wave 0 |
| VSWARM-11 | Replay yields full task state timeline | unit | `pytest tests/harness/test_swarm_store.py::test_audit_replay_full_timeline -x` | ❌ Wave 0 |
| E2E bar | 2-builder enforced run (SPEC §acceptance) | integration | `pytest tests/test_swarm_e2e.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/harness/test_swarm_store.py -x`
- **Per wave merge:** `pytest tests/harness/ tests/test_swarm_e2e.py -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
All test files are new — none exist yet.
- [ ] `tests/harness/test_swarm_store.py` — covers VSWARM-01, 04, 05, 06, 07, 09, 11
- [ ] `tests/harness/server/test_swarm_routes.py` — covers VSWARM-02, 03, 06, 08, 10
- [ ] `tests/test_swarm_e2e.py` — the 2-builder enforced integration test (SPEC acceptance bar)
- [ ] `voss/harness/swarm_store.py` — SwarmStore (must exist before tests can import)
- [ ] `voss/harness/swarm/__init__.py`, `swarm/events.py` — event log writer
- [ ] `voss/harness/swarm/prompts/coordinator.md`, `builder.md`, `reviewer.md` — authored from scratch

**Existing test infrastructure that covers adjacent code:**
- `tests/harness/test_server_app.py` — uses `VOSS_SERVE_FAKE_TURN` test seam + `TestClient` pattern. V25 tests should follow the same fixture pattern (monkeypatch `_resolve_provider`, monkeypatch `run_turn`, use `TestClient`).
- `tests/harness/test_permissions*.py` — covers `PermissionGate.check`; V25 tests can import and reuse `PermissionGate` directly.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing `_BearerASGI` middleware covers all `/swarm` routes automatically |
| V3 Session Management | yes | SwarmStore state is in-process; JSONL is 0600 chmod (mirrors session_store.save) |
| V4 Access Control | yes | `PermissionGate.check` deny-wins layer is the access control for file writes |
| V5 Input Validation | yes | Pydantic v2 models for all request bodies; `jail_path` in tools.py for path traversal |
| V6 Cryptography | no | No crypto needed; swarm IDs are random hex |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Owned-file path traversal | Tampering | `jail_path(cwd, path)` in tools.py already applied before gate check; no new exposure |
| Cross-swarm event injection | Spoofing | Swarm events carry `swarm_id`; route handlers validate swarm exists before emitting |
| Gate bypass via `auto_yes` | Elevation of privilege | The ownership deny is at `project_policy` layer which fires BEFORE mode/auto_yes (permissions.py:288 runs before the mode check at :316) |
| JSONL injection | Tampering | JSON serialization is via `json.dumps` with no string formatting; no injection vector |
| Operator permission timeout | Denial of service | Existing `PERMISSION_TIMEOUT_S = 300.0` applies; swarm gates use same timeout |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | BridgeSwarm coordinator playbook text does not exist on disk | Open Questions | Low: prompt must be authored fresh (same effort) |
| A2 | `asyncio.Event` construction in async context is needed for Python 3.13 event loop compatibility | Pitfall 2 | Low: Python 3.10+ decoupled Event from loop |
| A3 | The path-scope pitfall (fnmatch normalization) needs explicit mitigation | Pitfall 1 | High: ownership deny would silently fail to fire |
| A4 | Python-side SwarmStore index satisfies VSWARM-09 headless test; Rust registry migration is secondary | Open Questions | Medium: if acceptance literally means agent_registry.sqlite rows, needs Tauri call from Python test |
| A5 | `MemoryStore.recall` post-filter (not signature change) is the cleaner scope implementation | VSWARM-07 | Low: either approach works; signature change is also valid |
| A6 | SQLite `ALTER TABLE ADD COLUMN DEFAULT NULL` guards via `PRAGMA table_info` check | VSWARM-09 | Low: standard SQLite pattern; alternative is separate migration schema version |

---

## State of the Art

| Old Approach (A13/BridgeSwarm) | V25 Approach | Superseded | Impact |
|-------------------------------|--------------|------------|--------|
| File-bus coordination (`.voss/swarm/tasks/*.md`) | In-process SSE event bus | A13-02..06 plans superseded | Eliminates fs-watch polling, wakeup races |
| Coordinator = single Opus call | Coordinator = full `ServerSession` | A13 D-03 reversed | Enables mid-run re-planning |
| Spawn timing race (`+2s` sleep) | `asyncio.Event` spawn gate | BridgeSwarm pattern | Zero-race deterministic test |
| Advisory scope (task file says "don't touch X") | `PermissionGate` deny-wins enforcement | A13 D-20 reversed | Hard wall, not honor system |
| `manifest.json` mutable snapshot | Append-only `events/*.jsonl` | — | Replay-capable audit |
| fs.watch completion detection | `swarm.worker_done` SSE event | A13 D-14/D-21 | Server-push, no polling |

---

## Sources

### Primary (HIGH confidence)
- `voss/harness/server/app.py` (full read) — `_run_turn`, `_resolve_provider`, `create_app`, route table, `_BearerASGI`, `_install_server_permissions`
- `voss/harness/server/sessions.py` (full read) — `ServerSession` dataclass, `SessionManager`
- `voss/harness/server/events.py` (full read) — all event types, `AgentEvent` union, `EventBusRenderer`
- `voss/harness/server/renderer.py` (full read) — `EventBusRenderer._emit`, `emit` server-only helper
- `voss/harness/permissions.py` (full read) — `PermissionGate.check`, `_check_impl` line 260, deny-wins layer lines 288-295, `WRITE` set line 54
- `voss/harness/memory_store.py` (full read) — `MemoryStore.recall` signature, `Hit` dataclass, JSONL append pattern
- `voss/harness/cognition_schemas.py` (lines 1-80) — `PermissionsConfig`, `ToolPolicy`, `STRICT` model_config
- `crates/voss-app-core/src/agent_registry.rs` (full read) — `AgentEntry`, `create_schema`, `register_agent`, existing SQL
- `crates/voss-app-core/src/layouts.rs` (full read) — `LayoutFile`, `active_preset` ("swarm" is a valid preset string)
- `voss/harness/cli.py:1015-1052` — `_render_code_recall_text` injection pattern for scoped recall
- `tests/harness/test_server_app.py` (lines 1-60) — `TestClient` fixture pattern, monkeypatch approach

### Secondary (MEDIUM confidence)
- `V25-SPEC.md`, `V25-CONTEXT.md`, `V25-DISCUSSION-LOG.md` — locked requirements and decisions
- `A13-CONTEXT.md`, `A13-01-SUMMARY.md` — file-bus design context, A13-01 shipped artifacts
- `V24-CONTEXT.md` — `swarmReconcile` consumer, honest-signal rule
- `.voss/decisions/` directory listing — confirmed existing decision file format

### Tertiary (LOW confidence — flagged as ASSUMED)
- BridgeSwarm playbook non-existence: search found no file; ASSUMED not present

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified by direct source inspection
- Architecture patterns: HIGH — all integration points verified with exact line numbers
- Pitfalls: HIGH — derived from direct reading of the code paths involved
- VSWARM-09 Rust migration: MEDIUM — pattern is well-established but exact migration guard needs verification at implementation time
- BridgeSwarm playbook: LOW — playbook text not found on disk

**Research date:** 2026-06-17
**Valid until:** 2026-07-17 (stable harness codebase; 30-day window)

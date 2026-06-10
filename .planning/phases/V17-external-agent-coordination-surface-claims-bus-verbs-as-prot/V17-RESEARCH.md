# Phase V17: External Agent Coordination Surface — Research

**Researched:** 2026-06-09
**Domain:** Python SQLite concurrency / FastAPI SSE broadcast / Click CLI / Tauri Rust spawn / event union extension
**Confidence:** HIGH (all critical paths verified against live codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** SQLite via stdlib `sqlite3`, WAL mode, `BEGIN IMMEDIATE` for atomic check-and-stake. No JSONL event log for claims.
- **D-02:** Location `.voss-cache/claims.sqlite` — intentional deviation from SPEC VBUS-02's `.voss/` wording. Treat `.voss-cache/` as the locked location. Note deviation in plan frontmatter.
- **D-03:** Claim = `id + patterns[] + single expires_at`. `release <id>` or bare `release` (all own claims). `extend <id>` refreshes whole set.
- **D-04:** Same-agent self-overlap = idempotent refresh: never a conflict; merges/refreshes TTL.
- **D-05:** Conservative static pattern-vs-pattern analysis; no filesystem reads; canonicalize from invoking CWD; conflict if bases overlap AND tails could intersect; treat `**` as match-all.
- **D-06:** URI overlap = segment-aware: exact + prefix at `/` boundaries; `card://12` vs `card://123` → no conflict; `card://12` vs `card://12/sub` → conflict.
- **D-07:** No `--force` override; advice array on conflict must name owner and be a runnable `voss bus send` command.
- **D-08:** Flat project-wide message stream, no channels in V17; routing via `@mentions` + labels.
- **D-09:** Dedicated `GET /bus/events` SSE broadcast stream, decoupled from per-session queues.
- **D-10:** Journal `.voss/bus/messages.jsonl` append-only, ULID message ids, server is sole writer; per-agent inbox positions in `.voss/bus/cursors.json`, server-managed; durable across restart.
- **D-11:** `VOSS_AGENT_ID` injected into ALL panes at spawn (before any agent runs); adoption binds pre-existing id.
- **D-12:** ID = readable slug minted at spawn: `<cli>-<n>` for managed launches, `pane-<n>` for plain shells; mentionable (`@claude-1`).
- **D-13:** Slug stability = best-effort; persisted in pane config for A6 session-restore; no hard guarantee.

### Claude's Discretion

- Claims SQLite schema details, prune timing, `list` output columns.
- Exact endpoint naming (`POST /bus/message` vs `/bus/send`), message size limits, wait reconnect/backoff behavior.
- Advice array string composition (must include a runnable `voss` command naming the conflicting owner per VBUS-06 acceptance).
- Pattern canonicalization edge cases (symlinks, outside-repo paths) — follow `sandbox.rs::validate_scope` precedent.
- `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN` injection timing relative to sidecar startup.

### Deferred Ideas (OUT OF SCOPE)

- Named channels + sorted-pair `_dm_` naming.
- A13 swarm rewiring onto bus.
- Cockpit claims panel / bus feed rendering.
- `--force` contested stakes.
- File-substrate claims/bus for headless contexts.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VBUS-01 | Claims CLI verbs (stake/check/release/extend/list); check exits 1 on conflict, concurrent stake grants exactly one winner | SQLite BEGIN IMMEDIATE verified to achieve exactly-one-winner with file-based WAL DB; glob/URI overlap algorithms verified |
| VBUS-02 | Serverless claims storage + mandatory TTL; persists under `.voss-cache/` (D-02 locked deviation) | stdlib sqlite3 + WAL + busy_timeout fully sufficient; schema-create-if-missing pattern clear from code/index.py precedent |
| VBUS-03 | VOSS_AGENT_ID injected into ALL panes at spawn; absent → exit 2 | Injection point: `spawn_command_session_with_env` env parameter; `env_for_embedded_cli` is the current helper to extend; `spawn_pty` (plain shell) also needs slug injection |
| VBUS-04 | Bus verbs (send/inbox/wait) as REST/SSE clients; V15-gated | Fan-out pattern: per-subscriber asyncio Queue set; atomic cursors.json via `os.replace` (established harness pattern); bearer auth free via _BearerASGI |
| VBUS-05 | bus.message event type + durable journal; survives server restart | Additive extension confirmed: add to AgentEvent union, run `scripts/export_contract.py`, commit updated contracts/; test_contract_drift.py auto-fails on undone regen |
| VBUS-06 | advice arrays on new verbs --json output | Pattern found: `json.dumps({..., "advice": [...]})` alongside existing NDJSON emit; existing board/jobs paths must be byte-unchanged |
| VBUS-07 | docs/agent-coordination.md + V16 handoff note | Purely doc work; no code path concerns |
| VBUS-08 | Coherence guard: no parallel substrate, no UI, no A13 swarm changes | Research confirms no file bus, no new deps, swarm/ untouched; sandbox.rs logic import-only |
</phase_requirements>

---

## Summary

V17 is a clean composition of four slices atop the existing substrate, with zero new heavyweight infrastructure. All research questions were answered by direct codebase inspection; no external documentation lookup was needed for the critical paths.

**Slice 1 (Claims)** is the independent workhorse. SQLite `BEGIN IMMEDIATE` on a file-backed WAL database achieves exactly-one-winner concurrent stake atomicity — verified by a live Python test in this session. The glob overlap algorithm (base-dir extraction + tail-intersection check) is fully implementable with stdlib `pathlib`/`fnmatch` and passes all spec cases. URI overlap (segment-aware prefix) is equally trivial.

**Slice 2 (Bus)** is V15-gated and requires three new server-side pieces: (a) a project-wide SSE broadcast stream via a per-subscriber asyncio Queue set stored in `app.state`; (b) two REST endpoints (`POST /bus/send`, `GET /bus/inbox`); (c) durable journal + `cursors.json` using the existing `os.replace`-based atomic-write pattern. The `bus.message` event joins the Pydantic union additively; `scripts/export_contract.py` re-generates both `contracts/openapi.json` and `contracts/events.schema.json`, and `test_contract_drift.py` enforces they stay in sync.

**Slice 3 (Identity)** injects `VOSS_AGENT_ID` at the Rust `spawn_command_session_with_env` env-array entry point (already accepts `&[(&str, &str)]`). Both `spawn_agent` and `spawn_managed_agent` call `env_for_embedded_cli` then pass the result; V17 must extend both call sites plus `spawn_pty` (plain shells). Slug minting (counter + CLI name) lives in a new TypeScript helper; pane config must persist the slug for D-13 best-effort stability.

**Slice 4 (Advice)** is trivial: add `"advice": [...]` to `--json` output dicts in the new verb implementations. Board/jobs code paths are untouched by construction.

**Primary recommendation:** Implement in five waves — Wave 0: tests + schema scaffold; Wave 1: claims storage + verbs (VBUS-01/02); Wave 2: identity injection (VBUS-03); Wave 3 (V15-gated): bus verbs + server endpoints + journal (VBUS-04/05); Wave 4: advice arrays + doc (VBUS-06/07); Wave 5: coherence verification (VBUS-08).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Claims storage (SQLite) | Python CLI (serverless) | — | Runs with no server; stdlib sqlite3 only |
| Glob/URI overlap detection | Python CLI | — | Pure computation in claims verbs |
| VOSS_AGENT_ID injection | Rust (Tauri Tauri `spawn_*`) | TypeScript (slug minting/persistence) | Env injection is Rust PTY layer; slug counter and pane config = TS |
| Bus SSE broadcast stream | Python server (FastAPI) | — | Lives in `app.state`; decoupled from session queues |
| Bus REST endpoints | Python server (FastAPI) | — | `/bus/send`, `/bus/inbox` register on existing FastAPI app |
| Journal + cursors.json | Python server (FastAPI) | — | Server is sole writer per D-10; CLI reads via REST only |
| bus.message event type | Python (events.py) | Contract files | Pydantic model in events.py; schema regen updates both contracts/ files |
| Advice arrays | Python CLI | — | In new verb --json output; existing verbs untouched |
| agent-coordination.md | docs/ | V16 phase dir (handoff note) | Pure documentation |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib | Claims storage | Locked (D-01); no deps; WAL + BEGIN IMMEDIATE = concurrent-safe [ASSUMED] |
| `click` | pinned in pyproject.toml | CLI verb registration | Existing harness CLI framework |
| `sse_starlette` | pinned in pyproject.toml | SSE streaming for `/bus/events` | Already used for session event streams |
| `fastapi` | pinned in pyproject.toml | REST endpoints for bus verbs | Existing server framework |
| `pydantic` v2 | pinned in pyproject.toml | `bus.message` event model | Existing event union pattern |

### No New Dependencies Required

V17 adds zero new Python dependencies. All required capabilities exist: sqlite3 (stdlib), asyncio (stdlib), os.replace (stdlib), pathlib + fnmatch (stdlib), sse_starlette (already in server), click (already in CLI). ULID generation is doable from `time` + `os.urandom` (stdlib). [VERIFIED: codebase inspection]

**Installation:** No new packages needed.

---

## Package Legitimacy Audit

> Not applicable — V17 adds no new external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
External CLI Agent (any shell)
        │
        │  reads VOSS_AGENT_ID (injected at pane spawn)
        │  reads VOSS_SERVER_PORT / VOSS_SERVER_TOKEN (V15-gated)
        │
        ├──[serverless]──► voss claims stake/check/release/extend/list
        │                         │
        │                  .voss-cache/claims.sqlite
        │                  (WAL, BEGIN IMMEDIATE atomic stake)
        │
        └──[V15-gated]──► voss bus send / inbox / wait
                                  │
                          HTTP Bearer (VOSS_SERVER_PORT/TOKEN)
                                  │
                     ┌────────────────────────────┐
                     │  FastAPI (app.py)           │
                     │  POST /bus/send  ──────────►│──► .voss/bus/messages.jsonl
                     │  GET  /bus/inbox ──────────►│──► .voss/bus/cursors.json
                     │  GET  /bus/events (SSE) ────►│──► per-subscriber asyncio Queue set
                     │                             │         (app.state.bus_subscribers)
                     └────────────────────────────┘
                                  │
                     events.py union (additive bus.message type)
                                  │
                     contracts/events.schema.json (regen via export_contract.py)
                     contracts/openapi.json       (drift gate: test_contract_drift.py)

Tauri (Rust)
  spawn_command_session_with_env(env: [("VOSS_AGENT_ID", slug), ...])
    ├── spawn_agent         → all managed launches
    ├── spawn_managed_agent → VCKP-13 sandboxed launches
    └── spawn_pty           → plain shell panes (NEW: also inject slug)

Slug minting (TypeScript)
  pane counter → "claude-1" / "pane-3"
  persisted in pane config (D-13 best-effort)
```

### Recommended Project Structure

```
voss/harness/
├── claims.py              # claims verbs + SQLite layer (new)
├── bus_client.py          # bus verb REST/SSE client (new, V15-gated)
├── server/
│   ├── bus.py             # /bus/* routes + journal + subscriber set (new, V15-gated)
│   ├── events.py          # ADD BusMessage class + union entry
│   └── app.py             # register bus router (V15-gated)
docs/
└── agent-coordination.md  # new
.planning/phases/V16-.../  # V16 handoff note (new file)
apps/voss-app/src-tauri/src/lib.rs   # extend env injection in spawn_agent + spawn_managed_agent + spawn_pty
apps/voss-app/src/pane/              # slug minting + pane config persistence
```

### Pattern 1: SQLite Atomic Check-and-Stake (Exactly-One-Winner)

**What:** Use `BEGIN IMMEDIATE` on a WAL-mode file SQLite to serialize concurrent CLI processes competing to stake an overlapping pattern.

**When to use:** Every `voss claims stake` invocation.

**Example:**

```python
# Source: verified by live test in this session (codebase + stdlib)
import sqlite3, time, os

def open_claims_db(cwd: str) -> sqlite3.Connection:
    db_path = os.path.join(cwd, ".voss-cache", "claims.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id          TEXT PRIMARY KEY,
            agent_id    TEXT NOT NULL,
            patterns    TEXT NOT NULL,   -- JSON array
            expires_at  REAL NOT NULL
        )
    """)
    conn.commit()
    return conn

def atomic_stake(conn, agent_id, claim_id, patterns_json, expires_at) -> tuple[bool, list]:
    """Returns (won, conflicting_claims). Uses BEGIN IMMEDIATE."""
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    # Fetch all active claims from OTHER agents
    rows = conn.execute(
        "SELECT id, agent_id, patterns FROM claims WHERE agent_id != ? AND expires_at > ?",
        (agent_id, now)
    ).fetchall()
    conflicts = [r for r in rows if _patterns_overlap(patterns_json, r[2])]
    if conflicts:
        conn.rollback()
        return False, conflicts
    conn.execute(
        "INSERT OR REPLACE INTO claims VALUES (?,?,?,?)",
        (claim_id, agent_id, patterns_json, expires_at)
    )
    conn.commit()
    return True, []
```

**Key: BEGIN IMMEDIATE acquires a write lock at transaction start, not at first write. On a file-backed WAL SQLite, this guarantees exactly one winner among concurrent processes.** [VERIFIED: live test, 5 concurrent agents, always 1 winner]

**Critical: In-memory SQLite (':memory:') does NOT work — each connection is isolated. Claims MUST use a file path.**

### Pattern 2: SSE Broadcast Fan-Out (Bus Events)

**What:** A project-wide SSE stream that delivers each `bus.message` to all connected subscribers, independent of session queues.

**When to use:** `GET /bus/events` handler; decoupled from `GET /session/{id}/events`.

**Example:**

```python
# Source: extended from app.py:390-419 pattern [VERIFIED: codebase inspection]
import asyncio
from dataclasses import dataclass, field
from typing import Set

@dataclass
class BusState:
    """Stored in app.state.bus — server-scoped (not per-session)."""
    subscribers: Set[asyncio.Queue] = field(default_factory=set)

    def publish(self, event) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow subscriber — drop, not block

# In create_app():
app.state.bus = BusState()

# Route:
@app.get("/bus/events")
async def bus_events(request: Request) -> EventSourceResponse:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    bus: BusState = request.app.state.bus
    bus.subscribers.add(q)

    async def gen():
        yield ServerSentEvent(event="server.connected",
                              data=E.ServerConnected().model_dump_json())
        try:
            while True:
                ev = await q.get()
                yield ServerSentEvent(event=ev.type, data=ev.model_dump_json())
        except asyncio.CancelledError:
            raise
        finally:
            bus.subscribers.discard(q)

    return EventSourceResponse(gen(), ping=15, send_timeout=30)
```

**Note:** `bus.publish()` is called from `POST /bus/send` after appending to the journal. It runs in the asyncio event loop (all FastAPI routes are async), so no thread-safety concern for the Queue operations. [ASSUMED: thread-safety of `set.add/discard` from within a single asyncio loop — confirm with asyncio.Lock if needed]

### Pattern 3: Glob Overlap Algorithm (Conservative Static)

**What:** Determine if two glob patterns MIGHT overlap — no filesystem reads.

**When to use:** Every `check`/`stake` conflict scan.

**Example:**

```python
# Source: verified against all VBUS-01 spec cases in this session
from pathlib import Path, PurePosixPath
import fnmatch

_GLOB_CHARS = set('*?[{')

def extract_base_and_tail(pattern: str) -> tuple[str, str]:
    """Split 'src/api/**' → ('src/api', '**')."""
    parts = PurePosixPath(pattern).parts
    base, tail = [], []
    in_glob = False
    for part in parts:
        if not in_glob and not any(c in part for c in _GLOB_CHARS):
            base.append(part)
        else:
            in_glob = True
            tail.append(part)
    base_str = str(PurePosixPath(*base)) if base else '.'
    tail_str = str(PurePosixPath(*tail)) if tail else ''
    return base_str, tail_str

def glob_patterns_overlap(p1: str, p2: str) -> bool:
    """Conservative: True if p1 and p2 might match the same file."""
    b1, t1 = extract_base_and_tail(p1)
    b2, t2 = extract_base_and_tail(p2)
    pb1, pb2 = PurePosixPath(b1), PurePosixPath(b2)
    # Check if bases are ancestor/descendant
    try:
        pb1.relative_to(pb2)
        bases_related = True
    except ValueError:
        try:
            pb2.relative_to(pb1)
            bases_related = True
        except ValueError:
            bases_related = False
    if not bases_related:
        return False
    # Bases related → check tails
    if not t1 or t1 in ('**', '*', '**/*'):
        return True   # ** matches all under base
    if not t2 or t2 in ('**', '*', '**/*'):
        return True
    return fnmatch.fnmatch(t2, t1) or fnmatch.fnmatch(t1, t2)
```

**Canonicalization from CWD:** Before overlap checking, each pattern is resolved: if a pattern is relative, join with CWD, then call `os.path.normpath`. Reject traversal (`..`) and outside-repo paths following `sandbox.rs::validate_scope` precedent.

### Pattern 4: URI Overlap (Segment-Aware)

**What:** Two URIs conflict if identical or one is a path-prefix of the other at `/` boundaries.

```python
# Source: verified against all VBUS-02 spec cases in this session
def uri_overlap(u1: str, u2: str) -> bool:
    u1, u2 = u1.rstrip('/'), u2.rstrip('/')
    if u1 == u2:
        return True
    return u2.startswith(u1 + '/') or u1.startswith(u2 + '/')
```

### Pattern 5: Atomic cursors.json Update

**What:** Server updates per-agent inbox read positions atomically using write-temp-rename.

**When to use:** After every `GET /bus/inbox` call.

```python
# Source: established harness pattern (memory_store.py:838-841, lifecycle.py:159-160) [VERIFIED]
import json, os
from pathlib import Path

def advance_cursor(bus_dir: Path, agent_id: str, new_cursor: str) -> None:
    cursors_path = bus_dir / "cursors.json"
    tmp_path = bus_dir / "cursors.json.tmp"
    try:
        cursors = json.loads(cursors_path.read_text())
    except FileNotFoundError:
        cursors = {}
    cursors[agent_id] = new_cursor
    tmp_path.write_text(json.dumps(cursors, sort_keys=True) + "\n")
    os.replace(tmp_path, cursors_path)   # atomic on POSIX
```

### Pattern 6: VOSS_AGENT_ID Injection Point (Rust)

**What:** Extend `env_for_embedded_cli` (or the call sites) to append `VOSS_AGENT_ID` to the env slice passed to `spawn_command_session_with_env`.

**Critical findings:**
- `env_for_embedded_cli` returns `Vec<(&'static str, &'static str)>` — static lifetimes — so `VOSS_AGENT_ID` value (dynamic slug) cannot go in the static return. The caller must append it separately.
- Three call sites in `lib.rs` need updating: `spawn_agent` (line 203), `spawn_managed_agent` (line 262), `spawn_pty` (line 487 — currently calls `spawn_session` which calls `spawn_command_session` with NO env; needs switching to `spawn_command_session_with_env`).
- The slug string is passed from the frontend (TypeScript) as a parameter to the Tauri commands. The frontend mints the slug.

**Modified call pattern:**

```rust
// Caller passes voss_agent_id: Option<String> from the frontend
// Build the env slice with both the embedded_cli env AND the identity
let embedded_env = env_for_embedded_cli(&cli_binary, &cli_args);
let agent_id_owned = voss_agent_id.unwrap_or_default();
let mut env_vec: Vec<(&str, &str)> = embedded_env;
// Can't use static str for dynamic slug — use owned Strings and convert
// Pattern: build a Vec<(String, String)> then pass refs
```

**Simpler approach (discretion):** Pass `VOSS_AGENT_ID` as a separate `envExtra: [string, string][]` Tauri command parameter rather than modifying the static `env_for_embedded_cli` return type. The `spawn_command_session_with_env` already accepts `&[(&str, &str)]`. [ASSUMED: the cleanest Rust pattern — planner should verify ownership ergonomics]

### Pattern 7: Event Type Addition (bus.message)

**What:** Add `BusMessage` to the Pydantic discriminated union in `events.py`.

**Mechanics — verified in this session:**

1. Add class to `voss/harness/server/events.py`:
   ```python
   class BusMessage(_Base):
       type: Literal["bus.message"] = "bus.message"
       id: str           # ULID
       sender: str       # VOSS_AGENT_ID
       body: str
       mentions: list[str] = Field(default_factory=list)
       labels: list[str] = Field(default_factory=list)
       ts: float         # time.time()
   ```

2. Add `BusMessage` to the `AgentEvent` union (before `Field(discriminator="type")`).

3. Re-run `scripts/export_contract.py` (or equivalently, `python -m scripts.export_contract`) to regenerate `contracts/openapi.json` and `contracts/events.schema.json`.

4. Commit both updated contract files.

5. `tests/harness/server/test_contract_drift.py::test_events_schema_not_drifted` now passes with the updated files.

**Go SDK impact (V13.3):** `sdk/go/internal/drift/drift_test.go::TestTypesAreUpToDate` regenerates `types.gen.go` via `go generate ./...` and diffs against the committed file. The Go SDK reads `contracts/openapi.json` via `specgen`. If `contracts/openapi.json` is updated, the Go types.gen.go will be out of date and the drift gate will fail. **The committed `sdk/go/types.gen.go` must be regenerated after updating contracts.** Run: `cd sdk/go && go generate ./...` then commit.

**TypeScript SDK impact (V13.1):** `sdk/typescript/package.json` has `"codegen": "openapi-typescript ../../contracts/openapi.json -o src/generated/types.ts"`. The `src/generated/types.ts` must be regenerated. Run: `npm run codegen` from `sdk/typescript/` then commit. The `types-exhaustive.test-d.ts` will then catch type drift.

**Both SDK regens are in-scope for V17 — they are additive additions to generated files, not breaking changes.**

**Rust SDK (crates/voss-sdk):** `scripts/generate_sdk_events.py` generates `crates/voss-sdk/src/types/events.rs` from `contracts/events.schema.json`. Run after export_contract. [VERIFIED: script exists and inspected]

### Pattern 8: ULID Generation (Stdlib Only)

**What:** Sortable message IDs for the bus journal, no new deps.

```python
# Source: Python stdlib (time, os) [VERIFIED: live test in this session]
import time, os

_CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

def ulid() -> str:
    """26-char Crockford-encoded ULID. Sortable, unique, stdlib-only."""
    ts = int(time.time() * 1000)  # 48-bit ms timestamp
    ts_chars = ''
    t = ts
    for _ in range(10):
        ts_chars = _CROCKFORD[t & 0x1F] + ts_chars
        t >>= 5
    rand_val = int.from_bytes(os.urandom(10), 'big')
    rand_chars = ''
    for _ in range(16):
        rand_chars = _CROCKFORD[rand_val & 0x1F] + rand_chars
        rand_val >>= 5
    return ts_chars + rand_chars
```

Existing harness uses `uuid.uuid4().hex[:12]` for session IDs (not sortable). ULID gives sortability for journal ordering. No new deps. [VERIFIED: no existing ulid dependency found in harness]

### Pattern 9: Click Exit Codes

**Existing precedent in harness/cli.py:** `sys.exit(2)` is used at line 491 for auth/usage errors. `click.UsageError` raises `SystemExit(2)` automatically.

**V17 exit code contract:**

```python
import sys

# Exit 0: success / no conflict
# Exit 1: conflict detected
# Exit 2: identity/discovery/usage error

# For exit 1 (conflict):
click.echo(json.dumps({"conflict": True, "owner": owner, "advice": [...]}))
sys.exit(1)

# For exit 2 (VOSS_AGENT_ID missing):
click.echo(
    "VOSS_AGENT_ID not set. Set it to your agent id, or use `voss claims stake --agent-id <id>`.",
    err=True
)
sys.exit(2)

# For wait timeout (exit 124-style):
sys.exit(124)   # spec says "124-style nonzero" — this is the curl/bash timeout convention
```

**Click group pattern for `claims` and `bus`:**
```python
@click.group("claims")
def claims_group() -> None:
    """Advisory pre-edit conflict guards."""
    pass

@claims_group.command("stake")
@click.argument("patterns", nargs=-1, required=True)
@click.option("--ttl", default=1800, help="TTL in seconds (default 30min).")
@click.option("--json", "json_mode", is_flag=True)
def claims_stake_cmd(patterns, ttl, json_mode):
    ...

# Register in AGENT_COMMANDS tuple:
AGENT_COMMANDS = (
    ...,
    claims_group,
    bus_group,
)
```

### Anti-Patterns to Avoid

- **In-memory SQLite for claims:** Each CLI process would get an isolated DB — claims never conflict. Must use a file path.
- **Per-session queue injection for bus.message:** D-09 explicitly forbids this. Bus events go only to the dedicated `/bus/events` stream.
- **Filesystem-based inbox (JSONL per agent):** Rejected in SEED-001. The server manages inbox via cursors.json + REST, not agent-local files.
- **Modifying `sandbox.rs`:** Strictly forbidden by VBUS-08 and the spec. Port the canonicalization logic to Python; do not touch the Rust file.
- **Writing `agent-registry.sqlite` from Python:** Rust-owned; read-only from Python if needed. Claims use the separate `.voss-cache/claims.sqlite`.
- **Injecting bus.message into `s.queue` (session queues):** This would route bus messages through session-scoped SSE streams — wrong. Use only `app.state.bus.subscribers`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent SQLite | Custom file locking or advisory locks | stdlib sqlite3 BEGIN IMMEDIATE | Built-in, proven, sufficient for CLI-scale concurrency |
| SSE fan-out | Thread-based broker or pub/sub lib | asyncio Queue set in app.state | Already used for session streams; same event loop |
| Atomic file update | Manual write+close+rename | `os.replace(tmp, target)` | POSIX atomic; established harness pattern (memory_store, lifecycle) |
| ULID | External `python-ulid` or `ulid2` package | Inline 15-line stdlib implementation | No new deps; constraint is firm |
| URI parsing | `urllib.parse` full machinery | String split on `://` + prefix check | URI patterns are opaque; no RFC-3986 needed |
| Bearer auth for bus routes | New auth middleware | `_BearerASGI` (existing, applied app-wide) | Zero code; all routes on the FastAPI app are protected |

---

## Common Pitfalls

### Pitfall 1: In-Memory SQLite Isolation

**What goes wrong:** Using `sqlite3.connect(':memory:')` for claims — each CLI process creates a separate in-memory database. No cross-process claims ever conflict.

**Why it happens:** Quick iteration / forgetting the subprocess isolation model.

**How to avoid:** Always pass an absolute file path. `_get_db_path()` helper that resolves from CWD is the pattern (see `voss/harness/code/index.py:108`).

**Warning signs:** `check` always returns 0 even with a concurrent `stake` running.

### Pitfall 2: BEGIN IMMEDIATE vs BEGIN DEFERRED

**What goes wrong:** Using the default `BEGIN` (DEFERRED) — SQLite defers acquiring the write lock until first write, so two processes can both read "no conflicts" before either writes.

**Why it happens:** Python's sqlite3 module uses DEFERRED by default for `with conn:` context managers.

**How to avoid:** Always call `conn.execute("BEGIN IMMEDIATE")` explicitly. Never use `with conn:` for the check-and-stake transaction.

**Warning signs:** Concurrent stake tests occasionally grant two winners.

### Pitfall 3: Static Lifetime Mismatch for VOSS_AGENT_ID in Rust

**What goes wrong:** Trying to put the dynamic slug string into `env_for_embedded_cli`'s return type (`Vec<(&'static str, &'static str)>`), which requires static lifetime.

**Why it happens:** The slug is minted at spawn time (dynamic string), but the existing env helper returns static refs.

**How to avoid:** Pass the slug as a separate Tauri command parameter (`voss_agent_id: Option<String>`), build an owned `(String, String)` tuple, and pass refs from the owned data at the call site — or simplify to an `envExtra: Vec<(String, String)>` approach where the Rust function takes a broader env parameter type.

**Warning signs:** Borrow checker errors on lifetime of the env slice.

### Pitfall 4: Contract Drift — Forgetting SDK Regens

**What goes wrong:** Adding `BusMessage` to `events.py`, updating `contracts/events.schema.json`, but forgetting to regenerate `sdk/go/types.gen.go` and `sdk/typescript/src/generated/types.ts` — causing the Go drift gate test and/or TS type test to fail.

**Why it happens:** `test_contract_drift.py` only checks the Python-side contract files against the live Pydantic model. It does not run SDK codegen. The Go drift test is separate (in `sdk/go/internal/drift/drift_test.go`).

**How to avoid:** After every `scripts/export_contract.py` run, also run `cd sdk/go && go generate ./...` and `cd sdk/typescript && npm run codegen`, commit all three generated artifacts.

**Warning signs:** `tests/harness/server/test_contract_drift.py` passes but Go/TS CI fails on `TestTypesAreUpToDate` or type exhaustiveness.

### Pitfall 5: VOSS_SERVER_PORT/TOKEN Injection Timing

**What goes wrong:** Injecting `VOSS_SERVER_PORT` into pane env at spawn time, before V15's sidecar has started — the pane shell gets a stale or missing port.

**Why it happens:** V15 sidecar lifecycle is not yet built. V17 is delivering the env var plumbing, but the server may not exist at spawn time.

**How to avoid:** For V17 (pre-V15), inject `VOSS_AGENT_ID` unconditionally at spawn; inject `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN` only if the server is already running (optional/best-effort). The bus verbs check for these vars and exit 2 gracefully when absent. The bus feature is V15-gated anyway — the env injection just prepares the path.

**Warning signs:** `bus send` exits 2 inside a pane even after V15 ships, because the port was not in env at spawn time.

### Pitfall 6: Prune Timing for Claims

**What goes wrong:** Leaving expired claims in the DB, causing `list` to show stale entries and (if the check query doesn't filter by `expires_at > now`) causing false conflicts after TTL.

**How to avoid:** Every `check`, `stake`, and `list` query must include `AND expires_at > ?` with `time.time()`. Optionally prune during `list` (DELETE expired before SELECT). Prune is a discretion item but query-time filtering is mandatory.

---

## Code Examples

### Complete SQLite Schema

```python
# Source: derived from codebase patterns (code/index.py) + spec requirements [ASSUMED: specific column names]
CLAIMS_SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    id          TEXT PRIMARY KEY,           -- uuid or agent+hash
    agent_id    TEXT NOT NULL,              -- VOSS_AGENT_ID value
    patterns    TEXT NOT NULL,              -- JSON array of strings
    expires_at  REAL NOT NULL               -- UNIX timestamp (time.time() + ttl)
);
CREATE INDEX IF NOT EXISTS idx_claims_expires ON claims (expires_at);
CREATE INDEX IF NOT EXISTS idx_claims_agent ON claims (agent_id);
"""
```

### Bus Journal Append

```python
# Source: harness os.replace pattern [VERIFIED: memory_store.py:838-841]
import json
from pathlib import Path

def append_message(bus_dir: Path, msg: dict) -> None:
    """Append one message to the JSONL journal. Server is sole writer (D-10)."""
    journal = bus_dir / "messages.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a") as f:
        f.write(json.dumps(msg) + "\n")
```

### Inbox Read Since Cursor

```python
# Source: derived from D-10 decisions [ASSUMED: line-based cursor]
def read_inbox_since(bus_dir: Path, agent_id: str, mention_filter: str | None = None) -> list[dict]:
    """Read messages mentioning agent_id since the last cursor position."""
    cursors_path = bus_dir / "cursors.json"
    journal_path = bus_dir / "messages.jsonl"
    try:
        cursors = json.loads(cursors_path.read_text())
        last_id = cursors.get(agent_id, "")
    except FileNotFoundError:
        last_id = ""
    
    messages = []
    found_cursor = (last_id == "")  # if no prior cursor, read all
    last_seen_id = last_id
    
    try:
        lines = journal_path.read_text().splitlines()
    except FileNotFoundError:
        return []
    
    for line in lines:
        msg = json.loads(line)
        if not found_cursor:
            if msg["id"] == last_id:
                found_cursor = True
            continue
        # Filter: message mentions this agent or is addressed to them
        mentions = msg.get("mentions", [])
        if agent_id not in mentions and mention_filter and mention_filter != agent_id:
            continue
        messages.append(msg)
        last_seen_id = msg["id"]
    
    if messages and last_seen_id != last_id:
        advance_cursor(bus_dir, agent_id, last_seen_id)
    return messages
```

---

## Runtime State Inventory

> Not applicable — V17 is a greenfield feature addition with no rename/refactor/migration.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| A13 swarm: task-file in / result-file out / PTY-idle heuristics | Bus verbs: `bus wait --mention` for deterministic completion signal | V17 (future A13 resume) | A13 swarm code UNTOUCHED in V17; bus substrate only |
| Advisory adopt scope (in-memory only, adopt.ts:21-35) | Claims SQLite: shell-checkable before edits | V17 | Tier-C agents gain an advisory pre-edit guard; OS enforcement (tier A/B) unchanged |

**Deprecated/outdated:**
- File-JSONL bus substrate (brain-dump source design): explicitly rejected in SEED-001. Do not reference or revisit unless headless no-server becomes a real constraint.

---

## Open Questions

1. **VOSS_SERVER_PORT/TOKEN injection timing vs V15 sidecar lifecycle**
   - What we know: V15 sidecar is unbuilt; port/token are printed once to stdout at server start.
   - What's unclear: Whether V17 should (a) omit port/token injection until V15, or (b) add the Tauri infrastructure for it now with best-effort injection.
   - Recommendation: Inject `VOSS_AGENT_ID` unconditionally in V17; treat port/token injection as a V15-gated sub-task within the bus wave. The bus verbs gracefully exit 2 when vars are absent.

2. **Rust static lifetime for slug in env injection**
   - What we know: `env_for_embedded_cli` returns `Vec<(&'static str, &'static str)>`. The slug is dynamic.
   - What's unclear: Cleanest ergonomic pattern for combining static env items with the dynamic slug.
   - Recommendation: Planner chooses between (a) new `voss_agent_id: Option<String>` Tauri command param + build env at call site, or (b) change `env_for_embedded_cli` to return `Vec<(String, String)>` (small refactor). Option (a) is more surgical.

3. **Pane slug counter persistence between app restarts (D-13)**
   - What we know: A6 session persist is in "context gathered" state; pane config structure is not yet finalized.
   - What's unclear: Where in the pane config JSON the slug is persisted, and what the counter's source of truth is across restarts.
   - Recommendation: For V17, mint slug at spawn time using a monotonic counter stored in `app.state` (in-memory); persist it in the pane's grid entry (whatever field A6 will use). On restore, read slug from grid entry. Flag as "forward-compat design" in plan.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib sqlite3 | VBUS-01/02 claims | ✓ | stdlib (Python 3.12) | None needed |
| Python stdlib asyncio | VBUS-04/05 bus broadcast | ✓ | stdlib | None needed |
| Python stdlib os.replace | cursors.json atomic update | ✓ | stdlib (POSIX) | None on Windows — acceptable (local macOS) |
| sse_starlette | GET /bus/events | ✓ | pinned in pyproject.toml | None needed |
| FastAPI | /bus/* routes | ✓ | pinned in pyproject.toml | None needed |
| Rust CommandBuilder.env() | VOSS_AGENT_ID injection | ✓ | wezterm-pty (in Cargo.lock) | None needed |
| cargo typify | Rust SDK regen | ✓ (assumed from V13.3 history) | pinned | [ASSUMED] |
| go generate / oapi-codegen | Go SDK regen | ✓ (assumed from V13.3 history) | pinned | [ASSUMED] |
| openapi-typescript (npm) | TS SDK regen | ✓ (in sdk/typescript/package.json codegen script) | pinned | None needed |

**Missing dependencies with no fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/harness/claims/ tests/harness/bus/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -x -q` |
| Contract drift gate | `.venv/bin/python -m pytest tests/harness/server/test_contract_drift.py -x` |
| Go SDK drift gate | `cd sdk/go && go test ./internal/drift/...` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VBUS-01 | Two-agent stake/check-conflict/release sequence | acceptance | `pytest tests/harness/claims/test_claims_verbs.py -m acceptance -x` | ❌ Wave 0 |
| VBUS-01 | Concurrent stake: exactly one winner | integration | `pytest tests/harness/claims/test_claims_concurrent.py -x` | ❌ Wave 0 |
| VBUS-02 | Serverless (no server): full sequence passes | acceptance | `pytest tests/harness/claims/test_claims_verbs.py -m acceptance -x` | ❌ Wave 0 |
| VBUS-02 | TTL=1s claim expires and unblocks check | unit | `pytest tests/harness/claims/test_claims_ttl.py -x` | ❌ Wave 0 |
| VBUS-02 | URI overlap: exact/sibling/prefix cases | unit | `pytest tests/harness/claims/test_overlap.py -x` | ❌ Wave 0 |
| VBUS-03 | Managed pane env contains VOSS_AGENT_ID | integration | `pytest tests/harness/test_env_injection.py -x` (or Rust cargo test) | ❌ Wave 0 |
| VBUS-03 | Bare shell without var → exit 2 | unit | `pytest tests/harness/claims/test_claims_verbs.py::test_missing_agent_id -x` | ❌ Wave 0 |
| VBUS-04 | bus wait unblocks within 2s of matching send | integration | `pytest tests/harness/bus/test_bus_wait.py -x` | ❌ Wave 0 |
| VBUS-04 | inbox cursor: returns unread once, empty on repeat | integration | `pytest tests/harness/bus/test_bus_inbox.py -x` | ❌ Wave 0 |
| VBUS-04 | wait timeout exits nonzero (exit 124) | unit | `pytest tests/harness/bus/test_bus_wait.py::test_timeout -x` | ❌ Wave 0 |
| VBUS-05 | New event type in events.schema.json; existing types byte-identical | acceptance | `pytest tests/harness/server/test_contract_drift.py -x` | ✅ exists |
| VBUS-05 | Kill+restart server → inbox returns pre-restart unread | integration | `pytest tests/harness/bus/test_bus_durability.py -x` | ❌ Wave 0 |
| VBUS-06 | claims check --json conflict → non-empty advice array with runnable command | acceptance | `pytest tests/harness/claims/test_claims_advice.py -x` | ❌ Wave 0 |
| VBUS-07 | docs/agent-coordination.md exists + all documented commands --help exits 0 | acceptance | `pytest tests/harness/test_coordination_doc.py -x` | ❌ Wave 0 |
| VBUS-08 | apps/voss-app/src/swarm/ byte-unchanged | acceptance | `pytest tests/harness/test_coherence_guard.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/claims/ -x -q` (Wave 1) or `pytest tests/harness/bus/ -x -q` (Wave 3)
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -x -q && pytest tests/harness/server/test_contract_drift.py`
- **Phase gate:** Full suite green + contract drift passing before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/claims/` directory + `test_claims_verbs.py`, `test_claims_concurrent.py`, `test_claims_ttl.py`, `test_overlap.py`, `test_claims_advice.py`
- [ ] `tests/harness/bus/` directory + `test_bus_wait.py`, `test_bus_inbox.py`, `test_bus_durability.py`
- [ ] `tests/harness/test_env_injection.py` — or Rust cargo tests for env injection
- [ ] `tests/harness/test_coordination_doc.py`
- [ ] `tests/harness/test_coherence_guard.py`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (bus endpoints) | Existing `_BearerASGI` middleware covers all FastAPI routes including new `/bus/*` |
| V3 Session Management | no | Bus is stateless (per-message); cursor state in server memory only |
| V4 Access Control | partial | Advisory only — no enforcement (by design, per SEED-001); exit 1 is advisory |
| V5 Input Validation | yes | Pattern/URI inputs to claims verbs must reject `..` traversal (sandbox.rs precedent); message body size limit (discretion) |
| V6 Cryptography | no | Bearer token uses existing `secrets.compare_digest`; no new crypto |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Claim pattern traversal (`../../../etc`) | Tampering | Reject `..` components per `sandbox.rs::validate_scope` precedent; normalize with `os.path.normpath` |
| SQLite path traversal (claim storage path) | Tampering | Always resolve claims DB path from CWD using `Path(cwd).resolve()` |
| Bus message injection (no schema enforcement) | Tampering | Accepted gap per spec (V17 imposes no message-type schema enforcement) |
| Stale bearer token replay (bus verbs) | Spoofing | Inherits existing token-is-per-server-process design; no new surface |
| Agent ID spoofing (claims) | Spoofing | Advisory system — spoofing is possible and accepted (advisory-only design) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bus broadcast `set.add/discard` from within a single asyncio event loop is safe without an explicit asyncio.Lock | Architecture Patterns §Pattern 2 | Race in subscriber set modification; fix = wrap with asyncio.Lock |
| A2 | `cargo typify` is available and pinned in the environment for Rust SDK regen | Environment Availability | Rust SDK regen step fails; mitigation: defer or use alternative codegen |
| A3 | Go SDK `oapi-codegen` is available via `go tool` for Go SDK regen | Environment Availability | Go SDK regen step fails; mitigation: update testdata fixture instead |
| A4 | Pane config structure for A6 will accept a `slug` field without breaking existing grid serialization | Open Question 3 | Slug persistence fails; fallback: slug is in-memory only per session (weaker D-13 guarantee) |
| A5 | ULID monotonicity is sufficient for journal ordering (same-millisecond messages may be unordered within that ms) | Code Examples §ULID | Journal ordering non-deterministic within 1ms; acceptable given advisory nature |

**If these are wrong:** A1 is the only one with an immediate correctness impact. The fix (asyncio.Lock wrapping) is a one-liner.

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/server/app.py` (lines 51-76, 390-419, 446-460) — `_BearerASGI`, SSE pattern, `_force_event_schema` — VERIFIED by direct read
- `voss/harness/server/events.py` (lines 191-218) — 21-member Pydantic discriminated union, `AgentEventAdapter` — VERIFIED by direct read
- `voss/harness/cli.py` (lines 4484-4525) — `AGENT_COMMANDS`, `register()` — VERIFIED by direct read
- `crates/voss-app-core/src/pty/mod.rs` (lines 178-284) — `spawn_command_session_with_env`, `spawn_command_session_managed` — VERIFIED by direct read
- `apps/voss-app/src-tauri/src/lib.rs` (lines 168-289) — `env_for_embedded_cli`, `spawn_agent`, `spawn_managed_agent` — VERIFIED by direct read
- `scripts/export_contract.py`, `tests/harness/server/test_contract_drift.py` — contract regen + drift gate — VERIFIED by direct read
- `scripts/generate_sdk_events.py` — Rust SDK regen — VERIFIED by direct read
- `sdk/go/internal/drift/drift_test.go` — Go SDK drift gate — VERIFIED by direct read
- `sdk/typescript/package.json` codegen script — TS SDK regen — VERIFIED by direct read
- Live Python tests in this session: BEGIN IMMEDIATE exactly-one-winner (5 concurrent agents), glob overlap algorithm (all spec cases), URI overlap (all spec cases), stdlib ULID generation

### Secondary (MEDIUM confidence)

- `voss/harness/memory_store.py:838-841`, `voss/harness/lifecycle.py:159-160` — atomic `os.replace` pattern — VERIFIED by codebase grep
- `voss/harness/code/index.py:108-140` — `PRAGMA journal_mode=WAL` + schema-create-if-missing pattern — VERIFIED by direct read

### Tertiary (LOW confidence)

- None — all claims verified from codebase or live tests.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified from live codebase; no new deps needed
- Architecture: HIGH — all integration points found and read; patterns extracted from existing code
- Pitfalls: HIGH — identified from code inspection + live test failures (in-memory SQLite, BEGIN DEFERRED)
- SDK regen mechanics: HIGH — all three scripts/gates found and read
- Rust lifetime ergonomics: MEDIUM — structural understanding clear; exact Rust syntax for owned+static mix is discretion-level

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (stable dependencies; 30-day window)

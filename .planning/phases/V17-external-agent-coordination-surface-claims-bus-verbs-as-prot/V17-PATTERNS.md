# Phase V17: External Agent Coordination Surface - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/claims.py` | service + CLI group | CRUD / request-response | `voss/harness/code/index.py` (SQLite) + `voss/harness/cli.py` `mcp_group` (click group + `--json`) | role-match (SQLite + group structure) |
| `voss/harness/bus_client.py` | CLI group / HTTP client | request-response + streaming | `voss/harness/cli.py` `agent_group` (group shape) + SSE consumer | role-match |
| `voss/harness/server/bus.py` | route module | event-driven / pub-sub | `voss/harness/server/app.py` lines 388–419 (SSE), lines 288–311 (POST route) | exact (same app, same patterns) |
| `voss/harness/server/events.py` (modify) | event model | event-driven | `voss/harness/server/events.py` lines 191–218 (union, `_Base`) | exact |
| `voss/harness/server/app.py` (modify) | route registry | request-response | `voss/harness/server/app.py` lines 274–278 (router registration) | exact |
| `apps/voss-app/src-tauri/src/lib.rs` (modify) | Rust Tauri command | request-response | `apps/voss-app/src-tauri/src/lib.rs` lines 185–222 (`spawn_agent`) | exact |
| `apps/voss-app/src/pane/pty-ipc.ts` (modify) | TS transport / spawn | request-response | `apps/voss-app/src/pane/pty-ipc.ts` lines 194–243 (`spawnAgent`, `spawnManagedAgent`) | exact |
| `apps/voss-app/src/pane/slugRegistry.ts` (new) | utility / registry | CRUD | `apps/voss-app/src/pane/adoptionRegistry.ts` | exact (same SolidJS signal pattern) |
| `scripts/export_contract.py` (run, not modified) | build script | batch | `scripts/export_contract.py` (already exists) | exact — run as-is |
| `sdk/go/` regenerated file | generated artifact | batch | `sdk/go/internal/drift/drift_test.go` (describes the pattern) | exact (go generate) |
| `sdk/typescript/src/generated/types.ts` (regen) | generated artifact | batch | `sdk/typescript/package.json` `codegen` script | exact (npm run codegen) |
| `crates/voss-sdk/src/types/events.rs` (regen) | generated artifact | batch | `scripts/generate_sdk_events.py` | exact (run script) |
| `docs/agent-coordination.md` | documentation | — | `docs/sdk.md` (bare `# heading`, no frontmatter) | role-match |
| Test files under `tests/harness/claims/` and `tests/harness/bus/` | test | CRUD + streaming | `tests/harness/board/test_board_cli.py` + `tests/harness/conftest.py` | role-match |

---

## Pattern Assignments

### `voss/harness/claims.py` (service + CLI group, CRUD)

**Analogs:**
- SQLite layer: `voss/harness/code/index.py`
- Click group with `--json` output: `voss/harness/cli.py` `mcp_group` (lines 3556–3614) and `jobs_cmd` (lines 2856–2916)
- Exit-code conventions: `voss/harness/cli.py` lines 2304–2327, 3488

**Imports pattern** (from `voss/harness/code/index.py` lines 1–20 and `cli.py`):
```python
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import click
```

**SQLite schema-create-if-missing pattern** (`voss/harness/code/index.py` lines 107–148):
```python
def _get_db_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / DB_NAME


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # ...
    conn.commit()
```
Copy this shape for `open_claims_db()` and `_ensure_claims_schema()`. Use `.voss-cache/claims.sqlite` (D-02). Add WAL + `PRAGMA busy_timeout=5000`.

**Click group with subcommands pattern** (`voss/harness/cli.py` lines 3556–3614):
```python
@click.group("mcp")
def mcp_group() -> None:
    """Inspect and debug MCP server connections."""


@mcp_group.command("list")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
def mcp_list_cmd(cwd_str: str, json_mode: bool) -> None:
    ...
    if json_mode:
        click.echo(json_lib.dumps({"servers": servers_payload}, indent=2))
```
Mirror: `@click.group("claims")` with subcommands `stake`, `check`, `release`, `extend`, `list`. Each subcommand takes `--json "json_mode"` is_flag.

**`--json` NDJSON output pattern** (`voss/harness/cli.py` lines 2882–2886, `jobs_cmd`):
```python
if json_mode:
    for rec in records:
        rendered = dict(rec)
        rendered["status"] = _display_status(rec)
        click.echo(json.dumps(rendered))
    return
```
For claims, emit one JSON dict per line with `"advice": [...]` on conflict output.

**Exit-code pattern** (`voss/harness/cli.py` lines 2304–2327):
```python
# Exit 2 (usage/identity error):
click.echo(
    "voss login requires an interactive terminal. ...",
    err=True,
)
sys.exit(2)

# Exit 1 (conflict detected):
sys.exit(1)   # after emitting conflict JSON to stdout
```

**AGENT_COMMANDS registration** (`voss/harness/cli.py` lines 4484–4525):
```python
AGENT_COMMANDS = (
    do_cmd,
    # ... existing entries ...
    board_cmd,
    audit_cmd,
    # ADD:
    claims_group,
    bus_group,
)
```

---

### `voss/harness/bus_client.py` (CLI group, request-response + streaming)

**Analog:** `voss/harness/cli.py` `agent_group` (lines 3400–3441) for group shape; SSE consumer pattern from RESEARCH.md Pattern 2.

**Click group shape** (`voss/harness/cli.py` lines 3400–3402):
```python
@click.group("agent")
def agent_group() -> None:
    """Run registered subagents."""
```
Mirror: `@click.group("bus")` with subcommands `send`, `inbox`, `wait`.

**env var discovery pattern** (inferred from `cli.py` lines 1693–1697, exit-2 path):
```python
server_port = os.environ.get("VOSS_SERVER_PORT")
server_token = os.environ.get("VOSS_SERVER_TOKEN")
if not server_port or not server_token:
    click.echo(
        "VOSS_SERVER_PORT/VOSS_SERVER_TOKEN not set. "
        "Run inside a voss-managed pane or start voss serve.",
        err=True,
    )
    sys.exit(2)
```

**`--json` output with advice** (`voss/harness/cli.py` `jobs_cmd` lines 2882–2886):
```python
if json_mode:
    click.echo(json.dumps({"messages": ..., "advice": [
        "voss bus wait --mention @me --timeout 60"
    ]}))
```

---

### `voss/harness/server/bus.py` (route module, event-driven / pub-sub)

**Analog:** `voss/harness/server/app.py` — SSE handler (lines 390–419), POST route (lines 354–363), `create_app` lifespan (lines 266–278).

**Route registration idiom** — bus.py will be an `APIRouter` registered in `app.py`. Model after how FastAPI sub-apps are added; current app.py registers inline routes on the same `app` object. For bus, extract to a router:
```python
# In bus.py:
from fastapi import APIRouter, Request
from sse_starlette import EventSourceResponse, ServerSentEvent

bus_router = APIRouter(prefix="/bus", tags=["bus"])
```
Then in `app.py` in `create_app()`:
```python
from .bus import bus_router, BusState
app.state.bus = BusState()
app.include_router(bus_router)   # place after app.add_middleware(...)
```

**SSE generator pattern** (`voss/harness/server/app.py` lines 390–419):
```python
@app.get(
    "/session/{session_id}/events",
    responses={200: {"content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/EventEnvelope"}}}}},
)
async def events(session_id: str, request: Request) -> EventSourceResponse:
    s = _require(session_id)

    async def gen():
        yield ServerSentEvent(
            event="server.connected", data=E.ServerConnected().model_dump_json()
        )
        try:
            while True:
                ev = await s.queue.get()
                yield ServerSentEvent(event=ev.type, data=ev.model_dump_json())
        except asyncio.CancelledError:
            if s.busy and s.task is not None:
                s.task.cancel()
            raise

    return EventSourceResponse(gen(), ping=15, send_timeout=30)
```
For `/bus/events`: replace `s.queue.get()` with `q.get()` from a per-subscriber `asyncio.Queue` in `app.state.bus.subscribers`. Remove the CancelledError abort-turn block (no session task to cancel — just `bus.subscribers.discard(q)` in `finally`).

**POST route body + response pattern** (`voss/harness/server/app.py` lines 232–250, `MessageBody`/`CreateSessionBody`):
```python
class MessageBody(BaseModel):
    parts: list[MessagePart] = []
    mode: str = "plan"

@app.post("/session/{session_id}/message", status_code=202)
async def post_message(session_id: str, body: MessageBody) -> dict:
    ...
    return {"v": 1, "status": "accepted"}
```
For `/bus/send`: new `BusSendBody(BaseModel)` with `body: str`, `mentions: list[str] = []`, `labels: list[str] = []`, `sender: str = ""`. Route returns `{"v": 1, "id": msg_id}`.

**atomic `os.replace` pattern** (`voss/harness/lifecycle.py` lines 155–160):
```python
def _write_meta(rec: JobRecord) -> None:
    target = _meta_path(rec)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(rec.to_meta(), sort_keys=True) + "\n")
    tmp.replace(target)
```
Use for `cursors.json` updates: `tmp = cursors_path.with_suffix(".json.tmp")` → `tmp.write_text(...)` → `tmp.replace(cursors_path)` (or `os.replace(tmp, cursors_path)`).

---

### `voss/harness/server/events.py` (modify — add `BusMessage`)

**Analog:** Same file, lines 151–218 (Voss-native additive section + union).

**Additive class pattern** (`voss/harness/server/events.py` lines 151–218):
```python
# --- Voss-native (additive) ------------------------------------------------

class BudgetUpdated(_Base):
    type: Literal["budget.updated"] = "budget.updated"
    session_id: str
    spent: float
    limit: float
    remaining: float
    unit: Literal["tokens", "usd"] = "tokens"

# ... then union entry:
AgentEvent = Annotated[
    Union[
        ServerConnected,
        # ... existing 20 types ...
        GateUpdated,
        BusMessage,          # ADD HERE
    ],
    Field(discriminator="type"),
]
```

**New class shape** (from RESEARCH.md Pattern 7, matching `_Base` convention):
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
Place in the `# --- Voss-native (additive) ---` section, before the union.

**After class addition:** run `scripts/export_contract.py`, then `cd sdk/go && go generate ./...`, then `cd sdk/typescript && npm run codegen`, then `python scripts/generate_sdk_events.py`. Commit all generated artifacts before the drift gate runs.

---

### `voss/harness/server/app.py` (modify — register bus router)

**Analog:** `voss/harness/server/app.py` lines 274–278 (`add_middleware`) and the inline route registration block.

**Middleware + router registration pattern** (`voss/harness/server/app.py` lines 274–278):
```python
app = FastAPI(title="voss-harness", version="1", lifespan=lifespan)
app.state.token = token
app.state.sessions = mgr

app.add_middleware(_BearerASGI, token=token)
```
Add after `app.add_middleware(...)`:
```python
from .bus import bus_router, BusState
app.state.bus = BusState()
app.include_router(bus_router)
```
`_BearerASGI` is an ASGI-level middleware applied before routing, so `/bus/*` routes inherit auth for free (no per-route `Depends`).

---

### `apps/voss-app/src-tauri/src/lib.rs` (modify — env injection)

**Analog:** `apps/voss-app/src-tauri/src/lib.rs` lines 168–222 (`env_for_embedded_cli`, `spawn_agent`).

**`env_for_embedded_cli` current return type** (lines 168–181):
```rust
fn env_for_embedded_cli(
    cli_binary: &str,
    cli_args: &[String],
) -> Vec<(&'static str, &'static str)> {
    if !is_voss_cli_binary(cli_binary) {
        return Vec::new();
    }
    if is_interactive_voss_command(cli_args) {
        return vec![("VOSS_EMBEDDED", "1"), ("VOSS_FORCE_TUI", "1")];
    }
    vec![("VOSS_EMBEDDED", "1"), ("VOSS_RENDERER", "compact")]
}
```
**Critical:** Returns `Vec<(&'static str, &'static str)>`. The slug is a dynamic `String` — cannot go in this return. Follow RESEARCH.md Pattern 6 recommendation: add `voss_agent_id: String` as a new Tauri command parameter to `spawn_agent`, `spawn_managed_agent`, and `spawn_pty`. Build env at the call site by combining the static slice with the owned slug.

**`spawn_agent` call site pattern** (lines 203–212):
```rust
let embedded_env = env_for_embedded_cli(&cli_binary, &cli_args);
let (session, reader, pause_rx) = spawn_command_session_with_env(
    &cli_binary,
    &cli_args,
    &embedded_env,
    rows,
    cols,
    cwd.clone(),
)
.map_err(|e| e.to_string())?;
```
V17 modification — add `voss_agent_id: Option<String>` param and extend the env at call site:
```rust
// After embedded_env line, build an owned vec that includes the slug:
let mut full_env: Vec<(String, String)> = embedded_env
    .iter()
    .map(|(k, v)| (k.to_string(), v.to_string()))
    .collect();
if let Some(ref slug) = voss_agent_id {
    full_env.push(("VOSS_AGENT_ID".to_string(), slug.clone()));
}
let env_refs: Vec<(&str, &str)> = full_env.iter().map(|(k, v)| (k.as_str(), v.as_str())).collect();
let (session, reader, pause_rx) = spawn_command_session_with_env(
    &cli_binary, &cli_args, &env_refs, rows, cols, cwd.clone(),
).map_err(|e| e.to_string())?;
```

**`spawn_pty` current pattern** (lines 480–492) — currently calls `spawn_session` with NO env:
```rust
async fn spawn_pty(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    cwd: Option<String>,
    state: Reg<'_>,
) -> Result<String, String> {
    let (session, reader, pause_rx) = spawn_session(rows, cols, cwd).map_err(|e| e.to_string())?;
    ...
}
```
V17: add `voss_agent_id: Option<String>` param; switch from `spawn_session` to `spawn_command_session_with_env` with an empty cli binary / args and only the slug in env — or keep `spawn_session` and add the var via a shell environment wrapper (planner decides cleanest Rust approach).

---

### `apps/voss-app/src/pane/pty-ipc.ts` (modify — pass slug to Tauri)

**Analog:** `apps/voss-app/src/pane/pty-ipc.ts` lines 194–243 (`spawnAgent`, `spawnManagedAgent`).

**`spawnAgent` invoke pattern** (lines 201–212):
```typescript
async spawnAgent(o: {
  rows: number;
  cols: number;
  cwd?: string;
  paneId: string;
  workspacePath?: string;
} & AgentConfig): Promise<string> {
  this.sessionId = await invoke<string>('spawn_agent', {
    onData: this.channel,
    rows: o.rows,
    cols: o.cols,
    cwd: o.cwd,
    cliBinary: o.cliBinary,
    cliArgs: o.cliArgs,
    sessionId: o.sessionId,
    paneId: o.paneId,
    workspacePath: o.workspacePath,
  });
  return this.sessionId;
}
```
V17: add `vossAgentId?: string` to the `o` parameter type and the `invoke` call object:
```typescript
vossAgentId: o.vossAgentId ?? null,
```
Apply the same additive change to `spawnManagedAgent` and `spawn` (plain PTY).

**`AgentConfig` interface** (lines 42–54) — add `vossAgentId?: string`:
```typescript
export interface AgentConfig {
  cliBinary: string;
  cliArgs: string[];
  sessionId: string;
  managed?: boolean;
  scope?: string;
  tier?: 'A' | 'B' | 'C';
  budgetUsd?: number;
  vossAgentId?: string;   // ADD: slug minted at spawn time (D-11)
}
```

---

### `apps/voss-app/src/pane/slugRegistry.ts` (new — slug minting + persistence)

**Analog:** `apps/voss-app/src/pane/adoptionRegistry.ts` (identical SolidJS module-signal pattern, lines 1–41).

**Module signal pattern** (`apps/voss-app/src/pane/adoptionRegistry.ts` lines 1–41):
```typescript
import { createSignal } from 'solid-js';

export type AdoptionEntry = {
  cardId: string;
  budgetUsd: number;
  tier: 'C';
};

const [adoptionByPaneId, setAdoptionByPaneId] = createSignal<
  Record<string, AdoptionEntry>
>({});

export function registerAdoption(paneId: string, entry: AdoptionEntry): void {
  setAdoptionByPaneId((prev) => ({ ...prev, [paneId]: entry }));
}

export function unregisterAdoption(paneId: string): void {
  setAdoptionByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { adoptionByPaneId };

/** Test-only reset (module signal is global). */
export function __resetAdoptions(): void {
  setAdoptionByPaneId({});
}
```
For `slugRegistry.ts`: replace `AdoptionEntry` with `{ slug: string }`, rename `registerAdoption` → `registerSlug`, `unregisterAdoption` → `unregisterSlug`, add a `mintSlug(cliBinary: string): string` function using a module-level counter (`let _counter = 0; _counter++`). Slug format: `<cli>-<n>` for agent launches, `pane-<n>` for plain shells (D-12).

**Agent CLI detection pattern** (`apps/voss-app/src/pane/agentPaneRegistry.ts` lines 29–38, `apps/voss-app/src/org/adopt.ts` lines 70–75):
```typescript
const AGENT_CLIS = new Set(['claude', 'codex', 'gemini', 'opencode', 'aider']);

export function inferRole(cliBinary: string): string {
  const name = cliBinary.trim().toLowerCase().split('/').pop() ?? '';
  return AGENT_CLIS.has(name) ? 'executor' : 'user';
}
```
Use `AGENT_CLIS` to decide `<cli>-<n>` vs `pane-<n>` slug prefix.

---

### Test files under `tests/harness/claims/` and `tests/harness/bus/`

**Analog:** `tests/harness/board/test_board_cli.py` (click Runner + tmp_path pattern) and `tests/harness/conftest.py` (fixtures).

**Click Runner test pattern** (`tests/harness/board/test_board_cli.py` lines 1–58):
```python
"""VBUS-01 `voss claims stake/check/release` acceptance tests — Wave 0 RED scaffold."""
from __future__ import annotations

from pathlib import Path
from click.testing import CliRunner
import pytest


class TestClaimsVerbs:
    def test_stake_and_check_conflict(self, tmp_path: Path) -> None:
        from voss.harness.claims import claims_group
        runner = CliRunner(mix_stderr=False)
        # Set env to inject VOSS_AGENT_ID
        env = {"VOSS_AGENT_ID": "claude-1"}
        result = runner.invoke(claims_group, ["stake", "src/api/**", "--cwd", str(tmp_path)], env=env)
        assert result.exit_code == 0
```

**Acceptance test marker** (`tests/harness/board/test_board_cli.py` line 1 docstring): put `@pytest.mark.acceptance` on two-agent sequence tests matching RESEARCH.md Wave 0 map.

**`isolated_state` autouse fixture** (`tests/harness/conftest.py` lines 28–31) — already in scope for all `tests/harness/` subdirectories; new test dirs just need an `__init__.py`.

---

### `docs/agent-coordination.md` (new)

**Analog:** `docs/sdk.md` — bare `# Title` with no frontmatter (Voss docs convention).

**doc structure** (`docs/sdk.md` lines 1–5):
```markdown
# Voss SDK

Voss ships two embedding surfaces ...
```
`docs/agent-coordination.md` uses the same bare-heading style, no YAML frontmatter. Sections: Overview, Environment Variables, Claims Verbs, Bus Verbs, Exit Codes, Label Vocabulary, Pre-edit Guard Example, V16 Handoff.

---

## Shared Patterns

### SQLite WAL + schema-create-if-missing
**Source:** `voss/harness/code/index.py` lines 107–148
**Apply to:** `voss/harness/claims.py` (sole consumer)
```python
def _get_db_path(cwd: Path) -> Path:
    return cwd / ".voss-cache" / "code" / DB_NAME

def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("CREATE TABLE IF NOT EXISTS ...")
    conn.commit()
```

### Click `--json` / NDJSON output
**Source:** `voss/harness/cli.py` `jobs_cmd` lines 2882–2886; `mcp_list_cmd` lines 3609–3610
**Apply to:** `voss/harness/claims.py` (all subcommands), `voss/harness/bus_client.py` (all subcommands)
```python
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
# ...
if json_mode:
    click.echo(json.dumps({"conflict": True, "owner": owner_id, "advice": [...]}))
    sys.exit(1)
```

### Exit-code conventions (0/1/2)
**Source:** `voss/harness/cli.py` lines 2304–2327, 3488, 491
**Apply to:** `voss/harness/claims.py`, `voss/harness/bus_client.py`
```python
# Exit 2 — identity/discovery missing:
click.echo("VOSS_AGENT_ID not set. ...", err=True)
sys.exit(2)

# Exit 1 — conflict / bus timeout:
click.echo(json.dumps(result_dict))
sys.exit(1)
```

### Atomic file write (`os.replace`)
**Source:** `voss/harness/lifecycle.py` lines 155–160; `voss/harness/memory_store.py` lines 838–841
**Apply to:** `voss/harness/server/bus.py` (`cursors.json` update)
```python
tmp = target.with_suffix(target.suffix + ".tmp")
tmp.write_text(json.dumps(data, sort_keys=True) + "\n")
tmp.replace(target)   # POSIX atomic
```

### `_BearerASGI` auth (automatic for all `/bus/*` routes)
**Source:** `voss/harness/server/app.py` lines 51–76
**Apply to:** `voss/harness/server/bus.py` (zero extra code — middleware applies app-wide)
```python
class _BearerASGI:
    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        ok = auth.startswith("Bearer ") and secrets.compare_digest(auth[7:], self._token)
        if not ok:
            resp = JSONResponse({"v": 1, "detail": "unauthorized"}, status_code=401)
            await resp(scope, receive, send)
            return
        await self._app(scope, receive, send)
```

### Pydantic `_Base` event model + union extension
**Source:** `voss/harness/server/events.py` lines 24–28, 191–218
**Apply to:** `BusMessage` addition in `events.py`
```python
class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")
    v: int = PROTOCOL_VERSION

# Union entry:
AgentEvent = Annotated[
    Union[..., BusMessage],
    Field(discriminator="type"),
]
```

### SolidJS module-signal registry
**Source:** `apps/voss-app/src/pane/adoptionRegistry.ts` lines 1–41
**Apply to:** `apps/voss-app/src/pane/slugRegistry.ts`
```typescript
const [slugByPaneId, setSlugByPaneId] = createSignal<Record<string, { slug: string }>>({});
export function registerSlug(paneId: string, slug: string): void {
  setSlugByPaneId((prev) => ({ ...prev, [paneId]: { slug } }));
}
```

### Contract regen sequence
**Source:** `scripts/export_contract.py`, `scripts/generate_sdk_events.py`, `sdk/go/internal/drift/drift_test.go`, `sdk/typescript/package.json`
**Apply to:** After modifying `events.py` — mandatory before committing the wave
```
.venv/bin/python scripts/export_contract.py
cd sdk/go && go generate ./...  && cd -
cd sdk/typescript && npm run codegen && cd -
.venv/bin/python scripts/generate_sdk_events.py
# commit all four changed artifacts
```

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss/harness/server/`, `apps/voss-app/src/`, `apps/voss-app/src-tauri/src/`, `tests/harness/`, `scripts/`, `docs/`
**Files scanned:** 15 (read in full or targeted sections)
**Pattern extraction date:** 2026-06-09

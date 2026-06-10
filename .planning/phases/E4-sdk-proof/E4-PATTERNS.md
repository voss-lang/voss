# Phase E4: SDK Proof - Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 10 (4 modified, 6 new)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/eval/suite.py` | model | transform | `voss/eval/suite.py` lines 55-56 (`surface`/`target_file` E3-01 addition) | exact |
| `voss/eval/runner.py` | service | request-response + event-driven | `voss/eval/runner.py` lines 258-317 (`_drive_task` dispatch + `_drive_resume` helper pattern) | exact |
| `tests/eval/test_voss_eval_stub.py` | test | batch | self (lines 11-35 `REQUIRED_FIELDS` sentinel) | exact |
| `tests/eval/sdk/<NN>-<slug>/task.toml` | config | — | `tests/eval/golden/03-approved-edit/task.toml` + E3 surface task.toml shape | exact |
| `tests/eval/sdk/consumers/ts/consumer.js` | utility | request-response + event-driven | `sdk/typescript/src/client/rest.ts` + `src/client/sse.ts` + `src/client/permission.ts` | role-match |
| `tests/eval/sdk/consumers/ts/package.json` | config | — | `sdk/typescript/package.json` (module type, dep ref) | role-match |
| `tests/eval/sdk/consumers/go/main.go` | utility | request-response + event-driven | `sdk/go/client_test.go` lines 47-92 (`TestSpawnNoOrphan`) + `sdk/go/client.go` + `sdk/go/sse.go` | exact |
| `tests/eval/sdk/consumers/go/go.mod` | config | — | `sdk/go/go.mod` (module declaration pattern) | role-match |
| `tests/eval/sdk/consumers/rust/main.rs` | utility | request-response + event-driven | `crates/voss-sdk/tests/integration.rs` lines 116-155 (`sse_event_sequence` + `permission_roundtrip`) | exact |
| `tests/eval/test_sdk_drivers.py` | test | request-response + event-driven | `tests/eval/test_voss_eval_stub.py` (runner invocation + row field assertion pattern) | role-match |

---

## Pattern Assignments

### `voss/eval/suite.py` — extend `surface` Literal with sdk:* values (model, transform)

**Analog:** `voss/eval/suite.py` lines 55-56 (post-E3-01)

**Current `surface` field** (`/Users/benjaminmarks/Projects/Voss/voss/eval/suite.py`, line 55):
```python
surface: Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve"] = "internal"
```

**E4 extension — extend the Literal only:**
```python
surface: Literal[
    "internal", "cli:do", "cli:chat", "cli:edit", "serve",
    "sdk:python", "sdk:ts", "sdk:go", "sdk:rust",
] = "internal"
```

Key constraint: `model_config = ConfigDict(extra="forbid")` at line 44. New values extend the existing `Literal` — no new fields needed. `target_file` already present at line 56 (added by E3-01). Back-compat guaranteed: existing tasks default to `"internal"`.

**Dependency gate:** This edit is valid only after E3-01 merges (adds the `surface` field). If E3-01 has not merged, E4-W1 must absorb E3-01's addition in the same plan (copy the pattern verbatim from E3-01-PLAN.md task 1).

---

### `voss/eval/runner.py` — add `sdk:*` dispatch branches + `_drive_sdk_client` + `_drive_sdk_python` (service, event-driven)

**Analog:** `voss/eval/runner.py` lines 258-317 (`_drive_task`) and E3-RESEARCH.md Pattern 3 (`_drive_serve`)

**Existing dispatch skeleton** (`/Users/benjaminmarks/Projects/Voss/voss/eval/runner.py`, lines 258-280):
```python
async def _drive_task(
    task_id: str,
    spec: TaskSpec,
    *,
    cwd: Path,
    provider: ModelProvider,
    model: str | None,
    stub: bool = False,
    max_turns: int = 15,
) -> tuple[SessionRecord, str, str | None, bool]:
    record = SessionRecord.new(cwd=cwd, model=_record_model(model), name=task_id)
    permissions = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)
    net_session = _make_stub_net_session(spec, stub=stub)
    capped = False
    try:
        if spec.surface != "internal":
            # E3-02 (cli:*) and E3-03 (serve) replace these with real drivers.
            return (
                record,
                "",
                f"surface {spec.surface!r} driver not implemented (E3-02/E3-03)",
                False,
            )
```

**E4 adds after E3's branches (replace the `spec.surface != "internal"` guard with a match):**
```python
        match spec.surface:
            case "internal":
                pass  # falls through to existing run_turn path below
            case "cli:do" | "cli:chat" | "cli:edit":
                return await _drive_cli(spec, cwd=cwd, record=record)   # E3-02
            case "serve":
                return await _drive_serve(spec, cwd=cwd, record=record)  # E3-03
            case "sdk:python":
                final = await _drive_sdk_python(spec, cwd=cwd, provider=provider, model=model, max_turns=max_turns)
                return record, final, None, False
            case "sdk:ts" | "sdk:go" | "sdk:rust":
                final = await _drive_sdk_client(spec, cwd=cwd, consumer=spec.surface.split(":")[1])
                return record, final, None, False
```

**`_drive_sdk_python` helper — mirrors `_drive_resume` return shape** (lines 199-255 are the model):
```python
async def _drive_sdk_python(
    spec: TaskSpec,
    *,
    cwd: Path,
    provider: ModelProvider,
    model: str | None,
    max_turns: int = 15,
) -> str:
    """Drive via public voss.harness API symbols only. Proves external-consumer contract."""
    from voss.harness import run_turn, PermissionGate  # public __all__
    from voss.harness.render import PlainRenderer       # private — documented M7 gap
    from voss.harness.tools import make_toolset         # private — runner-internal acceptable
    from voss_runtime import EpisodicMemory, configure

    prev_cfg = get_config()
    configure(max_iterations=max_turns)
    try:
        permissions = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)
        result = await run_turn(
            spec.prompt,
            tools=make_toolset(cwd),
            cwd=cwd,
            renderer=PlainRenderer(),
            model=model,
            provider=provider,
            history=EpisodicMemory(capacity=40),
            permissions=permissions,
        )
    finally:
        configure(max_iterations=prev_cfg.max_iterations)
    return result.final
```

**`_drive_sdk_client` helper — mirrors E3's `_drive_serve` subprocess lifecycle pattern** (E3-RESEARCH.md lines 352-458):
```python
async def _drive_sdk_client(
    spec: TaskSpec,
    *,
    cwd: Path,
    consumer: str,   # "ts" | "go" | "rust"
    timeout: float = 180.0,
) -> str:
    """Spawn voss serve, then spawn consumer subprogram. Return final text."""
    import sys, json as _json

    env = dict(os.environ)
    env["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
    env["VOSS_DEV"] = "1"

    # Step 1: spawn voss serve (60s handshake — mirrors E3 _drive_serve pattern)
    proc_server = subprocess.Popen(
        [sys.executable, "-m", "voss.cli", "serve"],
        env=env,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    import threading, time
    stderr_lines: list[str] = []
    threading.Thread(target=lambda: [stderr_lines.append(l) for l in proc_server.stderr], daemon=True).start()

    handshake = None
    deadline = time.monotonic() + 60.0
    for line in proc_server.stdout:
        try:
            h = _json.loads(line.strip())
            if h.get("token"):
                handshake = h
                break
        except _json.JSONDecodeError:
            pass
        if time.monotonic() > deadline:
            proc_server.kill()
            raise TimeoutError("serve handshake timeout")

    base_url = f"http://127.0.0.1:{handshake['port']}"
    token = handshake["token"]

    # Step 2: build consumer command + env
    python_abs = str(Path(sys.executable).resolve())
    consumer_env = {
        **env,
        "VOSS_BASE_URL": base_url,
        "VOSS_TOKEN": token,
        "VOSS_CWD": str(cwd),
        "VOSS_PYTHON": python_abs,   # Go interpreterPath() resolution fix — Pitfall 2
        "VOSS_PROMPT": spec.prompt,
        "VOSS_MODE": spec.mode,
    }
    consumers_dir = Path("tests/eval/sdk/consumers")
    if consumer == "ts":
        cmd = ["node", str(consumers_dir / "ts" / "consumer.js")]
    elif consumer == "go":
        cmd = ["go", "run", "."]
        # go run . requires cwd=consumers/go so go.mod is found
    elif consumer == "rust":
        cmd = ["cargo", "run", "--manifest-path", "crates/voss-sdk/Cargo.toml",
               "--example", "sdk_proof_consumer", "--quiet"]

    # Step 3: run consumer, capture stdout JSON
    try:
        cp = subprocess.run(
            cmd, env=consumer_env, capture_output=True, text=True,
            timeout=timeout, check=False,
            cwd=str(consumers_dir / consumer) if consumer == "go" else None,
        )
        consumer_result = _json.loads(cp.stdout.strip().splitlines()[-1])
        return consumer_result.get("final", "")
    except (subprocess.TimeoutExpired, _json.JSONDecodeError, IndexError):
        return ""
    finally:
        if proc_server.stdin:
            proc_server.stdin.close()   # EOF heartbeat → server self-terminates
        try:
            proc_server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc_server.kill()
```

**Imports to add at runner.py top** (lines 1-18 already have `import subprocess, os, json, sys`; verify `import threading` and `import time` are present or add them):
- `threading` — drain stderr in background (E3 pattern, already in E3 additions)
- `time` — handshake deadline

---

### `tests/eval/test_voss_eval_stub.py` — update `REQUIRED_FIELDS` sentinel (test, batch)

**Analog:** `tests/eval/test_voss_eval_stub.py` lines 11-35 (current sentinel)

**Current REQUIRED_FIELDS** (`/Users/benjaminmarks/Projects/Voss/tests/eval/test_voss_eval_stub.py`, lines 11-35):
```python
REQUIRED_FIELDS = {
    "task_id", "run_idx", "success", "cost_usd", "confidence", "duration_s",
    "judge_verdict", "judge_confidence", "judge_rationale",
    "provider", "model", "judge_model", "live", "seed", "voss_version",
    "started_at", "gate_pass", "capped", "checks", "input_tokens",
    # E3: surface routing field
    "surface",
}
```

**E4 adds NO new JSONL fields** (consumer result is extracted to existing `"final"` which feeds judge; no new top-level row keys). The sentinel does NOT need updating for E4. Only update if a plan adds a new row key (e.g., `consumer_exit_code`) — in that case, add to `REQUIRED_FIELDS` in the same plan task per the stale-sentinel rule.

---

### `tests/eval/sdk/<NN>-<slug>/task.toml` — SDK scenario task files (config)

**Analog:** `tests/eval/golden/03-approved-edit/task.toml` (full field set with `[[checks]]`); E3 surface-scenario shape from E3-RESEARCH.md Pattern 1

**Golden task.toml field set** (`/Users/benjaminmarks/Projects/Voss/tests/eval/golden/03-approved-edit/task.toml`, lines 1-29):
```toml
# 03-approved-edit - apply an edit in edit mode with auto-approve; expect target file modified.
prompt = "Rename the function add() to sum_two() in calc.py and update its single call site in main.py."
mode = "edit"
rubric = """
PASS if:
- calc.py defines sum_two() (not add()).
...
"""
judge_inputs = ["final", "file_diff"]
auto_approve_edits = true

[[checks]]
type = "file_contains"
path = "calc.py"
text = "sum_two"

[[checks]]
type = "cmd"
run = "! grep -q 'def add(' calc.py"
```

**E4 sdk scenario pattern (add `surface` field, keep all other fields):**
```toml
# 01-python-basic - sdk:python in-process, proves run_turn via public API
surface = "sdk:python"
prompt = "Add a function sum_two(a, b) that returns a + b in calc.py."
mode = "edit"
auto_approve_edits = true
rubric = """
PASS if calc.py defines sum_two(a, b) returning a + b.
FAIL if the function is missing or incorrectly named.
"""
judge_inputs = ["final", "file_diff"]

[[checks]]
type = "file_contains"
path = "calc.py"
text = "sum_two"
```

```toml
# 02-ts-permission-allow - sdk:ts consumer, live permission gate Allow
surface = "sdk:ts"
prompt = "Use a shell command to print the current working directory."
mode = "plan"
rubric = """
PASS if the agent's final answer reports the working directory path.
FAIL if the answer is empty or the permission gate was not exercised.
"""
judge_inputs = ["final"]

[[checks]]
type = "cmd"
run = "echo stub-placeholder"   # hermetic: replaced by consumer JSON check in live mode
```

Key rule: `extra="forbid"` on `TaskSpec` means every key in `task.toml` must be a declared `TaskSpec` field. `surface` is the new declared field (E3-01). All other fields match the existing schema exactly.

---

### `tests/eval/sdk/consumers/ts/consumer.js` — TS consumer subprogram (utility, event-driven)

**Analog:** `sdk/typescript/src/client/rest.ts` lines 41-131 (`createVossClient`), `src/client/sse.ts` lines 12-67 (`subscribeToEvents`), `src/client/permission.ts` lines 11-30 (`replyPermission`)

**Import chain** (`sdk/typescript/src/index.ts`, lines 1-5):
```javascript
// Public exports consumed by the TS consumer (import from @vosslang/sdk or dist/index.js):
export { VossApiError } from "./errors";
export type * from "./generated/types";
export * from "./client/rest";    // createVossClient, VossClient, CostInfo, ...
export * from "./client/sse";     // subscribeToEvents, AgentEvent
export * from "./client/permission";  // replyPermission, PermissionChoice
```

**`createVossClient` signature** (`sdk/typescript/src/client/rest.ts`, line 41):
```javascript
export function createVossClient(baseUrl: string, token: string): VossClient
// Returns object with: createSession, postMessage, getCost, getSession, deleteSession, abort, listSessions
```

**`subscribeToEvents` — SSE async iterator** (`sdk/typescript/src/client/sse.ts`, lines 12-17):
```javascript
export async function* subscribeToEvents(
  baseUrl: string,
  sessionId: string,
  token: string,
  signal?: AbortSignal,
): AsyncIterable<AgentEvent>
// AgentEvent is the discriminated union: event.type === "permission.updated" | "final" | "session.idle" | ...
```

**`replyPermission` signature** (`sdk/typescript/src/client/permission.ts`, lines 11-14):
```javascript
export async function replyPermission(
  client: VossClient,
  sessionId: string,
  args: { id: string; choice: "a" | "A" | "d" | "y" | "n" },
): Promise<void>
```

**CRITICAL: do NOT call `VossLauncher.start()`** — it has `HANDSHAKE_TIMEOUT_MS = 1e4` (10s) baked into `sdk/typescript/dist/node.js` line 644. Cold litellm start is 15-45s. The Python runner pre-spawns the server and passes `VOSS_BASE_URL`/`VOSS_TOKEN` via env. The consumer uses `createVossClient(baseUrl, token)` directly — no VossLauncher.

**Full consumer program structure to copy:**
```javascript
// tests/eval/sdk/consumers/ts/consumer.js
// Receives VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD, VOSS_PROMPT, VOSS_MODE from env
import { createVossClient, subscribeToEvents, replyPermission } from "@vosslang/sdk";

const baseUrl = process.env.VOSS_BASE_URL;
const token = process.env.VOSS_TOKEN;
const cwd = process.env.VOSS_CWD || ".";
const prompt = process.env.VOSS_PROMPT;
const mode = process.env.VOSS_MODE || "plan";

const client = createVossClient(baseUrl, token);
const sessionId = await client.createSession(cwd);

let finalText = "";
let sawPermissionGate = false;
const eventTypesSeen = [];
const ac = new AbortController();

await client.postMessage(sessionId, prompt, mode);

for await (const event of subscribeToEvents(baseUrl, sessionId, token, ac.signal)) {
    eventTypesSeen.push(event.type);
    if (event.type === "permission.updated") {
        sawPermissionGate = true;
        await replyPermission(client, sessionId, { id: event.id, choice: "a" });
    }
    if (event.type === "final") { finalText = event.text; }
    if (event.type === "session.idle") { ac.abort(); break; }
}

const cost = await client.getCost(sessionId).catch(() => ({ total_usd: 0 }));
process.stdout.write(JSON.stringify({
    surface: "sdk:ts",
    session_id: sessionId,
    final: finalText,
    saw_permission_gate: sawPermissionGate,
    cost_usd: cost.total_usd,
    event_types_seen: eventTypesSeen,
}) + "\n");
```

**`package.json` for TS consumer:**
```json
{
  "type": "module",
  "dependencies": {
    "@vosslang/sdk": "file:../../../../../../sdk/typescript"
  }
}
```
Run `npm install` once in Wave 0 setup (or as part of the consumer setup task). After install, `node consumer.js` works without tsx or strip-types.

---

### `tests/eval/sdk/consumers/go/main.go` — Go consumer subprogram (utility, event-driven)

**Analog:** `sdk/go/client_test.go` lines 47-92 (`TestSpawnNoOrphan` — full lifecycle) and lines 119-145 (`TestAttachRoundTrip` — AttachClient pattern); `sdk/go/client.go` lines 29-35 (`AttachClient`); `sdk/go/sse.go` lines 20-47 (`Events`)

**`AttachClient` — connect to pre-spawned server** (`sdk/go/client.go`, lines 29-35):
```go
// AttachClient builds a Client for an already-running server. Owns no process.
func AttachClient(baseURL, token string) *Client {
    return &Client{
        http:    &http.Client{},
        baseURL: baseURL,
        token:   token,
    }
}
```

**`Events` — typed SSE channel** (`sdk/go/sse.go`, lines 20-47):
```go
// Events streams typed events from GET /session/:id/events.
// A non-200 open returns a *VossError. Cancelling ctx closes the channel.
func (c *Client) Events(ctx context.Context, sessionID string) (<-chan TypedEvent, error)
// TypedEvent is an interface; call ev.eventType() for type string
```

**Full consumer lifecycle from TestAttachRoundTrip** (`sdk/go/client_test.go`, lines 119-145):
```go
// Python runner pre-spawns the server and passes VOSS_BASE_URL + VOSS_TOKEN via env
att := AttachClient(os.Getenv("VOSS_BASE_URL"), os.Getenv("VOSS_TOKEN"))
id, err := att.CreateSession(ctx, os.Getenv("VOSS_CWD"))
// ...
ch, _ := att.Events(ctx, id)
att.PostMessage(ctx, id, prompt, mode)
for ev := range ch {
    switch e := ev.(type) {
    case *PermissionUpdatedEvent:
        att.PermissionReply(ctx, id, e.ID, "a")
    case *FinalEvent:
        finalText = e.Text
    case *SessionIdleEvent:
        goto done
    }
}
```

**No-orphan close pattern** (`sdk/go/client_test.go`, lines 78-91):
```go
if err := c.Close(); err != nil {
    t.Fatalf("Close: %v", err)
}
// Close() is a no-op on AttachClient (spawn == nil) — safe to call always
```

**CRITICAL: use `AttachClient`, NOT `Spawn`** — `Spawn` calls `interpreterPath()` which resolves `.venv/bin/python` relative to CWD (`sdk/go/spawn.go`, lines 29-40). From `tests/eval/sdk/consumers/go/`, this resolves wrong. The Python runner sets `VOSS_PYTHON` env var and owns the server lifecycle; the Go consumer uses `AttachClient`.

**`go.mod` pattern for the consumer directory:**
```
module sdk-go-consumer

go 1.24

require github.com/vosslang/voss/sdk/go v0.0.0

replace github.com/vosslang/voss/sdk/go => ../../../../sdk/go
```

**Run command:** `go run .` from `tests/eval/sdk/consumers/go/` (the Python runner sets `cwd=consumers_dir/"go"`).

**Structured result JSON (emit as last stdout line):**
```go
fmt.Printf(`{"surface":"sdk:go","session_id":%q,"final":%q,"saw_permission_gate":%t,"cost_usd":%f,"event_types_seen":%s}`+"\n",
    sessionId, finalText, sawPermissionGate, costUSD, eventTypesJSON)
```

---

### `tests/eval/sdk/consumers/rust/main.rs` (or as `crates/voss-sdk/examples/sdk_proof_consumer.rs`) — Rust consumer subprogram (utility, event-driven)

**Analog:** `crates/voss-sdk/tests/integration.rs` lines 116-155 (`sse_event_sequence`), lines 227-297 (`permission_roundtrip`), and lines 29-55 (`rest_roundtrip`)

**Import block** (`crates/voss-sdk/tests/integration.rs`, lines 1-8):
```rust
use futures_util::StreamExt;
use voss_sdk::error::VossError;
use voss_sdk::types::events::AgentEvent;
use voss_sdk::{event_stream, spawn_with, VossClient};
```

**`VossClient::new` — connect to pre-spawned server:**
```rust
// Analog: integration.rs line 70 (bad-token test uses VossClient::new directly)
let bad_client = VossClient::new(supervisor.client.base_url().to_string(), "bad-token".into());
// E4 consumer uses env vars instead of supervisor:
let client = VossClient::new(
    std::env::var("VOSS_BASE_URL").expect("VOSS_BASE_URL"),
    std::env::var("VOSS_TOKEN").expect("VOSS_TOKEN"),
);
```

**`event_stream` — typed Futures stream** (`crates/voss-sdk/tests/integration.rs`, lines 136-154):
```rust
let events: Vec<AgentEvent> = event_stream(client.clone(), sid.clone())
    .collect::<Vec<Result<AgentEvent, VossError>>>()
    .await
    .into_iter()
    .collect::<Result<Vec<_>, _>>()
    .expect("collect events");

assert!(matches!(events.first(), Some(AgentEvent::ServerConnected(_))));
assert!(matches!(events.last(), Some(AgentEvent::SessionIdle(_))));
```

**Permission roundtrip pattern** (`crates/voss-sdk/tests/integration.rs`, lines 247-279):
```rust
// For each event in stream:
match stream.next().await {
    Some(Ok(AgentEvent::PermissionUpdated(event))) => {
        permission_id = Some(event.id);
        break;
    }
    Some(Ok(AgentEvent::SessionIdle(_))) | None => break,
    Some(Ok(_)) => {}
    Some(Err(error)) => panic!("stream error: {error}"),
}
// Then reply:
client.permission_reply(&sid, &permission_id, "a").await.expect("allow");
```

**CRITICAL: FAKE_TURN emits NO `permission.updated`** — confirmed `crates/voss-sdk/tests/integration.rs` line 224-226 comment: "FAKE_TURN emits no permission.updated event (app.py 166-178). A hermetic permission test needs a future VOSS_SERVE_FAKE_TURN_PERMISSION server seam." Hermetic consumer tests verify SSE plumbing only. Permission gate = live-only.

**Run command:** `cargo run --manifest-path crates/voss-sdk/Cargo.toml --example sdk_proof_consumer --quiet`

**Structured result JSON:**
```rust
println!("{}", serde_json::json!({
    "surface": "sdk:rust",
    "session_id": sid,
    "final": final_text,
    "saw_permission_gate": saw_permission_gate,
    "event_types_seen": event_types_seen,
}));
```

---

### `tests/eval/test_sdk_drivers.py` — stub-mode driver unit tests (test, request-response)

**Analog:** `tests/eval/test_voss_eval_stub.py` lines 42-53 (`_run_eval` helper) and lines 79-100 (`test_voss_eval_stub_writes_single_jsonl_row`)

**`_run_eval` invocation pattern** (`/Users/benjaminmarks/Projects/Voss/tests/eval/test_voss_eval_stub.py`, lines 42-53):
```python
def _run_eval(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    repo = str(_repo_root())
    env["PYTHONPATH"] = repo + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
```

**Row field assertion pattern** (lines 88-100):
```python
result = _run_eval(
    ["--stub", "--auth", "none", "--task", "02-plan-only", "-k", "1", "--out", str(out)],
    cwd=golden_repo_root,
)
assert result.returncode == 0, result.stderr
rows = _read_rows(out / "runs.jsonl")
assert len(rows) == 1
row = rows[0]
assert set(row) == REQUIRED_FIELDS        # exact field-set equality
assert row["surface"] == "sdk:python"     # E4 assertion
```

**`conftest.py` autouse fixture** (`/Users/benjaminmarks/Projects/Voss/tests/eval/conftest.py`, lines 11-14):
```python
@pytest.fixture(autouse=True)
def _set_voss_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """All eval tests run with VOSS_DEV=1 so the gated verb is accessible."""
    monkeypatch.setenv("VOSS_DEV", "1")
```
All SDK driver tests inherit this autouse fixture — no per-test `VOSS_DEV` setup needed.

**Hermetic test for `sdk:ts`/`sdk:go`/`sdk:rust` with `VOSS_SERVE_FAKE_TURN=1`:**
```python
# Pattern: set VOSS_SERVE_FAKE_TURN=1 in the serve spawn env for hermetic tests
# The consumer connects to the pre-spawned fake server; final = "echo: <prompt>"
# Permission gate will NOT fire (FAKE_TURN skips tool calls) — saw_permission_gate: false is expected

@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_sdk_ts_consumer_hermetic(tmp_path, monkeypatch):
    monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")
    # ... invoke runner with surface="sdk:ts" + stub server
    # assert row["surface"] == "sdk:ts"
    # assert row["gate_pass"] is True  (or False depending on check configuration)
```

---

## Shared Patterns

### Serve spawn / handshake (60s timeout)
**Source:** E3-RESEARCH.md Pattern 3 (lines 352-458) — to be implemented by E3-03
**Apply to:** `_drive_sdk_client` in `voss/eval/runner.py`
```python
# Spawn voss serve with LITELLM_LOCAL_MODEL_COST_MAP=true and stdin=PIPE (heartbeat)
# Parse handshake: {"v":1,"port":N,"token":"..."} from stdout, 60s deadline
# Kill: close stdin pipe first (EOF heartbeat self-terminates), then proc.wait(timeout=10)
proc = subprocess.Popen(
    [sys.executable, "-m", "voss.cli", "serve"],
    env={**os.environ, "LITELLM_LOCAL_MODEL_COST_MAP": "true", "VOSS_DEV": "1"},
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1,
)
# drain stderr thread (prevents pipe buffer fill blocking server)
threading.Thread(target=lambda: [_ for _ in proc.stderr], daemon=True).start()
# read handshake line with 60s timeout
```

### Consumer structured result schema
**Source:** E4-RESEARCH.md lines 264-277
**Apply to:** All three consumer programs (ts, go, rust)
```json
{
  "surface": "sdk:ts",
  "session_id": "<uuid>",
  "final": "<agent final answer>",
  "saw_permission_gate": false,
  "cost_usd": 0.0,
  "event_types_seen": ["server.connected", "final", "session.idle"]
}
```
Runner extracts `consumer_result["final"]` as the judge input. `saw_permission_gate` maps to a deterministic `file_contains`/`cmd` check on captured output.

### `VOSS_PYTHON` env var for Go consumer
**Source:** `sdk/go/spawn.go` lines 29-43 (`interpreterPath()`)
**Apply to:** `_drive_sdk_client` when `consumer == "go"`
```python
# Go SDK resolves python as: VOSS_PYTHON env → ../../.venv/bin/python (relative) → python3
# From tests/eval/sdk/consumers/go/, the relative path resolves WRONG.
# Always set VOSS_PYTHON to absolute path when spawning Go consumer:
consumer_env["VOSS_PYTHON"] = str(Path(sys.executable).resolve())
```

### Auth pattern
**Source:** `voss/eval/runner.py` lines 320-349 (`_build_provider_from_resolution`, `_provider_for_eval`)
**Apply to:** `_drive_sdk_python` (inherits provider from `_drive_task` call site)
The `sdk:python` driver receives the already-resolved `provider` from `_drive_task` — no new auth resolution needed. For `sdk:ts`/`sdk:go`/`sdk:rust`, auth is inherited via `os.environ` (same pattern as E3's `_live_env`).

### `REQUIRED_FIELDS` sentinel update rule
**Source:** `tests/eval/test_voss_eval_stub.py` lines 11-35
**Apply to:** Any E4 plan that adds a new top-level JSONL row key
E4 adds NO new JSONL fields (consumer result feeds existing `final`/`gate_pass` paths). If a plan adds `consumer_exit_code` or similar to the row, update `REQUIRED_FIELDS` in the SAME plan task. This is the known stale-sentinel hazard (MEMORY.md).

---

## No Analog Found

All files have analogs. No gaps.

---

## Pitfall Register (planner MUST encode as plan task guards)

| Pitfall | File affected | Guard |
|---------|--------------|-------|
| TS `VossLauncher.start()` 10s timeout (`dist/node.js:644`) | `consumer.js` | MUST NOT import from `@vosslang/sdk/node`; use `createVossClient` only |
| Go `interpreterPath()` CWD-relative (`spawn.go:29-43`) | `main.go`, `runner.py` | Consumer uses `AttachClient`; runner sets `VOSS_PYTHON=<abs>` |
| `VOSS_SERVE_FAKE_TURN` emits no `permission.updated` (`app.py:166-178`) | All consumers | Permission-gate scenarios = live-only; stub tests assert `saw_permission_gate: false` |
| Go consumer `go.mod` missing | `consumers/go/` | Add `go.mod` with `replace` directive pointing to `../../../../sdk/go` |
| TS consumer no `package.json` / `npm install` | `consumers/ts/` | Add `package.json` with `"type":"module"` + file: dep; run `npm install` in setup task |
| `sdk:python` driver touching private symbols | `runner.py _drive_sdk_python` | Import only from `voss.harness.__all__` + `voss_runtime.__all__`; comment any private gap |
| E3-01 not yet merged | `suite.py`, `runner.py` | W1 must gate on E3-01 OR absorb the `surface` field addition idempotently |
| Suite dir double-nesting (`suite.py:66`) | `tests/eval/sdk/` | Place scenarios at `tests/eval/sdk/<NN-slug>/task.toml` directly (not `sdk/sdk/`) |

---

## Metadata

**Analog search scope:** `voss/eval/`, `tests/eval/`, `sdk/go/`, `sdk/typescript/src/`, `crates/voss-sdk/tests/`, `.planning/phases/E3-surface-e2e/`
**Files scanned:** 24
**Pattern extraction date:** 2026-06-10

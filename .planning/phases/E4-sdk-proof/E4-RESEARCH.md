# Phase E4: SDK Proof - Research

**Researched:** 2026-06-10
**Domain:** SDK consumer proof — Python in-process harness API, TypeScript client SDK, Go client SDK, Rust client SDK assessment
**Confidence:** HIGH

---

## Summary

E4 extends E3's surface-proof pattern to three SDK surfaces: `sdk:python` (in-process `voss.harness`/`voss_runtime` public API, driven as the existing E1 runner already does internally), `sdk:ts` (the built `sdk/typescript` dist via a committed Node consumer subprogram against a live `voss serve`), and `sdk:go` (the `sdk/go` package via a committed Go consumer subprogram against a live `voss serve`). A fourth surface, `sdk:rust` (`crates/voss-sdk`), is a FULL V13.2 client SDK — NOT merely a spawn helper — and constitutes a viable fourth consumer (see Rust Client SDK Assessment below). All scored by the E1 substrate. No new runner, no new scoring.

The phase-critical E3 dependency question resolves cleanly: `suite.py` and `runner.py` do NOT yet have the `surface` field or `_drive_task` dispatch (E3 plans exist but are unexecuted). E4's planner must account for E3's W1 plan (E3-01) landing first, or define `sdk:*` surfaces in the same wave that adds the surface field. E3-01 is the natural vehicle for all surface schema work; E4 extends it with `sdk:python|sdk:ts|sdk:go` (and optionally `sdk:rust`).

One critical pitfall discovered by direct source inspection: the TypeScript `VossLauncher.start()` uses a 10-second handshake timeout (`HANDSHAKE_TIMEOUT_MS = 10_000`) baked into both `src/launcher/launcher.ts` and `dist/node.js`. Cold litellm startup takes 15-45 seconds. The TS consumer subprogram MUST set `LITELLM_LOCAL_MODEL_COST_MAP=true` in the environment before spawning (which cuts startup to ~5-10s on warm imports) AND must NOT use `VossLauncher` directly — it must use the serve-fixture pattern from the SDK tests (`spawnVossServe` with the 60s pattern from `sdk/typescript/tests/helpers/serve-fixture.ts`) or spawn its own server before importing VossLauncher, keeping the server pre-warmed.

**Primary recommendation:** Implement E4 as three consumer subprograms + two new `sdk:*` surface drivers in `runner.py` (with `sdk:python` reusing the existing `_drive_task` in-process path plus a thin wrapper that proves the public API symbols). Consumer subprograms emit structured JSON to stdout; the Python runner scores against E1's gate+judge path. `VOSS_SERVE_FAKE_TURN=1` provides hermetic test paths for `sdk:ts` and `sdk:go` consumers.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** E4 proves exactly three SDK surfaces: `sdk:python` (in-process embedder via `voss.harness`/`voss_runtime` public API — M7 surface in `docs/sdk.md`), `sdk:ts` (`sdk/typescript` V13.1 client against live `voss serve`), `sdk:go` (`sdk/go` V13.3 client against live `voss serve`).

**D-02 (deferred surfaces):** Rust client (V13.2) — NOT in `sdk/` (only `go`+`typescript` present); deferred until its client surface is confirmed shipped (fast-follow if present). C ABI (V13.4) is doc-only — out.

**D-03:** Representative workflow, not smoke. The client SDKs (`sdk:ts`, `sdk:go`) each run the marquee path: construct client → spawn/attach `voss serve` → create session + one live model turn → consume the typed SSE event union → hit a gated tool call → reply Allow via the permission route → reach final → read the session/audit back. A Deny variant asserts the turn degrades without hanging.

**D-04:** `sdk:python` drives in-process via the public API (construct harness, run a live turn, introspect via the public `TurnResult`). Checks assert the typed result + readable session; judge scores the agent output.

**D-05:** Reuse the E1 substrate + extend E3's per-surface driver dispatch. Scenarios are `task.toml` files in `tests/eval/sdk/<NN>-<slug>/` invoked via `voss eval --suite sdk`. New `surface` values: `sdk:python | sdk:ts | sdk:go`.

**D-06:** For `sdk:ts`/`sdk:go`, the driver spawns a minimal committed consumer subprogram (`tests/eval/sdk/consumers/{ts,go}/`) that uses ONLY the real SDK's public client API against the live server and emits structured JSON to stdout.

**D-07:** Shape-AGNOSTIC — prove the SDK surface once on a single simple fixture.

**D-08:** One documented live run on codex subscription auth: every surface ≥1 scenario, overall ≥80% `gate_pass`, 0 capped rows, permission-gate scenario among the passers.

### Claude's Discretion
- Scenario count per surface (1–2 each; keep total sub burn ≤ ~8 scenarios).
- Consumer-subprogram internals (build/run command, structured-result schema, timeout plumbing).
- Whether `surface` dispatch extends E3's registry/match or adds parallel `sdk:*` entries.
- serve readiness/teardown for the client scenarios (reuse E3's serve driver lifecycle).

### Deferred Ideas (OUT OF SCOPE)
- Rust client SDK (V13.2) scenario (unless user decides to include based on this research).
- C ABI (V13.4) — doc-only, no SDK to exercise.
- SDK × repo-shape cross-product.
- Org-plane SDK scenarios.
- LangSmith trace export of SDK runs.
</user_constraints>

---

## Rust Client SDK Assessment (Research Question 1 — Priority)

**Finding: `crates/voss-sdk` IS the full V13.2 Rust client SDK.** D-02's "not in `sdk/`" deferral was based on directory location, not content. The crate is a complete client SDK with:

| Capability | Rust module | Public re-export |
|------------|-------------|-----------------|
| Serve spawn + handshake | `supervisor.rs` | `spawn`, `spawn_with`, `Supervisor` |
| REST client | `client.rs` | `VossClient` |
| SSE typed stream | `stream.rs` | `event_stream` |
| Auth/handshake parse | `auth.rs` | `Handshake` |
| Typed event union | `types/events.rs` | (via `event_stream` item type) |
| UI projection | `projection.rs` | `UiProjection` |

`lib.rs:pub use` exports: `Handshake`, `VossClient`, `UiProjection`, `event_stream`, `spawn`, `spawn_with`, `Supervisor`.

The integration tests in `crates/voss-sdk/tests/integration.rs` exercise: `spawn_with` → `create_session` → `post_message` → SSE stream via `event_stream()` → permission reply via `client.permission_reply()` — the full marquee path including a live permission gate roundtrip (`permission_roundtrip` test). All tests gate on `.venv/bin/python` presence; `VOSS_SERVE_FAKE_TURN=1` is the hermetic path. Cargo is present (`1.95.0-nightly`).

**Consumer subprogram command:** `cargo run --manifest-path crates/voss-sdk/Cargo.toml --example sdk_proof_consumer` (or a dedicated binary in `tests/eval/sdk/consumers/rust/`).

**Recommendation for planner/user:** Include `sdk:rust` as a fourth consumer (D-02 fast-follow condition is met). The consumer subprogram structure is identical to Go: emit structured JSON to stdout, driven by `spawn_with(&python, &[("VOSS_SERVE_FAKE_TURN","1")])` for hermetic tests and real creds for live. All toolchain present. Add to D-01 scope or leave to user decision — research surfaces the viable option explicitly.

[VERIFIED: direct source read of `crates/voss-sdk/src/lib.rs`, `client.rs`, `supervisor.rs`, `stream.rs`, `tests/integration.rs`]

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `sdk:python` in-process driving | eval runner (runner.py) | voss.harness public API | runner.py already drives `run_turn`; sdk:python scenario wraps it to prove only public symbols |
| `sdk:ts` consumer subprogram | tests/eval/sdk/consumers/ts/ | sdk/typescript dist | Node.js program using SDK public API; Python runner spawns it |
| `sdk:go` consumer subprogram | tests/eval/sdk/consumers/go/ | sdk/go package | Go program using SDK public API; Python runner spawns it |
| `sdk:rust` consumer subprogram (optional) | tests/eval/sdk/consumers/rust/ | crates/voss-sdk | Rust binary using SDK public API; Python runner spawns via `cargo run` |
| surface dispatch routing | voss/eval/runner.py `_drive_task` | suite.py `TaskSpec.surface` | Extends E3's dispatch skeleton with `sdk:*` branches |
| Consumer JSON scoring | E1 substrate (runner.py `_run_checks`, `judge_run`) | — | Consumers emit result JSON; runner scores it — no per-runtime scoring |
| serve spawn/handshake for ts/go/rust | eval runner serve lifecycle | sdk/{go,ts} spawn internals | Python runner spawns the serve subprocess; consumer gets baseURL+token via env or args |
| VOSS_SERVE_FAKE_TURN hermetic path | server/app.py seam | — | Already exists: emits canned SSE turn (no provider needed) |

---

## SDK Public API Map (Research Question 2)

### `sdk:python` — Public Entry Points

[VERIFIED: `voss/harness/__init__.py`, `voss_runtime/__init__.py`, `docs/sdk.md`]

**`voss.harness.__all__`:**
| Symbol | Type | E4 use |
|--------|------|--------|
| `run_turn` | `async def` | Drive one live turn; returns `TurnResult` |
| `Plan` | Pydantic model | Field on TurnResult |
| `TurnResult` | dataclass | Holds `final: str`, `confidence: float`, `cost_usd: float`, `plan: Plan`, `tool_results: list[str]`, `run: RunRecord | None` |
| `PermissionGate` | class | `PermissionGate(mode="plan")` — read-only tier |
| `ToolEntry` | class | Needed to build toolset |
| `RunSemantics` | dataclass | Closing-turn semantics |
| `ToolCall` | model | Plan step |
| `main` | callable | CLI entry point — not used for in-process driving |

**`voss_runtime.__all__`:**
Key symbols for E4: `StubProvider` (hermetic test), `configure(max_iterations=N)` (cap), `RuntimeConfig`, `EpisodicMemory` (history), `ProbableValue`.

**Critical gap:** `NullRenderer` / `PlainRenderer` are NOT in `voss.harness.__all__`. The runner uses `PlainRenderer()` internally (a private path). The `sdk:python` driver must use the same private path as the runner (`from voss.harness.render import PlainRenderer`) or pass a stub renderer object. Since the E4 driver runs inside the same process as the runner, using `PlainRenderer` (private) is acceptable — same pattern as `runner.py` itself. The public SDK gap is noted in `docs/sdk.md` ("Known gaps — NullRenderer"). The `sdk:python` scenario is essentially an audit that `run_turn` + public symbols work with only `PlainRenderer` as the renderer dependency.

**`sdk:python` driver approach:** The E4 `sdk:python` driver is NOT a separate consumer subprogram — it runs in-process inside `_drive_task` like the existing `internal` surface. The distinction is: the `sdk:python` driver calls `run_turn` using ONLY symbols reachable via `from voss.harness import ...` and `from voss_runtime import ...` (the public surface), not internals like `session_store`, `make_toolset`, or provider-building helpers. This proves the public-API contract from an external-consumer perspective, while remaining in-process for simplicity (D-04).

### `sdk:ts` — Public Entry Points

[VERIFIED: `sdk/typescript/src/index.ts`, `src/client/rest.ts`, `src/client/sse.ts`, `src/client/permission.ts`, `src/node.ts`, `dist/index.js`, `dist/node.js`]

**Main export (`@vosslang/sdk` — `dist/index.js`):**
| Symbol | Type | E4 use |
|--------|------|--------|
| `createVossClient(baseUrl, token)` | function → `VossClient` | Construct REST client |
| `VossClient.createSession(cwd?)` | async → `string` | Create session, get id |
| `VossClient.postMessage(sessionId, text, mode?)` | async → `AcceptedResponse` | Submit turn |
| `VossClient.getCost(sessionId)` | async → `CostInfo` | Read cost/turns after turn |
| `VossClient.getSession(sessionId)` | async → `SessionInfo` | Read session state |
| `VossClient.deleteSession(sessionId)` | async | Cleanup |
| `subscribeToEvents(baseUrl, sessionId, token, signal?)` | AsyncIterable `AgentEvent` | SSE typed stream |
| `replyPermission(client, sessionId, {id, choice})` | async | Permission gate reply |
| `VossApiError` | class | Typed error (status, detail) |
| `AgentEvent` | union type | Discriminated event union from `EventEnvelope["event"]` |

**Node export (`@vosslang/sdk/node` — `dist/node.js`):**
| Symbol | Type | E4 use |
|--------|------|--------|
| `VossLauncher` | class | Spawn `voss serve` + get client |
| `VossLauncher.start(options?)` | async → `{client, pid}` | Spawn server (BUT: 10s timeout — see Pitfall 1) |
| `VossLauncher.dispose()` | void | Kill server subprocess |
| `VossHandshake` | type | Handshake shape |

**CRITICAL NOTE:** `VossLauncher.start()` has a 10-second handshake timeout (baked into `dist/node.js:644: var HANDSHAKE_TIMEOUT_MS = 1e4`). Cold litellm startup is 15-45 seconds. The TS consumer subprogram MUST bypass `VossLauncher` and spawn the server directly (using the test helper pattern from `tests/helpers/serve-fixture.ts`) OR the Python runner must pre-spawn the server and pass `baseUrl` + `token` to the consumer via env/args.

**Recommended approach:** Python runner spawns the server (same as E3 serve driver — reuse `_drive_serve`'s spawn + handshake logic), then passes `VOSS_BASE_URL=http://127.0.0.1:PORT` and `VOSS_TOKEN=...` as env vars to the TS consumer subprocess. The consumer uses `createVossClient(baseUrl, token)` (no VossLauncher). This sidesteps the 10s timeout completely and keeps the Python runner as the single lifecycle owner.

**TS consumer build path:** The dist is already built (`dist/index.js`, `dist/node.js`). Consumer program is a plain `.js` file (ESM) that imports from `../../dist/index.js` (relative path from `tests/eval/sdk/consumers/ts/`). Run with `node consumer.js`. No `tsx` or `--experimental-strip-types` needed since the dist is pre-built CommonJS/ESM.

### `sdk:go` — Public Entry Points

[VERIFIED: `sdk/go/client.go`, `sdk/go/rest.go`, `sdk/go/spawn.go`, `sdk/go/sse.go`, `sdk/go/client_test.go`, `sdk/go/permission_test.go`]

Go module: `github.com/vosslang/voss/sdk/go` — imported as `package voss`.

| Symbol | Type | E4 use |
|--------|------|--------|
| `Spawn(ctx, extraEnv)` | func → `(*Client, error)` | Spawn `voss serve` (60s timeout, stdin heartbeat) |
| `AttachClient(baseURL, token)` | func → `*Client` | Attach to pre-spawned server |
| `Client.CreateSession(ctx, cwd)` | method → `(string, error)` | POST /session |
| `Client.PostMessage(ctx, id, text, mode)` | method → error | POST /session/:id/message |
| `Client.Events(ctx, sessionID)` | method → `(<-chan TypedEvent, error)` | GET SSE stream (returns typed channel) |
| `Client.PermissionReply(ctx, sessionID, id, choice)` | method → `(bool, error)` | POST /session/:id/permission; returns stale bool |
| `Client.GetSession(ctx, id)` | method → `(SessionInfo, error)` | Read live session |
| `Client.Cost(ctx, id)` | method → `(CostInfo, error)` | Read cost rollup |
| `Client.ListSavedSessions(ctx, cwd)` | method → `([]SavedSession, error)` | Read saved sessions |
| `Client.Close()` | method → error | Kill spawned child (no-op for attach) |
| `TypedEvent` | interface | Discriminated event; `.eventType()` → string |
| `SpawnError` | `*SpawnError` | Typed spawn failure |

**Go consumer approach:** `go run .` from `tests/eval/sdk/consumers/go/` directory. The consumer either calls `Spawn()` directly (Spawn has a 60-second handshake timeout — safe for cold start) OR the Python runner pre-spawns and passes env vars. Recommendation: let the Go consumer call `Spawn()` directly using `extraEnv = {"VOSS_SERVE_FAKE_TURN":"1"}` for hermetic tests; for live tests, pass `VOSS_PYTHON` env var so `interpreterPath()` resolves correctly.

**Go consumer `interpreterPath()` note:** The Go SDK's `interpreterPath()` resolves Python as: `VOSS_PYTHON` env var → `../../.venv/bin/python` (relative to CWD) → `python3`. For `go run` from `tests/eval/sdk/consumers/go/`, the relative path `../../.venv/bin/python` will NOT resolve correctly. The Python runner MUST set `VOSS_PYTHON=<absolute path to .venv/bin/python>` when spawning the Go consumer subprocess.

### `sdk:rust` — Public Entry Points

[VERIFIED: `crates/voss-sdk/src/lib.rs`, `client.rs`, `supervisor.rs`, `stream.rs`, `tests/integration.rs`]

| Symbol | Type | E4 use |
|--------|------|--------|
| `spawn_with(python, extra_env)` | `async fn` → `Supervisor` | Spawn server; 60s timeout, LITELLM guard |
| `Supervisor.client` | `VossClient` (pub field) | Attached client |
| `Supervisor.shutdown()` | `async fn` | Kill + reap server |
| `VossClient::new(base, token)` | constructor | Build client from known base/token |
| `VossClient.create_session(cwd)` | `async fn → String` | POST /session |
| `VossClient.post_message(sid, text, mode)` | `async fn` | POST /session/:id/message |
| `VossClient.permission_reply(sid, id, choice)` | `async fn` | POST /session/:id/permission |
| `VossClient.cost(sid)` | `async fn → CostInfo` | GET /session/:id/cost |
| `event_stream(client, session_id)` | fn → `impl Stream<Item=Result<AgentEvent,VossError>>` | Typed SSE stream |
| `UiProjection` | enum | TryFrom<&AgentEvent> lossy UI projection |

**Rust consumer command:** `cargo run --manifest-path crates/voss-sdk/Cargo.toml --bin <name>` or add a consumer binary to `tests/eval/sdk/consumers/rust/`. Cargo is present (`1.95.0-nightly`).

---

## E3 Dispatch Contract (Research Question 3)

[VERIFIED: `voss/eval/suite.py`, `voss/eval/runner.py`, `.planning/phases/E3-surface-e2e/E3-01-PLAN.md`]

**Current state (pre-E3 execution):** `suite.py` `TaskSpec` has NO `surface` field. `runner.py` `_drive_task` has NO surface dispatch — all tasks run in-process via `run_turn`. E3-01 adds both.

**E3-01 interface contract (from E3-01-PLAN.md — planned, not executed):**
```python
# voss/eval/suite.py — after E3-01
class TaskSpec(BaseModel):
    ...
    surface: Literal["internal","cli:do","cli:chat","cli:edit","serve"] = "internal"
    target_file: str | None = None  # for cli:edit
    checks: list[AnyCheck] = Field(default_factory=list)

# voss/eval/runner.py — after E3-01: _drive_task dispatch skeleton
# internal → existing run_turn() path (unchanged)
# cli:do | cli:chat | cli:edit | serve → raise NotImplementedError (stubs for E3-02/03)
```

**E4 integration:** E4 extends the surface Literal with `| "sdk:python" | "sdk:ts" | "sdk:go"` (and optionally `| "sdk:rust"`). The surface dispatch in `_drive_task` adds new branches for these values.

**Dependency ordering options:**

Option A (natural): E3-01 ships first (adds `surface` + dispatch skeleton); E4-01 extends it with `sdk:*` values. Clean dependency chain.

Option B (parallel): E4-01 adds both the E3 `surface`/`target_file` schema AND the `sdk:*` values in a single plan wave, if E3 hasn't merged. This is the backup — it adds more scope to E4-W1 but unblocks if E3 is delayed.

**Recommendation:** E4's W1 plan should gate on E3-01 being merged. If E3 is unexecuted when E4 is planned, the planner must add a Wave 0 "ensure E3-01 is merged" checkpoint. E4 MUST NOT re-implement the `surface`/`target_file` fields independently — that creates schema conflicts.

**`_drive_task` dispatch pattern (match statement, post-E3-01):**
```python
# E4 extends runner.py _drive_task with three new branches
match spec.surface:
    case "internal":
        ...  # existing run_turn path (unchanged)
    case "cli:do" | "cli:chat" | "cli:edit":
        ...  # E3-02 CLI driver
    case "serve":
        ...  # E3-03 serve driver
    case "sdk:python":
        ...  # E4: in-process, calls run_turn via public API symbols
    case "sdk:ts" | "sdk:go" | "sdk:rust":
        ...  # E4: spawn consumer subprogram, capture JSON result
```

---

## Consumer Subprogram Mechanics (Research Question 4)

[VERIFIED: `sdk/go/spawn.go`, `sdk/go/client_test.go`, `sdk/typescript/src/launcher/launcher.ts`, `sdk/typescript/dist/node.js`, `crates/voss-sdk/src/supervisor.rs`]

### Python Runner → Consumer Subprogram Protocol

The Python runner owns the entire lifecycle:
1. Spawns `voss serve` subprocess (reuses E3's `_drive_serve` spawn pattern — 60s handshake)
2. Parses `{v, port, token}` handshake from stdout
3. Spawns consumer subprocess with env: `VOSS_BASE_URL=http://127.0.0.1:<port>`, `VOSS_TOKEN=<token>`, `VOSS_CWD=<fixture_cwd>`, `VOSS_PYTHON=<abs .venv/bin/python>`, `LITELLM_LOCAL_MODEL_COST_MAP=true`, `VOSS_DEV=1`
4. Consumer connects to pre-existing server (no need to spawn its own)
5. Consumer emits one-line JSON to stdout on completion
6. Runner kills consumer (timeout), then kills server
7. Runner reads consumer JSON + file_diff → feeds E1 gate+judge

**Consumer structured result (stdout, one JSON line):**
```json
{
  "surface": "sdk:ts",
  "session_id": "<uuid>",
  "final": "<agent final answer text>",
  "saw_permission_gate": true,
  "permission_choice": "a",
  "cost_usd": 0.03,
  "event_types_seen": ["server.connected", "permission.updated", "final", "session.idle"]
}
```

Runner extracts `final` from this for judge scoring. `saw_permission_gate` maps to a deterministic check. `event_types_seen` maps to a check like `file_contains` on the captured JSON output (or a `cmd` check running jq).

### TS Consumer Subprogram

**File:** `tests/eval/sdk/consumers/ts/consumer.js` (plain ESM `.js`, no TS compilation needed)

**Import path:** `import { createVossClient, subscribeToEvents, replyPermission } from "../../../../../../sdk/typescript/dist/index.js"` (relative path from consumer location to dist).

**Run command:** `node --input-type=module tests/eval/sdk/consumers/ts/consumer.js` or just `node tests/eval/sdk/consumers/ts/consumer.js` (ESM auto-detect via `.js` extension when `"type":"module"` or explicit).

**Key pattern:** Consumer receives `VOSS_BASE_URL` + `VOSS_TOKEN` + `VOSS_CWD` from env. It calls `createVossClient(baseUrl, token)`, then `subscribeToEvents(baseUrl, sessionId, token)` to get the SSE stream as an `AsyncIterable<AgentEvent>`. No `VossLauncher` needed — server is pre-spawned by Python runner.

**SSE consumption in TS consumer:**
```javascript
// AgentEvent is the discriminated union; each event has a .type property
for await (const event of subscribeToEvents(baseUrl, sessionId, token)) {
    if (event.type === "permission.updated") {
        await replyPermission(client, sessionId, { id: event.id, choice: "a" });
    }
    if (event.type === "final") { finalText = event.text; }
    if (event.type === "session.idle") { break; }
}
```

### Go Consumer Subprogram

**File:** `tests/eval/sdk/consumers/go/main.go`

**Run command:** `go run tests/eval/sdk/consumers/go/main.go`

**Module approach:** The consumer imports `github.com/vosslang/voss/sdk/go` via `go.mod` with a `replace` directive pointing to `../../../../../../sdk/go` (relative from consumer directory) or an absolute path. Alternatively, the Go file uses `go.work` from the repo root.

**Preferred approach:** Add the consumer as a standalone Go program with its own `go.mod` that uses `replace github.com/vosslang/voss/sdk/go => ../../../../sdk/go`. This keeps it hermetically buildable without requiring workspace-level setup.

**Consumer connects to pre-spawned server:** Uses `AttachClient(baseURL, token)` — no `Spawn()` call. Receives env vars from Python runner.

**SSE consumption in Go consumer:**
```go
ch, err := client.Events(ctx, sessionID)
for ev := range ch {
    switch e := ev.(type) {
    case TypedEventPermissionUpdated:
        client.PermissionReply(ctx, sessionID, e.id, "a")
    case TypedEventFinal:
        finalText = e.text
    case TypedEventSessionIdle:
        break
    }
}
```

Note: `TypedEvent` is an interface; Go SDK uses a channel `<-chan TypedEvent`. The `TypedEvent` interface's concrete types come from `events.go` (the `Decode()` function maps to typed structs). Check `sdk/go/events.go` for the exact typed event structs — the Go SDK wraps the OpenAPI-generated types.

### Rust Consumer Subprogram (if included)

**File:** `tests/eval/sdk/consumers/rust/main.rs` in a minimal Cargo project or as `crates/voss-sdk/examples/sdk_proof_consumer.rs`

**Run command:** `cargo run --manifest-path crates/voss-sdk/Cargo.toml --example sdk_proof_consumer`

**Consumer connects to pre-spawned server:** Uses `VossClient::new(base_url, token)` — no `spawn_with()`. Env vars from Python runner.

**SSE consumption:** `event_stream(client, session_id)` returns a `Stream<Item=Result<AgentEvent, VossError>>`. Collect until `AgentEvent::SessionIdle`.

### Hermetic vs Live Boundary

| Mode | Server | Consumer env | Creds needed |
|------|--------|--------------|--------------|
| Hermetic (stub) | `VOSS_SERVE_FAKE_TURN=1` in spawn env | Same | No (no provider call) |
| Live | Real creds via `auth.resolve("auto")` | Same; `VOSS_AUTH=codex` | Yes — operator checkpoint |

Python driver spawns server with `VOSS_SERVE_FAKE_TURN=1` for stub-mode tests. The hermetic test validates the consumer subprogram's spawn, handshake, session create, SSE consumption, and structured-result JSON emission — without any model calls. The `final` text in fake turn is `"echo: <prompt>"`.

**FAKE_TURN does NOT emit `permission.updated`** (confirmed: `app.py:166-178` — the fake turn path skips all tool calls and the permission gate). Permission gate tests MUST run in live mode with real creds.

---

## Pitfalls (Research Question 4b + Permission Gate)

### Pitfall 1: TS `VossLauncher` 10-Second Handshake Timeout
**What goes wrong:** `VossLauncher.start()` has `HANDSHAKE_TIMEOUT_MS = 10_000` (10 seconds) hardcoded in both `src/launcher/launcher.ts` and the built `dist/node.js`. Cold litellm startup takes 15-45 seconds. Any TS consumer that calls `launcher.start()` directly will always time out on a cold start.
**Why it happens:** The SDK test suite always uses `VOSS_SERVE_FAKE_TURN=1` which skips litellm import entirely (instant start). The VossLauncher timeout was calibrated for FAKE_TURN, not live.
**How to avoid:** The Python runner pre-spawns the server (60s timeout, same as E3's `_drive_serve`). The TS consumer receives `VOSS_BASE_URL`+`VOSS_TOKEN` via environment and calls `createVossClient(baseUrl, token)` directly — `VossLauncher` is not used. For the hermetic test, `VOSS_SERVE_FAKE_TURN=1` in the serve spawn env still works fine.
**Warning signs:** TS consumer exits with "timed out waiting for voss serve handshake" after exactly 10 seconds.
[VERIFIED: `dist/node.js:644: var HANDSHAKE_TIMEOUT_MS = 1e4`]

### Pitfall 2: Go Consumer `interpreterPath()` CWD-Relative Resolution
**What goes wrong:** `sdk/go/spawn.go:interpreterPath()` resolves `.venv/bin/python` as `../../.venv/bin/python` relative to the CWD at `go run` time. When the Go consumer is run from `tests/eval/sdk/consumers/go/`, this path resolves to the wrong directory (4 levels deep, not 2).
**Why it happens:** The Go SDK was designed to be run from within `sdk/go/` (2 levels from repo root). A consumer binary run from a test directory has a different CWD.
**How to avoid:** Python runner sets `VOSS_PYTHON=<absolute .venv/bin/python path>` in env when spawning the Go consumer. The Go consumer uses `AttachClient()` (not `Spawn()`), so `interpreterPath()` is never called at all.
**Warning signs:** Go consumer exits with `spawn voss serve: fork/exec python3: no such file or directory` or connects to wrong/non-existent server.
[VERIFIED: `sdk/go/spawn.go:29-43 interpreterPath()`]

### Pitfall 3: FAKE_TURN Emits No `permission.updated` Event
**What goes wrong:** The `VOSS_SERVE_FAKE_TURN=1` seam emits a canned turn (`hello → echo: <text> → session.idle`) with no tool calls and no permission gate event. Consumer programs listening for `permission.updated` never receive it; they drain to `session.idle` and report `saw_permission_gate: false`.
**Why it happens:** `app.py:166-178` — the fake turn path deliberately skips all tool execution and permission machinery to provide a minimal hermetic test path.
**How to avoid:** Permission-gate proof scenarios MUST run in live mode. The stub path verifies SSE consumption and subprogram plumbing; the live path verifies the full gate roundtrip. Scenario task.toml files for permission proof must NOT set `stub = true` (they're live-only, gated behind VOSS_DEV + operator creds).
**Warning signs:** Permission-gate scenario passes in stub mode with `saw_permission_gate: false` — this is expected/correct for stub mode. Never interpret stub `saw_permission_gate: false` as a production regression.
[VERIFIED: `voss/harness/server/app.py:166-178`]

### Pitfall 4: Consumer `go run` Module Resolution
**What goes wrong:** `go run tests/eval/sdk/consumers/go/main.go` fails if `main.go` imports `github.com/vosslang/voss/sdk/go` but there's no `go.mod` or `go.work` file that maps this module path to the local `sdk/go/` directory.
**Why it happens:** Go requires explicit module resolution for local dependencies. `go run` without a module context fails with "cannot find module" for workspace-local packages.
**How to avoid:** The consumer directory needs its own `go.mod` with `require github.com/vosslang/voss/sdk/go v0.0.0` and `replace github.com/vosslang/voss/sdk/go => ../../../../sdk/go`. Alternatively, if a `go.work` exists at the repo root, add the consumer module to it.
**Warning signs:** `go run` exits with `no required module provides package github.com/vosslang/voss/sdk/go`.

### Pitfall 5: TS Consumer ESM Import Path
**What goes wrong:** The TS consumer imports from `../../../../../../sdk/typescript/dist/index.js` — this relative path is brittle and breaks if the consumer is moved.
**Why it happens:** The built dist is not installed as a package; relative imports are the only option for a standalone consumer file.
**How to avoid:** Use a `package.json` in `tests/eval/sdk/consumers/ts/` with `"dependencies": {"@vosslang/sdk": "file:../../../../../../sdk/typescript"}` so `import { ... } from "@vosslang/sdk"` resolves correctly. Run `npm install` as part of Wave 0 setup. The package.json `"type": "module"` enables ESM.
**Warning signs:** `import { createVossClient } from "@vosslang/sdk"` fails with `ERR_PACKAGE_PATH_NOT_EXPORTED` or `Cannot find module`.

### Pitfall 6: `sdk:python` Driver Touches Private Symbols
**What goes wrong:** The `sdk:python` scenario's intent is to prove the PUBLIC API. If the driver reaches into private paths (`voss.harness.tools.make_toolset`, `voss.harness.session.SessionRecord`, etc.), it proves nothing about the external-consumer experience.
**Why it happens:** The existing `_drive_task` uses many private paths for convenience. An `sdk:python` driver that just calls the same code is not an external-consumer proof.
**How to avoid:** The `sdk:python` driver must import from `voss.harness` and `voss_runtime` public `__all__` only. The renderer (`PlainRenderer`) is the one documented private gap — using it is acceptable with a comment noting the M7 SDK Polish gap.
**Warning signs:** Driver imports from `voss.harness.tools`, `voss.harness.session`, or `voss.harness.providers` directly.

### Pitfall 7: Suite dir loading path
**What goes wrong:** E4's `voss eval --suite sdk` requires `tests/eval/sdk/<NN-slug>/task.toml` structure. The `load_suite` function in `suite.py:63-70` does: `suite_dir = suite_root if suite_root.name == suite or suite == "" else suite_root / suite`. If `SUITE_ROOT / "sdk"` contains a subdirectory also named `sdk`, double-nesting occurs.
**Why it happens:** `load_suite` has a directory name check that can double-nest the path.
**How to avoid:** Place scenario dirs directly at `tests/eval/sdk/<NN-slug>/task.toml`. The suite loader finds `suite_dir = tests/eval/sdk` directly when `suite_root.name == "sdk"`.

### Pitfall 8: E1 `run_suite` Sentinel REQUIRED_FIELDS Goes Stale
**What goes wrong:** Adding `sdk:*` surface values does NOT add new JSONL fields (the `surface` field itself is added by E3-01). But if E4 adds new consumer-result fields (e.g., `consumer_exit_code`, `consumer_stdout_lines`) to the row, `REQUIRED_FIELDS` in `test_voss_eval_stub.py` must be updated in the SAME plan. Known project hazard (MEMORY.md "voss stale sentinel tests").
**How to avoid:** Document all new JSONL row fields added by E4 and update `REQUIRED_FIELDS` in the same plan task.

---

## Standard Stack

### No New Dependencies

E4 requires no new Python packages. All toolchains are already present.

| Dependency | Status | Version | Notes |
|------------|--------|---------|-------|
| Python `.venv` | Present | 3.13.12 | All E1/E3 deps |
| `httpx` | Present | 0.28.1 | E3 serve driver reuse |
| Node.js | Present | v22.22.3 | TS consumer runtime |
| Go | Present | 1.26.2 | Go consumer `go run` |
| Cargo | Present | 1.95.0-nightly | Rust consumer (if included) |
| `sdk/typescript/dist/` | Built | — | Pre-built dist present |
| `sdk/typescript/node_modules/` | Installed | — | `eventsource-parser`, `openapi-fetch` present |
| `sdk/go` | Present | go 1.24.3 module | No build step needed for `go run` |

[VERIFIED: `go version`, `node --version`, `cargo --version`, `ls sdk/typescript/dist/`, `ls sdk/typescript/node_modules/eventsource-parser`]

---

## Package Legitimacy Audit

E4 introduces **zero new external packages**. All required dependencies are already installed in the project environment. The Package Legitimacy Gate is not applicable.

**Packages removed due to slopcheck:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
voss eval --suite sdk
     │
     ▼
run_suite() ──── load_suite("sdk") ──► tests/eval/sdk/**/*.toml
     │                                  (surface: sdk:python | sdk:ts | sdk:go | sdk:rust)
     │
     ├── for each task:
     │     │
     │     ▼
     │   _drive_task(task_id, spec, ..., surface=spec.surface)
     │     │
     │     ├─ "sdk:python" ──► _drive_sdk_python(spec, cwd, provider, model)
     │     │                     import voss.harness, voss_runtime (public __all__ only)
     │     │                     run_turn(prompt, tools=make_toolset(cwd), ...)
     │     │                     returns (TurnResult.final, git_diff)
     │     │
     │     ├─ "sdk:ts" ──────► _drive_sdk_client(spec, cwd, consumer="ts")
     │     │                     │
     │     │                     ├─ spawn voss serve → parse {v, port, token} (60s)
     │     │                     ├─ set env: VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD
     │     │                     ├─ spawn: node tests/eval/sdk/consumers/ts/consumer.js
     │     │                     ├─ read stdout JSON: {final, saw_permission_gate, ...}
     │     │                     ├─ kill consumer subprocess
     │     │                     └─ kill server subprocess
     │     │                     returns (json["final"], git_diff)
     │     │
     │     ├─ "sdk:go" ──────► _drive_sdk_client(spec, cwd, consumer="go")
     │     │                     │  (same lifecycle as ts; go run consumer/main.go)
     │     │                     └─ returns (json["final"], git_diff)
     │     │
     │     └─ "sdk:rust" ────► _drive_sdk_client(spec, cwd, consumer="rust")
     │                           │  (same lifecycle; cargo run --example ...)
     │                           └─ returns (json["final"], git_diff)
     │
     ▼
   _run_checks(spec.checks, cwd)   ──► gate_pass, check_results  [E1 executor]
     │
     ▼
   judge_run(...)                  ──► verdict  [E1 judge; skipped if capped]
     │
     ▼
   _append_row(runs_path, row)     ──► .voss/eval/<ts>/runs.jsonl
     │                                 (additive: surface field from E3; no new E4-specific JSONL fields)
     ▼
   write_summary(...)              ──► .voss/eval/<ts>/summary.md
```

### Recommended Project Structure

```
tests/eval/
└── sdk/                         # new suite directory (E4 creates)
    ├── 01-python-basic/
    │   ├── task.toml            # surface = "sdk:python"
    │   └── fixture/             # minimal Python project
    ├── 02-ts-permission-allow/
    │   ├── task.toml            # surface = "sdk:ts"
    │   └── fixture/
    ├── 03-go-permission-allow/
    │   ├── task.toml            # surface = "sdk:go"
    │   └── fixture/
    ├── [04-rust-permission-allow/]  # optional
    │   ├── task.toml            # surface = "sdk:rust"
    │   └── fixture/
    └── consumers/
        ├── ts/
        │   ├── consumer.js      # ESM consumer, imports from dist
        │   └── package.json     # "type":"module", dep on @vosslang/sdk file:path
        ├── go/
        │   ├── main.go          # Go consumer, imports voss package
        │   └── go.mod           # module + replace directive
        └── rust/                # optional
            ├── main.rs          # or as crates/voss-sdk/examples/
            └── Cargo.toml

voss/eval/
└── runner.py                    # +sdk:python driver + _drive_sdk_client() (E4 change)
                                 # (surface + target_file fields added by E3-01)
```

### Pattern 1: `_drive_sdk_client` (ts/go/rust surfaces)

```python
# Source: E4-RESEARCH analysis of sdk/go/spawn.go, sdk/typescript/dist/node.js patterns
# Mirror of E3's _drive_serve but spawning a consumer subprocess instead of driving directly.

import subprocess, json
from pathlib import Path

async def _drive_sdk_client(
    spec: TaskSpec,
    cwd: Path,
    *,
    consumer: str,   # "ts" | "go" | "rust"
    timeout: float = 180.0,
) -> tuple[str, str]:
    """Spawn voss serve, then spawn consumer subprogram. Return (final, git_diff)."""
    # Step 1: spawn serve (reuse E3 pattern — 60s handshake)
    proc_server, handshake = await _spawn_serve(cwd)
    base_url = f"http://127.0.0.1:{handshake['port']}"
    token = handshake["token"]

    # Step 2: build consumer command
    python_abs = str(Path(sys.executable).resolve())  # absolute .venv python
    env = {**os.environ,
           "LITELLM_LOCAL_MODEL_COST_MAP": "true",
           "VOSS_DEV": "1",
           "VOSS_BASE_URL": base_url,
           "VOSS_TOKEN": token,
           "VOSS_CWD": str(cwd),
           "VOSS_PYTHON": python_abs,  # needed by Go interpreterPath()
           "VOSS_PROMPT": spec.prompt,
           "VOSS_MODE": spec.mode,
    }
    consumers_dir = Path("tests/eval/sdk/consumers")
    if consumer == "ts":
        cmd = ["node", str(consumers_dir / "ts" / "consumer.js")]
    elif consumer == "go":
        cmd = ["go", "run", str(consumers_dir / "go" / "main.go")]
    elif consumer == "rust":
        cmd = ["cargo", "run", "--manifest-path", "crates/voss-sdk/Cargo.toml",
               "--example", "sdk_proof_consumer", "--quiet"]

    # Step 3: run consumer, capture stdout JSON
    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout, check=False
        )
        consumer_json = json.loads(result.stdout.strip().splitlines()[-1])
        final = consumer_json.get("final", "")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as exc:
        final = ""
    finally:
        _kill_server(proc_server)

    return final, _file_diff(cwd)
```

### Pattern 2: `sdk:python` Driver (in-process, public API only)

```python
# Source: voss/harness/__init__.py + docs/sdk.md public surface
from voss.harness import run_turn, PermissionGate, TurnResult
from voss.harness.render import PlainRenderer  # private — documented M7 gap
from voss.harness.tools import make_toolset    # private — production internal
from voss_runtime import configure, EpisodicMemory

async def _drive_sdk_python(spec, cwd, provider, model, max_turns=15):
    """Drive via public API symbols only. Proves external-consumer contract."""
    configure(max_iterations=max_turns)
    permissions = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)
    result: TurnResult = await run_turn(
        spec.prompt,
        tools=make_toolset(cwd),          # make_toolset private — acceptable for runner
        cwd=cwd,
        renderer=PlainRenderer(),          # private — M7 SDK gap; acceptable
        model=model,
        provider=provider,
        history=EpisodicMemory(capacity=40),
        permissions=permissions,
    )
    # result.final, result.confidence, result.cost_usd are the public outputs
    return result.final, _file_diff(cwd)
```

Note: `sdk:python` is functionally identical to the existing `internal` path but explicitly limits itself to public API symbols. The primary test value is proving `run_turn` works as documented in `docs/sdk.md` — not that the internal harness plumbing works (E1 already proves that).

### Pattern 3: TS Consumer Program Structure

```javascript
// tests/eval/sdk/consumers/ts/consumer.js
// Source: sdk/typescript/src/client/rest.ts, sse.ts, permission.ts
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

### Anti-Patterns to Avoid

- **Using `VossLauncher.start()` in the TS consumer:** 10s timeout fails on cold litellm startup. Python runner owns server lifecycle.
- **Consumer calling `Spawn()` in Go:** `interpreterPath()` resolves python relative to CWD. Python runner owns server lifecycle and passes `VOSS_BASE_URL`/`VOSS_TOKEN`.
- **Permission-gate hermetic tests:** `VOSS_SERVE_FAKE_TURN=1` emits no `permission.updated`. Only real-creds live tests can exercise the gate path.
- **Adding per-runtime scoring:** Consumer programs emit structured JSON to stdout. The Python runner scores it via E1's `_run_checks` + `judge_run`. Never add JSONL writes or judge calls inside consumer programs.
- **Consumer programs reading private harness state:** Consumer programs prove the external-consumer contract. They must use ONLY the published SDK client API.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE parsing in TS consumer | Custom line parser | `subscribeToEvents()` from `sdk/typescript/dist/index.js` | Uses `EventSourceParserStream` from `eventsource-parser` — handles chunking, ping lines, AbortController |
| SSE parsing in Go consumer | Custom `bufio.Scanner` | `client.Events(ctx, id)` — returns `<-chan TypedEvent` | Go SDK handles buffering, max line cap, ctx cancel, typed decode |
| SSE parsing in Rust consumer | Custom `lines()` reader | `event_stream(client, session_id)` — returns typed `Stream` | Rust SDK uses `eventsource_stream` crate — handles all edge cases |
| Server spawn/teardown in consumer | Consumer-owned spawn | Python runner owns server lifecycle; consumers use `AttachClient`/`createVossClient` | Avoids 10s TS timeout bug; single lifecycle owner; no orphans |
| Scoring in consumer programs | Per-runtime gate/judge | E1 substrate in Python runner | Keeps E1 as single scoring substrate; consumer is only an invocation adapter |
| Permission gate test harness | Mock permission server | `VOSS_SERVE_FAKE_TURN=1` for structure; real server for gate (live mode) | Fake turn seam already exists and exercises full SSE path without model calls |

---

## Runtime State Inventory

Not applicable — E4 is a greenfield addition (new eval suite + consumer programs). No rename/refactor/migration.

---

## Common Pitfalls

(See detailed Pitfall 1-8 section above. Summary here for quick reference.)

| Pitfall | Impact | Fix |
|---------|--------|-----|
| TS VossLauncher 10s timeout | Consumer always fails cold start | Python runner pre-spawns; consumer uses `createVossClient` directly |
| Go `interpreterPath()` CWD relative | Consumer `go run` resolves wrong Python | Python runner sets `VOSS_PYTHON=<abs>` env var; consumer uses `AttachClient` |
| FAKE_TURN emits no `permission.updated` | Hermetic tests can't verify gate | Gate tests = live only; stub tests verify SSE plumbing only |
| Go consumer no `go.mod` | `go run` fails with module not found | Add `go.mod` + `replace` directive in consumer dir |
| TS consumer no `package.json` | Import `@vosslang/sdk` fails | Add `package.json` + `npm install` in Wave 0 |
| `sdk:python` uses private symbols | Doesn't prove public API | Driver imports from `__all__` only; document any private gap |
| Suite dir double-nesting | Tasks not found | Scenarios at `tests/eval/sdk/<NN-slug>/task.toml` directly |
| REQUIRED_FIELDS sentinel stale | Test passes with wrong field set | Update sentinel same-plan as any new JSONL fields |

---

## E1 Integration Points

These are the live (post-E1) interfaces E4 consumes. All confirmed executed via E1 summaries.

[VERIFIED: E3-RESEARCH.md "E1 Integration Points" section — E1-01/02 executed]

```python
# voss/eval/suite.py — post-E3-01 (extends E3-01's surface field)
class TaskSpec(BaseModel):
    surface: Literal["internal","cli:do","cli:chat","cli:edit","serve",
                     "sdk:python","sdk:ts","sdk:go"] = "internal"
    target_file: str | None = None
    checks: list[AnyCheck] = Field(default_factory=list)
    ...

# voss/eval/runner.py — post-E1-01/02, post-E3-01 dispatch skeleton
def _run_checks(checks: list, cwd: Path) -> tuple[bool, list[dict]]: ...
async def _drive_task(task_id, spec, *, cwd, provider, model, stub, max_turns) -> ...:
    match spec.surface:
        case "internal": ...  # existing path
        case "cli:do" | ...: ...  # E3 drivers
        case "sdk:python": ...  # E4 adds this
        case "sdk:ts" | "sdk:go": ...  # E4 adds these

# JSONL row — post-E1, post-E3 (surface additive field already present)
row = {
    "task_id": ...,
    "surface": spec.surface,  # from E3-01
    "gate_pass": gate_pass,   # from E1-01
    "capped": capped,         # from E1-02
    # E4 adds NO new JSONL fields (consumer result extracted to "final" + checked via checks)
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SDK clients tested via stub server + type drift only | E4 live end-to-end via real model | E4 (new) | First proof that TS/Go/Rust clients work against real model output |
| Permission gate tested via httptest stubs in Go | Full permission roundtrip on real server via Go client | E4 (live) | Proves async Future bridge + SSE delivery work under real model timing |
| Python harness always driven as internal path | `sdk:python` explicit public-API audit | E4 (new) | Proves `run_turn` works via `voss.harness.__all__` contract |
| NullRenderer not in public API | `PlainRenderer` (private) acceptable for E4 | M7 pending | M7 SDK Polish will promote renderer interface; E4 documents gap |
| TS SDK `VossLauncher` 10s timeout | Python runner owns lifecycle; consumer uses `createVossClient` | E4 workaround | Structural issue in VossLauncher.ts — M7 SDK Polish opportunity |

**Deprecated/outdated:**
- Using `VossLauncher.start()` for any production test that involves live litellm startup — use pre-spawn pattern.

---

## Open Questions

1. **Include `sdk:rust` in E4 scope?**
   - What we know: `crates/voss-sdk` is the full V13.2 client SDK; Cargo 1.95 present; integration tests exist with `VOSS_SERVE_FAKE_TURN` hermetic path.
   - What's unclear: User decision — D-02 deferred until "confirmed shipped in `sdk/`" but it IS shipped in `crates/voss-sdk`.
   - Recommendation: Surface this to the user as a planner decision. Fast-follow option: add `sdk:rust` as a fourth surface with 1 scenario. Incremental sub-burn: +2 scenarios max.

2. **`sdk:python` driver scope: is it truly distinct from `internal`?**
   - What we know: `sdk:python` and `internal` both call `run_turn` in-process. The distinction is the driver restricts itself to public `__all__` symbols.
   - What's unclear: Is this distinction meaningful enough to warrant a separate scenario, or should E4 simply note that `internal` already proves `run_turn` works (since it IS the public API)?
   - Recommendation: Keep `sdk:python` as a distinct surface for the audit value — it explicitly documents which symbols an external embedder uses, and flags the `NullRenderer`/`PlainRenderer` gap as a concrete M7 action item.

3. **TS consumer package.json + `npm install` in Wave 0**
   - What we know: `sdk/typescript/node_modules/` has `eventsource-parser` and `openapi-fetch` installed; the dist is pre-built.
   - What's unclear: Should the consumer use a `file:` dependency pointing to the already-installed dist, or copy the dist inline?
   - Recommendation: `package.json` with `"@vosslang/sdk": "file:../../../../../../sdk/typescript"` — this resolves the package with the pre-built dist in `sdk/typescript/dist/`. No separate `npm install` needed if the file reference resolves correctly. Wave 0 should verify the import resolves before writing consumer code.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv/bin/python` | All drivers | ✓ | 3.13.12 | Use `sys.executable` |
| `httpx` | serve spawn pattern | ✓ | 0.28.1 | — |
| `fastapi` + `uvicorn` + `sse-starlette` | `voss serve` | ✓ | installed | — |
| `node` | TS consumer subprocess | ✓ | v22.22.3 | — |
| `go` | Go consumer `go run` | ✓ | 1.26.2 | — |
| `cargo` | Rust consumer (optional) | ✓ | 1.95.0-nightly | — |
| `sdk/typescript/dist/` | TS consumer import | ✓ | pre-built | rebuild: `npm run build` in `sdk/typescript/` |
| `sdk/go/` source | Go consumer import | ✓ | module present | — |
| `crates/voss-sdk/` | Rust consumer (optional) | ✓ | present | — |
| Codex subscription auth | D-08 live run | Operator-supplied | — | Cannot run live proof without it |
| `VOSS_DEV=1` | `voss eval` gate | Set by conftest autouse | — | Gate blocks CLI if not set |

[VERIFIED: `go version`, `node --version`, `cargo --version`, `ls sdk/typescript/dist/`, `ls sdk/typescript/node_modules/eventsource-parser/`]

**Missing dependencies with no fallback:**
- Codex subscription auth — required for D-08 proof run; all consumer code testable with `VOSS_SERVE_FAKE_TURN=1` stub path.

**Missing dependencies with fallback:**
- `sdk/typescript/dist/` needs rebuild if source changes — run `npm run build` in `sdk/typescript/`; dist is currently present.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8.0 with pytest-asyncio (asyncio_mode="auto") |
| Config file | `pyproject.toml` (asyncio_mode = "auto" at line 103) |
| Quick run command | `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/test_sdk_drivers.py -x -q` |
| Full suite command | `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/ -q` |

### Stub vs Live Boundary (per surface)

| Surface | Hermetic stub path | Stub achieves | Live path |
|---------|-------------------|---------------|-----------|
| `sdk:python` | `stub=True` → `StubProvider` in runner | `run_turn` returns without model call | `stub=False` + codex auth |
| `sdk:ts` | `VOSS_SERVE_FAKE_TURN=1` in serve spawn env | SSE event stream + session create + message + drain to idle | Same consumer, real serve |
| `sdk:go` | `VOSS_SERVE_FAKE_TURN=1` in serve spawn env (set by Python runner) | Same as TS | Same consumer, real serve |
| `sdk:rust` (opt.) | `VOSS_SERVE_FAKE_TURN=1` via Python runner | Same as TS/Go | Same consumer, real serve |

**Permission gate scenarios:** LIVE ONLY. Hermetic stub cannot emit `permission.updated` (FAKE_TURN seam does not call tool stack). Permission tests in `test_sdk_drivers.py` use `pytest.mark.skip` or `pytest.mark.xfail(strict=False)` for the gate-proof check, with a comment explaining they require live mode.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVSDK-01 (D-04) | `TaskSpec.surface` accepts `sdk:python/ts/go` values | unit | `pytest tests/eval/test_task_spec.py -x -q` | Extends E3-01's test |
| EVSDK-02 (D-04) | `sdk:python` driver calls `run_turn` via public API; returns `TurnResult.final` as "final" | unit stub | `pytest tests/eval/test_sdk_drivers.py::test_sdk_python_stub -x -q` | ❌ Wave 0 |
| EVSDK-03 (D-05) | `sdk:ts` driver spawns consumer, reads JSON, extracts final | integration stub | `pytest tests/eval/test_sdk_drivers.py::test_sdk_ts_stub -x -q` | ❌ Wave 0 |
| EVSDK-04 (D-05) | `sdk:go` driver spawns consumer, reads JSON, extracts final | integration stub | `pytest tests/eval/test_sdk_drivers.py::test_sdk_go_stub -x -q` | ❌ Wave 0 |
| EVSDK-05 (D-03) | TS consumer emits valid JSON with `final`, `saw_permission_gate`, `event_types_seen` | integration stub | `pytest tests/eval/test_sdk_drivers.py::test_ts_consumer_output_schema -x -q` | ❌ Wave 0 |
| EVSDK-06 (D-03) | Go consumer emits valid JSON with same schema | integration stub | `pytest tests/eval/test_sdk_drivers.py::test_go_consumer_output_schema -x -q` | ❌ Wave 0 |
| EVSDK-07 (D-03) | Permission-gate Allow: consumer receives `permission.updated`, replies "a", sees `tool_event` | manual/live | `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex -k 02` | ❌ (human checkpoint) |
| EVSDK-08 (D-03) | Permission-gate Deny: consumer replies "d", turn degrades, no hang | manual/live | `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex -k deny` | ❌ (human checkpoint) |
| EVSDK-09 (D-08) | Full SDK suite: ≥80% gate_pass, 0 capped, all surfaces present, permission scenario passing | manual/live | `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite sdk --auth codex` | ❌ (human checkpoint) |
| EVSDK-10 (D-05) | `voss eval --suite sdk` loads N SDK scenarios | integration stub | `pytest tests/eval/test_sdk_suite_load.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/test_sdk_drivers.py -x -q`
- **Per wave merge:** `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/ -q`
- **Phase gate:** Full suite green + EVSDK-09 live run operator checkpoint before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/eval/test_sdk_drivers.py` — covers EVSDK-02..06 using stub paths
- [ ] `tests/eval/test_sdk_suite_load.py` — covers EVSDK-10 (load_suite finds sdk dir)
- [ ] `tests/eval/sdk/consumers/ts/consumer.js` + `package.json` — must be created before ts driver tests
- [ ] `tests/eval/sdk/consumers/ts/` npm setup: verify `@vosslang/sdk` import resolves from `file:` dep
- [ ] `tests/eval/sdk/consumers/go/main.go` + `go.mod` with replace directive
- [ ] `tests/eval/sdk/` directory with 3+ task.toml + fixture dirs

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (serve bearer token to consumer) | Token passed via env var (not CLI arg); Python runner owns token lifecycle |
| V3 Session Management | yes (consumer creates sessions) | Session ids are UUIDs; ephemeral per-scenario |
| V4 Access Control | no (internal tool, single-operator) | VOSS_DEV=1 friction gate |
| V5 Input Validation | yes (consumer JSON output) | Runner validates `json.loads()` + key access; `except json.JSONDecodeError` → crash_reason |
| V6 Cryptography | minimal | Token via `secrets.token_urlsafe(32)` in serve.py; loopback-only binding |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Consumer stdout injection (non-JSON last line) | Tampering | Parse only `stdout.strip().splitlines()[-1]`; `json.JSONDecodeError` → FAIL gracefully |
| VOSS_TOKEN leaked via process environment | Information Disclosure | Token is ephemeral per-scenario; loopback-only server; process env visible to same user only |
| Runaway consumer subprocess | Denial | `subprocess.run(..., timeout=timeout)` kills on timeout; server killed in `finally` |
| `go run` / `cargo run` fetching from network | Integrity | Go module cache + replace directive = local only; Rust: `CARGO_NET_OFFLINE=1` optional |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sdk/typescript/dist/index.js` ESM module can be imported by a consumer `.js` via `file:` package.json dep | TS consumer structure | If node ESM resolution fails for `file:` dep, consumer needs to use relative `../../dist/index.js` import instead |
| A2 | Go consumer `go run main.go` with a local `go.mod` + `replace` directive builds and runs without network access (module cache populated) | Go consumer | If Go module cache doesn't have `oapi-codegen` deps cached, `go run` may attempt network fetch and fail |
| A3 | `VOSS_SERVE_FAKE_TURN=1` fake turn emits `final` event with text `"echo: <prompt>"` — consumer can assert this for hermetic tests | Hermetic stub path | If fake turn text changes, hermetic `final` content check breaks — low risk, just update check |
| A4 | E3-01 will be executed before E4's W1 plan is implemented (adds `surface` field + dispatch skeleton) | E3 dispatch contract | If E3 is delayed, E4-W1 must expand scope to include the E3-01 schema changes |
| A5 | The Go `sdk/go/` module dependencies are in Go module cache (no network needed for `go run`) | Go consumer build | If not cached, `go run` hangs on network fetch; mitigation: run `go mod download` in Wave 0 setup task |

---

## Sources

### Primary (HIGH confidence)
- `crates/voss-sdk/src/lib.rs`, `client.rs`, `supervisor.rs`, `stream.rs`, `projection.rs` — Rust SDK full public API
- `crates/voss-sdk/tests/integration.rs` — integration test patterns including permission roundtrip
- `sdk/go/client.go`, `rest.go`, `spawn.go`, `sse.go` — Go SDK full public API
- `sdk/go/client_test.go`, `permission_test.go` — Go SDK test patterns
- `sdk/typescript/src/index.ts`, `client/rest.ts`, `client/sse.ts`, `client/permission.ts`, `launcher/launcher.ts` — TS SDK full public API
- `sdk/typescript/dist/node.js` — confirms 10s `HANDSHAKE_TIMEOUT_MS` in built dist (line 644)
- `sdk/typescript/tests/launcher.test.ts`, `permission.test.ts`, `helpers/serve-fixture.ts` — TS test patterns
- `voss/harness/__init__.py` — `voss.harness.__all__` confirmed
- `voss_runtime/__init__.py` — `voss_runtime.__all__` confirmed
- `voss/harness/agent.py:479-487` — `TurnResult` dataclass fields confirmed
- `voss/harness/server/app.py:166-178` — `VOSS_SERVE_FAKE_TURN` fake turn (no permission.updated)
- `voss/eval/runner.py` — current runner.py (no surface field yet, E3-01 pending)
- `voss/eval/suite.py` — current TaskSpec (no surface field yet, E3-01 pending)
- `.planning/phases/E3-surface-e2e/E3-01-PLAN.md` — surface dispatch schema (contract for E4)
- `.planning/phases/E3-surface-e2e/E3-RESEARCH.md` — serve driver mechanics reused by E4

### Secondary (MEDIUM confidence)
- `sdk/typescript/tests/helpers/serve-fixture.ts` — TS serve spawn pattern for consumer alternative

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Rust SDK assessment: HIGH — read directly from `crates/voss-sdk/src/lib.rs` + integration tests
- TS SDK public API + 10s timeout pitfall: HIGH — read from source + confirmed in built dist
- Go SDK public API: HIGH — read from source
- Python public API: HIGH — read from `__init__.py` `__all__`
- E3 dispatch contract: HIGH for E3-01 plan contracts; MEDIUM until E3-01 executes
- Consumer subprogram design: MEDIUM — derived from SDK test patterns; exact go.mod structure is [ASSUMED]
- Environment availability: HIGH — confirmed via `command -v` + `ls`

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 days — stable codebase; invalidated if E3-01 deviates from its plan or SDK dists are rebuilt with changed exports)

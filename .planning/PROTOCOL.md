# Voss Harness Protocol — v1

**Created:** 2026-06-02 (H0.1)
**Status:** Contract LOCKED for H1–H6. Changes require a version bump (`v` field) + migration note.
**Consumers:** Python server (`voss serve`, H1) · Rust client (`voss-tui`, H2) · future web/VSCode/SDK clients.
**Source of truth for shapes:** existing `JsonRenderer` (`voss/harness/render.py:485-568`) + OpenCode `packages/sdk/js/src/gen/types.gen.ts` (mirrored where applicable). Voss diverges only by **adding** part/event/gate types — never overloading existing ones, so an unmodified OpenCode-style client degrades gracefully.

This document is the wire contract. The server emits exactly these shapes; the client deserializes exactly these shapes; a parity test (H3.3) fails CI on drift.

---

## 1. Transport & versioning

- **REST** (commands, request/response) + **SSE** (server→client event stream). Not WebSocket.
- Base URL: `http://127.0.0.1:<port>` (loopback only). No TLS on loopback.
- Every JSON body and every SSE `data` payload carries `"v": 1`. A breaking change increments `v` and ships a migration note here.
- Content types: REST = `application/json`; event stream = `text/event-stream`.
- OpenAPI 3.1 served at `GET /openapi.json` (FastAPI auto-gen). The SSE event union is documented via an `_EventEnvelope` schema component (see §6) so typed clients can codegen a tagged enum.

## 2. Auth & handshake

- On `voss serve`: bind `127.0.0.1:0` (ephemeral port), then **print exactly one line** of JSON to stdout before serving:
  ```json
  {"v":1,"port":54123,"token":"<url-safe-32-byte>"}
  ```
  The client reads this line to discover the port + bearer token. (Bind-before-serve avoids the start-then-query race.)
- Every request (REST + the SSE GET) must carry `Authorization: Bearer <token>`. Rejected at middleware with `401` (constant-time compare). No token → never reaches route logic.
- The token is per-server-process, ephemeral, never persisted.

## 3. Lifecycle

- The client supervises the server child: spawns it, reads the handshake, kills it on exit (`kill_on_drop` + explicit `start_kill`+`wait`).
- The server also self-terminates if its parent dies: `getppid()` poll (2s) + stdin-EOF fallback (macOS has no `PR_SET_PDEATHSIG`).
- Graceful shutdown cancels all in-flight turn tasks; in-flight SSE streams get a final farewell event before close.

## 4. Endpoints

| Method | Path | Purpose | Returns |
|---|---|---|---|
| `POST` | `/session` | Create session. Body `{parentID?, title?}` | `{id}` |
| `GET` | `/session` | List sessions | `[SessionInfo]` |
| `GET` | `/session/:id` | Session detail | `SessionInfo` |
| `DELETE` | `/session/:id` | Delete session + data | `204` |
| `POST` | `/session/:id/message` | Enqueue a user turn (async) | `202 {status:"accepted"}` |
| `GET` | `/session/:id/events` | SSE event stream for the session | `text/event-stream` |
| `POST` | `/session/:id/abort` | Cancel the in-flight turn | `202` |
| `POST` | `/session/:id/permission` | Reply to a pending permission request | `200` |
| `GET` | `/doctor` | Auth/config/tooling status | `DoctorReport` |
| `GET` | `/openapi.json` | OpenAPI 3.1 spec | spec |

**Voss-native (additive):** `POST /session/:id/budget` (set/inspect token-or-cost envelope) · `GET /session/:id/confidence` (turn confidence rollup). Paths mirror OpenCode for everything shared so existing SDK clients work unmodified.

**Concurrency:** one running turn per session. `POST /message` while a turn runs → `409`.

## 5. Message & parts schema

A turn's user input and the assistant's reply are **messages** composed of **parts** (mirrors OpenCode). Parts stream incrementally via `message.part.updated`-style events (here flattened to the per-event types in §6).

```jsonc
// POST /session/:id/message body
{
  "v": 1,
  "messageID": "<optional client id>",
  "model": {"providerID": "anthropic", "modelID": "claude-..."},   // optional; server resolves default
  "agent": "<optional agent name>",                                  // .voss/agents/*.md
  "mode": "plan|edit|auto",                                          // optional; maps to PermissionGate.mode
  "parts": [ {"type":"text","text":"fix the build"} ]
}
```

**Part union** (shared envelope `{type, ...}`):

| `type` | fields | source |
|---|---|---|
| `text` | `text` | user input / assistant text |
| `reasoning` | `text` | model thinking |
| `tool` | `callID, tool, state` | tool invocation (state = `pending\|running\|completed\|error`) |
| `file` | `mime, filename?, url` | file attachment/ref |
| **`probable`** | `text, probability, alternatives?:[{text,probability}]` | **Voss** — probabilistic claim |
| **`budget`** | `spent, limit, remaining, unit:"tokens"\|"usd"` | **Voss** — budget envelope |
| **`confidence`** | `score, basis?` | **Voss** — confidence rating |

`ToolState` is discriminated on `status`: `pending{input}` · `running{input,title?,time:{start}}` · `completed{input,output,title,time:{start,end}}` · `error{input,error,time:{start,end}}`.

The assistant message summary (returned on turn completion, persisted) carries `cost`, `tokens:{input,output,cache:{read,write}}`, and **Voss-add** `confidence?`, `budget?:{spent,limit,remaining}`.

## 6. SSE event taxonomy

Wire framing (sse-starlette `EventSourceResponse`):
```
event: <type>
data: {"v":1, ...payload}
id: <seq>
```
First event is always `server.connected`. Turn completion is signalled by `session.idle`. Each `<type>` below maps **1:1 to an existing `JsonRenderer` emit** (`render.py:493-567`) unless marked Voss-native — so the server is `EventBusRenderer` publishing the same shapes the `Renderer` protocol already produces.

| `event:` type | `data` payload (beyond `v`) | JsonRenderer origin |
|---|---|---|
| `server.connected` | `{}` (handshake) | — (server-only) |
| `banner` | `model, cwd, git` | `render.py:493` |
| `user` | `task` | `:496` |
| `thinking` | `label` | `:499` |
| `plan` | `confidence, steps:[{name,args}], cost_usd` | `:502` |
| `tool` | `name, args, summary, state` (state ∈ `ok\|error\|pending`) | `:510` |
| `clarify` | `question, confidence` | `:513` |
| `final` | `text, confidence, cost_usd` | `:516` |
| `stream.delta` | `text` | `:519` |
| `stream.finalize` | `role, confidence, cost_usd, timestamp` | `:522` |
| `status` | `model, tokens, cost_usd, ctx_pct` | `:539` |
| `cognition_loaded` | `architecture_tokens, constraints_count, plans_loaded, decisions_loaded` | `:542` |
| `cognition_overflow` | `architecture_tokens, budget` | `:558` |
| `warning` | `message` | `:567` |
| `permission.updated` | `id, tool_name, args, dimension` | server-only (§7) |
| `session.idle` | `{sessionID}` (turn done) | server-only |
| **`probable`** | `text, probability, alternatives?` | **Voss-native** |
| **`budget.updated`** | `sessionID, spent, limit, remaining, unit` | **Voss-native** |
| **`confidence.updated`** | `sessionID, messageID, score` | **Voss-native** |
| **`gate.updated`** | `sessionID, gate, decision` | **Voss-native** |

Notes:
- `stream.delta` is the hot path — keep it minimal (`{v,text}`).
- Provider-internal tool-use sub-events (`ToolUseStart/Delta/End`) do **not** cross this boundary; they are folded into the `plan` by the provider (`agent.py` consume loop). The client never sees them.
- `banner`/`user`/`final` are emitted by the server around the turn; `show_final` is not called inside the loop — the server emits `final` from `TurnResult.final`.

### `_EventEnvelope` (OpenAPI schema component)
A pydantic discriminated union (`Field(discriminator="type")`) over all event payload models, wrapped as `{event: AgentEvent}`, forced into OpenAPI components so codegen emits a tagged Rust enum. The `type` literal is both the SSE `event:` name and the serde tag.

## 7. Permission protocol

The agent's `PermissionGate` blocks on a decision whenever a mutating/shell/network tool needs approval. **Server has no TTY → the gate would deny everything** (`permissions.py:300-301`) unless a `prompt_fn` is injected. The protocol bridges it:

1. Gate calls injected `prompt_fn(tool_name, args) -> str`.
2. Server emits `permission.updated` `{id, tool_name, args, dimension}` and blocks on an `asyncio.Future` keyed by `id`.
3. Client shows a modal; user chooses.
4. Client `POST /session/:id/permission {v:1, id, choice}` where `choice ∈ "a"` (allow once) `| "A"` (allow always) `| "d"` (deny). Scope-expand uses the same channel with `"y"|"n"`.
5. Server resolves the Future; gate proceeds. Timeout (default 300s) → deny.

`dimension ∈ "tool" | "confidence" | "budget"` (Voss gate dimensions, H5.2).

## 8. Abort

`POST /session/:id/abort` → server `loop.call_soon_threadsafe(task.cancel)` on the turn task. Reuses the existing handler (`agent.py:1052`): emits `stream.delta("\n[interrupted]\n")` + `stream.finalize(role="system")` then `session.idle`, and records `exit_reason="interrupt"`. SSE client disconnect triggers the identical cancel.

## 9. Error model

- REST errors: standard HTTP status + `{v:1, detail}`.
- In-turn errors surface as a `warning` event and/or a `tool` event with `state:"error"`, then the turn completes with `final` carrying a `halted: ...` message (`TurnResult.final` conventions: `halted: max-iter`, `halted: budget`).
- `session.error` (OpenCode parity, reserved): `{sessionID, error}` for fatal session-level failures.

## 10. Session persistence

On turn completion the server calls `session_store.save(record, history)` → `<cwd>/.voss/sessions/<id>.json` (mode 0600). Session id = `uuid4().hex[:12]`. Resume rehydrates `SessionInfo` + `EpisodicMemory`; the M2 fix (H4.2) forwards **all** prior runs and widens the in-turn history window (was `history.last(6)` / `runs[-1]` only).

## 11. Worked sequence (one turn)

```
client                                   server
  │  POST /session                         │
  │ ───────────────────────────────────►  │  create, id=ab12cd34ef56
  │  ◄─────────────────────────────────── │  {id}
  │  GET /session/ab../events (SSE open)   │
  │  ◄═══ server.connected                 │
  │  POST /session/ab../message {parts}    │
  │ ───────────────────────────────────►  │  202; create_task(run_turn)
  │  ◄═══ thinking{label:"planning 1/8"}   │
  │  ◄═══ plan{confidence:.9,steps:[...]}  │
  │  ◄═══ tool{name:"fs_read",state:pending}
  │  ◄═══ tool{...,state:ok}               │
  │  ◄═══ permission.updated{id:p1,tool:fs_write}
  │  POST /permission {id:p1,choice:"a"} ► │  resolve future
  │  ◄═══ tool{name:"fs_write",state:ok}   │
  │  ◄═══ stream.delta{text:"Done. "}      │  (repeated)
  │  ◄═══ stream.finalize{role:assistant}  │
  │  ◄═══ final{text,confidence,cost_usd}  │
  │  ◄═══ session.idle{sessionID}          │  save(record,history)
```

## 12. Divergence summary (Voss vs OpenCode)

Additive only — every Voss addition slots into an existing extension point:
- **New part types:** `probable`, `budget`, `confidence` (ride the parts channel).
- **New events:** `budget.updated`, `confidence.updated`, `gate.updated` (sibling bus events).
- **New gate dimensions:** `confidence`, `budget` in the permission map (threshold patterns like `"<0.5":"ask"`, `">100%":"deny"`), with `dimension` on `permission.updated`.
- **New endpoints:** `/session/:id/budget`, `/session/:id/confidence`.
- **Assistant summary** gains `confidence?`, `budget?`.

---

*Implements HYBRID-REFACTOR-PLAN.md H0.1. Bound by Appendix A of that plan (verified API surface + pinned versions).*

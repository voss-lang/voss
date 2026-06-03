# Hybrid Client/Server Refactor Plan — Voss Harness

**Created:** 2026-06-02
**Status:** Proposal — H0 ready immediately; H1+ gated on H0 protocol lock
**Codename:** H0–H7
**Supersedes:** `.planning/RUST-PORT-PLAN.md` (subprocess-bridge R1–R9)

> **No hotfix phase.** The earlier P0 "usability hotfix" is dropped: B1 (`voss do` invisible output) and M1 (plain REPL ergonomics) are bandaids on render paths this refactor *replaces*. The durable logic fixes survive and are folded in: **M2** (lossy resume) → H4.2; **M3** (non-interactive permission denial) → H1.9 + H5.1. Stale-doc reconciliation → H0.2.

---

## 0. Architecture

```
┌─ voss-tui (Rust binary) ──────────┐        ┌─ voss serve (Python) ───────────────┐
│ clap · tokio · ratatui · reqwest  │  HTTP  │ FastAPI + sse-starlette             │
│ eventsource-stream                │◄──────►│ EventBusRenderer → existing run_turn│
│ thin: no creds, no provider code  │  +SSE  │ auth · providers · tools · sessions │
│ spawns + supervises the server    │        │ permissions · multiagent · MCP      │
└───────────────────────────────────┘        └──────────────┬──────────────────────┘
                                                             │ subprocess (unchanged)
                                                  ┌──────────▼──────────┐
                                                  │ voss compiler +     │
                                                  │ voss_runtime (Python)│
                                                  └─────────────────────┘
```

**Why hybrid beats the subprocess-bridge port:** auth/providers/wire-formats **stay Python** (never ported → no drift); migration is incremental (rewrite one server endpoint in Rust at a time behind a frozen contract) instead of big-bang; extra clients (web, VSCode, SDK) come free from the protocol; if the Rust effort stalls, the server is still fully functional.

**The seam (why the server is cheap):** the harness already routes all output through a 13-method `Renderer` Protocol (`render.py:27-58`). `JsonRenderer` (`render.py:485`) already emits one versioned JSON event per line. The server is a new **`EventBusRenderer`** satisfying that same Protocol, publishing events to an `asyncio.Queue` drained by an SSE endpoint. **The agent loop, providers, tools, sessions, permissions, auth are not rewritten.**

**Honest limit:** hybrid keeps Python on the *server* side. It does not deliver "zero Python on disk" — that is pure-Rust only. It delivers a thin Rust client, clean packaging, and a reversible path to more Rust.

**Decisions locked (were open in v1 of this doc):**
- Server: **FastAPI 0.136 + sse-starlette 3.4** (`EventSourceResponse`, not raw `StreamingResponse`).
- Transport: **SSE** (events one-way) + REST (commands). Not WebSocket.
- Rust SSE: **`eventsource-stream` 0.2 over reqwest 0.13 `bytes_stream()`** — NOT `reqwest-eventsource` (0.6 pins reqwest 0.12, incompatible).
- Protocol shapes: **mirror OpenCode `packages/sdk/js/src/gen/types.gen.ts`** verbatim where applicable; Voss diverges only by *adding* part/event/gate types.

---

## PHASE H0 — Contract & cleanup (~1 day)

Goal: freeze the wire contract and fix lying docs before any code.

- **H0.1 — Author `.planning/PROTOCOL.md` v1.** Endpoints (§A1), SSE event taxonomy (§A2), message+parts schema (§A3) mirroring OpenCode types.gen.ts. Map every one of the 13 `JsonRenderer` event shapes (`render.py:493-567`) to an SSE event type. Specify Voss-native additions: `probable`/`budget`/`confidence` parts + `budget.updated`/`confidence.updated`/`gate.updated` events.
  *Verify:* every `Renderer` method (§A0) has a corresponding protocol event; doc peer-read.
- **H0.2 — Reconcile stale planning docs.** `ROADMAP.md:31-36` marks T1–T5 TBD/open but code implements iteration loop, streaming, interrupt, parallel reads, caching. Mark Complete; fix `notes/daily-driver-punch-list.md`.
  *Verify:* ROADMAP claims match code reality.

**Exit:** PROTOCOL.md v1 reviewed; docs honest.

---

## PHASE H1 — Python server core (~3–4 days)

Goal: `voss serve` exposes the existing harness over REST+SSE without touching the agent loop or breaking `voss chat`.

- **H1.1 — Deps.** Add optional extra `server` to `pyproject.toml`: `fastapi>=0.136`, `sse-starlette>=3.4`, `uvicorn[standard]`. (Pydantic v2 already present.)
  *Verify:* `.venv/bin/python -c "import fastapi, sse_starlette, uvicorn"`.
- **H1.2 — Event models.** `voss/harness/server/events.py`: pydantic v2 discriminated union (`Field(discriminator="type")`) mirroring the 13 `JsonRenderer` shapes (§A2) + Voss part types. Each model has `type: Literal[...]`.
  *Verify:* `model_json_schema()` emits; sample payloads round-trip; discriminator resolves.
- **H1.3 — `EventBusRenderer`.** `voss/harness/server/renderer.py`: implements all 13 `Renderer` methods (§A0); each builds the matching event model and `queue.put_nowait(...)` (bounded queue, drop-policy decided in H1.8). Must pass `isinstance(obj, Renderer)` (runtime_checkable).
  *Verify:* unit test — each method enqueues exactly the right event; `isinstance` True.
- **H1.4 — Session manager.** `voss/harness/server/sessions.py`: per-session struct `{queue: asyncio.Queue(256), task, history, gate, provider, cwd, tools}`. Session id = `uuid.uuid4().hex[:12]` (match `session.py:171`). Single subscriber per session (TUI).
  *Verify:* create/get/list/delete unit-tested.
- **H1.5 — App + auth + lifespan.** `voss/harness/server/app.py`: FastAPI app; `BearerAuth` middleware using `secrets.compare_digest` (reject at middleware); lifespan that cancels all in-flight `Session.task` on shutdown.
  *Verify:* 401 without/with-wrong token; 200 with token.
- **H1.6 — Session REST.** `POST /session` (`{parentID?,title?}`→`{id}`), `GET /session`, `GET /session/:id`, `DELETE /session/:id`. Paths mirror OpenCode (§A1).
  *Verify:* curl create→list→get→delete roundtrip.
- **H1.7 — Message handler.** `POST /session/:id/message` → 202; `asyncio.create_task` around `run_turn(...)` (§A0 signature). Per-session build-once: `provider` via `_resolve_auth_or_die(pref)` (`cli.py:401`), `tools: dict[str,ToolEntry]`, `EpisodicMemory(capacity=40)`, `PermissionGate(mode=...)`, `EventBusRenderer`. Reject with 409 if a turn is already running.
  *Verify:* returns 202; task starts; second concurrent message → 409.
- **H1.8 — SSE endpoint.** `GET /session/:id/events`: `EventSourceResponse(gen(), ping=15, send_timeout=30)`; drain queue → `ServerSentEvent(event=ev.type, data=ev.model_dump_json(), id=seq)`; break after `session.idle`; on `CancelledError` (client disconnect) cancel the turn task then re-raise.
  *Verify:* `curl -N` shows `server.connected` first, then live `stream.delta`/`plan`/`tool`/`final`/`session.idle`.
- **H1.9 — Permission bridge (folds M3).** Inject `gate.prompt_fn`/`gate.scope_prompt_fn` (signatures `(.tool_name,args)->str`, `(target)->str`) that emit a `permission.updated` event with a request id and block on an `asyncio.Future` keyed by id. `POST /session/:id/permission {id,choice}` resolves it (`a|A|d`). Mirror `tui/permissions_bridge.py:51-100`. **Without this the gate denies every prompt server-side** (`permissions.py:300-301`).
  *Verify:* `fs_write` emits `permission.updated`; reply `a` proceeds; no reply + timeout → deny.
- **H1.10 — Abort.** `POST /session/:id/abort` → `loop.call_soon_threadsafe(task.cancel)`; `await task` swallowing `CancelledError`. Reuses the existing handler at `agent.py:1052` (emits `[interrupted]`, records `exit_reason="interrupt"`).
  *Verify:* abort mid-turn → interrupt event on SSE + `exit_reason=interrupt` in saved record.
- **H1.11 — `voss serve` + handshake.** New command: bind `socket(127.0.0.1, 0)` yourself, `print(json.dumps({"port","token"}), flush=True)`, then `uvicorn ... server.serve(sockets=[sock])` (race-free port discovery).
  *Verify:* prints one handshake line; server reachable on that port.
- **H1.12 — Parent-death watcher.** In lifespan, `asyncio.create_task(watch_parent(os.getppid()))` (poll every 2s; on change `os.kill(self, SIGTERM)`) + stdin-EOF fallback (macOS has no `PR_SET_PDEATHSIG`).
  *Verify:* kill the parent process → server exits within ~2s (no zombie).
- **H1.13 — Persist on completion.** On turn end, `session_store.save(record, history)` (`session.py:210`).
  *Verify:* `.voss/sessions/<id>.json` written; `session_store.load` rehydrates.
- **H1.14 — OpenAPI + SSE schema.** Confirm `/openapi.json` (3.1). Document the SSE union via `responses={200:{"content":{"text/event-stream":{"schema":{"$ref":"#/.../AgentEvent"}}}}}` + an `_EventEnvelope` model so codegen sees a tagged enum.
  *Verify:* `/openapi.json` contains the `AgentEvent` discriminated union.

**Exit:** curl drives a full turn against Claude OAuth with live streamed events; abort + permission round-trip work; session persists; `voss chat` (Textual, in-process) **unchanged**.

---

## PHASE H2 — Rust ratatui client MVP (~5 days)

Goal: `voss-tui` spawns the server and drives a real multi-turn session.

- **H2.1 — Scaffold.** `crates/voss-tui/` binary; `Cargo.toml` with pinned deps (§A4); add to workspace `Cargo.toml`. Module layout: `main.rs · app.rs · event.rs · net.rs · server.rs`.
  *Verify:* `cargo build -p voss-tui`.
- **H2.2 — Server supervision.** `server.rs`: `tokio::process::Command("voss serve")`, stdout piped; read handshake line with 10s timeout; spawn a background task to drain remaining stdout (pipe-buffer deadlock guard); `kill_on_drop(true)` + explicit `start_kill()`+`wait()` on exit.
  *Verify:* launches server, parses `{port,token}`, kills it on quit (no zombie).
- **H2.3 — HTTP client.** `net.rs` `HttpClient` (reqwest 0.13, `bearer_auth`): `post_message`, `abort`, `permission_reply`. Loopback `http://` (no TLS needed).
  *Verify:* `abort`/`permission_reply` hit server, 2xx.
- **H2.4 — Event types.** `event.rs`: `AppEvent` enum + serde DTOs + SSE-event-name→`AppEvent` map, mirroring PROTOCOL.md (§A2). Unknown event name → ignore.
  *Verify:* `serde_json::from_str` parses captured server payloads into each variant.
- **H2.5 — SSE consumer.** `net.rs` `stream_turn`: `resp.bytes_stream().eventsource()`, parse typed frames, push to `mpsc`, stop on `final`/`session.idle`, track `Last-Event-ID`, backoff-reconnect only on error (not clean close).
  *Verify:* receives streamed token deltas end-to-end.
- **H2.6 — App state + draw.** `app.rs`: `App{transcript, input: ratatui-textarea, status, pending_permission, should_quit}`; pure `draw()` (transcript pane / input box / status line). No I/O in draw.
  *Verify:* renders static state.
- **H2.7 — Main loop.** `main.rs`: `color_eyre::install()` → `ratatui::init()`; `tokio::select!` over crossterm `EventStream` / `net_rx` / 50ms tick; single `terminal.draw` per iteration; always `ratatui::restore()` on exit.
  *Verify:* live token stream renders; resizes cleanly.
- **H2.8 — Key handling.** Enter→`post_message`(+spawn `stream_turn`); Ctrl-C→`abort`; `y`/`n` when `pending_permission`→`permission_reply`; else `textarea.input(key)`.
  *Verify:* full multi-turn turn driven from TUI against Claude OAuth; Ctrl-C aborts; permission prompt round-trips.

**Exit:** `voss-tui` is a working thin client over the H1 server.

---

## PHASE H3 — Thin-client guarantees + doctor (~2–3 days)

Goal: enforce + test that no credentials/provider logic live in Rust.

- **H3.1 — `GET /doctor`.** Server endpoint wrapping `auth.resolve` + env/config checks; `voss-tui doctor` renders it.
  *Verify:* output matches `python -m voss doctor` line-for-line; no secret ever crosses to the Rust process except the loopback bearer token.
- **H3.2 — Client config.** Client carries only connection + display prefs; all model/provider/auth config resolved server-side.
  *Verify:* grep client crate for credential handling → none.
- **H3.3 — Contract/parity test (CI).** A test that deserializes a recorded sample of *every* server event type into the Rust `AppEvent` enum; fails on schema drift.
  *Verify:* CI job green; deliberately breaking a field fails it.

**Exit:** thin-client invariant enforced and regression-guarded.

---

## PHASE H4 — Sessions, resume (folds M2), slash (~3–4 days)

Goal: parity with the Textual session UX, and fix lossy resume properly server-side.

- **H4.1 — Client session ops.** `voss-tui sessions` / `resume <id>` via `GET /session*`.
  *Verify:* list + resume from the client.
- **H4.2 — Fix M2 (resume context), server-side.** (a) `resume_cmd`/server resume forwards **all** prior `runs` into `_compose_prior_context_block` (not just `runs[-1]`, `cli.py:2542`); (b) raise the in-turn history-injection window above `history.last(6)` (`agent.py:516-522`); (c) keep `prior_context` across N turns instead of clearing after the first (`cli.py:1823,1916`). This is durable agent/session logic that survives the refactor — not a render bandaid.
  *Verify:* regression test — a fact stated in turn 1 of a prior session is recalled after `resume`.
- **H4.3 — Server-side slash endpoints.** Expose existing `/diff /apply /discard /budget /why /cost` as REST/commands + events.
  *Verify:* `/diff` returns the pending diff; `/cost` returns honest cache-inclusive cost.
- **H4.4 — Client slash palette.** UI palette dispatching to server slashes + client-only commands (scroll/theme).
  *Verify:* palette invokes `/diff` and shows result.

**Exit:** a session saved by the Textual TUI resumes byte-equivalently in the Rust client; deep history is recalled.

---

## PHASE H5 — Permission model + agent modes (OpenCode patterns) (~3–4 days)

Goal: adopt OpenCode's proven permission + agent-config patterns (as patterns, not code), now that the seam exists.

- **H5.1 — Wildcard permission model (folds M3 fully).** Generalize `PermissionGate` to an `allow|ask|deny` map with wildcards and per-bash-command gating, **last-match-wins, `*` first** (§A5), sourced from `.voss/permissions.yml`. Replaces the binary plain-path prompt.
  *Verify:* `"bash":{"*":"ask","git status *":"allow","rm *":"deny"}` enforced exactly.
- **H5.2 — Voss gate dimensions.** Add `confidence` and `budget` gate keys with threshold patterns (e.g. `"confidence":{"*":"allow","<0.5":"ask"}`, `"budget":{">100%":"deny"}`); emit `gate.updated`. Extend the permission event with `dimension`.
  *Verify:* a low-confidence step triggers an ask; over-budget step denied.
- **H5.3 — Plan/build modes.** Tab-cycle in the client; maps to `PermissionGate.mode` (`plan|edit|auto`, `permissions.py:42`).
  *Verify:* plan mode denies all mutating tools.
- **H5.4 — Agent-markdown config.** `.voss/agents/*.md` with YAML frontmatter (`description, mode, model, temperature, permission, tools` + Voss `confidence_threshold`, `budget`) per §A6. Loader + `@mention`/auto invocation.
  *Verify:* a read-only `explore.md` subagent loads and runs without edit access.

**Exit:** wildcard gates, Voss gate dimensions, modes, and agent files all functional.

---

## PHASE H6 — Distribution (~2–3 days)

Goal: single-command install.

- **H6.1 — `cargo-dist`.** Signed `voss-tui` binaries (macOS arm64/x64, Linux x64/arm64) + Homebrew tap.
  *Verify:* tagged release produces per-arch artifacts.
- **H6.2 — Server bundling.** PyInstaller/PyOxidizer sidecar for the brew/curl path; vendored-Python provisioning for `pip install voss`.
  *Verify:* `brew install` → `voss-tui` runs a turn with no user-managed Python.
- **H6.3 — Dispatcher.** `voss.cli:main`: if `voss-tui` reachable, `exec` it for agent verbs; else in-process Python harness fallback (Textual). (Same spirit as RUST-PORT-PLAN §9.)
  *Verify:* both paths run a turn.

**Exit:** `brew install voss/tap/voss` → client → bundled server → working turn.

---

## PHASE H7 — Incremental server→Rust (optional, future)

With the protocol frozen, rewrite hot server endpoints in Rust behind the same contract, one at a time (agent loop → tools → providers/auth). Compiler + `voss_runtime` (Lark parser, analyzer, codegen, probable/budget/semantic) **stay Python forever** (RUST-PORT-PLAN §16). End-state = the original pure-Rust port, reached incrementally and reversibly.

---

## 1. Effort

| Phase | Scope | Days |
|---|---|---|
| H0 | Contract + doc cleanup | 1 |
| H1 | Python server core | 3–4 |
| H2 | Rust ratatui client MVP | 5 |
| H3 | Thin-client + doctor + parity CI | 2–3 |
| H4 | Sessions/resume(M2)/slash | 3–4 |
| H5 | Permission model + agent modes | 3–4 |
| H6 | Distribution | 2–3 |
| **Total to daily-driver Rust client** | H0–H6 | **~19–24 days** |
| H7 | Incremental server→Rust | optional |

---

## 2. Risks

| Risk | Mitigation |
|---|---|
| `reqwest-eventsource` ⨯ reqwest 0.13 | Use `eventsource-stream` over `bytes_stream()` (H2.5); own the reconnect |
| Server denies all writes (no TTY) | H1.9 injects `prompt_fn` before any turn runs; covered by test |
| `CancelledError` swallowed → leaked turn/abort broken | Catch-for-cleanup-then-`raise` everywhere; abort + disconnect both tested |
| `port=0` start/query race | Bind socket first, `serve(sockets=[sock])` (H1.11) |
| Parent-death zombie server (macOS) | `getppid()` poll + stdin-EOF (H1.12); explicit child kill+wait (H2.2) |
| Protocol drift client/server | OpenAPI source of truth + parity CI (H3.3) |
| Regressing the working Textual TUI | Server is additive; Textual stays default until Rust client at parity |
| Scope creep into full rewrite | H7 optional; compiler/runtime never ported |

---

## Appendix A — Implementation reference (research-verified 2026-06)

### A0. `Renderer` protocol + `run_turn` (server must satisfy/call)

`Renderer` Protocol — `render.py:27-58`, 13 methods (keyword-only where shown):
`banner(*,model,cwd,git_status)` · `show_user(task)` · `show_thinking(label)` · `show_plan(plan,*,cost_usd)` · `show_tool_call(name,args,summary,state)` [state ∈ `ok|error|pending`] · `show_clarify(question,confidence)` · `show_final(text,*,confidence,cost_usd)` · `stream_delta(text)` · `finalize_stream(*,role,confidence?,cost_usd?,timestamp?,accumulated_text?)` · `status(*,model,tokens,cost_usd,ctx_pct)` · `show_cognition(...)` · `show_cognition_overflow(...)` · `show_warning(msg)`. (`banner/show_user/show_final` are driven by the caller, not the turn — server emits `final` from `TurnResult`.)

```python
# agent.py:412
async def run_turn(task, *, tools, cwd, renderer, confidence_threshold=0.60,
    token_budget=60_000, model=None, provider=None, history=None, permissions=None,
    session_id=None, cognition=None, prior_context=None, voss_md_text=None,
    project_index_text="", steer_inbox=None) -> TurnResult
# TurnResult (agent.py:393): plan, confidence, final, tool_results, cost_usd, run
```
Auth entry: `_resolve_auth_or_die(pref) -> (Resolution, ModelProvider)` (`cli.py:401`). Abort: `task.cancel()` → handler at `agent.py:1052`. Permission injection point: `gate.prompt_fn`/`gate.scope_prompt_fn` (else non-interactive deny, `permissions.py:300-301`). Session: `session_store.save(record, history)` / `load(id)` (`session.py:210/235`), id=`uuid4().hex[:12]`.

### A1. Endpoints (mirror OpenCode)
`POST /session` · `GET /session` · `GET /session/:id` · `DELETE /session/:id` · `POST /session/:id/message` (202, async) · `GET /session/:id/events` (SSE) · `POST /session/:id/abort` · `POST /session/:id/permission` · `GET /doctor` · `GET /openapi.json`. Voss-add: `POST /session/:id/budget`, `GET /session/:id/confidence`.

### A2. SSE events
Envelope `event: <type>\ndata: <json>`. First event `server.connected`. Turn-done = `session.idle`. Core types from the 13 `JsonRenderer` shapes (`render.py:493-567`): `banner,user,thinking,plan,tool,clarify,final,stream.delta,stream.finalize,status,cognition_loaded,cognition_overflow,warning` + `permission.updated`. Voss-add: `probable`, `budget.updated`, `confidence.updated`, `gate.updated`.

### A3. Message + parts
`Message{id,sessionID,role,time,...}`; `parts: Part[]`. Part union: `text,reasoning,file,tool,step-start,step-finish`. `ToolState` discriminated on `status: pending|running|completed|error`. Voss-add part types: `probable{text,probability,alternatives?}`, `budget{spent,limit,remaining,unit}`, `confidence{score,basis?}`; extend `AssistantMessage` with `confidence?`, `budget?`.

### A4. Rust `Cargo.toml` (pinned)
```toml
clap = { version = "4.6", features = ["derive","env"] }
tokio = { version = "1.52", features = ["rt-multi-thread","macros","process","io-util","sync","time","signal"] }
futures-util = "0.3"
ratatui = "0.30"
crossterm = { version = "0.29", features = ["event-stream"] }
ratatui-textarea = "*"   # ratatui-org fork (targets 0.30); NOT rhysd/tui-textarea 0.7 (0.29)
reqwest = { version = "0.13", default-features = false, features = ["json","stream","rustls-tls"] }
eventsource-stream = "0.2"   # NOT reqwest-eventsource 0.6 (pins reqwest 0.12)
serde = { version = "1", features = ["derive"] }
serde_json = "1"
color-eyre = "0.6"
```

### A5. Permission rules (OpenCode pattern)
`allow|ask|deny`. Per-tool map `{"*":"ask","bash":"allow"}`. Per-bash object, **last-match-wins, `*` first**: `"bash":{"*":"ask","git *":"allow","rm *":"deny"}`. Wildcards `*`/`?`; paths expand `~`/`$HOME`. Tool keys: `read,edit,glob,grep,bash,task,skill,lsp,question,webfetch,websearch,external_directory`. Voss-add gate dims: `confidence`, `budget` (threshold patterns).

### A6. Agent frontmatter (`.voss/agents/*.md`)
`description`(req), `mode`(subagent|primary|all), `model`, `temperature`, `permission`(nested map per A5), `tools`. Voss-add: `confidence_threshold`, `budget:{limit,unit}`.

### A7. Server stack (pinned)
`fastapi>=0.136` · `sse-starlette>=3.4` (`EventSourceResponse(ping=15,send_timeout=30)`) · `uvicorn[standard]`. Bind socket before serve for race-free `port=0`. Bearer via `secrets.compare_digest` at middleware. Serialize events with pydantic v2 `model_dump_json()`. Don't swallow `CancelledError`. Bound the per-session `asyncio.Queue` for backpressure.

---

## Relationship to existing plans
- **Supersedes** `RUST-PORT-PLAN.md` R1–R9; retains its §16 (compiler stays Python) + §9 (fallback dispatcher).
- **Consumes** harness-audit M2/M3 as folded tasks (H4.2/H1.9/H5.1); discards render bandaids B1/M1.
- **Does not touch** the voss-app Tauri ADE (A-track); both could later share this server protocol.

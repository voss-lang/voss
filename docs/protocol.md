# Voss Harness Protocol — v1

**Status:** Product contract, wire version `v = 1`. This is the authoritative integration boundary between the Voss engine and any client, including the separate Voss ADE desktop application. A breaking change bumps `v` and ships a migration note here. The committed `contracts/openapi.json` and `contracts/events.schema.json` are the machine-checkable form; a drift test fails CI when the server and these snapshots disagree.

**Created:** 2026-06-02 (H0.1)
**History:** Contract LOCKED for H1–H6. Changes require a version bump (`v` field) + migration note.
**Consumers:** Python server (`voss serve`, H1) · Go client (`voss-tui`) · future web/VSCode/SDK clients.
**Source of truth for shapes:** existing `JsonRenderer` (`voss/harness/render.py:485-568`) + OpenCode `packages/sdk/js/src/gen/types.gen.ts` (mirrored where applicable). Voss diverges only by **adding** part/event/gate types — never overloading existing ones, so an unmodified OpenCode-style client degrades gracefully.

This document is the wire contract. The server emits exactly these shapes; the client deserializes exactly these shapes; a parity test (H3.3) fails CI on drift.

---

## 1. Transport & versioning

- **REST** (commands, request/response) + **SSE** (server→client event stream). Not WebSocket.
- Base URL: `http://127.0.0.1:<port>` (loopback only). No TLS on loopback.
- Every JSON body and every SSE `data` payload carries `"v": 1`. A breaking change increments `v` and ships a migration note here.
- Content types: REST = `application/json`; event stream = `text/event-stream`.
- OpenAPI 3.1 served at `GET /openapi.json` (FastAPI auto-gen). The SSE event union is documented via an `_EventEnvelope` schema component (see §6) so typed clients can codegen a tagged enum.

### Capability discovery (added 2026-10-11)

`GET /capabilities` is a bearer-authenticated, read-only discovery endpoint. It
does not resolve provider credentials, create a session or run a model. Example:

```json
{"v":1,"engine_version":"0.1.2","capabilities":["sessions.v1","tasks.replay.v1","swarms.v1","diagnostics.v1"]}
```

`v` identifies the discovery/protocol major version. `engine_version` is the
installed Python distribution version, for diagnostics; clients negotiate by
protocol and capability rather than a version-string guess. Capability names
include their semantic version. Unknown optional names/fields may be ignored;
missing capabilities must not enable the corresponding action. An unsupported
`v`, malformed response or legacy server returning 404 leaves execution
unavailable while local history stays readable.

- `sessions.v1`: existing session/message/event/permission/cost routes. This
  does not promise durable replay, safe worker recovery or enforced task scope.
- `tasks.replay.v1`: authoritative task snapshots, durable cursor replay and command acknowledgements described below.
- `tasks.graph.v1`: recorded dependency graphs, worker attempts and bounded read-only output.
- `tasks.review.v1`: acceptance evidence for an exact recorded task attempt and candidate.
- `swarms.v1`: existing swarm create/snapshot/run routes and events.
- `diagnostics.v1`: existing read-only `/doctor` route.
- `harness.availability.v1`: typed local OAuth metadata and preflight.
- `harness.oauth-only.v1`: managed execution accepts subscription OAuth only.
- `plans.preview.v1`: prepare an execution graph and explicitly accept its exact revision; advertised only in OAuth-only mode.

These describe protocol support, not OAuth health, provider availability or
permission to execute. No memory-file layout, API fallback or acceptance-matrix capability is advertised.

### Durable tasks (added 2026-10-17)

`tasks.replay.v1` adds a snapshot and ordered event envelopes without changing
the existing AgentEvent union. The snapshot carries `task_id`, `session_id`,
optional `swarm_id`/`swarm_task_id`, `run_id`, `attempt_id`, `phase`, `outcome`,
`pending_actions`, and `watermark`. A plain task ID equals its session ID. A swarm
coordinator's task ID equals the swarm ID; a native member's task ID equals its
swarm task ID. Run and attempt IDs are generated at acceptance. Each accepted
message is one run with one attempt; no automatic retry or continuation occurs.

Phases are `idle`, `active`, `waiting`, `candidate_ready`, `completed`, `failed`,
`cancelled`, and `interrupted`. Completion comes from the turn/runtime result,
not warning, final-text, or idle events. Candidate-ready means retained work for
review, not merged or accepted work. A permission/diff request includes its ID in
`pending_actions`; a clarification uses kind `clarify` and requires another turn.
Unknown phases must remain unavailable to clients rather than imply success.

`GET /session/:id/task-events?after=N` replays every envelope after N and stays
open across turns. Each SSE ID equals the envelope's `cursor` and its snapshot's
`watermark`. Each envelope contains `v`, `cursor`, `snapshot`, and the original
`event` object. State-only transitions use `event.type = "task.state"`. Unknown
event kinds can be retained without interpreting them as outcomes. Snapshots
and events commit in the same SQLite transaction before publication. Subscribers
have independent cursors; dropping a stream never cancels execution.

A snapshot followed by a stream after its watermark cannot miss newer events.
Clients needing transcript history replay after their last committed cursor,
not the newest snapshot watermark. No event retention/expiry is currently applied.
A negative/ahead cursor returns 409. Missing journals/tasks return 404. Clients
must resync on a cursor gap; a snapshot-only resync must visibly identify missing
history. Duplicate envelopes are harmless. Deleted/replaced journals must not
silently reset a client's cursor or relaunch work.

The journal lives at `.voss/task-journal.sqlite3` under the server launch directory.
An exclusive file lock permits one server owner per journal. Reopening that
journal marks unfinished work interrupted and clears pending actions; it does not
load provider credentials, adopt conversations or spawn workers. Terminal history
survives. Graceful cancellation waits for owned CLI processes to terminate and
retains their worktrees. Hard process death records interruption on next access,
but cannot guarantee that every external descendant has stopped. This contract
does not promise detached execution or arbitrary subprocess continuation.

`POST /session/:id/message` accepts optional `command_id`. Reusing that ID with
identical input returns the original `{v,status:"accepted",run_id,attempt_id}`,
even after completion/restart. Different input with that ID returns 409. A new
command while busy returns 409. The receipt and active snapshot commit before
launch; a crash between acceptance and launch leaves interrupted work, never an
automatic replacement worker. Callers omitting the ID retain legacy non-deduplicated
submission semantics. `/swarm/:id/run` is one accepted command per swarm; repeated
calls return its receipt rather than re-executing members. Slash commands retain
their existing semantics and are not covered by this deduplication contract.

`POST /session/:id/abort` returns `cancelled` only after the driver has stopped,
or `not_running` if no live driver exists. Permission and diff replies return
`ok` or `stale`, including stale replies to persisted tasks after restart. Clients
must preserve those acknowledgements; HTTP 200 alone is not evidence of acceptance.

### Managed OAuth execution (added 2026-10-17)

ADE launches its owned engine with `VOSS_SERVE_OAUTH_ONLY=1` and requires
`harness.oauth-only.v1`. Other server callers retain their existing auth modes
unless they opt into this policy. Availability discovery alone does not enable
OAuth-only execution.

`GET /harnesses` returns `{v,harnesses,selected_harness}`. Each row identifies
`harness`, `provider`, `model`, `cli_installed`, `available`, `code`, `message`,
`login_command`, `checked_at`, `check_scope:"local_metadata"`, `account_alias`
and `account_selection:false`. `POST /harness/preflight` accepts `harness`, an
optional `model`, and an optional `account_alias`. Named-account selection is
unavailable; no background credential switch occurs. These calls create no
sessions, worktrees, workers or model requests. Local metadata cannot establish
remote token validity. Missing, expired, unreadable, API-key-only and unsupported
logins return availability data, not transport/authentication exceptions. The
loopback bearer token is separate: invalid transport authentication still gets 401.

In OAuth-only mode, session/swarm creation returns either its existing created
identity or HTTP 200 `{v,status:"unavailable",availability}`. Every swarm role
must pass preflight before persistence. Extra CLI arguments, custom launchers,
unsupported harnesses and conversation adoption are unavailable. Model selection
cannot enable API authentication or change a live swarm's selection. The SDK
preserves these outcomes as data. There is no automatic harness substitution.

Explicit message submission rechecks the session's selected harness/model before
acceptance. An unavailable command has no receipt or worker and can be retried
explicitly with the same command ID after sign-in. An accepted command still
deduplicates normally. Swarm Start rechecks every role before its first accepted
run; subsequent requests return the accepted receipt without relaunching members.

Native provider calls bind OAuth credentials and revalidate before dispatch.
Auth rejection blocks further calls through that binding and records phase
`waiting`, outcome `authentication_required`, and an `authentication` pending
action containing sanitized availability. CLI failures preserve work and require
operator attention; a nonzero exit alone does not prove an auth failure. Rechecking
or signing in never resumes work. A live session can accept an explicit follow-up;
restarting an accepted swarm remains a recovery operation, not a message to its
coordinator.

Managed native Codex calls use the ChatGPT backend without API keys or global
refresh writes. Managed Claude calls pin the OAuth token. Child CLI invocations
remove conflicting billing environment variables; Codex receives an isolated,
temporary login file and Claude an isolated config directory. Ordinary user and
project Claude setting sources are disabled. All temporary login files are removed
after the owned process exits. This does not establish compatibility with every
installed CLI or administrator-managed policy; installed-version verification is
a separate release gate. No credential material is included in availability or
task events.

The adapter follows the documented [Claude credential precedence](https://code.claude.com/docs/en/authentication)
and [Codex login restrictions](https://learn.chatgpt.com/docs/auth). Those documents
explain why selecting a login method alone is insufficient: conflicting credentials
must be excluded from the invocation too.

### Execution preview (added 2026-10-18)

`POST /plans/preview` accepts a briefing: `source` (`kind`, `text`, optional
`reference` and `revision`), repository-root `cwd`, explicit `harness` and `model`,
`tier`, `scope` (`allow`/`deny` patterns), and optional context items with distinct
`id` and `text`. Source kinds are `objective`, `prd` and `issue`. References are
provenance supplied by the client; this route does not fetch files or GitHub.
ADE revalidates selected local/issue sources before preview and first Start.

Preview performs one OAuth-bound structured model call without tools. It reads
Git metadata and file metadata, creates no session or worker, and makes no project
edit or Git mutation. The model receives the submitted text/context, not an
automatically discovered repository context. `accepted_context` lists only those
submitted IDs sent to the planner. Responses use `{v,status,preview?,availability?,message?}`;
unavailable OAuth remains a normal `unavailable` response. Unsupported execution
guarantees return `unsupported`, and malformed or stale planning returns `invalid`
or `stale` without dispatch.

A prepared preview includes stable task IDs, `depends_on` edges, file write lists,
acceptance criteria, the normalized briefing, input/base/workspace revisions,
execution policy and a content-derived `revision`. The selected harness/model
applies to every node. Dependencies must form an acyclic graph; proposed files
must fit the submitted scope. The supported route is `native_sequential` in
Observe, Plan or Apply mode. CLI swarms and Autonomous mode are unsupported.

`POST /plans/:id/start` accepts `{revision,briefing}`. Before first acceptance it
checks the exact input, Git HEAD, workspace/policy metadata and selected OAuth
binding. The workspace fingerprint covers tracked and nonignored untracked paths,
plus known project policy files and the local permission store. It uses path,
size, mode and modification time; it is not a byte snapshot or a lock against
concurrent editors. Engine runtime state is excluded. Changes require a new
preview; Start never silently replans or substitutes a provider.

Acceptance atomically records the immutable graph and receipt with a run/attempt
in the task journal before dispatch. Repeating the same Start returns the same
`accepted` response (`session_id`, `run_id`, `attempt_id`, `preview`), even after
engine restart or source changes. Conflicting input returns `stale`.
`GET /plans/:id` returns the prepared preview or accepted receipt. Unaccepted
previews are in memory, limited to the latest 100 and lost on restart; missing
previews return `stale`. Accepted receipts persist without expiry.

The driver executes fixed task goals sequentially in dependency order. The native
agent chooses tool steps within each goal. Only native file tools are exposed;
writes must target the current node's approved files within scope, and existing
mode/permission checks still apply. MCP, shell, Git commands, network tools,
memory and code-recall services are unavailable on this route. Normal internal
session/journal persistence still occurs. Acceptance criteria are supplied to the
agent, not an independently verified acceptance matrix.

Task snapshots add `execution_plan` and `node_states` for replay and graph rendering.
Failure, clarification, cancellation or OAuth loss stops dependent dispatch.
Restart marks unfinished work interrupted; a repeated accepted Start retrieves
its receipt without executing it again. Model changes and legacy message retries
cannot alter an accepted graph. Continuing stopped work requires a new preview;
in-place recovery remains a separate capability.

## 2. Auth & handshake

- On `voss serve`: bind `127.0.0.1:0` (ephemeral port), then **print exactly one line** of JSON to stdout before serving:
  ```json
  {"v":1,"port":54123,"token":"<url-safe-32-byte>"}
  ```
  The client reads this line to discover the port + bearer token. (Bind-before-serve avoids the start-then-query race.)
- Every request (REST + the SSE GET) must carry `Authorization: Bearer <token>`. Rejected at middleware with `401` (constant-time compare). No token → never reaches route logic.
- The token is per-server-process, ephemeral, never persisted.

## 3. Lifecycle

- The SDK supervises the server child. Explicit shutdown closes stdin, waits up to ten seconds for cleanup, then kills/reaps a nonresponsive child. Drop still kills as a last resort.
- The server also self-terminates if its parent dies: `getppid()` poll (2s) + stdin-EOF fallback (macOS has no `PR_SET_PDEATHSIG`).
- Graceful shutdown closes SSE streams, cancels and awaits owned turns/swarm drivers, and records interruption. No farewell delivery is guaranteed; clients reconcile from the journal.

## 4. Endpoints

| Method | Path | Purpose | Returns |
|---|---|---|---|
| `POST` | `/session` | Create session. Body `{parentID?, title?}` | `{id}` |
| `GET` | `/session` | List sessions | `[SessionInfo]` |
| `GET` | `/session/:id` | Session detail | `SessionInfo` |
| `GET` | `/session/:id/history` | Active conversation in chronological order | `{v:1, turns:[{role,content}]}` |
| `POST` | `/session/:id/clear` | Drop active conversation memory; `409` while busy | `204` |
| `GET` | `/sessions/saved?cwd=...` | Saved session metadata, including `first_task` | `{v:1, sessions:[...]}` |
| `DELETE` | `/session/:id` | Delete session + data | `204` |
| `POST` | `/session/:id/message` | Enqueue a user turn (async) | `202 {status:"accepted"}` |
| `GET` | `/session/:id/events` | Legacy payload stream; independent subscribers | `text/event-stream` |
| `GET` | `/session/:id/task` | Durable task snapshot | `TaskSnapshot` |
| `GET` | `/session/:id/task-events?after=N` | Envelopes after a committed cursor | `text/event-stream` |
| `POST` | `/session/:id/abort` | Cancel the in-flight turn | `202` |
| `POST` | `/session/:id/permission` | Reply to a pending permission request | `200` |
| `POST` | `/session/:id/diff` | Reply to an edit proposal. Body `{id,decisions}` | `{v:1,status:"ok"\|"stale"}` |
| `GET` | `/commands` | Slash command catalog | `{v:1, commands:[{name,description}]}` |
| `POST` | `/session/:id/command` | Execute a listed command. Body `{name,args?:string[]}` | `{v:1, stdout, stderr, code?}` |
| `GET` | `/doctor` | Auth/config/tooling status | `DoctorReport` |
| `GET` | `/openapi.json` | OpenAPI 3.1 spec | spec |

**Voss-native (additive):** `POST /session/:id/budget` (set/inspect token-or-cost envelope) · `GET /session/:id/confidence` (turn confidence rollup). Paths mirror OpenCode for everything shared so existing SDK clients work unmodified.

**Concurrency:** one running turn per session. `POST /message` while a turn runs → `409`.

The command catalog exposes `/tools`, `/skills`, and `/agents`. Each
accepts no arguments and uses the session's workspace. They list metadata without
starting a model turn or changing conversation history. Unknown commands return
`400`; unsupported arguments return usage text in `stderr`. Clients render
`stdout` as system output and `stderr` as a warning. Catalog loading does not
connect MCP servers; `/tools` connects for discovery and closes those connections
after listing. Listed tools remain subject to permission checks when invoked.

`/symbol <name>` and `/refs <name>` add an optional `code` payload:
`{query, items:[{file,line,name,language,source,snippet}], truncated}`. Paths are
workspace-relative, lines are one-based, and snippets contain at most 240
characters. Results are limited to 50 matches. The same results remain in `stdout`
for clients without a results panel. Definitions use the index; references use
LSP with a regex fallback. Lookups create a missing index; `/refresh` rebuilds it
after source changes and returns file/symbol counts in `stdout`. These commands
run in a worker thread without blocking the server event loop or starting a model
turn. Index writes are limited to the rebuildable `.voss-cache/code` cache.

`/probable [session] [--decision N]`, `/btrace [session]`, and `/vdiff <file.voss>`
return an optional `inspection: {title, text}` payload for a read-only panel,
along with the same text in `stdout`. Decision and budget views use the latest
completed run of the current session, or a saved session resolved by ID prefix or
name in the same workspace. `--decision` selects a zero-based decision index.
Fresh sessions and runs without inspection data return a no-data message.
`/vdiff` uses the existing compiler preview, including cached harness output when
available, and rejects sources or cached artifacts outside the workspace.
Invalid arguments and lookup/compiler errors appear in `stderr` without a panel.
Inspection runs in a worker thread and does not change history, call the session's
provider, or write workspace files.

`/budget [<usd>]` shows or sets an advisory budget for the active server session;
`0` clears it. Values must be finite and non-negative. Setting or clearing while
a turn or model switch runs returns `409`. Spending includes model and judgment
costs, matching `GET /session/:id/cost`, which also returns nullable `budget_usd`.
Go `/cost` shows the budget and percentage used when set. This matches Textual's
advisory behavior: it does not stop turns or replace per-run budget enforcement.
The setting is not persisted and starts unbounded when a session is resumed.

`/why` returns the last completed agent plan's rationale, confidence, step reasons,
open question and final-when-done text in `stdout`. No completed plan returns
`no plan yet — run a turn first` in `stderr`. Ambient chat and failed/aborted turns
leave that plan unchanged. Resume starts without a last plan; saved run records
are not reconstructed into one. Neither command invokes a provider or writes files.

`/save-session [name]` snapshots the current conversation, model selection and costs
to the existing session store, optionally renaming it. `/save <note text>` writes
a note to the configured memory backend with session provenance; it does not rename
the conversation. `/forget <pattern> --yes` requires explicit confirmation and uses
the backend's existing forget behavior. Local memory supports locator patterns;
Laravel accepts only an exact `memory:<project>:<id>` locator. Results use `stdout`,
while usage and storage errors use `stderr`. These commands run without a model call.
They return `409` while the session is busy and block new turns, model changes,
history clearing and other session mutations until storage work completes.

Conversation and model/auth status questions use the `ambient` phase. Work intents use the tool-enabled `run` phase; prefix a request with `run ` to select that path explicitly. Swarm sessions always run their assigned tasks. Permission `mode` remains independent of phase. Status events report phase changes and return to `ambient` on completion, cancellation, or failure.

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
| `status` | `model, tokens, cost_usd, ctx_pct`, optional `phase: ambient \| run` | `:539` |
| `cognition_loaded` | `architecture_tokens, constraints_count, plans_loaded, decisions_loaded` | `:542` |
| `cognition_overflow` | `architecture_tokens, budget` | `:558` |
| `warning` | `message` | `:567` |
| `permission.updated` | `id, tool_name, args, dimension` | server-only (§7) |
| `diff.proposed` | `id, hunks:[{file,start,lines}]` | opt-in edit review (§7) |
| `diff.resolved` | `id` | close the matching edit review |
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

### Edit review

Clients that support edit review send `review_diffs: true` when creating or
resuming a session. The default is false for existing clients. After permission
checks, `fs_edit` and `fs_edit_many` emit `diff.proposed` and await a reply before
writing. Each hunk has a file path, a one-based start line, and removed
(`- `) and added (`+ `) lines. Batch hunks describe edits in order against the
working buffer produced by preceding hunks.

Reply to `/session/:id/diff` with the proposal `id` and one decision per hunk:
`"accept"`, `"reject"`, or `"skip"`. An empty list cancels. Rejecting or skipping
any hunk cancels the whole batch. An invalid decision or count returns `422`
and leaves the proposal pending; expired or already answered IDs return
`status: "stale"`. Proposals belong to their session.

The server emits `diff.resolved` on reply, timeout (300 seconds), or cancellation.
This closes the review; tool results report whether an edit was applied. Timeout,
turn abort, or stream disconnect cancels pending edits. A file changed during
review requires a new preview. Previews over 256 KiB of encoded event data are
denied with a warning rather than truncated.

## 8. Abort

`POST /session/:id/abort` → server `loop.call_soon_threadsafe(task.cancel)` on the turn task. Reuses the existing handler (`agent.py:1052`): emits `stream.delta("\n[interrupted]\n")` + `stream.finalize(role="system")` then `session.idle`, and records `exit_reason="interrupt"`. SSE client disconnect triggers the identical cancel.

## 9. Error model

- REST errors: standard HTTP status + `{v:1, detail}`.
- In-turn errors surface as a `warning` event and/or a `tool` event with `state:"error"`, then the turn completes with `final` carrying a `halted: ...` message (`TurnResult.final` conventions: `halted: max-iter`, `halted: budget`).
- `session.error` (OpenCode parity, reserved): `{sessionID, error}` for fatal session-level failures.

## 10. Session persistence

On turn completion the server calls `session_store.save(record, history)` → `<cwd>/.voss/sessions/<id>.json` (mode 0600). Session id = `uuid4().hex[:12]`. Resume rehydrates `SessionInfo` + `EpisodicMemory`; the M2 fix (H4.2) forwards **all** prior runs and widens the in-turn history window (was `history.last(6)` / `runs[-1]` only).

After opening a resumed session, clients can fetch `/session/:id/history` before
opening the event stream. The response contains only user, assistant, and system
messages; tool payloads and run metadata are excluded. `first_task` in saved-session
listings is the first user message, limited to 60 characters, or `(empty)`.

`/session/:id/clear` matches the CLI's `/clear`: it clears active episodic memory
and pending resume context. It leaves the visible transcript, run records, costs,
and saved file intact. The next completed turn saves the new conversation history.

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


### Recorded task graph (added 2026-10-18)

`tasks.graph.v1` adds optional `graph` data to task snapshots and their existing
replay envelopes. It does not add a scheduler or a worker launch route. A graph
contains its plan ID/revision, run ID, owner session, observation timestamp and
nodes. Nodes retain declared `depends_on` IDs, scope, criteria, state, unresolved
dependencies, recorded blockers and separate worker attempts. Preview node IDs
are unchanged when execution starts. Swarm revisions hash task definitions;
roles and tool order never establish dependencies.

Attempts carry their own ID, run/plan revision, role, harness/provider/model,
optional native session, branch/worktree/base/candidate references, review state,
timestamps and output cursor bounds. CLI dispatch allocates an attempt ID and
records its worktree references; native dispatch links the actual journal attempt.
Repeated roles and retries therefore remain distinct. Missing legacy linkage and
uncaptured CLI output remain unavailable. Candidate-ready means review pending,
not accepted criteria or an approved merge. A new candidate resets that review
state to pending. Structured review evidence remains a separate contract.

The owner journal records native worker permission/blocker changes in the same
transaction as the worker event. Crash recovery marks unfinished attempts
interrupted; it never restarts them. An unresolved dependency is descriptive:
legacy swarm dispatch policy is unchanged. Native preview execution continues to
use its existing sequential dependency order.

`GET /session/{owner}/graph-output?node_id=...&attempt_id=...&after=0` returns
`{v,status,message,events,next_cursor,has_more}`. Each output row contains its
journal cursor and raw event. The server follows only the explicitly linked
attempt, excludes later turns, and returns at most 200 rows. Unknown attempts,
uncaptured output, interrupted attempts without a recorded boundary, and missing
journal ranges return `unavailable`. This read does not create a session, invoke
a provider or attach a terminal. The existing task snapshot and SSE endpoints
remain the graph transport; clients need no second graph subscription.

Preview also records the selected provider and base branch. Branch changes at the
same HEAD invalidate an unaccepted preview through its workspace fingerprint.

### Recorded acceptance evidence (added 2026-10-18)

`GET /session/{owner}/review?node_id=...&attempt_id=...` returns a versioned
bundle with session/run/task/attempt and plan IDs, candidate/base SHAs, worktree,
current HEAD, cleanliness, evidence revision and one row per recorded criterion.
Each row separates task-wide test status, reviewer label/mode, evidence references
and unresolved issues. Test states are `passed`, `failed`, `skipped`, `not_run`,
`unavailable` and `stale`. A scope check or successful worker exit is not a test
result. Reviewer labels retain their recorded meaning; shadow assessments are
advisory. This endpoint does not run tests, assess requirements, start sessions or
write Git state.

CLI candidate review production adds exact swarm/task/attempt/candidate linkage
to its existing review artifact. The graph records the repository root for that
artifact. The reader follows that fixed path only, checks ownership, and bounds
the artifact to 1 MiB. It does not scan board sidecars or match titles/paths.
Existing board artifacts lack a managed-attempt mapping, so they remain
unavailable. Preview criteria can be displayed without implying verification or
a committed candidate. Existing review enablement and dispatch policies do not
change; disabled review creates no new assessment.

Bundle status distinguishes `available`, `partial`, `unavailable` and `stale`.
Missing/malformed/unlinked artifacts are partial; an absent candidate/base or
inaccessible worktree is unavailable. Changed HEAD, dirty files, changed plan or
criteria and evidence for another candidate are stale. The evidence revision
hashes the projected bundle and artifact bytes, excluding the read timestamp.
Repeated unchanged reads retain the revision; tests, reviewer receipts, blockers,
criteria and candidate/base changes invalidate it.

The engine reports its recorded base. ADE separately chooses an integration
branch and binds its current target SHA to operator approval. It revalidates the
bundle before queueing and before integration. A rebase that changes the candidate
stops before merge; new candidate evidence and approval are required. These reads
do not regenerate evidence or adopt a manual commit as an engine candidate.

# Phase V17: External Agent Coordination Surface - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

External CLI agents (Claude Code, Codex, OpenCode in voss-app panes, or any shell) gain coordination primitives as thin clients of existing Voss substrate: serverless `voss claims stake/check/release/extend/list` (pre-edit conflict guard, `check` exits 1), `voss bus send/inbox/wait` fronting the server REST/SSE plane (V15-gated wave), `advice` arrays in new-verb structured output, and `docs/agent-coordination.md` + V16 handoff. Zero new substrate: no file bus, no hooks engine, no UI, no A13 code changes.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked (VBUS-01..08).** See `V17-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V17-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** claims verbs (serverless, globs + URIs, TTL, exit-code contract 0/1/2); claims storage (V17-owned, concurrent-safe); `VOSS_AGENT_ID` (+ `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN`) env injection in spawn paths; `voss bus send/inbox/wait` + server endpoints (V15-gated); one additive `bus.message`-style event type + durable journal under `.voss/bus/`; `advice` arrays on new verbs; `docs/agent-coordination.md` + V16 handoff note.

**Out of scope (from SPEC.md):** file-JSONL bus substrate / byte cursors / fs-notify / hooks engine (rejected — SEED-001 reframe); A13 swarm retrofit; any cockpit/app UI; advice retrofit on existing surfaces; AGENTS.md template edits (V16 territory); delivery guarantees/acks; cross-machine sync; message-type schema enforcement; OS-level claim enforcement.

</spec_lock>

<decisions>
## Implementation Decisions

### Claims storage + atomicity
- **D-01:** SQLite via stdlib `sqlite3`, single file. Atomic check-and-stake via `BEGIN IMMEDIATE` transaction; WAL mode for concurrent CLI processes. No JSONL event log for claims — TTL ephemera don't warrant event sourcing.
- **D-02:** Location: **`.voss-cache/claims.sqlite`** — machine-local ephemeral state matching 30-min TTL semantics; never synced; loss on cache wipe = agents re-stake. This is a **recorded, justified deviation** from SPEC VBUS-02's "under `.voss/`" wording (decided in discussion; planner should treat `.voss-cache/` as the locked location and note the deviation in plan frontmatter, not re-open it).
- **D-03:** Claim granularity: one claim = `id + patterns[] + single expires_at`. `release <id>` or bare `release` (= all own claims); `extend <id>` refreshes the whole set.
- **D-04:** Same-agent self-overlap = idempotent refresh: re-staking patterns overlapping your own active claim is never a conflict; it merges/refreshes TTL. Agents in loops can stake blindly.

### Glob overlap semantics
- **D-05:** Conservative static pattern-vs-pattern analysis — no filesystem reads. Normalize each pattern to canonical base dir + glob tail (canonicalized from invoking CWD); conflict if one base contains the other AND the glob tails could intersect (treat `**` as match-all under its base). Deterministic, covers not-yet-created files. False positives accepted — advisory guard.
- **D-06:** URI overlap is segment-aware exact + prefix: prefix conflicts only at `/` boundaries (`card://12` vs `card://123` → no conflict; `card://12` vs `card://12/sub` → conflict).
- **D-07:** No conflict override (`--force` rejected). Conflict resolution = coordinate with the owner; the `advice` array on a conflicting `check`/`stake` points at `voss bus send "@<owner> ..."`. Agents wanting through scope their patterns tighter.

### Bus shape
- **D-08:** Flat project-wide message stream — no channels in V17. Routing/filtering via `@mentions` + labels only; DMs emulated by mention (or a `dm:` label) if needed. Channel/sorted-pair-DM design deferred until a consumer demands it.
- **D-09:** Dedicated `GET /bus/events` SSE broadcast stream (bearer-authed, same `_BearerASGI` middleware), decoupled from per-session queues. `voss bus wait` and (later) the cockpit subscribe to it. Do NOT inject bus messages into session event queues.
- **D-10:** Journal: `.voss/bus/messages.jsonl` — append-only, ULID message ids, **server is the sole writer** (no cross-process lock complexity); per-agent inbox read positions in `.voss/bus/cursors.json`, server-managed. Durable across restart per VBUS-05.

### Identity mechanics
- **D-11:** `VOSS_AGENT_ID` injected into **ALL panes at spawn** (in the pane's shell env before any agent runs) — not just managed launches. Adoption then binds the pre-existing id to a card; the retroactive-env-injection problem dissolves. Tier-C agents (primary claims consumers) covered by construction.
- **D-12:** ID value = readable slug minted at spawn: `<cli>-<n>` for agent launches (`claude-1`, `codex-2`), `pane-<n>` for plain shells. Mentionable (`@claude-1`), greppable in the journal. Registry maps slug ↔ paneId ↔ cardId (at adoption).
- **D-13:** Slug stability = best-effort: persisted in pane config so A6 session-restore re-injects the same slug; no hard guarantee (claims are 30-min TTL — drift is low-stakes).

### Claude's Discretion
- Claims sqlite schema details, prune timing, `list` output columns.
- Exact endpoint naming (`POST /bus/message` vs `/bus/send`), message size limits, wait reconnect/backoff behavior.
- Advice array string composition (must include a runnable `voss` command naming the conflicting owner per VBUS-06 acceptance).
- Pattern canonicalization edge cases (symlinks, outside-repo paths) — follow `sandbox.rs::validate_scope` precedent where applicable.
- `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN` injection timing relative to sidecar startup (server may start after pane) — planner/researcher resolve against V15's sidecar design; flagged as an open coupling point, not a decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract
- `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md` — Locked requirements (VBUS-01..08) — MUST read before planning
- `.planning/seeds/SEED-001-coordination-bus.md` — Reframe rationale + rejected designs (file bus, cursors, fs-notify, hooks engine); do not relitigate file-vs-server

### Protocol surface
- `.planning/PROTOCOL.md` — Wire contract; LOCKED for H1–H6, additive event changes require migration note (§6 event taxonomy)
- `contracts/events.schema.json` — Event union the new `bus.message` type joins; pre-existing types must stay byte-identical
- `voss/harness/server/events.py` (lines ~191–216) — Python source of truth for the event union (Pydantic discriminated on `type`, `v` version field)
- `voss/harness/server/app.py` — FastAPI route surface + `_BearerASGI` middleware + SSE pattern (`GET /session/{id}/events`); new `/bus/*` routes follow these patterns
- `voss/harness/server/serve.py` — `{v,port,token}` stdout handshake (discovery contract the env injection mirrors)

### Integration points
- `voss/harness/cli.py` — click verb registration (`register()` + `AGENT_COMMANDS`); claims/bus verbs register here; existing `--json` NDJSON pattern
- `crates/voss-app-core/src/sandbox.rs` (lines ~31–61) — `validate_scope` canonicalization/traversal precedent for pattern canonicalization (reuse logic conceptually; do NOT modify the file)
- `apps/voss-app/src/org/adopt.ts` + `apps/voss-app/src/pane/adoptionRegistry.ts` — adoption binding (paneId→cardId, tier C) the identity slug must map into
- `crates/voss-app-core/src/agent_registry.rs` — Rust-owned `agent-registry.sqlite` (READ-ONLY from Python if read at all; no second writer)

### Adjacent phases
- `.planning/ROADMAP.md` §Phase V15 — sidecar/always-on server that gates VBUS-04/05 waves
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` — swarm file coordination V17's bus eventually supersedes (code untouched in V17)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_BearerASGI` middleware (app.py): `/bus/*` endpoints get auth for free by registering on the same FastAPI app
- SSE pattern via `sse_starlette` `EventSourceResponse` (app.py:390–419): template for `GET /bus/events`
- `JsonRenderer` NDJSON output + `--json` flag plumbing (harness/cli.py, render.py): pattern for claims/bus `--json` output
- Pydantic event union + `AgentEventAdapter` (events.py): additive `bus.message` type slots in with a `Literal` discriminator
- `sandbox.rs::validate_scope`: canonicalization/traversal-rejection precedent for glob base-dir normalization (port the logic to Python; don't touch the Rust)

### Established Patterns
- Additive-only protocol changes with PROTOCOL.md migration notes (V13.x discipline)
- `.voss/` durable vs `.voss-cache/` rebuildable split — claims sqlite goes cache-side (D-02), bus journal durable-side (D-10)
- Exit-code contracts documented + tested (existing harness CLI conventions)
- serde/IPC camelCase for anything crossing to the frontend (V14 `AgentEntry` lesson — latent until data exists)
- Atomic write-temp-then-rename for mutable JSON files (A13 manifest precedent → cursors.json)

### Integration Points
- `voss/harness/cli.py` `register()` — new `claims` + `bus` click groups
- `voss/harness/server/app.py` — `POST /bus/...`, `GET /bus/inbox`, `GET /bus/events` routes (VBUS-04 wave, V15-gated)
- Pane spawn path (Tauri `spawn_command_session*` / frontend spawn config) — `VOSS_AGENT_ID` env injection for ALL panes (D-11); slug minting + persistence in pane config (D-13)
- `docs/` — `agent-coordination.md`; V16 phase dir — handoff note

</code_context>

<specifics>
## Specific Ideas

- Advice on conflict must name the owner and be directly runnable: e.g. `voss bus send "@claude-1 I need src/api/** — when are you done?"` (VBUS-06 acceptance hinges on this).
- Brain-dump source patterns worth mirroring in shape (not substrate): ULID message ids, label vocabulary `coord:blocker`/`coord:handoff`/`mission:<id>`/`review-request`.

</specifics>

<deferred>
## Deferred Ideas

- Named channels + sorted-pair `_dm_` naming (D-08) — defer until a consumer demands them; labels emulate.
- A13 swarm rewiring onto bus wait — at A13 resume.
- Cockpit claims panel / bus feed rendering — later phase; events union makes it free to add.
- `--force` contested stakes (D-07) — rejected for V17; revisit only with evidence advisory-block is too blunt.
- File-substrate claims/bus for no-server headless contexts — reopens only on real constraint (SEED-001).

</deferred>

---

*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Context gathered: 2026-06-09*

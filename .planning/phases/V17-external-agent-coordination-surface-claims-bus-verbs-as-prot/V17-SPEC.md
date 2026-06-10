# Phase V17: External Agent Coordination Surface — Specification

**Created:** 2026-06-09
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 8 locked (VBUS-01..08)

## Goal

External CLI agents (Claude Code, Codex, OpenCode in voss-app panes, or any shell) gain coordination primitives as thin clients of what Voss already has: `voss claims stake/check/release/extend/list` works serverless as a pre-edit conflict guard (`check` exits 1 on overlap), `voss bus send/inbox/wait` fronts the existing REST/SSE plane for mid-flight messaging (gated on V15), and structured output gains `advice` next-command hints — with zero new substrate (no file bus, no hooks engine, no UI).

## Background

Voss's org layer (V4 session tree / V5 board / V7 EM) coordinates Voss-native agents in-process. VCKP-13 enforcement tiers give managed agents (A/B) OS-level scope sandboxing via `sandbox.rs`. But tier-C adopted/unmanaged external agents have **zero coordination**: `adopt.ts` records an advisory budget+scope that nothing checks (`apps/voss-app/src/org/adopt.ts:21-35`, in-memory only via `adoptionRegistry.ts`); A13 swarm (1/5 plans executed) is one-shot task-file in / result-file out with PTY-idle completion heuristics; no mid-flight agent↔agent messaging exists.

The server plane exists today: FastAPI at `voss/harness/server/app.py` (bearer-token loopback, SSE at `GET /session/{id}/events`), a 21-member Pydantic-discriminated event union at `voss/harness/server/events.py:191-216` (additive changes allowed; PROTOCOL.md requires a migration note), and click-based CLI verbs registered via `voss/harness/cli.py` `register()` with an existing `--json` NDJSON mode. No discovery mechanism exists for a CLI invoked inside a pane to find the running server (port/token are printed once to the spawning parent's stdout).

Reframe decision (recorded in `.planning/seeds/SEED-001-coordination-bus.md`): the source brain-dump's file-JSONL substrate, byte cursors, fs-notify wait, and hooks engine are **rejected** — they are server-replacement infrastructure and Voss has the server. Do not relitigate file-vs-server in discuss/plan.

## Requirements

1. **VBUS-01 — Claims CLI verbs**: `voss claims stake|check|release|extend|list` exist as click commands; `check` is a shell-scriptable pre-edit guard.
   - Current: No claims verbs exist. `adopt.ts` advisory scope is recorded but never checkable from a shell.
   - Target: `voss claims stake <pattern>...` registers a claim (file globs and/or URIs); `voss claims check <pattern>...` exits 0 when no overlap with another agent's active claim, exits 1 on conflict printing the conflicting claim + owner; `release` frees own claims; `extend` refreshes TTL; `list` shows active claims. Stake on a conflicting pattern is atomically rejected (exit 1) — no double-grant under concurrent stakes.
   - Acceptance: Two distinct agent identities: A stakes `src/api/**`; B `check src/api/handlers.py` → exit 1 naming A; B `check src/other/**` → exit 0; B `stake src/api/**` → exit 1; after A `release`, B's stake succeeds. Concurrent stake test grants exactly one winner.

2. **VBUS-02 — Serverless claims storage + mandatory TTL**: claims work with no `voss serve` running, persist under `.voss/`, and always expire.
   - Current: No claims storage. `agent-registry.sqlite` is Rust/Tauri-owned (`crates/voss-app-core/src/agent_registry.rs:91-108`) — not shared with the Python CLI.
   - Target: Claims persist in V17-owned storage under `.voss/` (mechanism = discuss-phase; NOT the Rust-owned `agent-registry.sqlite`, no second writer). Every claim has `expires_at` (default TTL 30 min, `--ttl` override); expired claims are ignored by `check`/`stake` and pruned from `list` (shown only with `--all`). Safe under concurrent multi-process access. Claim patterns: file globs (canonicalized from cwd; overlap via glob matching) and opaque URIs (`card://<id>`, `port://<n>`; overlap via exact + path-prefix match).
   - Acceptance: With no server process running, the full VBUS-01 acceptance sequence passes. A claim staked with `--ttl 1s` no longer blocks `check` after expiry. `card://123` vs `card://123` conflicts; `card://123` vs `card://124` does not; `bead://p/x` vs `bead://p` prefix-conflicts.

3. **VBUS-03 — Agent identity injection**: managed-launch and adopt flows inject `VOSS_AGENT_ID` into the agent's environment; claims/bus verbs read it.
   - Current: No identity reaches the agent's process. Panes have `paneId`, adopted agents get `cardId`, but nothing is injected into env (`spawn_managed_agent`, `adopt.ts`).
   - Target: `spawn_managed_agent` (and the adopt flow, for its pane where applicable) injects `VOSS_AGENT_ID` (stable per pane/card binding) and, when a server is attached, `VOSS_SERVER_PORT` + `VOSS_SERVER_TOKEN`. `voss claims`/`voss bus` resolve identity from `VOSS_AGENT_ID`; when absent, exit 2 with an actionable stderr message (how to set it).
   - Acceptance: A managed-launched pane's child process env contains `VOSS_AGENT_ID`; `voss claims stake` inside it records that id as owner; running `voss claims stake` in a bare shell without the var exits 2 with the documented message.

4. **VBUS-04 — Bus verbs as protocol-plane clients** *(gated on V15 — plans for this requirement execute only after V15 ships)*: `voss bus send|inbox|wait` are thin REST/SSE clients of the running server.
   - Current: No messaging verbs; no way for one pane agent to signal another except writing arbitrary files.
   - Target: `send` POSTs a message (body, optional `@mentions`, optional labels) to a new server endpoint; `inbox` returns messages addressed to / mentioning the caller since its last read; `wait` blocks on the SSE stream until a message matches a filter (`--mention <me>`, `--label <l>`, `--timeout <s>`; timeout → exit 124-style nonzero). Verbs discover the server via `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN`; absent/unreachable → exit 2 with actionable stderr.
   - Acceptance: Agent A `bus wait --mention A --timeout 60` blocks; agent B `bus send "@A done" --label task-done`; A unblocks within 2s printing the message, exit 0. `wait` with no matching message exits nonzero at timeout. `inbox` after two sends returns both, then returns neither on a second call (cursor advanced).

5. **VBUS-05 — Message event type + durable journal**: bus messages join the existing event union additively and survive server restart.
   - Current: 21-member union in `events.py`; no message/coordination event; session event queues are in-memory only.
   - Target: One new additive event type (discriminator `type`, e.g. `bus.message`, `v` field per PROTOCOL) added to the union, emitted on the SSE plane on send; `contracts/events.schema.json` regenerates to include it; PROTOCOL.md §6 gains the type + migration note. Messages append to a durable journal under `.voss/bus/`; per-agent inbox read position survives restart; after server restart, `inbox` still returns unread-before-restart messages.
   - Acceptance: SSE subscriber receives the new event on `bus send`; `contracts/events.schema.json` contains the new type; all existing event types byte-identical in the schema (additive-only proof); kill + restart server → `inbox` returns the pre-restart unread message.

6. **VBUS-06 — Advice arrays on new verbs**: structured output of claims/bus verbs includes machine-readable suggested next commands.
   - Current: No CLI surface emits suggested-next-commands.
   - Target: `--json` output of the new verbs includes `advice: [<string>...]` (e.g. `check` conflict → advise `voss bus send "@<owner> ..."` and `voss claims check` retry; `wait` timeout → advise inbox). Existing surfaces (`voss board`, `voss jobs`) untouched.
   - Acceptance: `voss claims check --json` on a conflict emits an `advice` array containing at least one runnable `voss` command referencing the conflicting owner; `git diff` shows no changes to board/jobs output code paths.

7. **VBUS-07 — Conventions doc + V16 handoff**: the coordination vocabulary and verb usage are documented for agent consumption, with a handoff to V16's managed AGENTS.md section.
   - Current: No coordination conventions documented anywhere; V16 (managed docs) unexecuted.
   - Target: `docs/agent-coordination.md` documents the verbs, exit codes, env vars, label vocabulary (`coord:blocker`, `coord:handoff`, `mission:<id>`, `review-request`), and a pre-edit guard example (`voss claims check <files> || ...`); a note in V16's phase dir instructs folding a condensed version into the managed AGENTS.md section template.
   - Acceptance: `docs/agent-coordination.md` exists covering all shipped verbs + exit codes + `VOSS_AGENT_ID`; every documented command parses (`--help` exits 0); V16 phase dir contains the handoff note referencing the doc.

8. **VBUS-08 — Coherence guard**: V17 adds no parallel substrate and touches no adjacent phase code.
   - Current: Rejected designs recorded in SEED-001.
   - Target: The V17 diff contains no file-JSONL message bus, no per-agent byte-cursor files, no fs-notify wait implementation, no standalone hook router, no new UI panels/components, and no modifications to A13 swarm code (`apps/voss-app/src/swarm/`), `sandbox.rs` behavior (logic may be reused/imported, not changed), or frozen schemas.
   - Acceptance: Diff inspection — `apps/voss-app/src/swarm/` byte-unchanged; no new Solid components; existing `sandbox.rs` tests pass unmodified; no fs-watcher dependency added to the harness.

## Boundaries

**In scope:**
- `voss claims stake/check/release/extend/list` (serverless, globs + URIs, TTL, exit-code contract)
- Claims storage under `.voss/` (V17-owned, concurrent-safe)
- `VOSS_AGENT_ID` (+ `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN`) env injection in managed-launch/adopt spawn paths
- `voss bus send/inbox/wait` REST/SSE client verbs + server endpoints (V15-gated wave)
- One additive `bus.message`-style event type + durable message journal under `.voss/bus/`
- `advice` arrays in the new verbs' `--json` output
- `docs/agent-coordination.md` + V16 handoff note

**Out of scope:**
- File-JSONL bus substrate, byte cursors, fs-notify wait, hooks engine — rejected server-replacement infra (SEED-001 reframe); reopens only if no-server headless coordination becomes a real constraint
- A13 swarm retrofit — substrate only; rewiring SWM-04/05/06 happens when A13 resumes
- Any cockpit/app UI (claims panel, bus feed) — events enter the union; rendering is a later phase's choice
- Advice retrofit on existing surfaces (`board`, `jobs`) — surgical scope
- Editing AGENTS.md templates directly — V16's design territory (handoff note instead)
- Delivery guarantees/acks/dead-letter, cross-machine sync, message-type schema enforcement — accepted gaps per seed
- OS-level claim enforcement — claims are advisory by design; tiers A/B remain the enforcement story

## Constraints

- **Protocol discipline:** event union changes must be additive; existing event types byte-identical in `contracts/events.schema.json`; PROTOCOL.md migration note required (PROTOCOL is LOCKED for H1–H6).
- **No second writer on `agent-registry.sqlite`:** claims storage is V17-owned; the Rust-owned registry is read-only from Python, if read at all.
- **Frozen surfaces:** `crates/` frozen-spike untouched; `sandbox.rs` logic reusable but not modified; A13 `apps/voss-app/src/swarm/` untouched.
- **No new heavyweight dependencies** in the harness (stdlib/sqlite3-level acceptable; no fs-watcher, no message-broker libs).
- **Claims must be concurrent-safe** across multiple simultaneous CLI processes (atomic stake — exactly one winner).
- **Exit-code contract:** 0 = clear/success, 1 = conflict, 2 = usage/identity/discovery error; stable across verbs (documented in VBUS-07 doc).
- **Wave gating:** VBUS-04/05 plans execute only after V15 ships the sidecar/always-on server; VBUS-01/02/03/06/07 have no upstream gate.

## Acceptance Criteria

- [ ] Full two-agent claims sequence (stake/check-conflict-exit-1/check-clear-exit-0/reject-conflicting-stake/release-then-stake) passes with no server running
- [ ] Concurrent stake race grants exactly one winner
- [ ] `--ttl 1s` claim stops blocking after expiry; default TTL applied when flag absent
- [ ] URI overlap: exact match conflicts, sibling ids don't, path-prefix conflicts
- [ ] Managed-launched pane env contains `VOSS_AGENT_ID`; bare-shell invocation without it exits 2 with actionable stderr
- [ ] `bus wait --mention` unblocks within 2s of a matching `bus send`; timeout exits nonzero
- [ ] `inbox` cursor semantics: returns unread once, empty on repeat call
- [ ] New event type in `contracts/events.schema.json`; all pre-existing event types byte-identical; PROTOCOL.md migration note present
- [ ] Server kill/restart: pre-restart unread message still returned by `inbox`
- [ ] `claims check --json` conflict output contains non-empty `advice` array with a runnable `voss` command
- [ ] `docs/agent-coordination.md` covers all verbs + exit codes + env vars; V16 handoff note exists
- [ ] Coherence guard: `apps/voss-app/src/swarm/` byte-unchanged, no new UI components, `sandbox.rs` tests pass unmodified, no fs-watcher dep added

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                              |
|--------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | 4 slices locked, server-backed reframe pre-decided |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | A13/UI/V16 perimeter locked in round 3             |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Storage ownership, TTL, protocol discipline locked |
| Acceptance Criteria| 0.72  | 0.70 | ✓      | 12 pass/fail criteria                              |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      |                                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective     | Question summary                                  | Decision locked                                                                 |
|-------|-----------------|---------------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher      | Slice 2 in V17 or split?                          | All 4 slices in V17; bus plans wave-gate on V15                                 |
| 1     | Researcher      | Claims serverless or server-backed?               | Serverless — own `.voss/` storage, no server required, no second sqlite writer |
| 1     | Researcher      | Claimant identity source?                         | Env-injected `VOSS_AGENT_ID` (+ port/token); injection changes in scope        |
| 2     | Simplifier      | Claim pattern types v1?                           | File globs + URIs (`card://` board-ontology payoff)                            |
| 2     | Simplifier      | Stale-claim story?                                | TTL mandatory w/ default (30 min) + `extend`; expired ignored                  |
| 2     | Simplifier      | Advice array surfaces?                            | New verbs only; board/jobs untouched                                           |
| 3     | Boundary Keeper | A13 retrofit in V17?                              | Substrate only — swarm code untouched, retrofit at A13 resume                  |
| 3     | Boundary Keeper | Any UI in V17?                                    | CLI + events only; cockpit renders later via the union                          |
| 3     | Boundary Keeper | Conventions delivery vs unexecuted V16?           | `docs/agent-coordination.md` + V16 handoff note; no template edits             |
| Gate  | —               | Message durability residue                        | Durable journal under `.voss/bus/`; inbox cursor survives restart              |

---

*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Spec created: 2026-06-09*
*Next step: /gsd-discuss-phase V17 — implementation decisions (storage mechanism, overlap algorithm, endpoint shapes)*

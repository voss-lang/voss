# Phase V17: External Agent Coordination Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
**Areas discussed:** Claims storage + atomicity, Glob overlap semantics, Bus shape, Identity mechanics

---

## Claims storage + atomicity

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite | stdlib sqlite3, BEGIN IMMEDIATE atomic stake, WAL for concurrent CLIs | ✓ |
| JSONL event log + file lock | Append-only + fcntl lock, replay-derived state, git-friendly | |
| JSONL journal + SQLite index | Event log source of truth + rebuildable index | |

**User's choice:** SQLite

| Option | Description | Selected |
|--------|-------------|----------|
| .voss-cache/claims.sqlite | Machine-local ephemera matching 30-min TTL; recorded deviation from SPEC "under .voss/" | ✓ |
| .voss/claims.sqlite | Literal SPEC compliance; needs gitignore entry | |

**User's choice:** .voss-cache/claims.sqlite
**Notes:** Recorded as justified deviation from VBUS-02 wording.

| Option | Description | Selected |
|--------|-------------|----------|
| Claim = id + patterns[] | Single expires_at per claim set; release/extend by id | ✓ |
| Row per pattern | Partial release possible, fiddlier CLI | |

**User's choice:** Claim = id + patterns[]

| Option | Description | Selected |
|--------|-------------|----------|
| Idempotent refresh | Own-overlap never conflicts; re-stake merges/refreshes TTL | ✓ |
| Error — explicit extend only | Own-overlap exits 1; stricter | |

**User's choice:** Idempotent refresh

---

## Glob overlap semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative static | Base-dir + glob-tail analysis, no fs reads, covers future files, false positives accepted | ✓ |
| Disk expansion at check time | File-set intersection against working tree; precise but misses future files, nondeterministic | |
| Hybrid | Static for dir claims, expansion for file paths; two code paths | |

**User's choice:** Conservative static

| Option | Description | Selected |
|--------|-------------|----------|
| Segment-aware prefix | URI prefix conflicts only at / boundaries | ✓ |
| Raw string prefix | card://12 vs card://123 would conflict — wrong for ids | |

**User's choice:** Segment-aware

| Option | Description | Selected |
|--------|-------------|----------|
| No override | Conflict = talk to owner (advice points at bus send) | ✓ |
| --force on stake | Contested stakes recorded; undermines guard | |

**User's choice:** No override

---

## Bus shape

| Option | Description | Selected |
|--------|-------------|----------|
| Flat stream | Project-wide stream, @mentions + labels routing; channels deferred | ✓ |
| Channels now | Named channels + sorted-pair DM naming | |

**User's choice:** Flat stream

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated GET /bus/events | Bearer-authed broadcast SSE, decoupled from session lifecycle | ✓ |
| Piggyback session streams | Inject into per-session queues; couples + duplicates | |

**User's choice:** Dedicated GET /bus/events

| Option | Description | Selected |
|--------|-------------|----------|
| JSONL append + cursors.json | messages.jsonl (ULID, server sole writer) + server-managed cursors | ✓ |
| SQLite | Same engine as claims; less greppable | |

**User's choice:** JSONL append + cursors.json

---

## Identity mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| ALL panes at spawn | Every pane shell gets VOSS_AGENT_ID at birth; adoption binds existing id | ✓ |
| Managed launches only | Adopted/unmanaged identity-less — guts tier-C story | |

**User's choice:** ALL panes at spawn

| Option | Description | Selected |
|--------|-------------|----------|
| Readable slug | cli+counter (claude-1, codex-2, pane-3); mentionable, greppable | ✓ |
| paneId verbatim | UUIDs hostile as mention targets | |
| cardId when adopted, else paneId | Identity changes mid-life — orphans pre-adopt claims | |

**User's choice:** Readable slug

| Option | Description | Selected |
|--------|-------------|----------|
| Best-effort stable | Slug persisted in pane config; restore re-injects; no hard guarantee | ✓ |
| Fresh each spawn | New identity per restore; old claims expire naturally | |

**User's choice:** Best-effort stable

---

## Claude's Discretion

- Claims sqlite schema details, prune timing, `list` output columns
- Endpoint naming, message size limits, wait reconnect/backoff
- Advice string composition (must include runnable command naming conflicting owner)
- Pattern canonicalization edge cases (symlink/outside-repo) — follow sandbox.rs precedent
- VOSS_SERVER_PORT/TOKEN injection timing vs sidecar startup — resolve against V15 design

## Deferred Ideas

- Named channels + `_dm_` sorted-pair naming — until a consumer demands
- A13 swarm rewiring onto bus wait — at A13 resume
- Cockpit claims/bus rendering — later phase
- `--force` contested stakes — rejected; revisit on evidence
- File-substrate claims/bus for no-server headless — reopens only on real constraint

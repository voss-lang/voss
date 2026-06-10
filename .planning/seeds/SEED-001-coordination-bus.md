---
id: SEED-001
status: dormant
planted: 2026-06-09
planted_during: v0.1.1 — post-V14 (frontier: V15 live plane / V16 managed docs / A4 presets)
trigger_when: A13 swarm resumes, Agents-launcher phase (999.1) activates, or any phase needs heterogeneous external-agent coordination (Claude/Codex panes talking to each other or to Voss)
scope: large
---

# SEED-001: Voss Coordination Bus — file-based messaging + advisory claims for heterogeneous external agents

Per-project append-only JSONL message bus + advisory resource claims + per-agent read cursors + wait/hook primitives, as the coordination substrate for external CLI agents (Claude Code, Codex, OpenCode in voss-app panes) that cannot speak the Voss SSE plane. Mirrored into the existing protocol plane as SSE events so the ADE cockpit renders coordination live.

## Source

Distilled from an external brain dump (2026-06-09) analyzing a multi-agent coordination primitive built on four reusable patterns. Full dump archived in conversation; the four primitives:

1. **Event log** — append-only JSONL messages with ULID ids, channels, `@mentions`, freeform labels. File-locked appends; multiple processes write safely. Git/union-merge friendly (ULID = no id coordination, append-only = no content conflicts).
2. **Advisory claims** — event-sourced resource reservations over file globs AND opaque URIs (`card://`, `port://`, `db://`). Overlap detection, atomic check-and-append, TTL expiry/refresh/release. `claims check` exits 1 on conflict → shell-scriptable pre-edit guard.
3. **Per-agent cursors** — byte offsets into channel JSONL per agent = `inbox` (unread since cursor) without any server. `wait` blocks on fs-notify until mention/label/channel match → conversational turn-taking without polling or Redis.
4. **Conditional hooks** — message arrives → condition (`claim_available {pattern}` / `mention_received {agent}`) → spawn subprocess, optionally atomically acquiring the claim on fire. Cooldown, priority, require-flag (`!dev` inline flags), audit trail of firings.

Supporting patterns worth copying: label-based coordination vocabulary as convention not schema (`coord:blocker`, `coord:handoff`, `mission:<id>`, `review-request`); `advice` arrays in structured CLI output (suggested next commands for agent loops); DM channels as sorted-pair naming (`_dm_a_b`) — deterministic without a registry; separate syncable event logs from gitignored machine-local cursor state; content-addressed attachment cache.

## Why This Matters

Voss has three coordination surfaces and a gap between them:

- **Voss-native org (V4/V5/V7/V8)** — in-process `SessionTreeManager` + board + EM loop. Rich, enforced (budget cages, OS sandbox, gates). Does NOT cover non-Voss agents.
- **A13 swarm (specced, 1/5 plans executed)** — file-mediated external-agent coordination, but crude: one-shot `.voss/swarm/tasks/*.md` in → `results/*.md` out; no mid-flight messaging; completion detection = result-file-exists + PTY-idle heuristic.
- **V15 live plane** — REST+SSE for the app/SDKs. External CLI agents in panes can't consume it.

External CLI agents' lowest common denominator is **run a command / read a file**. A file bus with CLI verbs (`voss bus send/inbox/wait`, `voss claims stake/check/release`) is the only substrate every pane-agent can use. Specifically:

- **Claims = the missing tier-C coordination layer.** VCKP-13 enforcement tiers: tier A/B managed agents get OS-level scope sandbox; tier-C adopted/unmanaged agents get nothing. Advisory claims + `check` exit-1 give tier-C agents a voluntary pre-edit guard — complements the cage model rather than competing with it.
- **`wait` + cursors replace A13's PTY-idle heuristic** with deterministic fan-in, and unlock mid-swarm agent↔agent Q&A (DM + wait) that the task/result model can't express.
- **Hooks (`mention_received` → spawn pane)** = app-side auto-dispatch (e.g. review-request message spawns reviewer pane) — the external-agent analog of the V7 EM dispatch.
- **`advice` arrays** are adoptable across the existing `voss` CLI/SDK structured output today, independent of the bus.

## Adaptations Required (do NOT copy verbatim)

- **Per-project, not global**: source system stores in `~/.local/share` cross-project. Voss convention: durable event logs under `.voss/bus/` (or absorb `.voss/swarm/`), rebuildable index + per-agent cursors under `.voss-cache/`. Sorted-pair DM naming removes the need for global agent registry.
- **Mirror to SSE, don't bypass it**: Voss already has a server plane (loopback REST+SSE, bearer token, V13 SDKs). Bus appends should emit protocol events so the V14 cockpit / V15 live plane renders coordination without tailing files. File bus = write path for externals; SSE = read path for the app.
- **Advisory positioned as tier-C complement**, never as the enforcement story — Voss's bet is caged/budgeted/enforced; the bus is the trust-boundary fallback where enforcement can't reach.
- **Label vocabulary maps onto V5 board**: `mission:<id>` ↔ board card; consider `card://<id>` claim URIs locking work items, aligning with V4 session-tree lineage.
- **Skip**: Telegram bridge, observer TUI (cockpit already exists), TOON output format (Voss has its own format cascade), global agent registration events.

## Known Gaps (inherit from source design — accept or address)

Advisory-only (rogue agent can ignore); no delivery guarantees/acks; per-channel ordering only; fs-notify latency is local-machine only (fine — Voss v0.1 excludes distributed agents); no message-type schema (labels are convention).

## When to Surface

**Trigger:** A13 swarm work resumes (this becomes its messaging substrate — supersede SWM-04/05/06 file formats), the Agents-launcher phase (999.1 backlog) activates, or a V-track phase needs Voss↔external-agent or pane↔pane coordination.

This seed will surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Large** — a full phase (likely phase-pair: bus core + app integration). Bus core (JSONL append + lock + ULID + cursors + inbox/wait + claims w/ overlap detection) is well-bounded Python/Rust; hooks + SSE mirroring + cockpit surface + A13 retrofit each add real surface. `advice` arrays are a small independent task extractable to a todo.

## Breadcrumbs

- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` — SWM-04/05/06 file-mediated coordination this would supersede/upgrade
- `crates/voss-app-core/src/sandbox.rs` + V14-11 summary — enforcement tiers; tier C = where advisory claims slot in
- `apps/voss-app/src/org/adopt.ts` — adopted agents (tier C always) = primary claims consumers
- `.planning/PROTOCOL.md` + `contracts/events.schema.json` — SSE event union the bus events would join
- `.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md` — `.voss` coordination grammar; a `bus{}`/channel declaration could eventually compile-to-config here
- `.planning/notes/seed-structured-pane-rendering.md` — sibling seed; both feed the "panes as first-class Voss citizens" direction

## Notes

Four primitives are independently adoptable — claims alone (tier-C guard) or advice arrays alone are viable first slices if the full bus is too big for one phase.

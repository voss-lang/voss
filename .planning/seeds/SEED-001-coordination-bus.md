---
id: SEED-001
status: dormant
planted: 2026-06-09
planted_during: v0.1.1 — post-V14 (frontier: V15 live plane / V16 managed docs / A4 presets)
trigger_when: A13 swarm resumes, Agents-launcher phase (999.1) activates, or post-V15 when external pane agents need coordination; claims slice + advice arrays have no upstream gate
scope: medium
---

# SEED-001: External Agent Coordination Surface — expose the org plane to external CLI agents

Give external CLI agents (Claude Code, Codex, OpenCode in voss-app panes) coordination primitives by **exposing what Voss already has** — adoption registry, board cards, server plane, SSE event union — through shell-scriptable CLI verbs. NOT a parallel file-bus substrate.

## Source + Reframe

Distilled from an external brain dump (2026-06-09) analyzing a zero-infrastructure multi-agent coordination tool built on four primitives: (1) append-only JSONL event log w/ ULID ids + channels + @mentions + labels, (2) advisory claims over file globs + opaque URIs w/ overlap detection + TTL + `check` exits 1, (3) per-agent byte cursors → inbox/wait via fs-notify, (4) conditional hooks (message → condition → spawn, atomic claim-on-fire).

**Reframe decision (2026-06-09 discussion):** the source system's file substrate exists because it has no server. **Voss has a server** (loopback REST + bearer + SSE; always-on in voss-app post-V15 sidecar), and external CLI agents can run commands — so every primitive becomes a thin client of the existing plane instead of new infrastructure. This keeps V17 coherent with the V14/V15 strategic direction (pull agents *into* the Voss plane via adopt/managed-launch/structured panes, not around it).

## The Slices (each maps to an existing asset)

1. **Advisory claims → adopt flow + sandbox.rs + V5 board.** `adopt.ts` already applies advisory budget+scope at adoption — nothing checks it. Add `voss claims stake/check/release`: `check <paths>` exits 1 on overlap with another agent's registered scope → shell-scriptable pre-edit guard. Reuse `sandbox.rs::validate_scope` canonicalization/traversal logic for overlap detection. URI claims `card://<id>` = board cards; `mission:<id>` label = cardId — work-item locking on the existing ontology. Storage: F1 SQLite registry / server plane. Positioned as the **tier-C complement** to VCKP-13 enforcement tiers (OS sandbox covers tier A/B; adopted/unmanaged agents get the advisory layer). No upstream gate — buildable now.
2. **Messaging + wait/inbox → thin CLI over the V15 SSE plane.** `voss bus send/inbox/wait` as protocol-plane clients: messages are a new event type in the `contracts/events.schema.json` union; `wait --mention <me>` blocks on the SSE stream with a filter until match. Replaces A13's result-file + PTY-idle completion heuristic with deterministic fan-in; unlocks mid-swarm agent↔agent Q&A. Cockpit rendering + AttentionQueue integration come free from the event union. **Gated on V15.**
3. **Advice arrays → existing structured CLI output.** Add `advice: [...]` suggested-next-commands to CLI-JSON surfaces (`RunData`, `voss board`, new claims/bus verbs) — guides autonomous loops. Trivial, independent, adoptable today.
4. **Hooks → existing engines.** mention→spawn-reviewer-pane = AttentionQueue action or V7 EM dispatch behavior. Do NOT build a standalone hook router.

## Explicitly Rejected (from the source design)

File JSONL substrate + fs locks; per-agent byte cursor files; fs-notify wait; standalone hooks engine; global `~/.local/share` cross-project storage; Telegram bridge; observer TUI; TOON output format. All server-replacement or out-of-band infrastructure — Voss has the server and the cockpit.

## Worth Keeping as Conventions (zero code)

Label vocabulary (`coord:blocker`, `coord:handoff`, `mission:<id>`, `review-request`) documented in the V16 managed AGENTS.md section — **V16 is the delivery vehicle** that tells external agents these verbs/conventions exist; advisory primitives are only as good as the prompt discipline that invokes them.

## Why This Matters

Voss's org layer (V4 tree / V5 board / V7 EM) covers Voss-native agents; VCKP-13 tiers A/B get OS enforcement. Tier-C adopted/unmanaged external agents have **zero coordination**: no pre-edit conflict guard, no mid-flight messaging (A13 is one-shot task-file in / result-file out), no deterministic completion signal. The lowest-common-denominator interface every pane agent has is "run a command" — so coordination must be CLI verbs, and those verbs should front the existing plane.

## Known Gaps (accepted)

Advisory-only (rogue agent can ignore — that's what tiers A/B are for); no delivery guarantees/acks; compliance depends on V16-managed instructions; local-machine only (v0.1 excludes distributed agents).

## When to Surface

**Trigger:** A13 swarm resumes (slice 2 supersedes SWM-04/05/06 file formats), Agents-launcher (999.1) activates, or post-V15. Slices 1 (claims) and 3 (advice) have no upstream gate and work as independent quick wins.

## Scope Estimate

**Medium** — reframe shrank it from large. Slice 1 claims = well-bounded (CLI verbs + SQLite + overlap detection reusing sandbox.rs). Slice 2 = thin clients + one event type, mostly post-V15 glue. Slice 3 = trivial. Slice 4 = config on existing engines.

## Breadcrumbs

- `apps/voss-app/src/org/adopt.ts` — advisory budget+scope applied at adoption; claims make it checkable; tier-C consumers
- `crates/voss-app-core/src/sandbox.rs` — `validate_scope` canonicalization/traversal logic to reuse for overlap detection
- `.planning/PROTOCOL.md` + `contracts/events.schema.json` — event union the message event type joins
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` — SWM-04/05/06 file coordination that slice 2 supersedes
- `.planning/phases/V10-voss-language-as-coordination-spec/V10-SPEC.md` — eventual `.voss` declaration could compile-to-config
- V16 (Managed Docs) — delivery vehicle for conventions/verbs in the managed AGENTS.md section
- `.planning/notes/seed-structured-pane-rendering.md` — sibling seed, same "panes as first-class Voss citizens" direction

## Notes

First SPEC question already answered by reframe: server-backed, not file-backed. Original four-primitive file design preserved above under Source for reference if the no-server case (headless agents outside voss-app, no `voss serve`) ever becomes a real constraint — that's the only condition that reopens the file substrate.

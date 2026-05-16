# voss-app — Concept

> Status: **concept**, not spec. Decisions locked below survive into spec phase; open questions must close before `/gsd:plan-phase`.

## 1. Mission

**voss-app is a desktop ADE where every workspace cell is a live Voss program.** The Voss harness is the substrate, not a guest. Shell, file edit, web fetch, git — all reachable as tool calls inside the loop. Users compose multi-agent workflows by wiring cells together in `.voss` and steer them in a tmux-density grid.

**Primary user (v0):** Voss devs and power dev-tool early adopters who already think in agent loops. Not "Cursor for everyone."

**Core value prop:** "Drive an agent in one cell, a reviewer watches every turn in another, intervene anywhere, replay anything." The grid IS the orchestrator UI.

**Anti-mission:** voss-app is not a chat client, not a code editor with AI bolted on, and not a single-agent CLI in a window.

## 2. v0 Killer Demo — Reviewer-as-Pair-Programmer

The single thing v0 must do flawlessly:

> User drives **one main cell**. A **reviewer cell** observes every turn, runs after each tool call, and posts inline critique. User can `⌘.` to apply reviewer suggestions or ignore.

That's it. Two cells. Everything else (swarm, pipeline, fanout, watchers) is v1+.

**Why this demo:**

- Smallest scope that proves the substrate (loop-primary, event-wired cells).
- Provable value for a single user from minute one — no "set up your swarm" friction.
- Reviewer pattern already lives in `voss/harness/agent/reviewer.voss`. Reuses existing harness logic.
- Reframes the "AI pair programmer" pitch: not chat-with-files, but loop-watching-loop with hand-off semantics.
- Forces the hard infra (cell isolation, event bus, streaming render) into v0 without the orchestration complexity.

**Out of v0:** worktree-per-cell, broadcast `>>>`, multi-model bench, layout transitions, swarm racing, replay scrubber. All preserved in v1 backlog.

## 3. Locked Decisions

| Layer | Decision |
|---|---|
| Shell | **Tauri** — Rust core + webview UI. Revives `crates/` spike. |
| UI | TypeScript + **Solid** (signal-based, fits token-rate streaming). |
| Cell process | **Subprocess per cell** — each cell = own `voss` Python subprocess over JSONL stdio. Real cwd/env. Crash isolation. |
| Cell IPC | JSONL framed messages over stdio + Unix-socket event bus for cell-to-cell. |
| State ownership | Shell owns layout, bus, cell registry. **Each Voss process owns its own session/turns/memory.** Shell coordinates, never injects. |
| Storage | SQLite per project (Voss harness already persists sessions). |
| Build | pnpm workspace at root + extend existing Cargo workspace. |
| Distribution | DMG/AppImage/MSI from Tauri. Existing `@vosslang/cli` unchanged. |
| Monorepo path | `apps/voss-app/` (TS+Tauri) + `crates/voss-app-core/` (Rust grid manager) + `crates/voss-app-ipc/` (typed protocol). |

## 4. Agent Orchestration Model

### Cell

A **cell** is a single Voss harness instance with:
- own pid, own cwd, own env
- own model + provider + budget
- own `.voss` loop file (defaults to `loop.voss` shipped with voss-app)
- own session state (SQLite-backed, durable across restarts)
- a JSONL stdio pipe to the shell
- a subscription channel on the event bus

Cells are sovereign. The shell never reaches inside a cell to mutate state.

### Event bus

Each cell emits structured events over a Unix socket the shell brokers:

```
turn_start    {cell_id, turn_id, prompt}
turn_token    {cell_id, turn_id, token, role}
tool_call     {cell_id, turn_id, tool, args}
tool_result   {cell_id, turn_id, tool, result, duration_ms}
turn_end      {cell_id, turn_id, summary, cost_usd, tokens}
error         {cell_id, type, message}
dsl_reload    {cell_id, file, reason}
```

Other cells subscribe via `.voss`:

```voss
on_event(pane: "main", type: "turn_end") {
  inject_context(pane.last_turn.summary)
}
```

In v0 the only consumer is the reviewer cell. The protocol is designed to scale to v1 fanout/pipeline without rework.

### Reviewer attachment

Reviewer is not "another chat window." It is a cell whose `.voss` loop subscribes to `turn_end` events from a named target cell and emits its own turns critiquing the target's work. Critiques surface in the reviewer cell's body and as side-attached annotations in the target cell (visual only — target cell's session is not mutated).

## 5. Stack Detail

### Frontend (apps/voss-app/src/)
- Solid for reactivity (signal updates per streamed token without React reconciler overhead)
- Tailwind for styling (variant B design system already proven in sketch 001)
- xterm.js **rejected** — we render structured turn lines, not raw VT sequences
- Existing Voss renderer logic (`voss/harness/render.py`, `voss/harness/tui/renderer.py`) ported to TS as the per-cell view

### Tauri core (apps/voss-app/src-tauri/)
- Thin Rust binary, wraps `voss-app-core` crate
- Owns: window mgmt, menu, system tray, OS integration
- Bridges Solid UI ↔ Rust core via Tauri commands + events

### voss-app-core (crates/voss-app-core/)
- Grid manager: layout state, cell registry, focus, lifecycle
- Cell supervisor: spawns/kills voss subprocesses, restart-on-crash policy
- Event bus broker: Unix socket server, pub/sub between cells, fanout to UI
- Session persistence orchestration (delegates SQLite writes to Voss; tracks layout state)

### voss-app-ipc (crates/voss-app-ipc/)
- Typed JSONL protocol schema (Rust types + TS types generated from same source)
- Versioned envelope (forward-compat as event types grow)
- Frame parser/serializer

### Voss harness (voss/, unchanged)
- voss-app spawns existing `voss` Python entry point with a new `--ipc-mode jsonl` flag
- Existing harness pieces (`agent.py`, `tools.py`, `permissions.py`, `recorder.py`, `tui/renderer.py`) reused as-is
- New code in voss/harness: a `bridge_mode` module emitting events on the contract above

## 6. Monorepo Layout

```
voss/                            # python harness (unchanged path)
crates/
  voss-app-core/                 # rust: grid manager, supervisor, bus
  voss-app-ipc/                  # rust: typed JSONL protocol
  ...existing frozen rust spike  # kept for reference, not built
apps/
  voss-app/
    CONCEPT.md                   # this file
    src/                         # solid + tailwind UI
    src-tauri/                   # tauri shell, depends on voss-app-core
    package.json
    tailwind.config.ts
shared/
  voss-events/                   # ts+rust schema generation
package.json                     # pnpm workspace root
Cargo.toml                       # cargo workspace root (extend existing)
```

## 7. Permission & Trust Model (v0)

- Cells spawned in a project inherit a per-project permission policy from `.voss/policy.yaml`.
- Default policy: read-only tools auto-approved; file writes prompt; shell exec prompts with arg preview.
- Reviewer cell is read-only by policy — cannot edit files or run shell. Enforced at cell-config level, not trust-based.
- Existing `voss/harness/permissions.py` handles enforcement; shell renders the prompt UX.

## 8. Open Conceptual Questions (must close before spec phase)

1. **Public name.** "voss-app" is the working name. Ship name? "Voss Studio"? "Voss"? "Voss Grid"?
2. **Authoring model.** Who writes `.voss` loops for cells?
   - Option A: Ship a curated library (`main.voss`, `reviewer.voss`, `executor.voss`) + opt-in customize.
   - Option B: Users author from scratch.
   - Option C: GUI builder for cell behaviors that emits `.voss`.
3. **Reviewer trigger granularity.** Per-turn (cheap, sometimes stale) vs per-tool-call (expensive, always fresh) vs user-triggered (cheapest, requires attention).
4. **Cell crash policy.** Auto-restart cell on Voss process crash? Or freeze and surface for user action? Reviewer should never auto-restart silently in worktree-write scenarios.
5. **Existing harness reuse.** `voss/harness/agent/loop.voss` already defines the default loop. Does voss-app ship it as the `main` cell default, or fork into `apps/voss-app/loops/`?
6. **Session boundary.** Project-level session (cells share a project context) or cell-level only (cells are fully independent processes)? Affects how memory/RAG primitives in Voss are scoped.
7. **Distribution channel.** DMG/AppImage/MSI direct downloads? Homebrew cask? Auto-update via Tauri updater? GitHub Releases?
8. **Replay record granularity.** Every event (cheap, large db) vs every turn boundary (smaller, less time-travel)?

## 9. Suggested Path Forward

1. **Now:** close 8 open questions above (target: 2-3 sessions of `/gsd:discuss-phase`).
2. **Then:** `/gsd:spec-phase` for v0 — locks WHAT reviewer-as-pair-programmer ships.
3. **Then:** spike phases:
   - Spike A: Tauri + Solid + one cell streaming end-to-end (proves the substrate).
   - Spike B: subprocess supervisor + JSONL protocol + 2 cells exchanging events (proves the bus).
   - Spike C: existing `reviewer.voss` running attached to a `main` cell (proves the demo).
4. **Then:** `/gsd:plan-phase` per feature slice.

Do not generate phases for surface features (multi-model bench, swarm) until the substrate spikes prove the model.

## 10. Reference Artifacts

- Sketch 001 (`/.planning/sketches/001-voss-grid-shell/`) — Variant B (Minimal Tile) locked as design direction. Header conventions, glyph affordances, density rules carry forward.
- Existing harness: `voss/harness/agent/loop.voss`, `voss/harness/agent/reviewer.voss`, `voss/harness/render.py`, `voss/harness/tui/renderer.py`.
- Frozen Rust spike: `crates/` — not the production target but informs voss-app-core IPC choices.

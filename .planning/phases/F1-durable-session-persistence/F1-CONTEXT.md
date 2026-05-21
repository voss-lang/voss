# Phase F1: Durable Session Persistence - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Agent lifecycle awareness in the ADE — a SQLite registry tracks which panes run Voss agent sessions (vs generic shells), and a startup-path restore routine auto-restarts those agent subprocesses on boot. A6 handles pane geometry/scrollback; F1 handles agent identity and restart.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 requirements are locked.** See `F1-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `F1-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- SQLite registry (`rusqlite` crate) in `voss-app-core`
- Registry schema: pane_id, session_id, cli_binary, cli_args, cwd, status, last_seen
- `spawn_agent` Tauri command (registers + spawns)
- Boot-path restore logic (read registry → spawn agents into A6-restored panes)
- Clean shutdown registry update (mark `last_seen` on quit)
- Orphan cleanup (stale rows → stopped)

**Out of scope (from SPEC.md):**
- Background watchdog / health monitoring — no subprocess death detection during runtime (F1 is boot-only)
- Crash-safe recovery (WAL/fsync) — boot-only, best-effort from last clean quit
- Mid-task context resume — F1 restarts the CLI process; the harness owns conversation/context recovery via its own session files
- Budget/cost display in HUD — that is F3
- Registry management UI — no UI to browse/manage agent sessions
- Multi-machine sync — registry is local only

</spec_lock>

<decisions>
## Implementation Decisions

### Registry Integration Point
- **D-01:** New standalone `agent_registry.rs` module in `voss-app-core` — same level as `session.rs`, `layouts.rs`, `grid.rs`. Owns rusqlite Connection, schema creation, CRUD. PTY layer stays generic; registry is agent-specific.
- **D-02:** `spawn_agent` wraps `spawn_pty` internally — calls existing `spawn_pty` to create the PTY session, then writes the registry row. PTY layer unchanged. Agent layer adds metadata.
- **D-03:** `Mutex<Connection>` for SQLite connection management — same pattern as `grid.rs` `Mutex<GridState>`. Open once on plugin init, wrap in Mutex. Commands lock briefly for reads/writes.

### Boot Restore Sequencing
- **D-04:** Frontend orchestration — after A6 loads session.json and rebuilds the tree, but before PaneComponent mounts spawn generic shells, the frontend checks registry for each pane_id. If agent entry exists with `status = 'active'`, pass `cli_binary` + `cli_args` to PaneComponent instead of default shell. No Rust-side restore logic.
- **D-05:** Rely on A6 pane_id stability — A6 already persists and restores pane IDs (UUIDs). Registry keys on `pane_id`. On boot, match `registry.pane_id` to restored tree `pane_id`. No extra mapping layer.

### Agent Spawn API Surface
- **D-06:** `PaneComponent` gets optional `agentConfig` prop: `{ cliBinary: string, cliArgs: string[], sessionId: string }`. If present, spawn_agent instead of spawn_pty. Tree leaf stores this config for A6 persistence.
- **D-07:** Command palette entry point — A7 command registry gets a "Start Voss Agent" (or "Start Agent") command that prompts for task description, then spawns agent in focused pane. Minimal UX, leverages existing A7 infrastructure.
- **D-08:** Any CLI binary from day one — `spawn_agent` takes a generic `cli_binary` string. "voss", "claude", "codex", "opencode" all work. Registry stores whatever was passed. Future Agents launcher (F6 council) needs this anyway.

### Quit + Lifecycle Hooks
- **D-09:** Extend A6 close-requested handler — add registry `last_seen` update AFTER session.json save but BEFORE `window.close()`. Same handler, sequential: scrollback → session.json → registry last_seen → close. One close-request flow.
- **D-10:** Both events trigger status change — agent exit (PTY EOF/exit event) → immediate registry update to `status = 'stopped'`. App quit → active rows stay `status = 'active'` (they're meant to restart on next boot). Clean distinction.
- **D-11:** Boot-time orphan sweep — after A6 restore + F1 agent restart, scan registry for `status = 'active'` rows with no matching `pane_id` in the restored tree. Mark those `status = 'stopped'`. One pass, no background work.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Session Persistence (A6 — the substrate F1 builds on)
- `crates/voss-app-core/src/session.rs` — Versioned SessionFile, fs2 locked writes, tmp-rename atomic pattern. F1 must not break this flow.
- `apps/voss-app/src/grid/sessionPersist.ts` — A6 lifecycle orchestration: structural autosave + close-requested full save. F1 D-09 extends the close-requested handler here.
- `apps/voss-app/src/grid/sessionCommands.ts` — `buildSessionFile()` assembler
- `apps/voss-app/src/grid/sessionStorage.ts` — `saveSession()`/`loadSession()` Tauri IPC wrappers

### PTY Backend (A2 — spawn_agent wraps this)
- `crates/voss-app-core/src/pty/mod.rs` — PtySession, PtyRegistry, spawn_session(). F1 D-02 wraps this.
- `crates/voss-app-core/src/pty/commands.rs` — 7 Tauri commands including `spawn_pty`. F1 adds `spawn_agent` alongside.
- `apps/voss-app/src-tauri/src/lib.rs` — App-level Tauri command wrappers (cross-crate generate_handler! pattern). F1 adds spawn_agent wrapper here.

### Crate Structure
- `crates/voss-app-core/src/lib.rs` — Module registry + Tauri plugin init. F1 adds `pub mod agent_registry` + `Mutex<Connection>` managed state + `spawn_agent` in invoke_handler.

### Grid + Pane Components (integration points)
- `apps/voss-app/src/grid/GridRoot.tsx` — Mounts tree; F1 boot restore happens before this mounts panes
- `apps/voss-app/src/pane/PaneComponent.tsx` — F1 D-06 adds agentConfig prop here
- `apps/voss-app/src/command-palette/registry.ts` — F1 D-07 registers "Start Agent" command here

### SPEC
- `.planning/phases/F1-durable-session-persistence/F1-SPEC.md` — Locked requirements — MUST read before planning

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `session.rs` versioned-file pattern (version field, typed errors, fail-closed `Ok(None)`, tmp-rename) — agent_registry.rs can follow same error patterns
- `PtyRegistry` (Arc-wrapped, default-constructible) — model for AgentRegistry Tauri state management
- A7 `CommandRegistry` — already supports programmatic command registration; "Start Agent" command plugs in naturally
- `installCloseSessionSave()` — the exact hook point for D-09 registry update

### Established Patterns
- **Cross-crate Tauri commands:** App-level wrappers in `src-tauri/src/lib.rs` delegate to `voss-app-core` public fns (A2 PTY, A3 grid). F1 follows same pattern.
- **Mutex state:** `Mutex<GridState>` in `grid.rs`, `Mutex<PtySession>` in PTY. F1 uses `Mutex<rusqlite::Connection>`.
- **Plugin init setup:** `app.manage(Arc::new(...))` in plugin `setup()` closure. F1 adds `Mutex<Connection>` alongside `Arc<PtyRegistry>`.

### Integration Points
- **PaneComponent mount:** Currently auto-calls `spawn_pty`. F1 adds branching: if `agentConfig` prop → `spawn_agent`, else → `spawn_pty`.
- **Session restore flow:** `loadSession()` → tree rebuild → PaneComponent mount. F1 inserts registry query between tree rebuild and PaneComponent mount.
- **Close-requested flow:** `installCloseSessionSave()` → scrollback → session.json → close. F1 adds registry update step before close.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Agent registry is a clean infrastructure layer following established crate patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Future Agents launcher (memory: voss-agents-launcher-feature) will consume the generic `spawn_agent` API designed here.

</deferred>

---

*Phase: F1-durable-session-persistence*
*Context gathered: 2026-05-20*

# Phase F1: Durable Session Persistence — Specification

**Created:** 2026-05-20
**Ambiguity score:** 0.17 (gate: ≤ 0.20)
**Requirements:** 5 locked

## Goal

When the ADE quits with active Voss agent panes, relaunching the app auto-restarts those agent subprocesses in the correct panes with the correct session IDs, cwd, and CLI arguments — without user intervention.

## Background

A6 session persistence (shipped) handles **pane geometry**: tree layout, cwd, shell, scrollback, and focus are persisted to `session.json` and restored on boot. However, A6 treats every pane as a generic shell — it has no concept of "this pane was running a Voss agent session." If the app restarts, panes reopen as plain shells; the user must manually re-launch their agent sessions.

The Python harness already maintains per-session state in `.voss/sessions/<id>.json` (via `voss/harness/session.py`). The ADE's PTY backend (`crates/voss-app-core/src/pty/`) spawns generic shell subprocesses but has no agent-awareness.

F1 bridges this gap: a durable SQLite registry in the ADE tracks which panes have active agent sessions, and a startup-path restore routine reads the registry and spawns the correct `voss` subprocesses before displaying the window.

## Requirements

1. **Agent Registry**: A SQLite database tracks active agent sessions per pane.
   - Current: No concept of "agent pane" vs "shell pane" exists in the ADE. PTY spawn is generic.
   - Target: `voss-app-core` maintains a SQLite database (via `rusqlite`) with one row per active agent session: `pane_id`, `session_id`, `cli_binary`, `cli_args` (JSON array), `cwd`, `status` (active/stopped), `last_seen` (timestamp).
   - Acceptance: After spawning a Voss agent in a pane, querying the registry returns a row with matching `pane_id`, `session_id`, and `status = 'active'`. After the agent exits normally, `status` changes to `'stopped'`.

2. **Registry Location**: The registry file lives at a deterministic, per-project path.
   - Current: No registry file exists.
   - Target: Registry is stored at `<project_path>/.voss/agent-registry.sqlite`. For project-less mode, falls back to `~/.config/voss-app/agent-registry.sqlite`.
   - Acceptance: File exists at the expected path after the first agent spawn. Opening a different project uses a different registry file.

3. **Agent Spawn Registration**: Launching a Voss agent in a pane writes a registry entry.
   - Current: PTY spawn (`spawn_session`) creates a generic shell with no metadata beyond PID.
   - Target: A new `spawn_agent` path (or extension of `spawn_session`) accepts agent-specific params (`session_id`, `cli_binary`, `cli_args`) and inserts a registry row atomically alongside PTY creation.
   - Acceptance: `spawn_agent("voss", ["do", "fix the bug"], "/path/to/repo", "abc123")` creates both a PTY session and a registry row. The PTY runs `voss do "fix the bug"` in `/path/to/repo`.

4. **Boot Restart**: On app launch, active registry entries trigger agent subprocess spawns.
   - Current: A6 restore creates panes with geometry/cwd but spawns plain shells.
   - Target: After A6 geometry restore, the startup path reads the registry for rows where `status = 'active'`, matches them to restored panes by `pane_id`, and spawns the corresponding `cli_binary cli_args` instead of a plain shell. Non-matched rows (orphaned entries) are marked `status = 'stopped'`.
   - Acceptance: Quit app with 2 panes running Voss agents + 1 plain shell pane → relaunch → 2 panes auto-start Voss with correct session IDs and cwd, 1 pane starts as plain shell. All 3 panes have correct geometry (A6).

5. **Clean Shutdown Marking**: When the app quits cleanly, active agents are marked for restart.
   - Current: A6 quit-save captures tree + scrollback but no agent metadata.
   - Target: The `close-requested` handler (A6 D-05) also writes `last_seen` timestamps on all active registry rows. Rows with `status = 'active'` at boot indicate "was running at last quit — restart."
   - Acceptance: After clean quit, all previously-active rows have `last_seen` within 2 seconds of quit time. After boot restart, those rows' agents are re-spawned.

## Boundaries

**In scope:**
- SQLite registry (`rusqlite` crate) in `voss-app-core`
- Registry schema: pane_id, session_id, cli_binary, cli_args, cwd, status, last_seen
- `spawn_agent` Tauri command (registers + spawns)
- Boot-path restore logic (read registry → spawn agents into A6-restored panes)
- Clean shutdown registry update (mark `last_seen` on quit)
- Orphan cleanup (stale rows → stopped)

**Out of scope:**
- Background watchdog / health monitoring — no subprocess death detection during runtime (F1 is boot-only)
- Crash-safe recovery (WAL/fsync) — boot-only, best-effort from last clean quit
- Mid-task context resume — F1 restarts the CLI process; the harness owns conversation/context recovery via its own session files
- Budget/cost display in HUD — that is F3
- Registry management UI — no UI to browse/manage agent sessions
- Multi-machine sync — registry is local only

## Constraints

- Must use `rusqlite` (not `sqlx` or other async SQLite) — matches the existing sync Mutex pattern in `voss-app-core` (grid.rs, session.rs, layouts.rs)
- Registry writes must not block the main thread — use `spawn_blocking` or Tauri's async command pattern
- Must integrate with existing A6 `close-requested` flow without breaking scrollback capture
- Must integrate with existing A6 geometry restore without duplicating tree restoration logic
- SQLite file must be excluded from git (`.gitignore` entry under `.voss/`)

## Acceptance Criteria

- [ ] `rusqlite` dependency added to `voss-app-core` and builds clean
- [ ] Registry SQLite file created at `<project>/.voss/agent-registry.sqlite` on first agent spawn
- [ ] `spawn_agent` Tauri command creates PTY + registry row atomically
- [ ] Agent exit (normal) updates registry row to `status = 'stopped'`
- [ ] App quit with 2 active agent panes → relaunch → both agents auto-restart with correct session_id + cwd
- [ ] App quit with 2 agent panes + 1 shell pane → relaunch → agents restart, shell pane starts as plain shell
- [ ] Plain shell panes (no agent) have NO registry entry
- [ ] Orphaned registry rows (pane_id not in restored tree) marked `status = 'stopped'` on boot
- [ ] Registry writes do not block UI thread
- [ ] `.voss/agent-registry.sqlite` is gitignored

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                           |
|--------------------|-------|------|--------|-------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Agent-aware restart, not full state resume       |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | 6 items explicitly out of scope                  |
| Constraint Clarity | 0.75  | 0.65 | ✓      | rusqlite, sync Mutex, boot-only, no WAL          |
| Acceptance Criteria| 0.75  | 0.70 | ✓      | 10 pass/fail criteria                            |
| **Ambiguity**      | 0.17  | ≤0.20| ✓      |                                                  |

## Interview Log

| Round | Perspective         | Question summary                                  | Decision locked                                              |
|-------|---------------------|----------------------------------------------------|--------------------------------------------------------------|
| 1     | Researcher          | What's the delta between A6 and F1?               | F1 = agent lifecycle (which panes had voss), A6 = geometry   |
| 1     | Researcher          | SQLite or JSON + file lock?                        | SQLite (new rusqlite dep) — better for concurrent queries    |
| 1     | Researcher          | Boot-only or crash recovery?                       | Boot-only — best-effort from last clean quit                 |
| 2     | Researcher+Simplifier| Minimal schema or with budget/full config?        | Minimal: pane_id, session_id, cli_binary, cli_args, cwd, status, last_seen |
| 2     | Simplifier          | Supervisor: background thread or startup path?     | Startup-path only — no background daemon                     |
| 2     | Simplifier          | Irreducible core if cut 50%?                       | Registry + boot restart, no UI, no health monitoring         |
| 3     | Boundary Keeper     | What's explicitly NOT F1?                          | Watchdog, WAL, context resume, budget UI (F3), registry UI, multi-machine |
| 3     | Boundary Keeper     | What does done look like?                          | 2 agent panes + 1 shell → quit → relaunch → agents restart, shell stays shell |

---

*Phase: F1-durable-session-persistence*
*Spec created: 2026-05-20*
*Next step: /gsd:discuss-phase F1 — implementation decisions (how to build what's specified above)*

# F1-01 Summary

**Self-Check: PASSED**

Rust agent registry layer and Tauri IPC backbone for F1 durable session persistence.

## Tasks

| Task | Status | Verification |
|------|--------|--------------|
| 0 — rusqlite legitimacy gate | PASS | crates.io 0.39.0, 64M+ downloads; github.com/rusqlite/rusqlite active; `bundled` compiles SQLite from source |
| 1 — agent_registry.rs + spawn_command_session | PASS | `cargo test -p voss-app-core -- agent_registry` (8/8), `cargo build -p voss-app-core` |
| 2 — Tauri command wrappers + managed state | PASS | `cargo build -p voss-app` |

## Deliverables

### `crates/voss-app-core/`

- **Cargo.toml** — `rusqlite = { version = "0.39", features = ["bundled"] }`
- **agent_registry.rs** (NEW) — SQLite `agent_sessions` table, path helpers (`registry_path`, `global_registry_path`), CRUD: `open_registry`, `register_agent`, `mark_stopped`, `update_last_seen_all`, `get_active_agents`, `sweep_orphans`; parameterized queries only
- **pty/mod.rs** — `spawn_command_session(cmd_binary, cmd_args, rows, cols, cwd)` for arbitrary CLI binaries
- **lib.rs** — `pub mod agent_registry` + re-exports; `pub use pty::spawn_command_session`

### `apps/voss-app/src-tauri/`

- **Cargo.toml** — `rusqlite` pin (for `Connection` in managed state)
- **lib.rs** — `Mutex<Option<Connection>>` lazy-open via `ensure_registry`; 5 commands: `spawn_agent`, `get_active_agents`, `mark_agent_stopped`, `update_agents_last_seen`, `sweep_orphan_agents`; all registered in `generate_handler!`

## Requirements covered

FPRS-01, FPRS-02, FPRS-03, FPRS-05

## Notes

- `get_active_agents` is best-effort: returns `[]` on lock/open/query failure (Pitfall 3).
- Registry connection opens once per app lifetime; first `workspace_path` wins for path selection.
- Existing PTY commands (`spawn_pty`, `pty_write`, etc.) unchanged.

## Next

F1-02+ can wire frontend restore flow, heartbeat, and orphan sweep on startup.

---

*Completed: 2026-05-21 | Plan: F1-01 | Phase: F1-durable-session-persistence*

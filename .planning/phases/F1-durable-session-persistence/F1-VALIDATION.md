# Phase F1: Durable Session Persistence — Validation Strategy

**Created:** 2026-05-20
**Phase:** F1-durable-session-persistence

## Test Framework

| Property | Value |
|----------|-------|
| Framework (Rust) | `cargo test -p voss-app-core` |
| Framework (TS) | vitest (`pnpm vitest --run`) |
| Config file (Rust) | Cargo.toml (standard) |
| Config file (TS) | `apps/voss-app/vitest.config.ts` |
| Quick run command | `cargo test -p voss-app-core -- agent_registry && cd apps/voss-app && pnpm vitest --run src/**/*agent*` |
| Full suite command | `cargo test -p voss-app-core && cd apps/voss-app && pnpm vitest --run` |

## Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FPRS-01 | Registry schema + CRUD | unit (Rust) | `cargo test -p voss-app-core -- agent_registry -x` | Wave 0 |
| FPRS-01 | Status transition active->stopped | unit (Rust) | same | Wave 0 |
| FPRS-02 | Path resolution project vs global | unit (Rust) | same | Wave 0 |
| FPRS-03 | spawn_agent creates PTY + row | integration (Rust) | `cargo test -p voss-app-core -- agent_registry::tests::spawn -x` | Wave 0 |
| FPRS-04 | Boot restore loads active agents | unit (TS) | `cd apps/voss-app && pnpm vitest --run -t "agent restore"` | Wave 0 |
| FPRS-05 | Close handler updates last_seen | unit (TS) | `cd apps/voss-app && pnpm vitest --run -t "close session"` | Wave 0 |
| FPRS-05 (AC) | last_seen within 2s of quit | unit (Rust) | `cargo test -p voss-app-core -- agent_registry::tests::last_seen -x` | Wave 0 |

## Sampling Rate

- **Per task commit:** `cargo test -p voss-app-core -- agent_registry && cd apps/voss-app && pnpm vitest --run`
- **Per wave merge:** Full suite: `cargo test -p voss-app-core && cd apps/voss-app && pnpm vitest --run && tsc --noEmit`
- **Phase gate:** Full suite green before `/gsd:verify-work`

## Wave 0 Gaps

- [ ] `crates/voss-app-core/src/agent_registry.rs` — new module with tests
- [ ] `apps/voss-app/src/**/__tests__/*agent*.test.ts` — frontend agent config / restore tests
- [ ] `rusqlite` dependency in Cargo.toml — must build clean

## Acceptance Criteria (from SPEC)

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

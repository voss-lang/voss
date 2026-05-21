# F1-03 Summary

**Self-Check: PASSED** (automated verification; Task 2 human E2E pending user approval)

End-to-end agent session persistence wiring: boot restore, quit lifecycle, PTY exit hooks, orphan sweep.

## Tasks

| Task | Status | Verification |
|------|--------|--------------|
| 1 — PTY exit + close-requested + boot restore | PASS | `tsc --noEmit`; vitest 512/512; `cargo test -p voss-app-core -- agent_registry`; `cargo build -p voss-app` |
| 2 — End-to-end human verification | PENDING | User checkpoint per plan — automated builds green |

## Deliverables

### `apps/voss-app/src/pane/pty-ipc.ts`

- `PtyTransportOpts`: optional `agentPaneId`, `workspacePath`
- On PTY `exit`, best-effort `invoke('mark_agent_stopped', …)` when `agentPaneId` set

### `apps/voss-app/src/pane/PaneComponent.tsx`

- Passes `agentPaneId` / `workspacePath` into `PtyTransport` when `agentConfig` present

### `apps/voss-app/src/workspaces/workspaceSessionPersist.ts`

- `installAllWorkspacesCloseSave` 4th param: `getWorkspacePath?: () => string | null`
- After `saveIndex`, calls `update_agents_last_seen` (best-effort `.catch()`)

### `apps/voss-app/src/App.tsx`

- `fetchAgentConfigs()` — `get_active_agents` → `Record<string, AgentConfig>` keyed by `paneId`
- `MountedWorkspace`: `agentConfigByPaneId` signal; `orphanSweepDone` guard
- Fetches configs before session restore in `restoreWorkspaceFromRecord`, `bootstrapWorkspaceProject`, `openSelectedProject` (first mount)
- `GridRoot`: `agentConfigByPaneId`, `workspacePath` props
- `bindController`: orphan sweep via `sweep_orphan_agents` + `collectLeaves(initialSession.grid.root)`
- Close-save: active workspace path passed to `installAllWorkspacesCloseSave`

### Test fixes

- `a5-acceptance.test.tsx` — mock `get_active_agents` returns `[]`
- `workspaceSessionPersist.test.ts` — mock `invoke`

## Requirements covered

FPRS-04, FPRS-05

## Lifecycle sequence (D-04 / D-11)

1. Load session → query registry → mount `GridRoot` (agent panes use `spawn_agent`)
2. After controller bind → sweep orphans (stale active rows → stopped)
3. On agent PTY exit → `mark_agent_stopped`
4. On quit → `update_agents_last_seen`

## Notes

- Registry is sole source of agent metadata; `PaneLeaf` / `session.json` unchanged (Pitfall 6).
- `startAgent` palette handler still optional/no-op until wired (D-07).
- Quit registry update uses active workspace `project()?.path` only (single `invoke` per plan).

## Task 2 — Manual verification (user)

Per plan: launch `pnpm tauri dev`, confirm grid/session regressions absent, palette shows "Start Agent", `.gitignore` covers registry file. Type **approved** when satisfied.

## Next

Optional: wire `startAgent` in `App.tsx` + spread `agentCommands()` into registry for full palette-driven agent spawn.

---

*Completed: 2026-05-21 | Plan: F1-03 | Phase: F1-durable-session-persistence*

# Voss ADE — archived in-repo desktop application

Frozen at master commit `794b9f13` (2026-09-12), the last commit that built
this app inside the Voss workspace. The Voss ADE desktop application is now
developed in its own repository and integrates with Voss only through
`voss serve`, the versioned protocol (`docs/protocol.md`), and the client SDKs.
See `docs/architecture/0004-voss-ade-repository-split.md` for the boundary.

## What is here

| Path | What it was |
|---|---|
| `apps/voss-app/` | Tauri + Solid desktop app: PTY panes, canvas, workspaces, themes, keymaps, settings, swarm and observe UI |
| `crates/voss-app-core/` | Rust core the Tauri shell called: PTY reader (OSC 133/1337 capture), session and layout persistence, sidecar launch |
| `docs/` | App-only docs and screenshots that used to live in `docs/` and the repo root |

## Planning history under `planning/`

Superseded by ADR 0004 (`docs/architecture/0004-voss-ade-repository-split.md`).
Moved from `.planning/` on 2026-09-12:

| Path here | Was |
|---|---|
| `planning/phases/A1..A13-voss-app-*`, `999.1-*`, `999.2-*` | The A-track: Tauri shell, PTY panes, grid, layouts, project open, session persistence, command palette, workspaces, settings, status bar, visual redesign, swarm orchestration, plus the two 999 fixups |
| `planning/phases/E5-tui-voss-app-autonomous-driving` | Autonomous-driving eval phase for the desktop app |
| `planning/phases/V11-ade-org-integration`, `V14-ade-run-cockpit-*`, `V24-ade-product-revamp-swarm-observability` | ADE cockpit and product-revamp phases |
| `planning/research/voss-ade/`, `planning/research/ade-ui-design-contract-research.md` | ADE terminal, workspace, attention, review, security, and UI-contract research |
| `planning/ADE-REDESIGN.md`, `VOSS-ADE-DEEP-DIVE-JUL19.md`, `VOSS-OBSERVE-IMPLEMENTATION-BRIEF.md`, `CANVAS-OBSERVE-INSTRUCTIONS-PLAN.md` | ADE redesign, deep dive, and the observe/canvas implementation plans |
| `planning/notes/plan-grid-drag-rearrange.md`, `seed-structured-pane-rendering.md` | Grid and pane-rendering notes |

`V15-live-plane-integration` stayed in active planning: its live SSE event plane
is engine work the ADE consumes, not desktop code.

## Nothing here is built

- Not a Cargo workspace member. The root `Cargo.toml` lists `archive` under
  `exclude`, so cargo ignores these crates entirely.
- Not a pnpm workspace package. `pnpm install` at the root never touches
  `apps/voss-app`.
- Not linted, tested, or covered by any workflow under `.github/workflows/`.
- Not installable in place. Both Cargo manifests inherit `version.workspace`
  and friends, which no longer resolve outside the workspace, and the app's
  `src/org/` files import the TypeScript SDK through a relative path that
  breaks at this depth. Those references are left as they were on purpose.

To build any of it, check out `794b9f13` or earlier.

## Why archive instead of delete

The code stays greppable and cherry-pickable by path for the separate ADE
repository, and the history behind every decision in the app stays attached
to the files it shaped.

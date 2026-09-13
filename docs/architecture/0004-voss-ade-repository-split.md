# ADR 0004: Voss and Voss ADE are separate products

**Status:** Accepted, 2026-09-12
**Supersedes:** the in-repo desktop application, now frozen under `archive/voss-ade/`

## Context

The repository once held both the Voss orchestration engine and a Tauri desktop
application, Voss ADE, that wrapped it. The two are different products with
different release cadences, dependencies, and audiences. Keeping them in one
workspace tied the engine's build, tests, and dependency graph to a desktop UI
that most engine consumers never use.

## Decision

Voss and Voss ADE are separate products in separate repositories. The desktop
application no longer lives in or builds from this repository. Its last in-repo
revision is frozen at `archive/voss-ade/` for history and porting; nothing there
is built, linted, or tested.

Voss ADE integrates with Voss only across the versioned protocol boundary:

```
Voss ADE  ->  voss-sdk / client contract  ->  REST + SSE over loopback  ->  voss serve  ->  engine
```

Voss never imports ADE. ADE never imports Voss internals. ADE consumes the
released Voss executable, a version-compatible SDK, and the protocol
(`docs/protocol.md`), never a Voss source checkout.

## Ownership

**Voss owns** the orchestration platform: the `.voss` language and compiler, the
Python harness and runtime, the orchestration pipeline (teams, roles, session
tree, board, engineering-manager loop, reviewers, audit, budgets, confidence,
context allocation, memory), permissions and safety policy, provider
integration, `voss serve`, the CLI, the TUI, the protocol and contract
artifacts, the SDKs, and packaging of the engine.

**Voss ADE owns** the desktop product: the Tauri shell and native lifecycle,
PTYs and tmux-backed terminal persistence, xterm rendering, raw Claude Code and
Codex terminals and their process-state detection, pane lifecycle, the
canvas and grid, pane geometry, layouts, application workspaces, themes,
appearance and keymaps, file and folder panes, worktree UX, and
application-local persistence.

## Non-goals

Voss does not own pane geometry, Tauri IPC, canvas state, xterm, terminal
themes, tmux layout state, desktop workspaces, or desktop application settings.

Voss ADE does not reimplement Voss team semantics, the session tree, the board
and gate logic, reviewers, orchestration budgets or confidence, Voss memory
semantics, or the Voss event schema.

Two distinctions the boundary rests on:

- A terminal or pane session belongs to ADE. A Voss orchestration session
  belongs to Voss.
- Raw CLI process state belongs to ADE. Voss protocol event state belongs to
  Voss.

## Consequences

- `voss-sdk` launches `voss serve` by executable (explicit path, then
  `VOSS_BIN`, then `voss` on PATH), so an external client needs no Voss
  source-tree layout.
- The engine's CI and dependency graph no longer carry the desktop app or its
  Tauri and frontend toolchain.
- A future ADE integration depends only on the released Voss executable, a
  compatible SDK, and the protocol. What moved out and where is listed in
  `archive/voss-ade/README.md`.

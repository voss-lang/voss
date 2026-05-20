---
phase: A7
slug: voss-app-command-palette-keymap
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-20
---

# Phase A7 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|---|---|
| **Framework** | Vitest 4.1.6, Cargo test, TypeScript/Vite build, Playwright smoke where practical |
| **Config file** | `apps/voss-app/vitest.config.ts`, `apps/voss-app/tsconfig.json`, root `Cargo.toml`, `apps/voss-app/playwright.config.ts` |
| **Quick run command** | `pnpm --dir apps/voss-app test -- --run src/command-palette src/grid src/__tests__/App.test.tsx && cargo test -p voss-app-core keymap` |
| **Full suite command** | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core && cargo build -p voss-app` |
| **Estimated runtime** | ~120-240 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pnpm --dir apps/voss-app test -- --run src/command-palette src/grid src/__tests__/App.test.tsx && cargo test -p voss-app-core keymap`
- **After every plan wave:** Run `pnpm --dir apps/voss-app test && cargo test -p voss-app-core`
- **Before `/gsd:verify-work`:** Full suite must be green: `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core && cargo build -p voss-app`
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|---|---|---|
| A7-00-01 | 00 | 0 | CMD-01..CMD-07 | T-A7-00 | A7 does not execute before UI-SPEC and A3/A4/A5 substrate exist | source + shell | `test -f .planning/phases/A7-voss-app-command-palette-keymap/A7-UI-SPEC.md` | no | pending |
| A7-01-01 | 01 | 1 | CMD-02, CMD-03, CMD-04, CMD-05 | T-A7-01 | Registry dispatch consumes only handled chords and preserves PTY pass-through | Vitest | `pnpm --dir apps/voss-app test -- --run src/command-palette src/grid/__tests__/keymap.test.ts` | no | pending |
| A7-02-01 | 02 | 2 | CMD-01, CMD-02, CMD-03, CMD-04, CMD-07 | T-A7-02 | Palette captures focus/keys while open and exposes all catalog commands/layouts/recents | Vitest | `pnpm --dir apps/voss-app test -- --run src/command-palette src/__tests__/App.test.tsx` | no | pending |
| A7-03-01 | 03 | 3 | CMD-05, CMD-06 | T-A7-03/T-A7-04 | Keymap JSON validates per entry, partially applies valid overrides, and surfaces invalid entries as toasts | Vitest + Cargo | `pnpm --dir apps/voss-app test -- --run src/command-palette && cargo test -p voss-app-core keymap` | no | pending |
| A7-04-01 | 04 | 4 | CMD-05 | T-A7-05 | Tmux prefix mode times out, cancels, dispatches mapped keys, and passes unknown keys to PTY | Vitest | `pnpm --dir apps/voss-app test -- --run src/command-palette src/grid` | no | pending |
| A7-05-01 | 05 | 5 | CMD-01..CMD-07 | T-A7-06 | Native menus and final acceptance route through the same registry without duplicate handlers | build + e2e/manual | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo build -p voss-app` | no | pending |

---

## Wave 0 Requirements

- [ ] `A7-UI-SPEC.md` exists before planner/executor work proceeds; A7 is a frontend phase and the UI safety gate is enabled.
- [ ] A3 keymap substrate exists: `apps/voss-app/src/grid/keymap.ts`, `GridRoot.tsx`, and `keymap.test.ts`.
- [ ] A4 layout persistence seam exists: `listLayouts`, `loadLayout`, `saveLayout`, `GridController.applyLoadedLayout`, and App-level layout closures.
- [ ] A5 project-open seam exists: `projectStorage.ts`, `openProject`, `listRecents`, `SetupWindow`, and project state in `App.tsx`.
- [ ] Tauri menu/event strategy is selected before implementation to avoid native menu/catalog drift.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Native menu items trigger the same commands as palette rows | CMD-03 | jsdom cannot prove OS menubar accelerator behavior | Run Tauri app, open the native menu for Window/Pane/Layout/Project/Settings/Help, trigger representative items, and confirm the same visible behavior as palette commands. |
| `.voss/keymap.json` hot reload updates bindings without restart | CMD-05/CMD-06 | Requires real filesystem watcher and app event loop | Run Tauri app in an open project, edit `.voss/keymap.json`, confirm valid binding takes effect and invalid entry shows a toast. |
| Cmd+B prefix indicator appears only on focused pane | CMD-05 | Visual/focus behavior is easier to validate in the real shell | Switch to tmux profile, press Cmd+B, confirm `[Cmd+B...]` appears in the focused pane header, times out after 1.5s, and does not appear on unfocused panes. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing substrate references
- [x] No watch-mode flags
- [x] Feedback latency < 240s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending UI-SPEC and planning

---
phase: A7
slug: voss-app-command-palette-keymap
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-20
closed_out: 2026-05-21
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
| A7-00-01 | 00 | 0 | CMD-01..CMD-07 | T-A7-00 | A7 does not execute before UI-SPEC and A3/A4/A5 substrate exist | source + shell | A7 artifacts and substrate inspected | yes | pass |
| A7-01-01 | 01 | 1 | CMD-02, CMD-03, CMD-04, CMD-05 | T-A7-01 | Registry dispatch consumes only handled chords and preserves PTY pass-through | Vitest | `npm test -- App.test.tsx keymapStorage.test.ts registry.test.ts --run` | yes | pass |
| A7-02-01 | 02 | 2 | CMD-01, CMD-02, CMD-03, CMD-04, CMD-07 | T-A7-02 | Palette captures focus/keys while open and exposes all catalog commands/layouts/recents | Vitest + build | `npm test -- App.test.tsx keymapStorage.test.ts registry.test.ts --run`; `npm run build` | yes | pass |
| A7-03-01 | 03 | 3 | CMD-05, CMD-06 | T-A7-03/T-A7-04 | Keymap JSON validates per entry, partially applies valid overrides, and surfaces invalid entries as toasts | Vitest + Cargo | `npm test -- App.test.tsx keymapStorage.test.ts registry.test.ts --run`; `cargo test -p voss-app-core keymap --lib` | yes | pass |
| A7-04-01 | 04 | 4 | CMD-05 | T-A7-05 | Tmux prefix mode times out, cancels, dispatches mapped keys, and passes unknown keys to PTY | Vitest + build | `npm test -- App.test.tsx keymapStorage.test.ts registry.test.ts --run`; `npm run build` | yes | pass |
| A7-05-01 | 05 | 5 | CMD-01..CMD-07 | T-A7-06 | Native menus and final acceptance route through the same registry without duplicate handlers | build + manual | `npm run build`; `cargo check -p voss-app` | yes | automated pass; runtime manual pending |

---

## Wave 0 Requirements

- [x] `A7-UI-SPEC.md` exists before planner/executor work proceeds; A7 is a frontend phase and the UI safety gate is enabled.
- [x] A3 keymap substrate exists: `apps/voss-app/src/grid/keymap.ts`, `GridRoot.tsx`, and `keymap.test.ts`.
- [x] A4 layout persistence seam exists: `listLayouts`, `loadLayout`, `saveLayout`, `GridController.applyLoadedLayout`, and App-level layout closures.
- [x] A5 project-open seam exists: `projectStorage.ts`, `openProject`, `listRecents`, `SetupWindow`, and project state in `App.tsx`.
- [x] Tauri menu/event strategy is selected before implementation to avoid native menu/catalog drift.

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

## Close-Out Evidence

Validated on 2026-05-21:

- `npm test -- App.test.tsx keymapStorage.test.ts registry.test.ts --run` from `apps/voss-app`: 4 files, 47 tests passed.
- `npm test -- --run` from `apps/voss-app`: 34 files, 384 tests passed.
- `npm run build` from `apps/voss-app`: TypeScript and Vite production build passed.
- `cargo test -p voss-app-core keymap --lib`: 14 keymap tests passed.
- `cargo check -p voss-app`: Tauri app crate checked successfully.

Manual runtime checks remain recorded below because they require a live Tauri shell and OS menu/event loop:

- Native menu item dispatch equivalence.
- `.voss/keymap.json` hot reload through the live app event loop.
- Cmd+B prefix indicator visual behavior in a live pane.

**Approval:** automated close-out complete; live runtime manual sign-off pending.

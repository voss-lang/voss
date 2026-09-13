# A8 Phase Summary — Workspaces, UX Polish, & Theming

**Phase:** A8-voss-app-workspaces-ux-polish-theming  
**Date:** 2026-05-21  
**Environment:** macOS darwin (agent acceptance session)  
**Owner for manual runtime:** human QA before `/gsd:verify-work`

---

## Phase objective recap

Deliver Warp-style multi-workspace tabs with isolated pane trees and persistence (extending A6), a VSCode-compatible theme engine with 12 bundled themes and live hot-swap, appearance/accessibility polish (font, cursor, bell, reduced motion, high contrast), named setting profiles, and platform-native window chrome (vibrancy/acrylic/mica, Linux desktop entry). Satisfy locked requirements **UXP-01 through UXP-30** per `.planning/ROADMAP.md`.

---

## Automated suite evidence (2026-05-21)

| Gate | Result | Notes |
|------|--------|-------|
| Vitest (`apps/voss-app`) | **512 passed** (47 files) | Full frontend unit/component suite |
| Cargo `voss-app-core` | **120 passed** | themes, profiles, workspaces, session, appearance, fonts |
| `pnpm --dir apps/voss-app build` | **OK** | Production frontend build |
| `cargo build -p voss-app` | **OK** | Tauri app compiles |
| Playwright e2e | **64 skipped** | 13 new A8 specs in `e2e/workspaces.spec.ts`, `e2e/themes.spec.ts` skip unless `TAURI_E2E=1` |

---

## UXP-01..30 evidence map

| Req | Requirement (summary) | Evidence type | Primary evidence |
|-----|----------------------|---------------|------------------|
| UXP-01 | Workspace tab bar | Automated | `WorkspaceTabBar.test.tsx`, `App.test.tsx` (tab bar below titlebar) |
| UXP-02 | Isolated pane tree per workspace | Automated | `App.test.tsx` D-01 multi-mount; `GridRoot.test.tsx` active gate |
| UXP-03 | `+` opens workspace picker | Automated | `NewWorkspacePicker.test.tsx`, `App.test.tsx` |
| UXP-04 | Per-workspace accent color | Automated | `WorkspaceTabBar.test.tsx` (8-color palette); `workspaceStore.test.ts` |
| UXP-05 | Ctrl+1..9 / Ctrl+Tab workspace switch | Automated | `workspaceShortcuts.test.ts`, `App.test.tsx` Ctrl+Tab |
| UXP-06 | Multi-workspace restore on relaunch | Automated + manual | `workspaceSessionPersist.test.ts`; Rust `session` + `workspaces` tests — **manual quit/reopen NOT RUN** |
| UXP-07 | Drag-to-reorder tabs | Automated + manual | `workspaceStore.test.ts` reorder; `WorkspaceTabBar.tsx` draggable — **manual pointer NOT RUN** |
| UXP-08 | Close guard (running process / last tab) | Automated | `WorkspaceTabBar.test.tsx` |
| UXP-09 | VSCode theme import path | Automated | `themes/schema.test.ts`; Rust `themes.rs` custom `.voss/themes/` |
| UXP-10 | 8 bundled dark themes | Automated | `themeCatalog.test.ts` |
| UXP-11 | 3 bundled light themes | Automated | `themeCatalog.test.ts` |
| UXP-12 | Live theme preview | Automated | `themeRuntime.test.ts` preview stack |
| UXP-13 | Custom theme JSON schema | Automated | Rust `themes.rs`; `schema.test.ts` |
| UXP-14 | Theme hot-swap ≤100ms | Automated | `themeRuntime.test.ts` apply (latency not e2e-measured) |
| UXP-15 | Opacity / vibrancy / acrylic | Automated + manual | `windowEffects.test.ts`; A8-05 build — **manual compositor NOT RUN** |
| UXP-16 | Font picker + live preview | Automated | `fontStorage.test.ts`, `settings.test.ts` |
| UXP-17 | Cursor customization | Automated | `settings.test.ts`, `PaneComponent` wiring (A8-04) |
| UXP-18 | Smooth transitions (reduced-motion aware) | Automated | `PaneChrome.test.tsx`, `index.css` |
| UXP-19 | Pane chrome refinement | Automated | `PaneChrome.test.tsx`, `pane.css` |
| UXP-20 | Window corner radius / shadow | Plan + build | A8-05 `tauri.conf.json`, CSS tokens — visual manual deferred |
| UXP-21 | High-contrast WCAG AAA | Automated + manual | `schema.test.ts` `contrastRatio`; `settings.test.ts` overlay — **manual 12-theme visual NOT RUN** |
| UXP-22 | `prefers-reduced-motion` global | Automated | `settings.test.ts`, `PaneChrome.test.tsx` |
| UXP-23 | 10px font floor | Automated | `settings.test.ts` |
| UXP-24 | Bell behavior modes | Automated | `settings.test.ts` |
| UXP-25 | Named setting profiles | Automated | `profiles.test.ts`; Rust `profiles.rs` |
| UXP-26 | Profile quick-switch (palette / menu) | Automated | `registry.test.ts`, `nativeMenu.test.ts` |
| UXP-27 | Profile storage path + workspace pin | Automated | Rust `profiles.rs`; `workspaceStore` pinned profile |
| UXP-28 | macOS vibrancy + native menu | Automated + manual | `windowEffects.test.ts` macOS branch; `nativeMenu.test.ts` — **manual vibrancy NOT RUN** |
| UXP-29 | Windows acrylic / snap | Automated + manual | `windowEffects.test.ts` Windows branch — **NOT RUN (no Windows session)** |
| UXP-30 | Linux desktop entry / WM hints | Automated + manual | `resources/voss-ade.desktop`, `tauri.conf.json` — **NOT RUN (no Linux compositor session)** |
| — | E2E workspace flows | E2E skip | `e2e/workspaces.spec.ts` (7 scenarios, `TAURI_E2E` gate) |
| — | E2E theme / appearance flows | E2E skip | `e2e/themes.spec.ts` (6 scenarios, `TAURI_E2E` gate) |

---

## Manual acceptance table

Per `A8-VALIDATION.md` manual-only verifications. Agent session cannot substitute for human visual/runtime QA.

| # | Behavior | Requirements | OS | Date | Result | Owner / follow-up |
|---|----------|--------------|-----|------|--------|-------------------|
| 1 | Native vibrancy / acrylic / mica visible or gracefully absent | UXP-15, UXP-28–30 | macOS darwin | 2026-05-21 | **NOT RUN (visual)** — PARTIAL: `windowEffects.test.ts` + builds pass; agent cannot verify compositor | Human QA: run `pnpm --dir apps/voss-app tauri dev`, opacity &lt; 1.0; repeat on Windows + Linux |
| 2 | Hidden workspace PTYs keep running | UXP-01, UXP-02 | macOS darwin | 2026-05-21 | **NOT RUN (live PTY)** — cite `App.test.tsx` multi-mount + `GridRoot.test.tsx` inactive keydown gate | Human QA: 3 workspaces, `watch` in ws1, switch away 10s, confirm output |
| 3 | Quit/reopen restores three workspaces | UXP-06 | macOS darwin | 2026-05-21 | **NOT RUN (app lifecycle)** — cite `workspaceSessionPersist.test.ts` + Rust `workspaces`/`session` tests | Human QA: distinct layouts/cwds, quit, relaunch |
| 4 | Drag-to-reorder tabs feels native | UXP-07 | macOS darwin | 2026-05-21 | **NOT RUN (pointer)** — cite `workspaceStore.test.ts` reorder + `WorkspaceTabBar` draggable | Human QA: drag tabs, confirm order persists |
| 5 | High-contrast quality over 12 themes | UXP-21 | macOS darwin | 2026-05-21 | **NOT RUN (visual)** — cite `schema.test.ts` contrastRatio + `settings.test.ts` high-contrast overlay | Human QA: toggle HC per bundled theme, inspect chrome |

---

## Wave completion checklist

| Wave | Plan | Summary | Self-Check | Key deliverables |
|------|------|---------|------------|------------------|
| 0 | A8-00 | `A8-00-SUMMARY.md` | PASSED | Preflight: UI-SPEC, A7 seams, source probes |
| 1 | A8-01 | `A8-01-SUMMARY.md` | PASSED | Theme schema, 12 bundled themes, Rust IO, profiles substrate |
| 2 | A8-02 | `A8-02-SUMMARY.md` | PASSED | Workspace store, multi-mount GridRoot, central close save |
| 3 | A8-03 | `A8-03-SUMMARY.md` | PASSED | WorkspaceTabBar, NewWorkspacePicker, shortcuts, registry |
| 4 | A8-04 | `A8-04-SUMMARY.md` | PASSED | Theme runtime, appearance settings, transitions, pane chrome |
| 5 | A8-05 | `A8-05-SUMMARY.md` | PASSED | Window effects, platform metadata, native menu A8 alignment |
| 6 | A8-06 | `A8-06-SUMMARY.md` | PASSED | E2E acceptance specs + this phase summary |

---

## Known gaps and follow-up

1. **Linux CI `TAURI_E2E=1`** — Un-skip `e2e/workspaces.spec.ts` and `e2e/themes.spec.ts` on Linux with `tauri-driver` (macOS WebDriver blocked per `voss-app-tauri-e2e-macos-blocked`).
2. **Windows manual** — UXP-29 acrylic/mica and snap layout require a Windows machine; not exercised in this session.
3. **Visual QA** — UXP-15/21/28 compositor and theme-quality checks remain human-owned before verify-work.
4. **E2E latency** — UXP-14 ≤100ms hot-swap not measured in live browser; unit tests prove apply path only.
5. **Drag reorder UX** — Store reorder logic tested; pointer drag feel and tab dimension stability need manual sign-off (UXP-07).

---

## Threat model note (T-A8-09)

Automated suites are green and manual gaps are **explicitly recorded** (not silently accepted). Phase is evidence-ready for `/gsd:verify-work` pending human completion of the manual acceptance table above.

---

*Recorded: 2026-05-21 | Phase: A8-voss-app-workspaces-ux-polish-theming | Plan: A8-06 Task 2*

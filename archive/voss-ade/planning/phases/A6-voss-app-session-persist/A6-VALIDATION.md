---
phase: A6
slug: voss-app-session-persist
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-20
---

# Phase A6 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|---|---|
| **Framework** | Vitest 4.1.6, Cargo test, TypeScript/Vite build, Playwright for app smoke where available |
| **Config file** | `apps/voss-app/vitest.config.ts`, `apps/voss-app/tsconfig.json`, root `Cargo.toml`, `apps/voss-app/playwright.config.ts` |
| **Quick run command** | `pnpm --dir apps/voss-app test -- --run src/grid src/pane && cargo test -p voss-app-core session` |
| **Full suite command** | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core` |
| **Estimated runtime** | ~90-180 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pnpm --dir apps/voss-app test -- --run src/grid src/pane && cargo test -p voss-app-core session`
- **After every plan wave:** Run `pnpm --dir apps/voss-app test && cargo test -p voss-app-core`
- **Before `/gsd:verify-work`:** Full suite must be green: `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core`
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|---|---|---|
| A6-00-01 | 00 | 0 | PER-01..PER-06 | T-A6-00 | A6 does not execute before A5/A4/A3 substrate exists | source + shell | `test -f .planning/phases/A5-voss-app-project-open/A5-PHASE-SUMMARY.md || test -f .planning/phases/A5-voss-app-project-open/A5-06-SUMMARY.md` | yes | pending |
| A6-01-01 | 01 | 1 | PER-01, PER-03, PER-04, PER-05, PER-06 | T-A6-01/T-A6-02 | Session files are versioned, path-safe, locked during write, and fail closed | Rust unit | `cargo test -p voss-app-core session -- --nocapture` | yes | pending |
| A6-01-02 | 01 | 1 | PER-01, PER-03 | T-A6-01 | Tauri commands are registered with correct payload keys | source + build | `cargo build -p voss-app` | yes | pending |
| A6-02-01 | 02 | 2 | PER-01, PER-02, PER-03, PER-04 | T-A6-03 | Frontend wrappers and transforms serialize only allowed session state | Vitest | `pnpm --dir apps/voss-app test -- --run src/grid/session` | yes | pending |
| A6-03-01 | 03 | 3 | PER-01, PER-02 | T-A6-04 | Scrollback extraction uses `buffer.normal`, strips ANSI, caps at 2,000 | Vitest + source | `pnpm --dir apps/voss-app test -- --run src/pane src/grid/session` | yes | pending |
| A6-04-01 | 04 | 4 | PER-01, PER-02, PER-03 | T-A6-05/T-A6-06 | Restore priority and close-request save avoid data loss and close loops | Vitest | `pnpm --dir apps/voss-app test -- --run src/App src/grid/session` | yes | pending |
| A6-05-01 | 05 | 5 | PER-01..PER-06 | T-A6-07 | End-to-end restart behavior is covered by automated/source/manual gates | full + manual | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core` | yes | pending |

---

## Wave 0 Requirements

- [ ] Verify A5 project-open app lifecycle exists before A6 execution: project signal in `App.tsx`, project-less accepted state, `default_cwd` command wrapper, and setup bypass behavior.
- [ ] Verify A4 layout persistence is complete: `LayoutFile`, `loadDefaultLayout`, `GridController.applyLoadedLayout`, and active layout ownership in `App.tsx`.
- [ ] Verify A3 grid substrate is complete: `GridRoot` mounted, `GridController.snapshot()`, `sync_grid` registered, and `markStructuralChange` available.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Quit with four panes and reopen to exact geometry | PER-01/PER-02 | Tauri window lifecycle plus macOS close timing is difficult to fully prove in jsdom | Run app, create four panes, run visible output in each, quit, reopen same project, confirm geometry/focus/banner/scrollback. |
| Project-less global session bypasses setup window | PER-03 | Depends on first-launch local app state | Start without project, quit, relaunch, confirm setup does not show and pane cwd is home. |
| Corrupt `session.json` falls through to default layout | PER-04 | Needs filesystem setup and app startup observation | Write invalid JSON to `.voss/session.json`, ensure app opens via default layout or fresh pane and logs warning without dialog/crash. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing substrate references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution


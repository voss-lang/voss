---
phase: A4
slug: voss-app-layout-presets
status: green
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-19
---

# Phase A4 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.6, Cargo test, TypeScript/Vite build |
| **Config file** | `apps/voss-app/vitest.config.ts`, `apps/voss-app/tsconfig.json`, root `Cargo.toml` |
| **Quick run command** | `pnpm --dir apps/voss-app test -- --run src/grid` |
| **Full suite command** | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core` |
| **Estimated runtime** | ~60-120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pnpm --dir apps/voss-app test -- --run src/grid`
- **After every plan wave:** Run `pnpm --dir apps/voss-app test && cargo test -p voss-app-core`
- **Before `/gsd:verify-work`:** Full suite must be green: `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core`
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| A4-00-01 | 00 | 0 | LAY-04, LAY-05 | T-A4-01 | Existing pane ids preserved across preset/app integration preflight | source + unit | `pnpm --dir apps/voss-app test -- --run src/grid` | yes | green |
| A4-01-01 | 01 | 1 | LAY-01, LAY-03, LAY-04, LAY-05, LAY-08 | T-A4-01 | Preset transforms are pure visual tree rewrites, not process/pane destruction | unit | `pnpm --dir apps/voss-app test -- --run src/grid` | yes | green |
| A4-02-01 | 02 | 1 | LAY-02, LAY-03 | T-A4-02 | Titlebar switcher and `Cmd+G` cannot drift from grid state | component | `pnpm --dir apps/voss-app test -- --run src` | yes | green |
| A4-03-01 | 03 | 2 | LAY-06, LAY-07 | T-A4-03 | Layout path/name validation blocks traversal and corrupt files fail closed | Rust unit | `cargo test -p voss-app-core` | yes | green |
| A4-04-01 | 04 | 2 | LAY-04, LAY-05, LAY-06, LAY-07 | T-A4-01 / T-A4-03 | Load remaps/spawns only as allowed and never kills existing panes | unit + component | `pnpm --dir apps/voss-app test -- --run src/grid && cargo test -p voss-app-core` | yes | green |
| A4-05-01 | 05 | 3 | LAY-01..LAY-08 | T-A4-01 / T-A4-02 / T-A4-03 | End-to-end acceptance passes with build and focused tests | full | `pnpm --dir apps/voss-app test && pnpm --dir apps/voss-app build && cargo test -p voss-app-core` | yes | green |

---

## Wave 0 Requirements

- [ ] Add or verify tests that assert `App.tsx` renders `GridRoot`, not a direct single `PaneComponent`, before A4 work assumes grid runtime wiring.
- [ ] Add or verify Rust-side tests/source assertions that `sync_grid` is registered and `Mutex<GridState>` is managed by the Tauri app before layout persistence depends on the mirror.
- [ ] Add pure fixture helpers for pane-id set equality, focused-id preservation, and layout tree leaf order.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual titlebar density and active/custom state | LAY-02 | Pixel polish depends on Variant B visual judgment | Run the app, cycle all presets, verify the switcher remains 22px-titlebar compatible, dense, and non-rounded. |
| Save/load workflow from command stubs before A7 palette | LAY-06 | A7 owns final palette UI, so A4 may expose callable stubs only | Trigger the A4 save/load stub path and verify files appear under `.voss/layouts/` only after save. |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all known preflight gaps.
- [x] No watch-mode flags.
- [x] Feedback latency < 120 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** green 2026-05-19 — all 22 LAY-01..LAY-08 acceptance tests pass; full vitest suite 177/177; cargo `voss-app-core` 22/22; vite build is a pre-existing config issue (safari13 destructuring in solid-js compiled output) tracked separately.


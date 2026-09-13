---
phase: A5-voss-app-project-open
plan: 00
subsystem: substrate-preflight
status: complete
completed: 2026-05-20
---

# Phase A5, Plan 00: Substrate Preflight Summary

Completed the A5 blocking preflight and cleared the substrate gate before further A5 work.

## A4 Status

- `.planning/phases/A4-voss-app-layout-presets/A4-05-SUMMARY.md` exists and records `status: complete`.
- A4-05 summary records:
  - `pnpm --dir apps/voss-app test`: 15 files, 174 tests passed
  - `pnpm --dir apps/voss-app build`: passed
  - `cargo test -p voss-app-core`: 22 passed at A4 closeout time
  - `cargo test -p voss-app-core layouts`: 16 passed at A4 closeout time

## MSRV

- Before: `rust-version = "1.75"`
- After: `rust-version = "1.77.2"`
- Reason: `tauri-plugin-dialog` 2.4.2 requires Rust >= 1.77.2 per A5-RESEARCH Pitfall 7 / Q1.
- Local toolchain: `rustc 1.95.0-nightly`, sufficient for the new workspace floor.

## Seam Checks

- `apps/voss-app/src/App.tsx` still defines `saveCurrentLayout`, `loadLayoutByName`, and `applyDefaultLayout`.
- `apps/voss-app/src/App.tsx` still carries the unused-suppression lines for all three callable closures.
- `apps/voss-app/src-tauri/src/lib.rs` registers `save_layout`, `load_layout`, `list_layouts`, and `load_default_layout` in `tauri::generate_handler!`.
- `crates/voss-app-core/src/layouts.rs` still defines `LayoutError` with UI-copy Display strings for A5 `ProjectError` to mirror.

## Package Audit

Re-confirmed A5-RESEARCH `## Package Legitimacy Audit` on 2026-05-20:

- `tauri-plugin-dialog`: `[OK]`, Approved
- `@tauri-apps/plugin-dialog`: `[OK]`, Approved
- `git2`: `[OK]`, Approved

## Baselines

- A5-00 automated substrate gate: passed and printed `A5_SUBSTRATE_READY`
- `cargo check --workspace --quiet`: passed
- `cargo test -p voss-app-core`: 46 passed, 0 failed
- `pnpm --dir apps/voss-app test -- --run`: 15 files passed, 174 tests passed

## Outcome

A5 substrate is verified, the workspace MSRV is sufficient for the dialog plugin, package legitimacy is re-affirmed, and A5 can continue on top of the A4 seams.

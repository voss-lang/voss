---
phase: A4-voss-app-layout-presets
plan: 03
subsystem: rust-layout-persistence
status: complete
completed: 2026-05-20
---

# Phase A4, Plan 03: Rust Layout Persistence Summary

Implemented the Rust/Tauri persistence surface for `.voss/layouts/<name>.json`.

## Accomplishments

- Added versioned `LayoutFile` schema in `voss-app-core`.
- Added layout name validation to block traversal, separators, hidden names, control chars, drive prefixes, and `.json` suffix ambiguity.
- Added lazy save path creation for `.voss/layouts`.
- Added load/list/default helpers that do not create `.voss` on reads.
- Added fail-safe `default.json` handling for corrupt or unsupported layout files.
- Registered app-level Tauri commands: `save_layout`, `load_layout`, `list_layouts`, `load_default_layout`.

## Key Files

- `crates/voss-app-core/src/layouts.rs`
- `crates/voss-app-core/src/lib.rs`
- `apps/voss-app/src-tauri/src/lib.rs`

## Verify

```
cargo test -p voss-app-core layouts
16 passed

cargo test -p voss-app-core
22 passed
```

## Outcome

LAY-06 and LAY-07 persistence requirements are implemented on the Rust-owned I/O seam.

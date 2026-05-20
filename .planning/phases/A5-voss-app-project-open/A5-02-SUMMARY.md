---
phase: A5-voss-app-project-open
plan: 02
subsystem: tauri-project-open-ipc
status: complete
completed: 2026-05-20
---

# Phase A5, Plan 02: Tauri Project-Open IPC Summary

Wired the A5-01 Rust project core through the Tauri app crate and installed the native dialog plugin surface required by the frontend picker.

## Shipped

- Added Rust dependency `tauri-plugin-dialog = "2"` to `apps/voss-app/src-tauri/Cargo.toml`.
- Added JS dependency `"@tauri-apps/plugin-dialog": "^2"` to `apps/voss-app/package.json`.
- Updated `pnpm-lock.yaml`; resolved package is `@tauri-apps/plugin-dialog@2.7.1`.
- Registered `.plugin(tauri_plugin_dialog::init())` immediately after the existing OS plugin.
- Added minimal capability permission `dialog:allow-open`.
- Added app-crate command wrappers:
  - `fn open_project(path: String) -> Result<ProjectInfo, String>`
  - `fn load_recents() -> Vec<String>`
  - `fn default_cwd(project_path: Option<String>) -> String`
- Registered all three commands in `tauri::generate_handler!`.

## Capability Diff

```diff
   "permissions": [
     "core:default",
     "core:window:allow-close",
     "core:window:allow-minimize",
     "core:window:allow-toggle-maximize",
     "core:window:allow-set-fullscreen",
     "core:window:allow-is-fullscreen",
-    "core:window:allow-start-dragging"
+    "core:window:allow-start-dragging",
+    "dialog:allow-open"
   ]
```

`dialog:default` was not added; the permission surface is limited to open dialogs.

## Handler Count

- Before A5-02: 14 handlers
- After A5-02: 17 handlers

The A5-02 plan expected 16 (`existing 13 + 3`), but current `lib.rs` already had 14 handlers because `get_theme_overrides` is registered alongside PTY, grid, and layout commands. The correct final count for this codebase is 17.

## Verification

- `pnpm --filter voss-app install`: passed
- `cargo build -p voss-app --quiet`: passed
- Warm-cache build timing after plugin install: 2 seconds
- `cargo test -p voss-app-core project:: -- --nocapture`: 24 passed, 0 failed
- Static A5-02 plugin gate: `PROJECT_PLUGIN_OK`
- Capability JSON parse/minimal-permission gate: `CAP_OK`
- Command wrapper/handler gate: `PROJECT_COMMANDS_OK`

## Notes

The implementation was committed by a subagent as `f5a477c feat: implement project opening capabilities with tauri-plugin-dialog integration`. This summary records the post-commit verification and the handler-count correction.

# Phase A7 Close-Out

**Date:** 2026-05-21
**Status:** Code close-out complete; live runtime manual checks pending

## Code Closed

- Command registry dispatch is now wired through `App.tsx` for registered chords, palette execution, and native menu actions.
- `GridRoot` exposes the controller methods required by the command registry for pane split/close/equalize/focus/resize and layout cycling.
- Keymap profile switching persists through the existing keymap settings command; tmux prefix mode is active only under the tmux profile and drives registry command ids.
- Workspace keymap overrides can be watched through the Tauri command/event path, validated, partially applied, and surfaced as warning/error toasts.
- `help.keybindings` resolves to the full command palette instead of a placeholder.

## Verification

Run from `apps/voss-app` unless noted:

- `npm test -- App.test.tsx keymapStorage.test.ts registry.test.ts --run` — pass, 4 files / 47 tests.
- `npm test -- --run` — pass, 34 files / 384 tests.
- `npm run build` — pass.
- `cargo test -p voss-app-core keymap --lib` from repo root — pass, 14 tests.
- `cargo check -p voss-app` from repo root — pass.

## Manual Runtime Checks

These require a live Tauri runtime and were not executed in this close-out pass:

- Native menu items trigger the same command handlers as palette rows.
- Editing `.voss/keymap.json` in an open project emits `voss://keymap-updated`, applies valid bindings, and shows invalid-entry toasts.
- Under the tmux profile, Cmd+B shows the focused-pane prefix indicator, dispatches mapped keys, and times out after 1.5s.

## Notes

- No new dependency was added for keymap watching; the Tauri command uses scoped std polling.
- The unrelated deleted A10 checkpoint was left untouched.

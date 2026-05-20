import { test } from '@playwright/test';

/**
 * A7 command palette + keymap end-to-end — palette open/close,
 * command execution, keymap override, toast feedback, tmux prefix.
 *
 * SKIPPED on macOS — platform block: Tauri WebDriver unsupported
 * (tauri-driver = Linux WebKitWebDriver / Windows Edge only).
 * Per the A2-04 user decision (project memory
 * `voss-app-tauri-e2e-macos-blocked`) the A7 command palette logic
 * is unit-proven on macOS via vitest:
 *
 *   - `src/command-palette/__tests__/chords.test.ts` — chord normalization
 *   - `src/command-palette/__tests__/fuzzy.test.ts` — scoring + ranking
 *   - `src/command-palette/__tests__/registry.test.ts` — catalog + dispatch
 *   - `src/command-palette/__tests__/CommandPalette.test.tsx` — palette UI
 *   - `src/command-palette/__tests__/keymapStorage.test.ts` — profile/override bridge
 *   - `src/command-palette/__tests__/toast.test.tsx` — toast stack
 *   - `src/command-palette/__tests__/prefixMode.test.ts` — tmux prefix
 *   - `src/command-palette/__tests__/nativeMenu.test.ts` — menu model
 *   - `src/grid/__tests__/PaneChrome.test.tsx` — prefix indicator
 *
 * Plus the Rust `cargo test -p voss-app-core keymap` suite.
 */
const SKIP_REASON =
  'Tauri WebDriver unsupported on macOS — deferred to Linux CI (A10/future); see voss-app-tauri-e2e-macos-blocked';
test.describe.configure({ mode: 'serial' });
void SKIP_REASON;

// --- CMD-01: Cmd+P quick-open ------------------------------------------------

test.skip('cmd-ac1: Cmd+P opens quick mode with layouts and recents', () => {
  // Launch app → open project → save a layout → press Cmd+P.
  // Confirm palette appears with "Open layout or recent project" placeholder.
  // Confirm layout name appears in Layouts section.
  // Confirm recent project path appears in Recent Projects section.
});

// --- CMD-02: Cmd+Shift+P full palette ----------------------------------------

test.skip('cmd-ac2: Cmd+Shift+P opens full mode with all command categories', () => {
  // Press Cmd+Shift+P. Confirm palette appears with "Run command" placeholder.
  // Confirm Window, Pane, Layout, Project, Settings, Help categories are represented.
  // Type "split" → confirm Split Right and Split Below appear with chord hints.
});

// --- CMD-03: all six categories discoverable ---------------------------------

test.skip('cmd-ac3: all six categories findable in full palette', () => {
  // Open full palette. Search for one command from each category:
  // "Quick Open" (Window), "Split Right" (Pane), "Cycle Layout" (Layout),
  // "Open Project" (Project), "Switch Keymap" (Settings), "Keyboard" (Help).
});

// --- CMD-04: recent ranking affects order ------------------------------------

test.skip('cmd-ac4: recently used commands rank higher', () => {
  // Execute "Cycle Layout" via palette.
  // Reopen palette, type "c".
  // Confirm "Cycle Layout" appears before "Close Pane".
});

// --- CMD-05: custom keymap override ------------------------------------------

test.skip('cmd-ac5: .voss/keymap.json override rebinds a command', () => {
  // Write { "version": 1, "bindings": { "pane.splitRight": { "key": "Cmd+Shift+X" } } }
  // to .voss/keymap.json. Confirm toast "Keymap updated" appears.
  // Confirm Cmd+Shift+X splits a pane.
});

// --- CMD-06: invalid keymap toast feedback -----------------------------------

test.skip('cmd-ac6: invalid keymap entries produce toast errors', () => {
  // Write { "version": 1, "bindings": { "nonexistent.cmd": { "key": "Cmd+X" } } }
  // to .voss/keymap.json. Confirm toast "Keymap entry ignored" appears.
});

// --- CMD-07: tmux prefix mode ------------------------------------------------

test.skip('cmd-ac7: tmux Cmd+B then % dispatches vertical split', () => {
  // Switch to tmux profile via palette.
  // Press Cmd+B → confirm [Cmd+B...] indicator in header.
  // Press % → confirm pane splits vertically.
});

// --- Native menu smoke -------------------------------------------------------

test.skip('cmd-ac8: native menu items trigger same commands as palette', () => {
  // Open native Pane menu → click "Split Right".
  // Confirm pane splits the same as Cmd+D.
});

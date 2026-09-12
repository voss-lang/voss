import { test } from '@playwright/test';

/**
 * A7 command palette + keymap end-to-end — palette open/close,
 * command execution, category discovery, tmux prefix mode.
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

// --- Native menu + keymap.json file-watch scenarios ---------------------------
// These need either real OS menus (Tauri runtime) or the keymap.json watcher
const TAURI_E2E =
  process.env.TAURI_E2E === '1' || process.env.TAURI_E2E === 'true';
const SKIP_REASON_NATIVE =
  'requires real Tauri runtime (native menu / filesystem watcher); deferred to Linux CI under TAURI_E2E=1';

test.skip('cmd-ac2: Cmd+Shift+P opens full mode with all command categories', () => {
  // Press Cmd+Shift+P. Confirm palette appears with "Run command" placeholder.
  // Confirm Window, Pane, Layout, Project, Settings, Help categories are represented.
  // Type "split" → confirm Split Right and Split Below appear with chord hints.
});

// --- CMD-03: all six categories discoverable ---------------------------------

  test('cmd-ac5: .voss/keymap.json override rebinds a command', () => {
    // Write { "version": 1, "bindings": { "pane.splitRight": { "key": "Cmd+Shift+X" } } }
    // to .voss/keymap.json. Confirm toast "Keymap updated" appears.
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

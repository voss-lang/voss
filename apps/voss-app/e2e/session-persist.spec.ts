import { test } from '@playwright/test';

/**
 * A6 session persistence end-to-end — restart restore, project-less
 * bypass, corrupt fallback, scrollback banner.
 *
 * SKIPPED on macOS — platform block: Tauri WebDriver unsupported on
 * macOS (tauri-driver = Linux WebKitWebDriver / Windows Edge only).
 * Per the A2-04 user decision (project memory
 * `voss-app-tauri-e2e-macos-blocked`) the A6 session persistence logic
 * is unit-proven on macOS via vitest:
 *
 *   - `src/grid/__tests__/sessionStorage.test.ts` — invoke wrappers
 *   - `src/grid/__tests__/sessionCommands.test.ts` — pure transforms
 *   - `src/grid/__tests__/sessionPersist.test.ts` — autosave debounce
 *   - `src/grid/__tests__/RestoreBanner.test.tsx` — banner DOM
 *   - `src/grid/__tests__/a6-acceptance.test.tsx` — PER-01..PER-06
 *   - `src/pane/__tests__/scrollbackRegistry.test.ts` — registry
 *
 * Plus the Rust `cargo test -p voss-app-core session` suite covering
 * versioned schema, locked writes, fail-safe loads, and global path.
 *
 * The live restart-integration layer is deferred to a Linux CI job
 * (candidate A10). Specs retain assertion intent as the unchanged
 * contract for the CI un-skip.
 */
const SKIP_REASON =
  'Tauri WebDriver unsupported on macOS — deferred to Linux CI (A10/future); see voss-app-tauri-e2e-macos-blocked';
test.describe.configure({ mode: 'serial' });
void SKIP_REASON;

// --- session.json project session smoke --------------------------------------

test.skip('per-ac1: quit with 4 panes writes session.json and restart restores geometry', () => {
  // Launch app → open a project → split to 4 panes → quit.
  // Verify `.voss/session.json` exists and contains `"version":1`,
  // 4 pane entries with scrollback arrays, and `"focusedId"`.
  // Relaunch app → same project → confirm 4 panes at exact geometry.
});

test.skip('per-ac2: structural autosave writes session.json with null scrollback', () => {
  // Launch app → split once → wait 3s → read `.voss/session.json`.
  // Confirm pane scrollback entries are `null` (tree-only save, D-04).
});

test.skip('per-ac3: session restore wins over default.json layout', () => {
  // Save a `default.json` with 2-pane pipeline layout.
  // Save a `session.json` with 3-pane swarm layout.
  // Launch app → confirm 3 panes (session), not 2 (default).
});

// --- global-session.json project-less smoke ----------------------------------

test.skip('per-ac4: project-less quit writes global-session.json and restart bypasses setup', () => {
  // Launch app → "Start without project" → split → quit.
  // Verify `~/.config/voss-app/global-session.json` has
  // `"projectLessAccepted":true` and pane entries.
  // Relaunch → confirm setup window does NOT show and grid appears.
});

// --- corrupt fallback --------------------------------------------------------

test.skip('per-ac5: corrupt session.json falls through to default layout or fresh pane', () => {
  // Write `{not-json` to `.voss/session.json`.
  // Launch app → confirm no crash/dialog, default layout or fresh pane loads.
});

test.skip('per-ac6: unsupported session version falls through gracefully', () => {
  // Write `{"version":999}` to `.voss/session.json`.
  // Launch app → confirm no crash, falls through.
});

// --- restore banner ----------------------------------------------------------

test.skip('per-ac7: restored panes show "Session restored - N lines" banner that dismisses on input', () => {
  // Launch app with a valid session.json containing scrollback.
  // Confirm banner text "Session restored - N lines" is visible.
  // Type a character → confirm banner disappears.
});

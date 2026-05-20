import { test } from '@playwright/test';

/**
 * A4 layout presets end-to-end — preset cycle, custom-state surfacing,
 * save/load round-trip, and `.voss/layouts/default.json` auto-apply.
 *
 * SKIPPED on macOS — platform block: drives a live Tauri app under
 * WebDriver (`tauri-driver`), unsupported by Apple's WKWebView
 * (tauri-driver = Linux WebKitWebDriver / Windows Edge only). Per the
 * A2-04 user decision (project memory
 * `voss-app-tauri-e2e-macos-blocked`) the A4 preset/cycle/save/load
 * logic is unit-proven on macOS via vitest:
 *
 *   - `src/grid/__tests__/layoutPresets.test.ts` — preset model
 *   - `src/grid/__tests__/keymap.test.ts` — Cmd+G dispatch
 *   - `src/grid/__tests__/GridRoot.test.tsx` — Cmd+G integration
 *   - `src/grid/__tests__/PresetSwitcher.test.tsx` — controlled switcher
 *   - `src/grid/__tests__/layoutStorage.test.ts` — invoke wrappers + copy
 *   - `src/grid/__tests__/layoutCommands.test.ts` — load remap + no-destroy
 *   - `src/grid/__tests__/a4-acceptance.test.tsx` — LAY-01..LAY-08
 *
 * Plus the Rust `cargo test -p voss-app-core layouts` suite covering
 * versioned schema, lazy `.voss/layouts/` creation, path traversal
 * rejection, fail-safe `default.json` reads. The live browser-
 * integration layer is deferred to a Linux CI job (candidate A10). The
 * A4 D-01..D-09 human checkpoint on the real dev-machine GPU is the
 * authoritative visual sign-off. Specs retain the assertion intent as
 * the unchanged contract for the CI un-skip.
 */
const SKIP_REASON =
  'Tauri WebDriver unsupported on macOS — deferred to Linux CI (A10/future); see voss-app-tauri-e2e-macos-blocked';
test.describe.configure({ mode: 'serial' });
void SKIP_REASON;

test.skip('lay-ac1: Cmd+G cycles fanout → pipeline → swarm → watchers → fanout', () => {
  // Create 4 panes via ⌘D x3. Press Cmd+G four times. Assert the active
  // switcher label and the visual geometry (computePaneRects equivalent
  // via DOM data attrs) change through the fixed cycle. Pane count
  // stays at 4 across all five states.
});

test.skip("lay-ac2: manual split after preset flips switcher state to 'custom'", () => {
  // After a Cmd+G that lands on `fanout`, perform ⌘D. Assert the
  // titlebar switcher renders the `custom` display-only label and no
  // preset button shows aria-pressed='true'.
});

test.skip('lay-ac3: clicking a preset and pressing Cmd+G share one apply path', () => {
  // Click pipeline. Assert geometry matches A4-01 pipeline silhouette.
  // Press Cmd+G. Assert geometry advances to swarm and switcher
  // active-state advances to swarm. No re-mount of any pane DOM node.
});

test.skip('lay-ac4: save layout writes .voss/layouts/<name>.json with version=1', () => {
  // Build a 3-pane swarm, invoke the A7-seam saveCurrentLayout via the
  // app callable, assert .voss/layouts/build-watch.json exists and its
  // JSON body has { version: 1, activePreset: "swarm", grid: {…} }.
});

test.skip('lay-ac5: load layout restores geometry+focus without killing panes', () => {
  // Save a 4-pane fanout. Modify geometry to 2 panes via ⌘W. Load the
  // saved fanout. Assert 4 panes are present, the two original ids
  // survived (LAY-04), and two new panes were spawned with the saved
  // cwd/shell. Switcher reads `fanout`. Focus matches saved focusedId.
});

test.skip('lay-ac6: smaller saved layout preserves extras via overflow spill', () => {
  // Open 6 panes. Save a 2-pane V layout under `pair`. Open 6 panes
  // again, load `pair`. Assert all 6 ids are still present and the
  // last region holds 5 spill panes via the A4-01 D-04 chain.
});

test.skip('lay-ac7: default.json auto-applies on project open', () => {
  // Place a valid layout file at <workspace>/.voss/layouts/default.json
  // before launching the harness. On boot, assert the geometry matches
  // the file and the switcher reflects activePreset.
});

test.skip('lay-ac8: corrupt default.json does NOT crash startup', () => {
  // Write `{not-json` to default.json before launch. App must boot
  // with the single default pane and a stderr log line containing
  // `layout ignored: invalid file`. No modal, no destructive prompt.
});

test.skip('lay-ac9: unsupported version default.json is ignored', () => {
  // Write `{"version":999,…}` to default.json. App boots with the
  // single default pane; stderr contains `layout ignored: unsupported version`.
});

test.skip('lay-ac10: save layout with invalid name surfaces UI-SPEC error string', () => {
  // Attempt save with name "../escape". Assert the rejected promise
  // resolves to the exact string "layout name cannot contain /, \\ or .."
});

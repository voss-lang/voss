import { test } from '@playwright/test';

/**
 * A5 project-open end-to-end - setup-vs-grid branching, folder picker,
 * project metadata, recent projects, project-less mode, default layout
 * auto-apply, and no pane destruction on project change.
 *
 * SKIPPED on macOS - platform block: drives a live Tauri app under
 * WebDriver (`tauri-driver`), unsupported by Apple's WKWebView
 * (tauri-driver = Linux WebKitWebDriver / Windows Edge only). Per the
 * A2-04 user decision (project memory
 * `voss-app-tauri-e2e-macos-blocked`) the A5 project-open logic is
 * unit-proven on macOS via vitest:
 *
 *   - `src/__tests__/App.test.tsx` - setup-vs-grid branching,
 *     open-project orchestration, default-layout hook, pane preservation
 *   - `src/components/setup/__tests__/SetupWindow.test.tsx` - controlled
 *     component behavior, token discipline, L1 vocabulary
 *   - `src/project/__tests__/projectStorage.test.ts` - invoke wrappers,
 *     camelCase mapping, dialog cancel behavior
 *   - `src/project/__tests__/a5-acceptance.test.tsx` - WS-01..WS-07
 *     requirement coverage and SPEC AC #1..#11 mapping
 *
 * Plus the Rust `cargo test -p voss-app-core project::` suite covering
 * canonical project open, lazy `.voss/` behavior, recent-project cap and
 * dedupe, git-branch metadata, home-directory cwd fallback, and read-only
 * project metadata. The live browser-integration layer is deferred to a
 * Linux CI job (candidate A10).
 *
 * Additional blocker: the folder picker is a native folder dialog surfaced
 * through `tauri-plugin-dialog` (`open({ directory: true, multiple: false })`).
 * Playwright cannot drive that native folder dialog directly. Even on Linux,
 * this spec needs a test-build seam that mocks `@tauri-apps/plugin-dialog`
 * at the JS boundary before these scenarios can be un-skipped.
 *
 * Specs retain the assertion intent as the unchanged contract for the CI
 * un-skip.
 */
const SKIP_REASON =
  'Tauri WebDriver unsupported on macOS and native folder dialog requires a test-build mock - deferred to Linux CI (A10/future); see voss-app-tauri-e2e-macos-blocked';
test.describe.configure({ mode: 'serial' });

test.skip(
  `setup window visible on launch with no project (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: launch without persisted project/session state.
    // Assert Titlebar shows "Voss ADE", SetupWindow is visible, GridRoot is
    // not mounted, and no project path is required before interaction.
    await page.evaluate(() => void 0);
  },
);

test.skip(
  `click Open project -> mocked picker returns /tmp/x -> titlebar updates to "x" (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: inject a dialog mock returning /tmp/x, click
    // "Open project", assert the setup surface disappears, GridRoot mounts,
    // and Titlebar renders the basename "x".
    await page.evaluate(() => void 0);
  },
);

test.skip(
  `Start without project -> grid mounts -> titlebar stays "Voss ADE" (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: click "Start without project", assert GridRoot
    // mounts, project remains null, Titlebar remains "Voss ADE", and future
    // panes inherit the Rust-resolved home cwd.
    await page.evaluate(() => void 0);
  },
);

test.skip(
  `Open recent -> existing project changes -> pane id from prior project survives (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: start in a project with a pane, capture its pane
    // id, open a different recent project, assert metadata changes while the
    // prior pane id remains present per A5-CONTEXT D-13.
    await page.evaluate(() => void 0);
  },
);

test.skip(
  `Open same dir twice -> recents list does not duplicate (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: open the same mocked directory twice, assert the
    // second open succeeds and the recents UI/storage view contains one entry
    // for that path (SPEC AC #3).
    await page.evaluate(() => void 0);
  },
);

test.skip(
  `Open 6 dirs -> recents capped at 5 (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: open six unique mocked directories, assert recents
    // are newest-first and the oldest entry was dropped (SPEC Req-5).
    await page.evaluate(() => void 0);
  },
);

test.skip(
  `Open dir with .voss/layouts/default.json present -> default layout applies (${SKIP_REASON})`,
  async ({ page }) => {
    // TODO when un-skipped: prepare a project containing a valid default
    // layout, open it through the mocked picker, and assert A4's default layout
    // geometry applies without blocking project open.
    await page.evaluate(() => void 0);
  },
);

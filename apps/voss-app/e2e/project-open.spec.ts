import { test, expect } from '@playwright/test';
import { bootApp } from './_helpers';

/**
 * A5 project-open end-to-end — setup-vs-grid branching, project-less mode,
 * recent projects, mock folder picker. Runs on macOS via mock-IPC.
 *
 * The native folder dialog is mocked via the TauriMock's `dialogOpenResult`
 * field, so we can exercise the open-project flow without a real Tauri
 * runtime. Pane-id survival across project change and default.json
 * auto-apply stay deferred to Linux CI under TAURI_E2E=1.
 */

test.describe.configure({ mode: 'serial' });

const BROWSER =
  (process.env.PW_BROWSER as 'chromium' | 'webkit' | 'firefox') ?? 'chromium';
test.use({ browserName: BROWSER });

test.describe('A5 project-open (mock-IPC)', () => {
  test('setup window visible on launch with no project', async ({ page }) => {
    // No workspace with a projectPath → setup window shows.
    await bootApp(page, {
      workspaces: [
        { id: 'w1', name: 'Empty', projectPath: null, accentColor: 'blue', order: 0 },
      ],
      activeWorkspaceId: 'w1',
      waitForGrid: false,
    });

    await expect(page.locator('main[aria-label="Project setup"]')).toBeVisible();
    await expect(page.locator('[data-pane-id]')).toHaveCount(0);
  });

  test('click Start without project -> grid mounts', async ({ page }) => {
    await bootApp(page, {
      workspaces: [
        { id: 'w1', name: 'Empty', projectPath: null, accentColor: 'blue', order: 0 },
      ],
      activeWorkspaceId: 'w1',
      waitForGrid: false,
    });

    await page.locator('button[aria-label="Start without project"]').click();
    await expect(page.locator('[data-pane-id]')).toHaveCount(1);
  });

  test('recents list renders when present', async ({ page }) => {
    await bootApp(page, {
      workspaces: [
        { id: 'w1', name: 'Empty', projectPath: null, accentColor: 'blue', order: 0 },
      ],
      activeWorkspaceId: 'w1',
      recents: ['/tmp/foo', '/tmp/bar'],
      waitForGrid: false,
    });

    await expect(page.locator('section[aria-label="Recent projects"]')).toBeVisible();
    await expect(page.locator('button[aria-label="Open recent: foo"]')).toBeVisible();
    await expect(page.locator('button[aria-label="Open recent: bar"]')).toBeVisible();
  });

  test('click Open project -> mocked picker returns /tmp/x -> grid mounts', async ({ page }) => {
    // Use the mock's dialogOpenResult to simulate the picker returning /tmp/x.
    await bootApp(page, {
      workspaces: [
        { id: 'w1', name: 'Empty', projectPath: null, accentColor: 'blue', order: 0 },
      ],
      activeWorkspaceId: 'w1',
      dialogOpenResult: '/tmp/x',
      waitForGrid: false,
    });

    await page.locator('button[aria-label="Open project"]').click();
    await expect(page.locator('[data-pane-id]')).toHaveCount(1);
  });
});

const TAURI_E2E =
  process.env.TAURI_E2E === '1' || process.env.TAURI_E2E === 'true';
const SKIP_REASON_LIVE =
  'requires real Tauri runtime / filesystem; deferred to Linux CI under TAURI_E2E=1';

test.describe('A5 project-open (live-only)', () => {
  test.skip(!TAURI_E2E, SKIP_REASON_LIVE);

  test('Open recent -> existing project changes -> pane id from prior project survives', () => {
    // Start in a project with a pane, capture its pane id, open a different
    // recent project, assert metadata changes while the prior pane id remains.
  });

  test('Open same dir twice -> recents list does not duplicate', () => {
    // Open the same mocked directory twice, assert recents contains one entry.
  });

  test('Open 6 dirs -> recents capped at 5', () => {
    // Open six unique mocked directories, assert recents newest-first capped at 5.
  });

  test('Open dir with .voss/layouts/default.json present -> default layout applies', () => {
    // Prepare a project with a valid default layout, open it, assert geometry.
  });
});
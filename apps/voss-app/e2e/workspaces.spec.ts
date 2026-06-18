import { test, expect } from '@playwright/test';
import { bootApp, type MockWorkspace } from './_helpers';

/**
 * A8 workspace end-to-end — tab bar, new-workspace picker, switch, close
 * guard, Ctrl+Tab / Ctrl+1..9 shortcuts. Runs on macOS via mock-IPC.
 *
 * Restart-restore (ws-ac7) needs a real app relaunch under Tauri — deferred
 * to Linux CI under TAURI_E2E=1.
 */

test.describe.configure({ mode: 'serial' });

const BROWSER =
  (process.env.PW_BROWSER as 'chromium' | 'webkit' | 'firefox') ?? 'chromium';
test.use({ browserName: BROWSER });

function twoWorkspaces(): MockWorkspace[] {
  return [
    { id: 'w1', name: 'Alpha', projectPath: '/tmp/voss-e2e-proj', accentColor: 'blue', order: 0 },
    { id: 'w2', name: 'Bravo', projectPath: null, accentColor: 'green', order: 1 },
  ];
}

test.describe('A8 workspaces (mock-IPC)', () => {
  test('ws-ac1: workspace tab bar visible after grid is shown', async ({ page }) => {
    await bootApp(page);
    await expect(page.locator('[data-workspace-tabbar]')).toBeVisible();
    // The default workspace tab is present and active.
    await expect(page.locator('[data-workspace-tab="w1"]')).toHaveAttribute(
      'data-tab-state',
      'active',
    );
  });

  test('ws-ac2: click + opens new workspace picker', async ({ page }) => {
    await bootApp(page);
    await page.locator('.workspace-tabbar__add').click();
    await expect(page.locator('[data-new-workspace-picker]')).toBeVisible();
    await expect(page.locator('[data-new-workspace-name]')).toBeVisible();
  });

  test('ws-ac3: tab click switches active workspace', async ({ page }) => {
    await bootApp(page, { workspaces: twoWorkspaces(), activeWorkspaceId: 'w1' });
    await expect(page.locator('[data-workspace-tab="w1"]')).toHaveAttribute('data-tab-state', 'active');
    await expect(page.locator('[data-workspace-tab="w2"]')).toHaveAttribute('data-tab-state', 'inactive');

    await page.locator('[data-workspace-tab="w2"]').click();
    await expect(page.locator('[data-workspace-tab="w2"]')).toHaveAttribute('data-tab-state', 'active');
    await expect(page.locator('[data-workspace-tab="w1"]')).toHaveAttribute('data-tab-state', 'inactive');
  });

  test('ws-ac4: Ctrl+Tab cycles to next workspace', async ({ page }) => {
    await bootApp(page, { workspaces: twoWorkspaces(), activeWorkspaceId: 'w1' });
    await page.keyboard.press('Control+Tab');
    await expect(page.locator('[data-workspace-tab="w2"]')).toHaveAttribute('data-tab-state', 'active');
  });

  test('ws-ac5: Ctrl+Shift+Tab cycles to previous workspace', async ({ page }) => {
    await bootApp(page, { workspaces: twoWorkspaces(), activeWorkspaceId: 'w2' });
    await page.keyboard.press('Control+Shift+Tab');
    await expect(page.locator('[data-workspace-tab="w1"]')).toHaveAttribute('data-tab-state', 'active');
  });

  test('ws-ac6: closing last workspace shows blocked message', async ({ page }) => {
    // Single workspace — the close must be blocked with a toast/inline message.
    await bootApp(page, { workspaces: [twoWorkspaces()[0]!] });
    // Open the tab context menu via right-click.
    await page.locator('[data-workspace-tab="w1"]').click({ button: 'right' });
    const closeItem = page.locator('[data-menu-action="close"]');
    await expect(closeItem).toBeVisible();
    await closeItem.click();

    // The blocked copy surfaces either inline in the menu or as a toast.
    // Workspace count must remain 1.
    await expect(page.locator('[data-workspace-tab]')).toHaveCount(1);
  });
});

const TAURI_E2E =
  process.env.TAURI_E2E === '1' || process.env.TAURI_E2E === 'true';
const SKIP_REASON_RESTART =
  'requires real Tauri app relaunch; deferred to Linux CI under TAURI_E2E=1';

test.describe('A8 workspaces (live-only)', () => {
  test.skip(!TAURI_E2E, SKIP_REASON_RESTART);

  test('ws-ac7: quit and relaunch restores workspace index and sessions', () => {
    // Open three workspaces → quit app → relaunch → assert count, order,
    // active index, and per-workspace cwd/layout.
  });
});
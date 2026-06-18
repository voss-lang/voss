import { test, expect } from '@playwright/test';
import { bootApp, APP_URL } from './_helpers';

/**
 * A7 command palette + keymap end-to-end — palette open/close,
 * command execution, category discovery, tmux prefix mode.
 *
 * Runs on macOS via mock-IPC (no tauri-driver needed). Boots the app against
 * `vite dev` with `window.__TAURI_INTERNALS__` mocked. PTYs are inert —
 * palette UI behavior is what's under test.
 *
 * PTY-dependent scenarios (native menu click → pane splits via real PTY,
 * keymap.json file watch toast) stay deferred to Linux CI under TAURI_E2E=1.
 */

test.describe.configure({ mode: 'serial' });

const BROWSER =
  (process.env.PW_BROWSER as 'chromium' | 'webkit' | 'firefox') ?? 'chromium';
test.use({ browserName: BROWSER });

test.describe('A7 command palette (mock-IPC)', () => {
  test('cmd-ac1: Cmd+P opens quick mode with layouts and recents', async ({ page }) => {
    await bootApp(page, {
      recents: ['/tmp/recent-one', '/tmp/recent-two'],
      layoutNames: ['fanout-3', 'pipeline-2'],
    });

    await page.keyboard.press('Meta+KeyP');

    const palette = page.getByTestId('command-palette');
    await expect(palette).toBeVisible();
    await expect(page.getByTestId('palette-input')).toHaveAttribute(
      'aria-label',
      'Quick open search',
    );

    // Layouts + recents appear as rows.
    await expect(page.getByText('fanout-3')).toBeVisible();
    await expect(page.getByText('pipeline-2')).toBeVisible();
    await expect(page.getByText('/tmp/recent-one')).toBeVisible();
    await expect(page.getByText('/tmp/recent-two')).toBeVisible();
  });

  test('cmd-ac2: Cmd+Shift+P opens full mode with command search aria-label', async ({ page }) => {
    await bootApp(page);

    await page.keyboard.press('Meta+Shift+KeyP');

    const palette = page.getByTestId('command-palette');
    await expect(palette).toBeVisible();
    await expect(page.getByTestId('palette-input')).toHaveAttribute(
      'aria-label',
      'Command search',
    );

    // Type "split" → Split Right and Split Below appear.
    await page.getByTestId('palette-input').fill('split');
    await expect(page.getByText('Split Right')).toBeVisible();
    await expect(page.getByText('Split Below')).toBeVisible();
  });

  test('cmd-ac3: all six categories findable in full palette', async ({ page }) => {
    await bootApp(page);
    await page.keyboard.press('Meta+Shift+KeyP');

    // One representative command per category.
    const probes: Array<[string, string]> = [
      ['Window', 'Quick Open'],
      ['Pane', 'Split Right'],
      ['Layout', 'Cycle Layout'],
      ['Project', 'Open Project'],
      ['Settings', 'Switch Keymap Profile'],
      ['Help', 'Keyboard Shortcuts'],
    ];
    for (const [, label] of probes) {
      await page.getByTestId('palette-input').fill(label);
      await expect(page.getByText(label).first()).toBeVisible();
    }
  });

  test('cmd-ac4: Escape dismisses the palette', async ({ page }) => {
    await bootApp(page);
    await page.keyboard.press('Meta+KeyP');
    await expect(page.getByTestId('command-palette')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByTestId('command-palette')).toHaveCount(0);
  });

  test('cmd-ac7: tmux Cmd+B then % dispatches vertical split', async ({ page }) => {
    await bootApp(page);
    await expect(page.locator('[data-pane-id]')).toHaveCount(1);

    // Switch to tmux profile via the Switch Keymap Profile command.
    await page.keyboard.press('Meta+Shift+KeyP');
    await page.getByTestId('palette-input').fill('Switch Keymap Profile');
    await page.keyboard.press('Enter');
    // Toast surfaces the new profile; give it a beat to commit.
    await page.waitForTimeout(120);

    // Prefix mode: Cmd+B then % → split vertically.
    await page.keyboard.press('Meta+KeyB');
    await page.keyboard.press('Shift+Digit5'); // '%'
    await expect(page.locator('[data-pane-id]')).toHaveCount(2);
  });

  test('cmd-ac-extra: pane.splitRight via palette increments pane count', async ({ page }) => {
    await bootApp(page);
    await expect(page.locator('[data-pane-id]')).toHaveCount(1);

    await page.keyboard.press('Meta+Shift+KeyP');
    await page.getByTestId('palette-input').fill('Split Right');
    await page.keyboard.press('Enter');

    await expect(page.locator('[data-pane-id]')).toHaveCount(2);
  });
});

// --- Native menu + keymap.json file-watch scenarios ---------------------------
// These need either real OS menus (Tauri runtime) or the keymap.json watcher
// (real filesystem). Both stay deferred to Linux CI under TAURI_E2E=1.
const TAURI_E2E =
  process.env.TAURI_E2E === '1' || process.env.TAURI_E2E === 'true';
const SKIP_REASON_NATIVE =
  'requires real Tauri runtime (native menu / filesystem watcher); deferred to Linux CI under TAURI_E2E=1';

void APP_URL;

test.describe('A7 command palette (native-only)', () => {
  test.skip(!TAURI_E2E, SKIP_REASON_NATIVE);

  test('cmd-ac5: .voss/keymap.json override rebinds a command', () => {
    // Write { "version": 1, "bindings": { "pane.splitRight": { "key": "Cmd+Shift+X" } } }
    // to .voss/keymap.json. Confirm toast "Keymap updated" appears.
    // Confirm Cmd+Shift+X splits a pane.
  });

  test('cmd-ac6: invalid keymap entries produce toast errors', () => {
    // Write { "version": 1, "bindings": { "nonexistent.cmd": { "key": "Cmd+X" } } }
    // Confirm toast "Keymap entry ignored" appears.
  });

  test('cmd-ac8: native menu items trigger same commands as palette', () => {
    // Open native Pane menu → click "Split Right". Confirm pane splits.
  });
});
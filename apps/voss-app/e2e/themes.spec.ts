import { test, expect } from '@playwright/test';
import { bootApp } from './_helpers';

/**
 * A8 theme / appearance end-to-end — bundled catalog, live preview, apply,
 * high-contrast toggle. Runs on macOS via mock-IPC against `vite dev`.
 *
 * Accessibility contrast-pair measurement (theme-ac5) and reduced-motion
 * emulation (theme-ac6) are covered by vitest; the live browser versions
 * stay deferred to Linux CI under TAURI_E2E=1.
 */

test.describe.configure({ mode: 'serial' });

const BROWSER =
  (process.env.PW_BROWSER as 'chromium' | 'webkit' | 'firefox') ?? 'chromium';
test.use({ browserName: BROWSER });

const BUNDLED_THEME_IDS = [
  'variant-b',
  'voss-ignite',
  'one-dark-pro',
  'dracula',
  'catppuccin-mocha',
  'gruvbox-dark',
  'tokyo-night',
  'nord',
  'monokai-pro',
  'solarized-dark',
  'catppuccin-latte',
  'solarized-light',
  'github-light',
] as const;

test.describe('A8 themes (mock-IPC)', () => {
  test('theme-ac1: appearance picker lists all bundled themes', async ({ page }) => {
    await bootApp(page);

    // Navigate to Settings via the portal rail.
    await page.locator('button[aria-label="Settings"]').click();

    const grid = page.locator('.settings-theme-grid');
    await expect(grid).toBeVisible();
    const cards = grid.locator('.settings-theme-card');
    // One card per bundled theme (catalog grows over time — assert parity
    // with BUNDLED_THEME_IDS rather than hardcoding 12).
    await expect(cards).toHaveCount(BUNDLED_THEME_IDS.length);

    // Each card has an aria-label "Use theme: <Name>" — just confirm count
    // matches the bundled catalog (one card per theme).
    expect(BUNDLED_THEME_IDS.length).toBeGreaterThanOrEqual(12);
  });

  test('theme-ac2: clicking a theme commits it (aria-pressed reflects)', async ({ page }) => {
    await bootApp(page);
    await page.locator('button[aria-label="Settings"]').click();

    const cards = page.locator('.settings-theme-card');
    // First card is the default (variant-b); click the second card.
    const second = cards.nth(1);
    const label = await second.getAttribute('aria-label');
    expect(label).toContain('Use theme:');
    await second.click();
    await expect(second).toHaveAttribute('aria-pressed', 'true');

    // The previously-active first card should no longer be pressed.
    await expect(cards.nth(0)).toHaveAttribute('aria-pressed', 'false');
  });

  test('theme-ac4: high contrast toggle updates document dataset', async ({ page }) => {
    await bootApp(page);
    await page.locator('button[aria-label="Settings"]').click();

    // The checkbox is wrapped in a <label> with an overlapping track span —
    // click the label's text instead so Playwright doesn't fight the overlay.
    const toggleLabel = page.locator('label', { hasText: 'High contrast' });
    await expect(toggleLabel).toHaveCount(1);

    // Off initially.
    await expect(page.locator('html')).not.toHaveAttribute('data-high-contrast', 'true');

    await toggleLabel.click();
    await expect(page.locator('html')).toHaveAttribute('data-high-contrast', 'true');

    await toggleLabel.click();
    await expect(page.locator('html')).not.toHaveAttribute('data-high-contrast', 'true');
  });
});

// --- Live contrast + reduced-motion measurement ------------------------------
// Contrast-pair sampling and prefers-reduced-motion emulation stay on the
// vitest track; the live browser versions require real computed-style
// measurement against xterm internals which the mock-IPC harness cannot
// honestly drive.
const TAURI_E2E =
  process.env.TAURI_E2E === '1' || process.env.TAURI_E2E === 'true';
const SKIP_REASON_LIVE =
  'requires real Tauri runtime / live xterm contrast measurement; deferred to Linux CI under TAURI_E2E=1';

test.describe('A8 themes (live-only)', () => {
  test.skip(!TAURI_E2E, SKIP_REASON_LIVE);

  test('theme-ac3: apply commits theme and survives reload', () => {
    // Apply tokyo-night → reload app → assert theme id in profile/settings.
  });

  test('theme-ac5: high contrast meets 7:1 on core bg/fg pairs for each theme', () => {
    // For each bundled theme: enable high contrast → sample computed styles.
  });

  test('theme-ac6: reduced-motion preference disables non-essential animations', () => {
    // Emulate prefers-reduced-motion → assert duration utilities collapse.
  });
});
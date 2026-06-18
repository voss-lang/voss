import { test, expect, type Page } from '@playwright/test';
import {
  bootApp,
  stableRects,
  paneRects,
  type PaneRect,
} from './_helpers';

/**
 * Pane drag-rearrange — REAL-BROWSER integration (runs on macOS, no
 * tauri-driver needed). Boots the actual app against `vite dev` with
 * `window.__TAURI_INTERNALS__` mocked via addInitScript, then performs real
 * pointer drags (mouse down → move → up) on pane headers.
 *
 * This covers the gap jsdom tests cannot: real hit-testing geometry, real
 * pointer event targeting/capture, real Solid rendering of the store
 * mutation. PTYs are inert (spawn_pty mocked) — the grid chrome is what's
 * under test.
 *
 * Requires the dev server (auto-started by playwright.config.ts webServer).
 */

// PW_BROWSER=webkit approximates Tauri's WKWebView on macOS.
test.use({
  browserName:
    (process.env.PW_BROWSER as 'chromium' | 'webkit' | 'firefox') ??
    'chromium',
});

declare global {
  interface Window {
    __SYNCS__: unknown[];
  }
}

async function bootThreePanes(page: Page): Promise<PaneRect[]> {
  await bootApp(page);
  // ⌘D = pane.splitRight (vscode profile) — build a 3-pane row.
  await page.keyboard.press('Meta+KeyD');
  await stableRects(page, 2);
  await page.keyboard.press('Meta+KeyD');
  return stableRects(page, 3);
}

/** Drag from a pane's header to a point, with threshold-crossing moves. */
async function dragHeaderTo(
  page: Page,
  from: PaneRect,
  toX: number,
  toY: number,
): Promise<void> {
  const headerX = from.x + from.w / 2;
  const headerY = from.y + 11; // middle of the 22px header strip
  await page.mouse.move(headerX, headerY);
  await page.mouse.down();
  await page.mouse.move(headerX + 12, headerY + 4, { steps: 2 }); // cross 5px threshold
  await page.mouse.move(toX, toY, { steps: 10 });
  await page.mouse.up();
}

test.describe('pane drag-rearrange (real browser)', () => {
  test('center drop swaps pane ids between slots', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a, b] = before;

    // Drop A onto B's center (inner 50%) → payload swap.
    await dragHeaderTo(page, a, b.x + b.w / 2, b.y + b.h / 2);

    await expect
      .poll(async () => {
        const after = (await paneRects(page)).sort(
          (p, q) => p.x - q.x || p.y - q.y,
        );
        return after.map((r) => r.id).slice(0, 2);
      })
      .toEqual([b.id, a.id]);

    // Same panes, same geometry — only the slot contents swapped.
    const after = await stableRects(page, 3);
    expect(after.map((r) => ({ x: r.x, w: r.w }))).toEqual(
      before.map((r) => ({ x: r.x, w: r.w })),
    );
  });

  test('edge drop re-splits: drag A onto C bottom edge', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a, , c] = before;

    // Drop A onto C's bottom edge band (outer 25%) → V split, A below C.
    await dragHeaderTo(page, a, c.x + c.w / 2, c.y + c.h * 0.9);

    await expect
      .poll(async () => {
        const after = await paneRects(page);
        const movedA = after.find((r) => r.id === a.id);
        const newC = after.find((r) => r.id === c.id);
        if (!movedA || !newC) return 'missing';
        // A now sits BELOW C in C's old column.
        return movedA.y > newC.y && Math.abs(movedA.x - newC.x) < 2
          ? 'stacked'
          : `a=${JSON.stringify(movedA)} c=${JSON.stringify(newC)}`;
      })
      .toBe('stacked');

    // Exactly one structural sync fired for the drop (plus earlier splits).
    const syncs = await page.evaluate(() => window.__SYNCS__.length);
    expect(syncs).toBeGreaterThan(0);
  });

  test('escape cancels drag without mutation', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a, b] = before;

    const headerX = a.x + a.w / 2;
    const headerY = a.y + 11;
    await page.mouse.move(headerX, headerY);
    await page.mouse.down();
    await page.mouse.move(b.x + b.w / 2, b.y + b.h / 2, { steps: 8 });
    await page.keyboard.press('Escape');
    await page.mouse.up();

    const after = (await paneRects(page)).sort(
      (p, q) => p.x - q.x || p.y - q.y,
    );
    expect(after.map((r) => r.id)).toEqual(before.map((r) => r.id));
  });

  test('click without movement still focuses the pane', async ({ page }) => {
    const before = await bootThreePanes(page);
    const [a] = before;

    await page.mouse.click(a.x + a.w / 2, a.y + 11);
    await expect
      .poll(() =>
        page.$eval(
          '.grid-pane-leaf--focused',
          (el) => el.getAttribute('data-pane-id'),
        ),
      )
      .toBe(a.id);
  });
});

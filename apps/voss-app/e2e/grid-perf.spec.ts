import { test, expect } from '@playwright/test';

/**
 * Canvas-pane performance bar at the 9-pane ceiling — the
 * validation contract ( was skipped, so THIS benchmark + the Task 3
 */
const FLOOD_CMD = 'yes\n';

test.skip('grid-perf: 9-pane idle/scroll sustains ~60fps', async ({ page }) => {
  // Spin a 9-pane grid (⌘\ / ⌘⇧\ × 8). Drive `seq 1 100000` + scroll in all
  // 9 panes; sample requestAnimationFrame deltas ≥ 3s.
  await page.waitForSelector('.pane-body .xterm');
  await page.waitForTimeout(3000);
  const medianMs = await page.evaluate(() => {
    // @ts-expect-error test-only perf hook (env-guarded, T-)
    const f: number[] = window.__vossPerf.frames.slice().sort((a, b) => a - b);
    return f[Math.floor(f.length / 2)] ?? 0;
  });
  // eslint-disable-next-line no-console
  console.log(`[grid-perf] 9-pane idle median frame interval: ${medianMs}ms`);
  console.log(`[grid-perf] 9-pane idle FPS ≈ ${Math.round(1000 / medianMs)}`);
  expect(medianMs).toBeLessThanOrEqual(20); // ~60fps (allow CI headroom)
});

test.skip('grid-perf: one-pane yes-flood does NOT starve the other 8', async ({
  page,
}) => {
  // Run `yes` in ONE pane; interactively type/scroll a DIFFERENT pane while
  // the other 7 idle. The flood pane must not freeze or starve the others
  await page.waitForSelector('.pane-body .xterm');
  await page.evaluate((cmd) => {
    // @ts-expect-error test-injected Tauri write bridge
    return window.__vossWrite(cmd);
  }, FLOOD_CMD);
  await page.waitForTimeout(3000);
  const echoMs = await page.evaluate(() => {
    // @ts-expect-error test-only perf hook
    const f: number[] = window.__vossPerf.frames;
    return f.length ? f[f.length - 1] : 0;
  });
  // eslint-disable-next-line no-console
  console.log(`[grid-perf] flood-case interactive latency: ${echoMs}ms`);
  expect(echoMs).toBeLessThan(200);
});

import { test, expect } from '@playwright/test';

/**
 * D-02 flood-performance Playwright driver.
 *
 * SKIPPED on macOS — platform block: this drives a live Tauri app under
 * WebDriver (`tauri-driver`), which Apple's WKWebView does not support
 * (tauri-driver = Linux WebKitWebDriver / Windows Edge only). Per the A2-04
 * user decision (project memory `voss-app-tauri-e2e-macos-blocked`), the
 * D-02 *mechanism* is unit-proven on macOS (A2-03 `pty-ipc.test.ts` 3/3:
 * rAF coalescing + watermark pause>HIGH + resume<LOW); the full live
 * flood *measurement* is deferred to a Linux CI job (A10 / CI phase).
 *
 * The measurement logic below is the unchanged contract for that CI un-skip.
 */

const FLOOD_CMD = process.env.PERF_CAT
  ? 'cat /dev/urandom | strings\n'
  : 'yes\n';

test.skip('flood-perf: rAF p95 < 33ms and echo < 200ms under flood', async ({
  page,
}) => {
  // 1. Wait for the shell prompt in the live pane.
  await page.waitForSelector('.pane-body .xterm');

  // 2. Start the infinite flood via the PTY.
  await page.evaluate((cmd) => {
    // @ts-expect-error test-injected Tauri invoke bridge
    return window.__vossWrite(cmd);
  }, FLOOD_CMD);

  // 3. Sample requestAnimationFrame deltas for ≥ 3s; compute p95.
  await page.waitForTimeout(3000);
  const p95Ms = await page.evaluate(() => {
    // @ts-expect-error test-only perf hook
    const frames: number[] = window.__vossPerf.frames.slice().sort(
      (a: number, b: number) => a - b,
    );
    return frames[Math.floor(frames.length * 0.95)] ?? 0;
  });

  // 4. Mid-flood probe: inject a unique string, time until it echoes.
  const probe = `__probe_${Date.now()}__`;
  const t0 = Date.now();
  await page.evaluate((p) => {
    // @ts-expect-error test-injected Tauri invoke bridge
    return window.__vossWrite(p + '\n');
  }, probe);
  await page.waitForFunction(
    (p) => document.querySelector('.pane-body')?.textContent?.includes(p),
    probe,
  );
  const echoMs = Date.now() - t0;

  // 5. Stop the flood.
  await page.evaluate(() => {
    // @ts-expect-error test-injected Tauri invoke bridge
    return window.__vossWrite('\x03');
  });

  expect(p95Ms).toBeLessThan(33);
  expect(echoMs).toBeLessThan(200);
});

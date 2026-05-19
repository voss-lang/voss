/**
 * D-02 flood-performance assertion harness.
 *
 * Contract (A2-RESEARCH / A2-VALIDATION): while `yes` OR
 * `cat /dev/urandom | strings` floods the PTY, the measured
 * requestAnimationFrame p95 delta must be < 33ms AND a keystroke injected
 * mid-flood must echo back in < 200ms. Both `yes` and `--cat` modes must pass
 * (the `cat /dev/urandom` mode is the one that fails if watermark
 * backpressure is missing).
 *
 * Execution model: this script drives the Playwright perf spec
 * (`e2e/flood-perf.spec.ts`) against a live Tauri app, reads back
 * `{ p95Ms, echoMs }`, and asserts the thresholds — failing the build
 * (process.exit(1)) on violation.
 *
 * PLATFORM NOTE (project memory `voss-app-tauri-e2e-macos-blocked`): Tauri
 * WebDriver is unavailable on macOS (no WKWebView WebDriver). On macOS this
 * script DEFERS the live measurement (exit 0 with a DEFERRED notice) — it is
 * NOT a silent pass-mask: the assertion code path below is real and runs on
 * Linux CI, and the D-02 *mechanism* is unit-proven on macOS by
 * `src/pane/__tests__/pty-ipc.test.ts` (coalescing + watermark pause/resume).
 */

import { spawnSync } from 'node:child_process';

const P95_MAX_MS = 33;
const ECHO_MAX_MS = 200;

interface PerfResult {
  p95Ms: number;
  echoMs: number;
}

function isCat(argv: string[]): boolean {
  return argv.includes('--cat') || !!process.env.PERF_CAT;
}

/** Linux CI path: run the Playwright perf spec and parse {p95Ms, echoMs}. */
function runLivePerf(cat: boolean): PerfResult {
  const res = spawnSync(
    'pnpm',
    ['playwright', 'test', 'flood-perf', '--reporter=json'],
    {
      cwd: process.cwd(),
      env: { ...process.env, PERF_CAT: cat ? '1' : '' },
      encoding: 'utf8',
    },
  );
  // The spec reports {p95Ms, echoMs} via test annotations / stdout JSON.
  const m = res.stdout.match(/"p95Ms"\s*:\s*([\d.]+).*?"echoMs"\s*:\s*([\d.]+)/s);
  if (!m) {
    console.error('flood-perf: could not parse Playwright perf output');
    process.exit(1);
  }
  return { p95Ms: Number(m[1]), echoMs: Number(m[2]) };
}

function assertThresholds(r: PerfResult): void {
  const ok = r.p95Ms < P95_MAX_MS && r.echoMs < ECHO_MAX_MS;
  if (!ok) {
    console.error(
      `D-02 FAIL p95=${r.p95Ms}ms (<${P95_MAX_MS}) echo=${r.echoMs}ms (<${ECHO_MAX_MS})`,
    );
    process.exit(1);
  }
  console.log(`D-02 PASS p95=${r.p95Ms}ms echo=${r.echoMs}ms`);
}

function main(): void {
  const cat = isCat(process.argv.slice(2));
  const mode = cat ? 'cat /dev/urandom | strings' : 'yes';

  if (process.platform === 'darwin') {
    console.log(
      `D-02 DEFERRED [${mode}] — Tauri WebDriver unavailable on macOS. ` +
        `Mechanism unit-proven (src/pane/__tests__/pty-ipc.test.ts: rAF ` +
        `coalescing + watermark pause>100k/resume<10k). Live p95<${P95_MAX_MS}ms ` +
        `/ echo<${ECHO_MAX_MS}ms measurement deferred to Linux CI ` +
        `(see memory voss-app-tauri-e2e-macos-blocked).`,
    );
    process.exit(0);
  }

  // Linux/Windows CI: real measurement + build-failing assertion.
  assertThresholds(runLivePerf(cat));
}

main();

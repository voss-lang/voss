import { test } from '@playwright/test';

/**
 * PTY end-to-end specs (PTY-03/04/05/06/07).
 *
 * SKIPPED — platform block: these require a running Tauri app under WebDriver
 * (`tauri-driver`). Tauri WebDriver is supported only on Linux
 * (WebKitWebDriver) and Windows (Edge driver); Apple ships NO WKWebView
 * WebDriver, so Tauri E2E cannot run on the macOS dev machine (A1 platform).
 *
 * User decision (2026-05-19, A2-04): implement all interaction code, gate on
 * what IS runnable on macOS (Vitest + cargo test + tsc), and defer real E2E
 * to a future Linux CI job (candidate: A10 / a dedicated CI phase). The
 * interaction logic is still verified via Vitest unit tests + tsc; only the
 * full browser-integration layer is deferred. See project memory
 * `voss-app-tauri-e2e-macos-blocked`.
 *
 * Each spec retains its name + the assertion intent (as comments) so the
 * Linux CI job can un-skip and implement against an unchanged contract.
 */
const SKIP_REASON =
  'Tauri WebDriver unsupported on macOS — deferred to Linux CI (A10/future)';

test.skip('pty-scrollback', () => {
  // PTY-03: fill 10k lines, ⌘F, assert match on line ~9999. (Linux CI)
});

test.skip('pty-clear', () => {
  // PTY-03: ⌘⇧K → scrollback buffer empty. (Linux CI)
});

test.skip('pty-copy', () => {
  // PTY-04: select text → ⌘C → clipboard contains selection. (Linux CI)
});

test.skip('pty-sigint', () => {
  // PTY-04: run `sleep 999`, ⌘C with no selection → `^C` echoed. (Linux CI)
});

test.skip('pty-osc8', () => {
  // PTY-05: emit OSC 8, ⌘+click → mocked open_url invoked. (Linux CI)
});

test.skip('pty-title', () => {
  // PTY-06: `printf '\\033]0;vim\\007'` → header process slot shows `vim`. (Linux CI)
});

test.skip('pty-exit-restart', () => {
  // PTY-07: `exit 0` → `[exited 0]` banner → Restart → fresh prompt,
  // scrollback preserved. (Linux CI)
});

// Reference the reason so it is not an unused-symbol lint failure and is
// greppable in CI logs when these are un-skipped.
void SKIP_REASON;

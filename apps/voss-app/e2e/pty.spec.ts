import { test } from '@playwright/test';

/**
 * PTY end-to-end specs (PTY-03/04/05/06/07)
 * SKIPPED — platform block: these require a running Tauri app under WebDriver
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

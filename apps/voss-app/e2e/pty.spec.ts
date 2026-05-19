import { test, expect } from '@playwright/test';

/**
 * RED scaffolds for the PTY end-to-end requirements. Each test name matches the
 * exact command string A2-VALIDATION.md greps for. All currently fail (never
 * skipped) so every PTY-0N requirement has a discoverable failing command
 * before A2-02..05 implement against it.
 */

test('pty-scrollback', async () => {
  // RED: PTY-03 — A2-03 (scrollback buffer retains N lines, scroll up works)
  expect(false).toBeTruthy();
});

test('pty-clear', async () => {
  // RED: PTY-03 — A2-03 (clear / ⌘K resets the viewport + scrollback)
  expect(false).toBeTruthy();
});

test('pty-copy', async () => {
  // RED: PTY-05 — A2-04 (selection → clipboard copy)
  expect(false).toBeTruthy();
});

test('pty-sigint', async () => {
  // RED: PTY-06 — A2-02 (Ctrl-C SIGINTs the foreground child, not the shell)
  expect(false).toBeTruthy();
});

test('pty-osc8', async () => {
  // RED: PTY-07 — A2-04 (OSC 8 hyperlinks are clickable via web-links addon)
  expect(false).toBeTruthy();
});

test('pty-title', async () => {
  // RED: PTY-08 — A2-03 (OSC 0/2 title escape updates the pane title)
  expect(false).toBeTruthy();
});

test('pty-exit-restart', async () => {
  // RED: PTY-08 — A2-05 (shell exit shows ExitBanner; restart respawns PTY)
  expect(false).toBeTruthy();
});

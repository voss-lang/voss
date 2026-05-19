import { describe, it, expect } from 'vitest';

/**
 * RED scaffold for PTY-04 (paste-guard banner + bypass) — owned by A2-04.
 *
 * Documented target interface (A2-PATTERNS.md §PasteGuard.tsx):
 *
 *   interface PasteGuardProps {
 *     text: string;                 // pending clipboard payload
 *     onConfirm: (text: string) => void;
 *     onCancel: () => void;
 *     bypass?: boolean;             // ⌘⇧V / Win+Shift+V skips the banner
 *   }
 *
 * The real <PasteGuard/> component does not exist yet. These tests assert the
 * behaviour A2-04 must satisfy; they are intentionally RED (not skipped) so the
 * Nyquist contract has a discoverable failing command for PTY-04.
 *
 * NOTE: the component is deliberately NOT imported — importing a non-existent
 * module would crash collection ("no tests found") instead of producing a clean
 * red test. A2-04 replaces the `expect(false)` lines with real assertions.
 */
describe('PasteGuard (PTY-04)', () => {
  it('multi-line paste shows the confirmation banner', () => {
    // RED: PTY-04 — A2-04 (multi-line clipboard payload must raise the banner)
    expect(false).toBe(true);
  });

  it('⌘⇧V (Win+Shift+V) bypasses the banner', () => {
    // RED: PTY-04 — A2-04 (bypass prop / chord pastes directly, no banner)
    expect(false).toBe(true);
  });
});

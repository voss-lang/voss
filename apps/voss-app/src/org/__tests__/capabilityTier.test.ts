import { describe, it, expect } from 'vitest';
import { resolveTier, hookCapableCli } from '../capabilityTier';

// VCKP-13 (D-13): honest A/B/C capability tiers. A = per-tool gate + sandbox +
// budget; B = sandbox + budget; C = observe-only. Adopt is ALWAYS C.

describe('resolveTier — honest capability tiers (VCKP-13)', () => {
  it('a non-hook managed CLI resolves to tier B (sandbox + budget, no per-tool prompt, no error)', () => {
    expect(
      resolveTier({ cli: 'gemini', managed: true, hookCapable: false, adopted: false }),
    ).toBe('B');
  });

  it('a hook-capable managed CLI resolves to tier A (per-tool gate + sandbox + budget)', () => {
    expect(
      resolveTier({ cli: 'claude', managed: true, hookCapable: true, adopted: false }),
    ).toBe('A');
  });

  it('an adopted running agent resolves to tier C', () => {
    expect(
      resolveTier({ cli: 'claude', managed: true, hookCapable: true, adopted: true }),
    ).toBe('C');
  });

  it('an unmanaged spawn resolves to tier C (observe-only)', () => {
    expect(
      resolveTier({ cli: 'claude', managed: false, hookCapable: false, adopted: false }),
    ).toBe('C');
  });

  it('NEVER returns A for an adopted agent (no retro-sandbox), whatever the other flags', () => {
    for (const managed of [true, false]) {
      for (const hookCapable of [true, false]) {
        for (const cli of ['claude', 'codex', 'gemini', 'opencode', 'aider', 'bash']) {
          expect(resolveTier({ cli, managed, hookCapable, adopted: true })).toBe('C');
        }
      }
    }
  });

  it('hookCapableCli is false for every CLI until the permission proxy ships (no overclaim)', () => {
    for (const cli of ['claude', 'codex', 'gemini', 'opencode', 'aider']) {
      expect(hookCapableCli(cli)).toBe(false);
    }
  });
});

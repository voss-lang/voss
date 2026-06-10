/**
 * V17-04 (VBUS-03): slug minting + registry — D-12 format (<cli>-<n> for
 * agent CLIs, pane-<n> for plain shells), shared monotonic counter.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  mintSlug,
  registerSlug,
  unregisterSlug,
  slugByPaneId,
  __resetSlugs,
} from '../slugRegistry';

describe('slugRegistry', () => {
  beforeEach(() => {
    __resetSlugs();
  });

  it('mints <cli>-<n> for repeated agent CLIs', () => {
    expect(mintSlug('claude')).toBe('claude-1');
    expect(mintSlug('claude')).toBe('claude-2');
  });

  it('uses the lowercased basename of an agent CLI path', () => {
    expect(mintSlug('/usr/local/bin/codex')).toBe('codex-1');
  });

  it('mints pane-<n> for a non-agent CLI', () => {
    expect(mintSlug('bash')).toBe('pane-1');
  });

  it('mints pane-<n> for a plain shell (undefined)', () => {
    expect(mintSlug('bash')).toBe('pane-1');
    expect(mintSlug(undefined)).toBe('pane-2');
  });

  it('registers and reads back a slug by paneId', () => {
    registerSlug('pane-id-1', 'claude-1');
    expect(slugByPaneId()['pane-id-1']).toBe('claude-1');
  });

  it('unregisters a slug', () => {
    registerSlug('pane-id-1', 'claude-1');
    unregisterSlug('pane-id-1');
    expect(slugByPaneId()['pane-id-1']).toBeUndefined();
  });

  it('__resetSlugs clears registry and counter', () => {
    mintSlug('claude');
    registerSlug('p', 'claude-1');
    __resetSlugs();
    expect(slugByPaneId()).toEqual({});
    expect(mintSlug('claude')).toBe('claude-1');
  });
});

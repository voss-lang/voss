import { beforeEach, describe, expect, it, vi } from 'vitest';

const h = vi.hoisted(() => ({
  platform: vi.fn(),
  setEffects: vi.fn(),
  clearEffects: vi.fn(),
}));

vi.mock('@tauri-apps/plugin-os', () => ({ platform: h.platform }));
vi.mock('@tauri-apps/api/window', () => ({
  getCurrentWindow: () => ({
    setEffects: h.setEffects,
    clearEffects: h.clearEffects,
  }),
}));

import {
  LINUX_CSS_OPACITY_ONLY,
  _resetWindowEffectsForTest,
  applyWindowEffects,
  clearWindowEffects,
  detectPlatform,
} from '../windowEffects';

describe('windowEffects — platform detection', () => {
  beforeEach(() => {
    _resetWindowEffectsForTest();
    h.platform.mockReset();
    h.setEffects.mockReset();
    h.clearEffects.mockReset();
    document.documentElement.removeAttribute('style');
    document.body.removeAttribute('style');
  });

  it('exports LINUX_CSS_OPACITY_ONLY for Linux gating', () => {
    expect(LINUX_CSS_OPACITY_ONLY).toBe(true);
  });

  it('detectPlatform falls back to navigator when plugin is unavailable', () => {
    expect(detectPlatform()).toBeTypeOf('string');
  });
});

describe('windowEffects — Linux CSS-only path', () => {
  beforeEach(() => {
    _resetWindowEffectsForTest();
    h.platform.mockResolvedValue('linux');
    h.setEffects.mockReset();
    h.clearEffects.mockReset();
    document.documentElement.removeAttribute('style');
    document.body.removeAttribute('style');
  });

  it('sets CSS var only and does not call setEffects', async () => {
    await applyWindowEffects({ opacity: 0.75, enabled: true });

    expect(h.setEffects).not.toHaveBeenCalled();
    expect(
      document.documentElement.style.getPropertyValue('--window-opacity-bg'),
    ).toContain('color-mix');
    expect(document.documentElement.style.background).toBe(
      'var(--window-opacity-bg)',
    );
  });
});

describe('windowEffects — unsupported platform no-op', () => {
  beforeEach(() => {
    _resetWindowEffectsForTest();
    h.platform.mockResolvedValue('freebsd');
    h.setEffects.mockReset();
    document.documentElement.removeAttribute('style');
    document.body.removeAttribute('style');
  });

  it('does not throw and skips native effects', async () => {
    await expect(
      applyWindowEffects({ opacity: 0.8, enabled: true }),
    ).resolves.toBeUndefined();
    expect(h.setEffects).not.toHaveBeenCalled();
  });
});

describe('windowEffects — macOS / Windows fail soft', () => {
  beforeEach(() => {
    _resetWindowEffectsForTest();
    h.setEffects.mockReset();
    h.clearEffects.mockReset();
    document.documentElement.removeAttribute('style');
    document.body.removeAttribute('style');
  });

  it('macOS setEffects rejection does not throw', async () => {
    h.platform.mockResolvedValue('macos');
    h.setEffects.mockRejectedValueOnce(new Error('effects unsupported'));

    await expect(
      applyWindowEffects({ opacity: 0.85, enabled: true }),
    ).resolves.toBeUndefined();
    expect(h.setEffects).toHaveBeenCalledWith({
      effects: ['underWindowBackground'],
    });
  });

  it('Windows setEffects rejection does not throw', async () => {
    h.platform.mockResolvedValue('windows');
    h.setEffects.mockRejectedValueOnce(new Error('tabbed unavailable'));

    await expect(
      applyWindowEffects({ opacity: 0.9, enabled: true }),
    ).resolves.toBeUndefined();
    expect(h.setEffects).toHaveBeenCalledWith({ effects: ['tabbed'] });
  });
});

describe('windowEffects — clear', () => {
  beforeEach(() => {
    _resetWindowEffectsForTest();
    h.platform.mockResolvedValue('linux');
    h.clearEffects.mockResolvedValue(undefined);
    document.documentElement.removeAttribute('style');
    document.body.removeAttribute('style');
  });

  it('resets opaque CSS backgrounds', async () => {
    await applyWindowEffects({ opacity: 0.7, enabled: true });
    await clearWindowEffects();

    expect(document.documentElement.style.background).toBe('var(--bg-0)');
    expect(document.body.style.background).toBe('var(--bg-0)');
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
}));

vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import { getBundledTheme, resolveThemeCssVars } from '../../themes/themeCatalog';
import { contrastRatio } from '../../themes/schema';
import { HIGH_CONTRAST_OVERLAY } from '../../themes/highContrast';
import {
  _resetForTest,
  applyAppearanceToAllTerminals,
  registerTerminal,
} from '../../themes/themeRuntime';
import {
  _resetAppearanceForTest,
  applyAppearanceSettings,
  clampFontSize,
  parseAppearanceSettings,
  saveAppearanceSettings,
  loadAppearanceSettings,
  DEFAULT_APPEARANCE_SETTINGS,
  MIN_FONT_SIZE,
} from '../settings';

describe('appearance settings — clamp and parse', () => {
  beforeEach(() => {
    _resetAppearanceForTest();
    _resetForTest();
  });

  it('clamps font size 9 to MIN_FONT_SIZE 10', () => {
    expect(clampFontSize(9)).toBe(10);
    expect(MIN_FONT_SIZE).toBe(10);
  });

  it('accepts only block/bar/underline cursor shapes', () => {
    expect(parseAppearanceSettings({ cursorShape: 'block' }).cursorShape).toBe(
      'block',
    );
    expect(parseAppearanceSettings({ cursorShape: 'bar' }).cursorShape).toBe(
      'bar',
    );
    expect(parseAppearanceSettings({ cursorShape: 'underline' }).cursorShape).toBe(
      'underline',
    );
    expect(parseAppearanceSettings({ cursorShape: 'crosshair' }).cursorShape).toBe(
      'block',
    );
  });

  it('accepts only off/slow/fast cursor blink values', () => {
    expect(parseAppearanceSettings({ cursorBlink: 'off' }).cursorBlink).toBe(
      'off',
    );
    expect(parseAppearanceSettings({ cursorBlink: 'slow' }).cursorBlink).toBe(
      'slow',
    );
    expect(parseAppearanceSettings({ cursorBlink: 'fast' }).cursorBlink).toBe(
      'fast',
    );
    expect(parseAppearanceSettings({ cursorBlink: 'medium' }).cursorBlink).toBe(
      'fast',
    );
  });

  it('validates bell behavior enum', () => {
    for (const behavior of ['visual', 'audible', 'none', 'badge'] as const) {
      expect(parseAppearanceSettings({ bellBehavior: behavior }).bellBehavior).toBe(
        behavior,
      );
    }
    expect(parseAppearanceSettings({ bellBehavior: 'ring' }).bellBehavior).toBe(
      'visual',
    );
  });
});

describe('appearance settings — high contrast runtime', () => {
  beforeEach(() => {
    _resetAppearanceForTest();
    _resetForTest();
    document.documentElement.removeAttribute('style');
    document.documentElement.classList.remove('reduced-motion');
  });

  it('applyAppearanceSettings toggles high-contrast overlay on theme runtime', () => {
    applyAppearanceSettings({
      ...DEFAULT_APPEARANCE_SETTINGS,
      highContrastEnabled: true,
    });
    expect(document.documentElement.dataset.highContrast).toBe('true');
    expect(document.documentElement.style.getPropertyValue('--bg-0')).toBe(
      HIGH_CONTRAST_OVERLAY['--bg-0'],
    );
  });

  it('high-contrast core bg/fg pairs meet 7:1 contrast', () => {
    const theme = getBundledTheme('github-light')!;
    const resolved = resolveThemeCssVars(theme, true);
    const pairs: [string, string][] = [
      ['--bg-0', '--fg-0'],
      ['--bg-1', '--fg-0'],
      ['--bg-2', '--fg-1'],
      ['--bg-3', '--fg-2'],
    ];
    for (const [bg, fg] of pairs) {
      const ratio = contrastRatio(resolved[bg], resolved[fg]);
      expect(ratio, `${bg} vs ${fg}`).toBeGreaterThanOrEqual(7);
    }
  });

  it('reduced motion adds html.reduced-motion class', () => {
    applyAppearanceSettings({
      ...DEFAULT_APPEARANCE_SETTINGS,
      reducedMotionEnabled: true,
    });
    expect(document.documentElement.classList.contains('reduced-motion')).toBe(
      true,
    );
  });
});

describe('appearance settings — terminal broadcast', () => {
  beforeEach(() => {
    _resetAppearanceForTest();
    _resetForTest();
  });

  it('applyAppearanceSettings updates registered terminal font options', () => {
    const mockTerm = {
      options: {
        theme: {},
        fontFamily: '',
        fontSize: 0,
        lineHeight: 0,
        letterSpacing: 0,
        customGlyphs: false,
        cursorStyle: 'block',
        cursorBlink: true,
      },
    };
    registerTerminal('pane-1', mockTerm as never);

    applyAppearanceSettings({
      ...DEFAULT_APPEARANCE_SETTINGS,
      fontFamily: 'Fira Code',
      fontSize: 14,
      cursorShape: 'bar',
      cursorBlink: 'off',
    });

    expect(mockTerm.options.fontSize).toBe(14);
    expect(mockTerm.options.fontFamily).toContain('Fira Code');
    expect(mockTerm.options.cursorStyle).toBe('bar');
    expect(mockTerm.options.cursorBlink).toBe(false);
  });
});

describe('appearance settings — invoke bridges', () => {
  beforeEach(() => {
    h.invoke.mockReset();
    _resetAppearanceForTest();
  });

  it('loadAppearanceSettings invokes load_appearance_settings', async () => {
    h.invoke.mockResolvedValueOnce({ fontSize: 12, cursorShape: 'underline' });
    const settings = await loadAppearanceSettings();
    expect(h.invoke).toHaveBeenCalledWith('load_appearance_settings');
    expect(settings.fontSize).toBe(12);
    expect(settings.cursorShape).toBe('underline');
  });

  it('saveAppearanceSettings invokes save_appearance_settings', async () => {
    h.invoke.mockResolvedValueOnce(undefined);
    await saveAppearanceSettings({
      ...DEFAULT_APPEARANCE_SETTINGS,
      fontSize: 11,
    });
    expect(h.invoke).toHaveBeenCalledWith('save_appearance_settings', {
      settings: expect.objectContaining({ fontSize: 11 }),
    });
  });
});

describe('appearance settings — applyAppearanceToAllTerminals direct', () => {
  it('updates cursor shape on registered terminals', () => {
    _resetForTest();
    const mockTerm = {
      options: {
        theme: {},
        fontFamily: '',
        fontSize: 13,
        lineHeight: 1.5,
        letterSpacing: 0,
        customGlyphs: false,
        cursorStyle: 'block',
        cursorBlink: true,
      },
    };
    registerTerminal('p1', mockTerm as never);
    applyAppearanceToAllTerminals({
      ...DEFAULT_APPEARANCE_SETTINGS,
      cursorShape: 'underline',
    });
    expect(mockTerm.options.cursorStyle).toBe('underline');
  });
});

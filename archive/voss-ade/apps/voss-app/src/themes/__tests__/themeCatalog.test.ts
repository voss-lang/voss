import { describe, it, expect } from 'vitest';
import {
  BUNDLED_THEME_IDS,
  listBundledThemes,
  getBundledTheme,
  resolveThemeCssVars,
  validateTheme,
} from '../themeCatalog';
import { contrastRatio } from '../schema';
import { HIGH_CONTRAST_OVERLAY } from '../highContrast';

const EXPECTED_IDS = [
  'voss-ignite',
  'variant-b',
  'one-dark-pro',
  'dracula',
  'catppuccin-mocha',
  'gruvbox-dark',
  'tokyo-night',
  'nord',
  'monokai-pro',
  'solarized-dark',
  'catppuccin-latte',
  'solarized-light',
  'github-light',
] as const;

describe('theme catalog', () => {
  it('exposes exactly 13 bundled theme IDs in UI-SPEC order', () => {
    expect(BUNDLED_THEME_IDS).toEqual([...EXPECTED_IDS]);
    expect(listBundledThemes()).toHaveLength(13);
    expect(listBundledThemes().map((t) => t.id)).toEqual([...EXPECTED_IDS]);
  });

  it('every bundled theme validates', () => {
    for (const id of BUNDLED_THEME_IDS) {
      const theme = getBundledTheme(id);
      expect(theme, `missing bundled theme ${id}`).toBeDefined();
      const result = validateTheme(theme!);
      expect(result.ok, `${id}: ${!result.ok ? result.error : ''}`).toBe(true);
    }
  });

  it('variant-b bundled JSON matches variant-b.css default tokens', () => {
    const theme = getBundledTheme('variant-b')!;
    expect(theme.name).toBe('Variant B');
    expect(theme.appearance).toBe('dark');
    expect(theme.cssVars['--bg-0']).toBe('#0a0b0e');
    expect(theme.cssVars['--bg-1']).toBe('#11131a');
    expect(theme.cssVars['--bg-2']).toBe('#171a23');
    expect(theme.cssVars['--bg-3']).toBe('#1f232e');
    expect(theme.cssVars['--border']).toBe('#262b38');
    expect(theme.cssVars['--border-bright']).toBe('#353b4a');
    expect(theme.cssVars['--focus']).toBe('#5a7cff');
    expect(theme.cssVars['--focus-glow']).toBe('rgba(90, 124, 255, 0.18)');
    expect(theme.cssVars['--fg-0']).toBe('#e8eaf0');
    expect(theme.cssVars['--fg-1']).toBe('#aab0c0');
    expect(theme.cssVars['--fg-2']).toBe('#6a7080');
    expect(theme.cssVars['--fg-3']).toBe('#444a5a');
    expect(theme.cssVars['--accent-green']).toBe('#6fd28f');
    expect(theme.cssVars['--accent-amber']).toBe('#e8b86c');
    expect(theme.cssVars['--accent-red']).toBe('#e87b7b');
    expect(theme.cssVars['--accent-cyan']).toBe('#6cc7d4');
    expect(theme.cssVars['--accent-magenta']).toBe('#c084d4');
    expect(theme.cssVars['--accent-blue']).toBe('#7aa2ff');
  });

  it('resolveThemeCssVars maps ansi[0..15] to --ansi-0..15', () => {
    const theme = getBundledTheme('dracula')!;
    const resolved = resolveThemeCssVars(theme, false);
    for (let i = 0; i < 16; i++) {
      expect(resolved[`--ansi-${i}`]).toBe(theme.ansi[i]);
    }
  });

  it('high-contrast overlay applies after theme and overrides core tokens', () => {
    const theme = getBundledTheme('nord')!;
    const base = resolveThemeCssVars(theme, false);
    const hc = resolveThemeCssVars(theme, true);
    expect(hc['--bg-0']).toBe(HIGH_CONTRAST_OVERLAY['--bg-0']);
    expect(hc['--fg-0']).toBe(HIGH_CONTRAST_OVERLAY['--fg-0']);
    expect(hc['--focus']).toBe(HIGH_CONTRAST_OVERLAY['--focus']);
    expect(base['--bg-0']).not.toBe(hc['--bg-0']);
    // Non-overlay keys remain from theme
    expect(hc['--accent-green']).toBe(base['--accent-green']);
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

  it('light bundled themes declare appearance light', () => {
    for (const id of ['catppuccin-latte', 'solarized-light', 'github-light'] as const) {
      expect(getBundledTheme(id)?.appearance).toBe('light');
    }
  });

  it('getBundledTheme returns undefined for unknown id', () => {
    expect(getBundledTheme('vscode-import')).toBeUndefined();
  });
});

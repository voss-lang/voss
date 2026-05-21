import { describe, it, expect } from 'vitest';
import {
  REQUIRED_CSS_VARS,
  validateTheme,
  contrastRatio,
  type Theme,
} from '../schema';

const minimalTheme = (): Theme => ({
  id: 'test',
  name: 'Test',
  appearance: 'dark',
  cssVars: Object.fromEntries(REQUIRED_CSS_VARS.map((k) => [k, '#101010'])) as Theme['cssVars'],
  ansi: Array.from({ length: 16 }, (_, i) =>
    i < 8 ? '#101010' : '#eeeeee',
  ),
});

describe('theme schema', () => {
  it('exports all required CSS var keys', () => {
    expect(REQUIRED_CSS_VARS).toContain('--bg-0');
    expect(REQUIRED_CSS_VARS).toContain('--window-opacity-bg');
    expect(REQUIRED_CSS_VARS).toHaveLength(28);
  });

  it('validateTheme accepts a complete theme', () => {
    expect(validateTheme(minimalTheme())).toEqual({ ok: true });
  });

  it('validateTheme rejects missing required cssVars', () => {
    const theme = minimalTheme();
    delete (theme.cssVars as Record<string, string>)['--bg-0'];
    const result = validateTheme(theme);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toContain('--bg-0');
  });

  it('validateTheme rejects ansi arrays that are not length 16', () => {
    const theme = minimalTheme();
    theme.ansi = theme.ansi.slice(0, 15);
    const result = validateTheme(theme);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/ansi/i);
  });

  it('validateTheme rejects tokenColors field (no VSCode import path)', () => {
    const theme = { ...minimalTheme(), tokenColors: [] } as Theme & { tokenColors: unknown[] };
    const result = validateTheme(theme);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/tokenColors/i);
  });

  it('validateTheme rejects invalid appearance', () => {
    const theme = { ...minimalTheme(), appearance: 'auto' as 'dark' };
    const result = validateTheme(theme);
    expect(result.ok).toBe(false);
  });

  it('contrastRatio computes WCAG ratio for black on white', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 0);
  });
});

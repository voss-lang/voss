import { HIGH_CONTRAST_OVERLAY } from './highContrast';
import { validateTheme, type Theme } from './schema';

import variantB from './bundled/variant-b.json';
import oneDarkPro from './bundled/one-dark-pro.json';
import dracula from './bundled/dracula.json';
import catppuccinMocha from './bundled/catppuccin-mocha.json';
import gruvboxDark from './bundled/gruvbox-dark.json';
import tokyoNight from './bundled/tokyo-night.json';
import nord from './bundled/nord.json';
import monokaiPro from './bundled/monokai-pro.json';
import solarizedDark from './bundled/solarized-dark.json';
import catppuccinLatte from './bundled/catppuccin-latte.json';
import solarizedLight from './bundled/solarized-light.json';
import githubLight from './bundled/github-light.json';

export { validateTheme } from './schema';
export type { Theme, ThemeAppearance, ThemeValidationResult } from './schema';
export { HIGH_CONTRAST_OVERLAY } from './highContrast';
export { contrastRatio } from './schema';

/** Curated bundled theme IDs (A8 UI-SPEC — exactly 12, no VSCode import). */
export const BUNDLED_THEME_IDS = [
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

export type BundledThemeId = (typeof BUNDLED_THEME_IDS)[number];

const BUNDLED_BY_ID: Record<BundledThemeId, Theme> = {
  'variant-b': variantB as Theme,
  'one-dark-pro': oneDarkPro as Theme,
  dracula: dracula as Theme,
  'catppuccin-mocha': catppuccinMocha as Theme,
  'gruvbox-dark': gruvboxDark as Theme,
  'tokyo-night': tokyoNight as Theme,
  nord: nord as Theme,
  'monokai-pro': monokaiPro as Theme,
  'solarized-dark': solarizedDark as Theme,
  'catppuccin-latte': catppuccinLatte as Theme,
  'solarized-light': solarizedLight as Theme,
  'github-light': githubLight as Theme,
};

export function listBundledThemes(): Theme[] {
  return BUNDLED_THEME_IDS.map((id) => BUNDLED_BY_ID[id]);
}

export function getBundledTheme(id: string): Theme | undefined {
  if (!(BUNDLED_THEME_IDS as readonly string[]).includes(id)) {
    return undefined;
  }
  return BUNDLED_BY_ID[id as BundledThemeId];
}

/**
 * Merge theme cssVars, ANSI palette (--ansi-0..15), and optional high-contrast overlay
 * for applyThemeOverrides().
 */
export function resolveThemeCssVars(
  theme: Theme,
  highContrastEnabled: boolean,
): Record<string, string> {
  const resolved: Record<string, string> = { ...theme.cssVars };

  for (let i = 0; i < 16; i++) {
    resolved[`--ansi-${i}`] = theme.ansi[i]!;
  }

  if (highContrastEnabled) {
    Object.assign(resolved, HIGH_CONTRAST_OVERLAY);
  }

  return resolved;
}

/** Required CSS variable keys every theme must supply (A8 UI-SPEC). */
export const REQUIRED_CSS_VARS = [
  '--bg-0',
  '--bg-1',
  '--bg-2',
  '--bg-3',
  '--fg-0',
  '--fg-1',
  '--fg-2',
  '--fg-3',
  '--border',
  '--border-bright',
  '--focus',
  '--focus-glow',
  '--accent-green',
  '--accent-amber',
  '--accent-red',
  '--accent-cyan',
  '--accent-magenta',
  '--accent-blue',
  '--workspace-neutral',
  '--workspace-red',
  '--workspace-orange',
  '--workspace-green',
  '--workspace-yellow',
  '--workspace-cyan',
  '--workspace-blue',
  '--workspace-purple',
  '--window-opacity-bg',
] as const;

export type RequiredCssVar = (typeof REQUIRED_CSS_VARS)[number];

export type ThemeAppearance = 'dark' | 'light';

export type Theme = {
  id: string;
  name: string;
  appearance: ThemeAppearance;
  cssVars: Record<RequiredCssVar, string>;
  ansi: string[];
  selection?: string;
  cursor?: string;
  cursorText?: string;
};

export type ThemeValidationResult =
  | { ok: true }
  | { ok: false; error: string };

const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
const RGBA_RE = /^rgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*(,\s*[\d.]+\s*)?\)$/;

function isThemeLike(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function validateTheme(value: unknown): ThemeValidationResult {
  if (!isThemeLike(value)) {
    return { ok: false, error: 'Theme must be an object' };
  }

  if ('tokenColors' in value) {
    return { ok: false, error: 'tokenColors is not allowed (no VSCode import path)' };
  }

  if (typeof value.id !== 'string' || value.id.length === 0) {
    return { ok: false, error: 'id is required' };
  }
  if (typeof value.name !== 'string' || value.name.length === 0) {
    return { ok: false, error: 'name is required' };
  }
  if (value.appearance !== 'dark' && value.appearance !== 'light') {
    return { ok: false, error: 'appearance must be "dark" or "light"' };
  }

  if (!isThemeLike(value.cssVars)) {
    return { ok: false, error: 'cssVars must be an object' };
  }

  for (const key of REQUIRED_CSS_VARS) {
    const v = value.cssVars[key];
    if (typeof v !== 'string' || v.length === 0) {
      return { ok: false, error: `Theme ignored: missing ${key}` };
    }
  }

  if (!Array.isArray(value.ansi) || value.ansi.length !== 16) {
    return { ok: false, error: 'ansi must be an array of 16 hex colors' };
  }

  for (let i = 0; i < value.ansi.length; i++) {
    const color = value.ansi[i];
    if (typeof color !== 'string' || !HEX_RE.test(color)) {
      return { ok: false, error: `ansi[${i}] must be a hex color` };
    }
  }

  for (const opt of ['selection', 'cursor', 'cursorText'] as const) {
    if (opt in value && value[opt] !== undefined && typeof value[opt] !== 'string') {
      return { ok: false, error: `${opt} must be a string when present` };
    }
  }

  return { ok: true };
}

/** Parse #rgb, #rrggbb, or rgba(...) into sRGB channels 0–1. */
function parseColor(input: string): [number, number, number] {
  const hex = input.trim();
  if (RGBA_RE.test(hex)) {
    const inner = hex.replace(/^rgba?\(|\)$/g, '').split(',').map((s) => s.trim());
    return [inner[0], inner[1], inner[2]].map((n) => Number(n) / 255) as [number, number, number];
  }
  if (!HEX_RE.test(hex)) {
    return [0, 0, 0];
  }
  let h = hex.slice(1);
  if (h.length === 3) {
    h = h
      .split('')
      .map((c) => c + c)
      .join('');
  }
  if (h.length === 8) {
    h = h.slice(0, 6);
  }
  const n = parseInt(h, 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** WCAG 2.x contrast ratio between two CSS colors (hex or rgba). */
export function contrastRatio(a: string, b: string): number {
  const l1 = relativeLuminance(parseColor(a));
  const l2 = relativeLuminance(parseColor(b));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

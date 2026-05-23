import type { ITheme, Terminal } from '@xterm/xterm';
import { applyThemeOverrides } from '../theme/applyTheme';
import {
  getBundledTheme,
  resolveThemeCssVars,
} from './themeCatalog';
import type { Theme } from './schema';
import type { AppearanceSettings } from '../appearance/types';
import { clampFontSize } from '../appearance/types';

const DEFAULT_THEME = getBundledTheme('voss-ignite')!;

const terminals = new Map<string, Terminal>();

let committedTheme: Theme = DEFAULT_THEME;
let committedHighContrast = false;
let committedAppearance: AppearanceSettings | null = null;

/** Baseline committed state saved when preview begins. */
let previewBaseline: { theme: Theme; highContrast: boolean } | null = null;
/** Theme currently shown during preview (if any). */
let previewThemeCurrent: Theme | null = null;
let previewHighContrast = false;

const ANSI_XTERM_KEYS = [
  'black',
  'red',
  'green',
  'yellow',
  'blue',
  'magenta',
  'cyan',
  'white',
  'brightBlack',
  'brightRed',
  'brightGreen',
  'brightYellow',
  'brightBlue',
  'brightMagenta',
  'brightCyan',
  'brightWhite',
] as const satisfies readonly (keyof ITheme)[];

/** Build xterm ITheme from theme cssVars + 16-color ANSI palette. */
export function themeToXtermTheme(
  theme: Theme,
  highContrast = false,
): ITheme {
  const resolved = resolveThemeCssVars(theme, highContrast);
  const xtermTheme: ITheme = {
    background: resolved['--bg-0'],
    foreground: resolved['--fg-0'],
    cursor: theme.cursor ?? resolved['--focus'],
    cursorAccent: theme.cursorText ?? resolved['--bg-0'],
    selectionBackground:
      theme.selection ?? resolved['--focus-glow'],
  };

  for (let i = 0; i < 16; i++) {
    xtermTheme[ANSI_XTERM_KEYS[i]!] = theme.ansi[i]!;
  }

  return xtermTheme;
}

/** xterm theme for newly opened terminals (committed state, not preview). */
export function getCurrentXtermTheme(): ITheme {
  return themeToXtermTheme(committedTheme, committedHighContrast);
}

export function getCommittedTheme(): Theme {
  return committedTheme;
}

function cursorBlinkEnabled(blink: AppearanceSettings['cursorBlink']): boolean {
  return blink !== 'off';
}

/** Apply font/cursor options to one live terminal without remount. */
export function applyAppearanceToTerminal(
  terminal: Terminal,
  settings: AppearanceSettings,
): void {
  terminal.options.fontFamily = `"${settings.fontFamily}", "SF Mono", "Menlo", ui-monospace, monospace`;
  terminal.options.fontSize = clampFontSize(settings.fontSize);
  terminal.options.lineHeight = settings.lineHeight;
  terminal.options.letterSpacing = settings.letterSpacing;
  terminal.options.customGlyphs = settings.ligatures;
  terminal.options.cursorStyle = settings.cursorShape;
  terminal.options.cursorBlink = cursorBlinkEnabled(settings.cursorBlink);

  const theme = terminal.options.theme ?? {};
  if (settings.cursorColor) {
    terminal.options.theme = { ...theme, cursor: settings.cursorColor };
  } else {
    const derived = themeToXtermTheme(committedTheme, committedHighContrast);
    terminal.options.theme = {
      ...theme,
      cursor: derived.cursor,
      cursorAccent: derived.cursorAccent,
    };
  }
}

/** Broadcast appearance settings to all registered terminals. */
export function applyAppearanceToAllTerminals(
  settings: AppearanceSettings,
): void {
  committedAppearance = settings;
  for (const term of terminals.values()) {
    applyAppearanceToTerminal(term, settings);
  }
}

function broadcastXtermTheme(theme: ITheme): void {
  for (const term of terminals.values()) {
    term.options.theme = theme;
  }
}

function applyVisual(theme: Theme, highContrast: boolean): void {
  applyThemeOverrides(resolveThemeCssVars(theme, highContrast));
  broadcastXtermTheme(themeToXtermTheme(theme, highContrast));
}

export function registerTerminal(id: string, terminal: Terminal): void {
  terminals.set(id, terminal);
  terminal.options.theme = getCurrentXtermTheme();
  if (committedAppearance) {
    applyAppearanceToTerminal(terminal, committedAppearance);
  }
}

export function unregisterTerminal(id: string): void {
  terminals.delete(id);
}

export function applyThemeToRuntime(
  theme: Theme,
  options?: { highContrast?: boolean; preview?: boolean },
): void {
  const highContrast = options?.highContrast ?? committedHighContrast;
  const isPreview = options?.preview === true;

  if (isPreview) {
    if (!previewBaseline) {
      previewBaseline = {
        theme: committedTheme,
        highContrast: committedHighContrast,
      };
    }
    previewThemeCurrent = theme;
    previewHighContrast = highContrast;
  } else {
    committedTheme = theme;
    committedHighContrast = highContrast;
    previewBaseline = null;
    previewThemeCurrent = null;
  }

  applyVisual(theme, highContrast);
}

/** Hover preview: save committed snapshot, apply theme without committing. */
export function previewTheme(
  theme: Theme,
  options?: { highContrast?: boolean },
): void {
  applyThemeToRuntime(theme, { ...options, preview: true });
}

/** Restore committed theme after preview (Esc / cancel). */
export function cancelThemePreview(): void {
  if (!previewBaseline) return;

  const { theme, highContrast } = previewBaseline;
  previewBaseline = null;
  previewThemeCurrent = null;
  applyVisual(theme, highContrast);
}

/** Clear preview stack after user commits the previewed theme. */
export function commitThemePreview(): void {
  if (previewThemeCurrent) {
    committedTheme = previewThemeCurrent;
    committedHighContrast = previewHighContrast;
  }
  previewBaseline = null;
  previewThemeCurrent = null;
}

/** Test-only: reset registry and committed state. */
export function _resetForTest(): void {
  terminals.clear();
  committedTheme = DEFAULT_THEME;
  committedHighContrast = false;
  committedAppearance = null;
  previewBaseline = null;
  previewThemeCurrent = null;
  previewHighContrast = false;
}

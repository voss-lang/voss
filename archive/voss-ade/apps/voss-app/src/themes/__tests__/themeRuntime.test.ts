import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  applyThemeToRuntime,
  cancelThemePreview,
  commitThemePreview,
  getCurrentXtermTheme,
  previewTheme,
  registerTerminal,
  themeToXtermTheme,
  unregisterTerminal,
  _resetForTest,
} from '../themeRuntime';
import { getBundledTheme } from '../themeCatalog';

const variantB = getBundledTheme('variant-b')!;
const dracula = getBundledTheme('dracula')!;

beforeEach(() => {
  _resetForTest();
  document.documentElement.removeAttribute('style');
  for (const prop of [
    '--bg-0',
    '--fg-0',
    '--focus',
    '--ansi-0',
    '--ansi-1',
  ]) {
    document.documentElement.style.removeProperty(prop);
  }
});

describe('themeRuntime — CSS vars', () => {
  it('applyThemeToRuntime updates document CSS vars', () => {
    applyThemeToRuntime(dracula);
    const root = document.documentElement;
    expect(root.style.getPropertyValue('--bg-0')).toBe(
      dracula.cssVars['--bg-0'],
    );
    expect(root.style.getPropertyValue('--fg-0')).toBe(
      dracula.cssVars['--fg-0'],
    );
    expect(root.style.getPropertyValue('--ansi-0')).toBe(dracula.ansi[0]);
  });
});

describe('themeRuntime — terminal registry', () => {
  it('register + apply updates mock terminal.options.theme without dispose', () => {
    const dispose = vi.fn();
    const mockTerm = {
      options: { theme: {} as Record<string, string> },
      dispose,
    };

    registerTerminal('pane-1', mockTerm as never);
    applyThemeToRuntime(dracula);

    expect(mockTerm.options.theme).toEqual(themeToXtermTheme(dracula));
    expect(dispose).not.toHaveBeenCalled();

    unregisterTerminal('pane-1');
    applyThemeToRuntime(variantB);
    expect(dispose).not.toHaveBeenCalled();
  });
});

describe('themeRuntime — preview stack', () => {
  it('preview then cancel restores committed theme vars', () => {
    applyThemeToRuntime(variantB);
    const root = document.documentElement;
    expect(root.style.getPropertyValue('--bg-0')).toBe(
      variantB.cssVars['--bg-0'],
    );

    previewTheme(dracula);
    expect(root.style.getPropertyValue('--bg-0')).toBe(
      dracula.cssVars['--bg-0'],
    );

    cancelThemePreview();
    expect(root.style.getPropertyValue('--bg-0')).toBe(
      variantB.cssVars['--bg-0'],
    );
  });

  it('commitThemePreview keeps previewed theme as committed', () => {
    applyThemeToRuntime(variantB);
    previewTheme(dracula);
    commitThemePreview();

    cancelThemePreview(); // no-op — preview stack cleared
    expect(document.documentElement.style.getPropertyValue('--bg-0')).toBe(
      dracula.cssVars['--bg-0'],
    );
    expect(getCurrentXtermTheme().background).toBe(
      dracula.cssVars['--bg-0'],
    );
  });
});

describe('themeRuntime — ansi → xterm mapping', () => {
  it('maps ansi[0..15] to xterm theme color keys', () => {
    const xterm = themeToXtermTheme(variantB);
    expect(xterm.black).toBe(variantB.ansi[0]);
    expect(xterm.red).toBe(variantB.ansi[1]);
    expect(xterm.green).toBe(variantB.ansi[2]);
    expect(xterm.brightWhite).toBe(variantB.ansi[15]);
    expect(xterm.background).toBe(variantB.cssVars['--bg-0']);
    expect(xterm.foreground).toBe(variantB.cssVars['--fg-0']);
    expect(xterm.cursor).toBe(variantB.cursor);
    expect(xterm.cursorAccent).toBe(variantB.cursorText);
    expect(xterm.selectionBackground).toBe(variantB.selection);
  });
});

// V24-10 (VADE2-10) Settings surface.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { DEFAULT_APPEARANCE_SETTINGS } from '../../../appearance/types';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
}));

const runtime = vi.hoisted(() => ({
  applyThemeSpy: vi.fn(),
}));

vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

vi.mock('../../../themes/themeRuntime', async () => {
  const catalog = await import('../../../themes/themeCatalog');
  return {
    getCommittedTheme: () => catalog.getBundledTheme('voss-ignite')!,
    applyThemeToRuntime: (theme: unknown, options: unknown) =>
      runtime.applyThemeSpy(theme, options),
  };
});

const applySpy = vi.fn();
const saveSpy = vi.fn().mockResolvedValue(undefined);
let committed = { ...DEFAULT_APPEARANCE_SETTINGS, fontSize: 13 };

vi.mock('../../../appearance/settings', async () => {
  const types = await import('../../../appearance/types');
  return {
    getCommittedAppearanceSettings: () => committed,
    subscribeAppearanceSettings: () => () => {},
    applyAppearanceSettings: (s: unknown) => applySpy(s),
    saveAppearanceSettings: (s: unknown) => saveSpy(s),
    clampFontSize: types.clampFontSize,
    MIN_FONT_SIZE: types.MIN_FONT_SIZE,
  };
});

import SettingsSurface from '../SettingsSurface';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

beforeEach(() => {
  h.invoke.mockReset();
  h.invoke.mockResolvedValue(null);
});

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  applySpy.mockClear();
  saveSpy.mockClear();
  runtime.applyThemeSpy.mockClear();
  committed = { ...DEFAULT_APPEARANCE_SETTINGS, fontSize: 13 };
});

describe('SettingsSurface', () => {
  it('renders a real settings tabpanel with theme, interface, terminal, and agent sections', () => {
    const el = mount(() => <SettingsSurface />);
    const panel = el.querySelector('[role="tabpanel"][aria-label="Settings"]');
    expect(panel).toBeTruthy();

    expect(el.querySelectorAll('.settings-theme-card')).toHaveLength(13);
    expect(el.querySelector('[aria-label="Terminal font"]')).toBeTruthy();
    expect(
      el.querySelector<HTMLInputElement>('input[aria-label="Font size"]')?.value,
    ).toBe('13');
    expect(el.querySelector('[aria-label="High contrast"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Bell behavior"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Cursor shape"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Codex model"]')).toBeTruthy();
  });

  it('applies and persists a theme selection through the active theme command', () => {
    const el = mount(() => <SettingsSurface />);
    const dracula = el.querySelector<HTMLButtonElement>(
      'button[aria-label="Use theme: Dracula"]',
    )!;
    dracula.click();

    expect(runtime.applyThemeSpy).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'dracula' }),
      expect.objectContaining({ highContrast: false }),
    );
    expect(h.invoke).toHaveBeenCalledWith('save_active_theme_id', {
      id: 'dracula',
    });
  });

  it('applies and persists a high-contrast change', () => {
    const el = mount(() => <SettingsSurface />);
    const toggle = el.querySelector<HTMLInputElement>('input[aria-label="High contrast"]')!;
    toggle.checked = true;
    toggle.dispatchEvent(new Event('change', { bubbles: true }));

    expect(applySpy).toHaveBeenCalledTimes(1);
    expect(saveSpy).toHaveBeenCalledTimes(1);
    expect(applySpy.mock.calls[0][0]).toMatchObject({ highContrastEnabled: true });
    expect(saveSpy.mock.calls[0][0]).toMatchObject({ highContrastEnabled: true });
  });

  it('applies and persists a bell behavior change', () => {
    const el = mount(() => <SettingsSurface />);
    const button = el.querySelector<HTMLButtonElement>(
      'button[aria-label="Set bell behavior: none"]',
    )!;
    button.click();

    expect(applySpy).toHaveBeenCalledWith(
      expect.objectContaining({ bellBehavior: 'none' }),
    );
    expect(saveSpy).toHaveBeenCalledWith(
      expect.objectContaining({ bellBehavior: 'none' }),
    );
  });

  it('persists per-CLI model defaults through appearance settings', () => {
    const el = mount(() => <SettingsSurface />);
    const input = el.querySelector<HTMLInputElement>('input[aria-label="Codex model"]')!;
    input.value = 'gpt-5.1-codex';
    input.dispatchEvent(new Event('change', { bubbles: true }));

    expect(applySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        cliDefaultModels: expect.objectContaining({ codex: 'gpt-5.1-codex' }),
      }),
    );
    expect(saveSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        cliDefaultModels: expect.objectContaining({ codex: 'gpt-5.1-codex' }),
      }),
    );
  });
});

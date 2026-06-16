// V24-10 (VADE2-10) — Settings surface: persisted appearance controls.
//
// Asserts the surface reflects committed appearance settings and that changing a
// control both applies (live) and persists. The appearance store module is mocked
// so we can observe apply/save without a real Tauri backend.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { DEFAULT_APPEARANCE_SETTINGS } from '../../../appearance/types';

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

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  applySpy.mockClear();
  saveSpy.mockClear();
  committed = { ...DEFAULT_APPEARANCE_SETTINGS, fontSize: 13 };
});

describe('SettingsSurface', () => {
  it('renders a Settings tabpanel reflecting committed appearance values', () => {
    const el = mount(() => <SettingsSurface />);
    const panel = el.querySelector('[role="tabpanel"][aria-label="Settings"]');
    expect(panel).toBeTruthy();

    const fontSize = el.querySelector<HTMLInputElement>('input[aria-label="Font size"]');
    expect(fontSize).toBeTruthy();
    expect(fontSize!.value).toBe('13');

    expect(el.querySelector('[aria-label="High contrast"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Bell behavior"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Cursor shape"]')).toBeTruthy();
  });

  it('applies AND persists a high-contrast change', () => {
    const el = mount(() => <SettingsSurface />);
    const toggle = el.querySelector<HTMLInputElement>('input[aria-label="High contrast"]')!;
    toggle.checked = true;
    toggle.dispatchEvent(new Event('change', { bubbles: true }));

    expect(applySpy).toHaveBeenCalledTimes(1);
    expect(saveSpy).toHaveBeenCalledTimes(1);
    expect(applySpy.mock.calls[0][0]).toMatchObject({ highContrastEnabled: true });
    expect(saveSpy.mock.calls[0][0]).toMatchObject({ highContrastEnabled: true });
  });

  it('applies AND persists a bell-behavior change', () => {
    const el = mount(() => <SettingsSurface />);
    const select = el.querySelector<HTMLSelectElement>('select[aria-label="Bell behavior"]')!;
    select.value = 'none';
    select.dispatchEvent(new Event('change', { bubbles: true }));

    expect(applySpy).toHaveBeenCalledWith(
      expect.objectContaining({ bellBehavior: 'none' }),
    );
    expect(saveSpy).toHaveBeenCalledWith(
      expect.objectContaining({ bellBehavior: 'none' }),
    );
  });
});

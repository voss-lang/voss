// 10 (VADE2 Settings surface

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { DEFAULT_APPEARANCE_SETTINGS } from '../../../appearance/types';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
}));

const runtime = vi.hoisted(() => ({
  applyThemeSpy: vi.fn(),
}));

const observeApi = vi.hoisted(() => ({
  getObserveSettings: vi.fn(),
  patchObserveSettings: vi.fn(),
}));

vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

vi.mock('../../../org/live/sidecarClient', () => ({
  callSidecar: vi.fn(),
  getObserveSettings: observeApi.getObserveSettings,
  patchObserveSettings: observeApi.patchObserveSettings,
}));

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
import {
  __resetLiveServer,
  setLiveServer,
} from '../../../org/live/liveServer';
vi.mock('../../../pane/observeClient', () => ({
  observeContextForWorkspace: async () => ({ repositoryId: 'repo-1', worktreeId: 'wt-1' }),
}));

import { observeContextForWorkspace } from '../../../pane/observeClient';

async function settle(rounds = 10): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await new Promise((r) => setTimeout(r, 0));
  }
}

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
  __resetLiveServer();
  observeApi.getObserveSettings.mockReset().mockResolvedValue({});
  observeApi.patchObserveSettings.mockReset();
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

describe('SettingsSurface — Observation section (S3.8)', () => {
  const ENROLLED = {
    enabled: true,
    capture: true,
    analysis: false,
    provider: 'anthropic',
    disclosure: false,
    budget_usd: null,
    paused: false,
  };

  async function mountWithServer(
    repos: Record<string, typeof ENROLLED>,
  ): Promise<HTMLElement> {
    observeApi.getObserveSettings.mockResolvedValue(repos);
    setLiveServer({ sidecarId: 'sc-1', cwd: '/ws' });
    const el = mount(() => <SettingsSurface />);
    await settle();
    return el;
  }

  it('shows a fallback instead of toggles when no live server exists', async () => {
    const el = mount(() => <SettingsSurface />);
    await settle();

    expect(el.querySelector('#settings-observation')).toBeTruthy();
    expect(el.textContent).toContain(
      'Open a project with a live session to manage observation.',
    );
    expect(observeApi.getObserveSettings).not.toHaveBeenCalled();
  });

  it('reflects enrollment state and shows the provider disclosure text', async () => {
    const ctx = await observeContextForWorkspace('/ws', 'sc-1');
    const el = await mountWithServer({ [ctx.repositoryId]: ENROLLED });

    const section = el.querySelector('#settings-observation')!;
    expect(section.querySelector('.settings-panel__meta')?.textContent).toContain(
      'capturing',
    );
    expect(
      section.querySelector<HTMLInputElement>(
        'input[aria-label="Observe this repository"]',
      )?.checked,
    ).toBe(true);
    expect(section.textContent).toContain(
      'Failure analysis sends captured commands and output to anthropic.',
    );
  });

  it('pauses capture via PATCH with the repository id', async () => {
    const ctx = await observeContextForWorkspace('/ws', 'sc-1');
    observeApi.patchObserveSettings.mockResolvedValue({
      ...ENROLLED,
      paused: true,
    });
    const el = await mountWithServer({ [ctx.repositoryId]: ENROLLED });

    const toggle = el.querySelector<HTMLInputElement>(
      'input[aria-label="Pause capture"]',
    )!;    toggle.checked = true;
    toggle.dispatchEvent(new Event('change', { bubbles: true }));
    await settle();

    expect(observeApi.patchObserveSettings).toHaveBeenCalledWith(
      'sc-1',
      ctx.repositoryId,
      { paused: true },
    );
  });

  it('enabling analysis acknowledges the provider disclosure', async () => {
    const ctx = await observeContextForWorkspace('/ws', 'sc-1');
    observeApi.patchObserveSettings.mockResolvedValue({
      ...ENROLLED,
      analysis: true,
      disclosure: true,
    });
    const el = await mountWithServer({ [ctx.repositoryId]: ENROLLED });

    const toggle = el.querySelector<HTMLInputElement>(
      'input[aria-label="Failure analysis"]',
    )!;
    toggle.checked = true;
    toggle.dispatchEvent(new Event('change', { bubbles: true }));
    await settle();

    expect(observeApi.patchObserveSettings).toHaveBeenCalledWith(
      'sc-1',
      ctx.repositoryId,
      { analysis: true, disclosure: true },
    );
  });

  it('enrolls an unenrolled repository via PATCH when observation is enabled', async () => {
    const ctx = await observeContextForWorkspace('/ws', 'sc-1');
    observeApi.patchObserveSettings.mockResolvedValue({
      ...ENROLLED,
      provider: null,
    });
    const el = await mountWithServer({});

    const toggle = el.querySelector<HTMLInputElement>(
      'input[aria-label="Observe this repository"]',
    )!;
    toggle.checked = true;
    toggle.dispatchEvent(new Event('change', { bubbles: true }));
    await settle();

    expect(observeApi.patchObserveSettings).toHaveBeenCalledWith(
      'sc-1',
      ctx.repositoryId,
      { enabled: true },
    );
  });
});

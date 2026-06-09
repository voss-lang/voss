import { describe, it, expect, vi, beforeEach } from 'vitest';

// modelPrefs persists via the real appearance-settings flatten store, which
// calls @tauri-apps/api/core invoke('save_appearance_settings'). Mock invoke so
// the persistence call is observable and round-trips through committedSettings.
const h = vi.hoisted(() => ({
  invoke: vi.fn(),
}));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  MODEL_PRESETS,
  MODEL_CLI_KEYS,
  defaultModelFor,
  saveDefaultModel,
  loadModelPrefs,
  type ModelCliKey,
} from '../modelPrefs';
import { _resetAppearanceForTest } from '../../appearance/settings';

beforeEach(() => {
  _resetAppearanceForTest();
  h.invoke.mockReset();
  h.invoke.mockResolvedValue(undefined);
});

describe('modelPrefs — catalog honesty', () => {
  it('exposes exactly the five model CLI keys', () => {
    expect(MODEL_CLI_KEYS).toEqual(['claude', 'codex', 'gemini', 'opencode', 'aider']);
    expect(Object.keys(MODEL_PRESETS).sort()).toEqual(
      ['aider', 'claude', 'codex', 'gemini', 'opencode'],
    );
  });

  it('Claude is the only verified-real preset with a hardcoded default model', () => {
    expect(MODEL_PRESETS.claude.modelVerified).toBe(true);
    expect(MODEL_PRESETS.claude.defaultModel).toBe('sonnet');
    expect(MODEL_PRESETS.claude.alternates).toEqual(['opus', 'sonnet', 'haiku']);
  });

  it('non-Claude CLIs inject no default model and expose no verified alternates', () => {
    for (const cli of ['codex', 'gemini', 'opencode', 'aider'] as ModelCliKey[]) {
      expect(MODEL_PRESETS[cli].defaultModel).toBeNull();
      expect(MODEL_PRESETS[cli].modelVerified).toBe(false);
      expect(MODEL_PRESETS[cli].alternates).toEqual([]);
    }
  });
});

describe('modelPrefs — defaultModelFor', () => {
  it('returns the real built-in default for each CLI when nothing is persisted', () => {
    expect(defaultModelFor('claude')).toBe('sonnet');
    // null = omit --model so a missing/renamed model can never break the launch.
    expect(defaultModelFor('codex')).toBeNull();
    expect(defaultModelFor('gemini')).toBeNull();
    expect(defaultModelFor('opencode')).toBeNull();
    expect(defaultModelFor('aider')).toBeNull();
  });

  it('round-trips a saved override: set then get returns the persisted id', async () => {
    expect(defaultModelFor('claude')).toBe('sonnet');
    await saveDefaultModel('claude', 'opus');
    expect(defaultModelFor('claude')).toBe('opus');

    // A non-Claude override flips its default from null to the chosen id.
    expect(defaultModelFor('codex')).toBeNull();
    await saveDefaultModel('codex', 'gpt-5.1-codex');
    expect(defaultModelFor('codex')).toBe('gpt-5.1-codex');
  });

  it('a blank/whitespace override clears back to the preset built-in', async () => {
    await saveDefaultModel('claude', 'haiku');
    expect(defaultModelFor('claude')).toBe('haiku');
    await saveDefaultModel('claude', '   ');
    expect(defaultModelFor('claude')).toBe('sonnet');
  });

  it('trims surrounding whitespace on the saved id', async () => {
    await saveDefaultModel('claude', '  opus  ');
    expect(defaultModelFor('claude')).toBe('opus');
  });
});

describe('modelPrefs — persistence', () => {
  it('saveDefaultModel invokes save_appearance_settings with cliDefaultModels', async () => {
    await saveDefaultModel('claude', 'opus');
    expect(h.invoke).toHaveBeenCalledWith(
      'save_appearance_settings',
      expect.objectContaining({
        settings: expect.objectContaining({
          cliDefaultModels: expect.objectContaining({ claude: 'opus' }),
        }),
      }),
    );
  });

  it('merges multiple CLI defaults into one persisted map', async () => {
    await saveDefaultModel('claude', 'opus');
    await saveDefaultModel('aider', 'sonnet');
    const calls = h.invoke.mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall[1].settings.cliDefaultModels).toMatchObject({
      claude: 'opus',
      aider: 'sonnet',
    });
  });

  it('loadModelPrefs hydrates the persisted map from the appearance store', async () => {
    h.invoke.mockResolvedValueOnce({ cliDefaultModels: { claude: 'opus', codex: 'gpt-x' } });
    const prefs = await loadModelPrefs();
    expect(prefs).toMatchObject({ claude: 'opus', codex: 'gpt-x' });
    // After hydration, the synchronous default reflects the loaded value.
    expect(defaultModelFor('claude')).toBe('opus');
  });

  it('loadModelPrefs returns an empty map when nothing is persisted', async () => {
    h.invoke.mockResolvedValueOnce({});
    expect(await loadModelPrefs()).toEqual({});
  });
});

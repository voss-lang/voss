import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
}));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import { applyThemeOverrides } from '../../theme/applyTheme';
import {
  CURRENT_PROFILE_VERSION,
  PROFILE_CHANGED,
  PROFILE_IGNORED_UNSUPPORTED_VERSION,
  PROFILE_SAVE_FAILED,
  PROFILE_SETTINGS_SAVE_FAILED,
  applyAppearanceDocumentHints,
  applyAppearanceFromSnapshot,
  applyProfile,
  buildProfileListEntries,
  extractAppearanceSnapshot,
  isSupportedProfileVersion,
  listProfiles,
  loadActiveProfileId,
  loadProfile,
  parseProfileFile,
  previewProfile,
  saveActiveProfileId,
  saveProfile,
} from '../profiles';

describe('profiles — invoke bridges', () => {
  beforeEach(() => h.invoke.mockReset());

  it('listProfiles invokes list_profiles', async () => {
    h.invoke.mockResolvedValueOnce(['work', 'personal']);
    const names = await listProfiles();
    expect(h.invoke).toHaveBeenCalledWith('list_profiles');
    expect(names).toEqual(['work', 'personal']);
  });

  it('loadProfile invokes load_profile with name', async () => {
    const file = { version: 1, appearance: { themeId: 'nord' } };
    h.invoke.mockResolvedValueOnce(file);
    const result = await loadProfile('work');
    expect(h.invoke).toHaveBeenCalledWith('load_profile', { name: 'work' });
    expect(result).toEqual(file);
  });

  it('saveProfile invokes save_profile', async () => {
    const file = { version: 1 as const, appearance: { themeId: 'dracula' } };
    h.invoke.mockResolvedValueOnce(undefined);
    await saveProfile('work', file);
    expect(h.invoke).toHaveBeenCalledWith('save_profile', {
      name: 'work',
      profile: file,
    });
  });

  it('loadActiveProfileId invokes load_active_profile_id', async () => {
    h.invoke.mockResolvedValueOnce('work');
    const id = await loadActiveProfileId();
    expect(h.invoke).toHaveBeenCalledWith('load_active_profile_id');
    expect(id).toBe('work');
  });

  it('saveActiveProfileId invokes save_active_profile_id', async () => {
    h.invoke.mockResolvedValueOnce(undefined);
    await saveActiveProfileId('personal');
    expect(h.invoke).toHaveBeenCalledWith('save_active_profile_id', {
      id: 'personal',
    });
  });
});

describe('profiles — copy constants', () => {
  it('matches A8 UI-SPEC profile strings', () => {
    expect(PROFILE_CHANGED).toBe('Profile changed');
    expect(PROFILE_IGNORED_UNSUPPORTED_VERSION).toBe(
      'Profile ignored: unsupported version',
    );
    expect(PROFILE_SAVE_FAILED).toBe('could not save profile');
    expect(PROFILE_SETTINGS_SAVE_FAILED).toBe('could not save profile settings');
  });
});

describe('profiles — parse and list metadata', () => {
  it('accepts current profile version only', () => {
    expect(isSupportedProfileVersion(CURRENT_PROFILE_VERSION)).toBe(true);
    expect(isSupportedProfileVersion(2)).toBe(false);
    expect(isSupportedProfileVersion(undefined)).toBe(false);
  });

  it('parseProfileFile rejects unsupported versions', () => {
    expect(parseProfileFile({ version: 2, appearance: {} })).toBeNull();
    expect(parseProfileFile({ appearance: {} })).toBeNull();
    expect(
      parseProfileFile({
        version: CURRENT_PROFILE_VERSION,
        appearance: { themeId: 'nord' },
      }),
    ).toEqual({
      version: CURRENT_PROFILE_VERSION,
      appearance: { themeId: 'nord' },
    });
  });

  it('buildProfileListEntries sets active and pinned as optional data fields', () => {
    const rows = buildProfileListEntries(
      ['work', 'personal', 'presentation'],
      'work',
      'presentation',
    );
    expect(rows).toEqual([
      { id: 'work', name: 'work', active: true },
      { id: 'personal', name: 'personal' },
      { id: 'presentation', name: 'presentation', pinned: true },
    ]);
    expect(rows[0]).not.toHaveProperty('pinned');
    expect(rows[1]).not.toHaveProperty('active');
  });

  it('extractAppearanceSnapshot returns appearance object', () => {
    expect(
      extractAppearanceSnapshot({
        appearance: {
          themeId: 'dracula',
          highContrastEnabled: true,
          fontSize: 14,
        },
      }),
    ).toEqual({
      themeId: 'dracula',
      highContrastEnabled: true,
      fontSize: 14,
    });
  });
});

describe('profiles — appearance application', () => {
  const originalGetComputedStyle = window.getComputedStyle;

  beforeEach(() => {
    h.invoke.mockReset();
    document.documentElement.style.cssText = '';
    delete document.documentElement.dataset.highContrast;
    delete document.documentElement.dataset.reducedMotion;
  });

  afterEach(() => {
    window.getComputedStyle = originalGetComputedStyle;
  });

  it('applyAppearanceFromSnapshot applies bundled theme css vars', async () => {
    await applyAppearanceFromSnapshot({
      appearance: { themeId: 'nord', highContrastEnabled: false },
    });
    const bg = document.documentElement.style.getPropertyValue('--bg-0');
    expect(bg.length).toBeGreaterThan(0);
  });

  it('applyAppearanceDocumentHints clamps font size floor to 10px', () => {
    applyAppearanceDocumentHints({ fontSize: 8, fontFamily: 'Menlo' });
    expect(document.documentElement.style.fontSize).toBe('10px');
    expect(document.documentElement.style.getPropertyValue('--font-mono')).toBe(
      'Menlo',
    );
  });

  it('previewProfile does not persist active profile id', async () => {
    const snapshot = {
      version: CURRENT_PROFILE_VERSION,
      appearance: { themeId: 'dracula' },
    };
    await previewProfile(snapshot);
    expect(h.invoke).not.toHaveBeenCalledWith(
      'save_active_profile_id',
      expect.anything(),
    );
  });

  it('applyProfile persists active profile id when profileId is set', async () => {
    h.invoke.mockResolvedValue(undefined);
    const snapshot = {
      version: CURRENT_PROFILE_VERSION,
      appearance: { themeId: 'variant-b' },
    };
    await applyProfile(snapshot, { profileId: 'work' });
    expect(h.invoke).toHaveBeenCalledWith('save_active_profile_id', {
      id: 'work',
    });
  });

  it('applyProfile can persist active theme id when requested', async () => {
    h.invoke.mockResolvedValue(undefined);
    const snapshot = {
      version: CURRENT_PROFILE_VERSION,
      appearance: { themeId: 'tokyo-night' },
    };
    await applyProfile(snapshot, { persistThemeId: true });
    expect(h.invoke).toHaveBeenCalledWith('save_active_theme_id', {
      id: 'tokyo-night',
    });
  });
});

describe('profiles — theme override seam', () => {
  it('applyThemeOverrides remains the css application path', () => {
    applyThemeOverrides({ '--bg-0': '#010101' });
    expect(document.documentElement.style.getPropertyValue('--bg-0')).toBe(
      '#010101',
    );
  });
});

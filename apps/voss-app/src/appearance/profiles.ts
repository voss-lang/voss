import { invoke } from '@tauri-apps/api/core';
import { initWindowEffectsFromAppearance } from './windowEffects';
import {
  getBundledTheme,
  validateTheme,
  type Theme,
} from '../themes/themeCatalog';
import { applyThemeToRuntime } from '../themes/themeRuntime';

/**
 * A8-01 Task 3 — frontend bridge for settings profile snapshots.
 *
 * Profiles are full settings snapshots at `~/.config/voss-app/profiles/<name>.json`.
 * Active profile id lives in `settings.json` (`appearance.activeProfileId`).
 * Row labels `active` / `pinned` are UI metadata — not stored inside profile files.
 */

// --- Version -----------------------------------------------------------------

export const CURRENT_PROFILE_VERSION = 1 as const;

// --- Types (aligned with Rust `voss_app_core::profiles::ProfileFile`) --------

export type CursorShape = 'block' | 'bar' | 'underline';
export type CursorBlink = 'off' | 'slow' | 'fast';
export type BellBehavior = 'visual' | 'audible' | 'none' | 'badge';

/** Appearance slice of a profile snapshot (D-14). */
export interface AppearanceSnapshot {
  themeId?: string;
  activeThemeId?: string;
  highContrastEnabled?: boolean;
  fontFamily?: string;
  fontSize?: number;
  lineHeight?: number;
  letterSpacing?: number;
  ligaturesEnabled?: boolean;
  windowOpacity?: number;
  cursorShape?: CursorShape;
  cursorBlink?: CursorBlink;
  cursorColor?: string;
  bellBehavior?: BellBehavior;
  reducedMotion?: boolean;
}

/** Terminal and layout sections are opaque forward-compat buckets. */
export type TerminalSnapshot = Record<string, unknown>;
export type LayoutSnapshot = Record<string, unknown>;

/**
 * Flattened settings map — mirrors Rust `ProfileFile` with `#[serde(flatten)]`
 * on `settings` (top-level keys beside `version` in JSON).
 */
export interface ProfileSettings {
  appearance?: AppearanceSnapshot;
  terminal?: TerminalSnapshot;
  layout?: LayoutSnapshot;
  keymap?: Record<string, unknown>;
  [key: string]: unknown;
}

export type ProfileFile = {
  version: typeof CURRENT_PROFILE_VERSION;
} & ProfileSettings;

/** Picker row metadata; `active` / `pinned` are computed for display only. */
export interface ProfileListEntry {
  id: string;
  name: string;
  active?: boolean;
  pinned?: boolean;
}

export interface ProfileApplyOptions {
  /** Workspace path for resolving custom themes under `.voss/themes/`. */
  workspacePath?: string;
  /** When set, `applyProfile` persists `appearance.activeProfileId`. */
  profileId?: string;
  /** When true, `applyProfile` also persists `appearance.activeThemeId`. */
  persistThemeId?: boolean;
}

type CustomThemeWire = {
  version: number;
  id: string;
  name: string;
  appearance: 'dark' | 'light';
  cssVars: Record<string, string>;
  ansi: string[];
  selection?: string;
  cursor?: string;
  cursorText?: string;
};

// --- Copy (A8 UI-SPEC) -------------------------------------------------------

export const PROFILE_SWITCH_COMMAND = 'Switch Profile';
export const PROFILE_CHANGED = 'Profile changed';
export const PROFILE_IGNORED_UNSUPPORTED_VERSION =
  'Profile ignored: unsupported version';
export const PROFILE_SAVE_FAILED = 'could not save profile';
export const PROFILE_LOAD_FAILED = 'could not load profile';
export const PROFILE_SETTINGS_SAVE_FAILED = 'could not save profile settings';

// --- Tauri command bridges ---------------------------------------------------

export async function listProfiles(): Promise<string[]> {
  return invoke<string[]>('list_profiles');
}

export async function loadProfile(name: string): Promise<ProfileFile | null> {
  return invoke<ProfileFile | null>('load_profile', { name });
}

export async function saveProfile(
  name: string,
  profile: ProfileFile,
): Promise<void> {
  await invoke('save_profile', { name, profile });
}

export async function loadActiveProfileId(): Promise<string | null> {
  return invoke<string | null>('load_active_profile_id');
}

export async function saveActiveProfileId(
  id: string | null,
): Promise<void> {
  await invoke('save_active_profile_id', { id });
}

// --- Parsing / list metadata -------------------------------------------------

export function isSupportedProfileVersion(
  version: unknown,
): version is typeof CURRENT_PROFILE_VERSION {
  return version === CURRENT_PROFILE_VERSION;
}

/** Fail-safe parse for wire values; unsupported versions return null. */
export function parseProfileFile(value: unknown): ProfileFile | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (!isSupportedProfileVersion(record.version)) {
    return null;
  }
  return record as ProfileFile;
}

export function buildProfileListEntries(
  names: string[],
  activeProfileId?: string | null,
  pinnedProfileId?: string | null,
): ProfileListEntry[] {
  return names.map((id) => ({
    id,
    name: id,
    ...(activeProfileId === id ? { active: true } : {}),
    ...(pinnedProfileId === id ? { pinned: true } : {}),
  }));
}

export function extractAppearanceSnapshot(
  profile: ProfileSettings,
): AppearanceSnapshot {
  const appearance = profile.appearance;
  if (!appearance || typeof appearance !== 'object' || Array.isArray(appearance)) {
    return {};
  }
  return appearance as AppearanceSnapshot;
}

// --- Appearance application --------------------------------------------------

function wireCustomThemeToTheme(wire: CustomThemeWire): Theme | null {
  const candidate = {
    id: wire.id,
    name: wire.name,
    appearance: wire.appearance,
    cssVars: wire.cssVars,
    ansi: wire.ansi,
    selection: wire.selection,
    cursor: wire.cursor,
    cursorText: wire.cursorText,
  };
  return validateTheme(candidate).ok ? (candidate as Theme) : null;
}

async function resolveThemeForAppearance(
  appearance: AppearanceSnapshot,
  workspacePath?: string,
): Promise<Theme | null> {
  const themeId = appearance.themeId ?? appearance.activeThemeId;
  if (!themeId) {
    return null;
  }

  const bundled = getBundledTheme(themeId);
  if (bundled) {
    return bundled;
  }

  if (!workspacePath) {
    return null;
  }

  const wire = await invoke<CustomThemeWire | null>('load_custom_theme', {
    workspacePath,
    name: themeId,
  });
  if (!wire) {
    return null;
  }
  return wireCustomThemeToTheme(wire);
}

/** Apply font/opacity/document hints from appearance (terminal reload is A8-04). */
export function applyAppearanceDocumentHints(
  appearance: AppearanceSnapshot,
): void {
  const root = document.documentElement;

  if (appearance.fontFamily) {
    root.style.setProperty('--font-mono', appearance.fontFamily);
  }

  if (typeof appearance.fontSize === 'number') {
    root.style.fontSize = `${Math.max(10, appearance.fontSize)}px`;
  }

  if (typeof appearance.lineHeight === 'number') {
    root.style.lineHeight = String(appearance.lineHeight);
  }

  if (typeof appearance.letterSpacing === 'number') {
    root.style.letterSpacing = `${appearance.letterSpacing}px`;
  }

  void initWindowEffectsFromAppearance(appearance);

  root.dataset.highContrast = appearance.highContrastEnabled ? 'true' : 'false';
  root.dataset.reducedMotion = appearance.reducedMotion ? 'true' : 'false';
  root.dataset.cursorShape = appearance.cursorShape ?? '';
  root.dataset.cursorBlink = appearance.cursorBlink ?? '';
  root.dataset.bellBehavior = appearance.bellBehavior ?? '';
}

/**
 * Apply theme + document-level appearance from a snapshot without persisting ids.
 */
export async function applyAppearanceFromSnapshot(
  profile: ProfileSettings,
  workspacePath?: string,
): Promise<void> {
  const appearance = extractAppearanceSnapshot(profile);
  const theme = await resolveThemeForAppearance(appearance, workspacePath);

  if (theme) {
    applyThemeToRuntime(theme, {
      highContrast: appearance.highContrastEnabled === true,
    });
  } else if (appearance.highContrastEnabled) {
    applyThemeToRuntime(getBundledTheme('variant-b')!, {
      highContrast: true,
    });
  }

  applyAppearanceDocumentHints(appearance);
}

/** Commit profile snapshot and persist active profile (and optional theme) ids. */
export async function applyProfile(
  snapshot: ProfileFile,
  options: ProfileApplyOptions = {},
): Promise<void> {
  await applyAppearanceFromSnapshot(snapshot, options.workspacePath);

  if (options.profileId !== undefined) {
    await saveActiveProfileId(options.profileId);
  }

  if (options.persistThemeId) {
    const themeId = extractAppearanceSnapshot(snapshot).themeId
      ?? extractAppearanceSnapshot(snapshot).activeThemeId
      ?? null;
    await invoke('save_active_theme_id', { id: themeId });
  }
}

/** Preview snapshot live without updating active profile id. */
export async function previewProfile(
  snapshot: ProfileFile,
  workspacePath?: string,
): Promise<void> {
  await applyAppearanceFromSnapshot(snapshot, workspacePath);
}

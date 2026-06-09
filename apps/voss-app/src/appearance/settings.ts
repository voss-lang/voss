import { invoke } from '@tauri-apps/api/core';
import type { CursorBlink, CursorShape, BellBehavior } from './profiles';
import {
  applyThemeToRuntime,
  applyAppearanceToAllTerminals,
  getCommittedTheme,
} from '../themes/themeRuntime';
import {
  clampFontSize,
  DEFAULT_APPEARANCE_SETTINGS,
  type AppearanceSettings,
} from './types';

export type { AppearanceSettings, CursorBlink, CursorShape, BellBehavior };
export {
  clampFontSize,
  DEFAULT_APPEARANCE_SETTINGS,
  MIN_FONT_SIZE,
} from './types';

const CURSOR_SHAPES = new Set<CursorShape>(['block', 'bar', 'underline']);
const CURSOR_BLINKS = new Set<CursorBlink>(['off', 'slow', 'fast']);
const BELL_BEHAVIORS = new Set<BellBehavior>([
  'visual',
  'audible',
  'none',
  'badge',
]);

type AppearanceWire = {
  fontFamily?: string;
  fontSize?: number;
  lineHeight?: number;
  letterSpacing?: number;
  ligatures?: boolean;
  cursorShape?: string;
  cursorBlink?: string;
  cursorColor?: string;
  bellBehavior?: string;
  highContrastEnabled?: boolean;
  reducedMotionEnabled?: boolean;
  cliDefaultModels?: unknown;
};

const listeners = new Set<(settings: AppearanceSettings) => void>();
let committedSettings: AppearanceSettings = { ...DEFAULT_APPEARANCE_SETTINGS };

function isCursorShape(value: unknown): value is CursorShape {
  return typeof value === 'string' && CURSOR_SHAPES.has(value as CursorShape);
}

function isCursorBlink(value: unknown): value is CursorBlink {
  return typeof value === 'string' && CURSOR_BLINKS.has(value as CursorBlink);
}

function isBellBehavior(value: unknown): value is BellBehavior {
  return typeof value === 'string' && BELL_BEHAVIORS.has(value as BellBehavior);
}

/** Fail-safe parse for wire/partial values. */
export function parseAppearanceSettings(wire: unknown): AppearanceSettings {
  const base = { ...DEFAULT_APPEARANCE_SETTINGS };
  if (typeof wire !== 'object' || wire === null || Array.isArray(wire)) {
    return base;
  }
  const w = wire as AppearanceWire;

  if (typeof w.fontFamily === 'string' && w.fontFamily.trim()) {
    base.fontFamily = w.fontFamily.trim();
  }
  if (typeof w.fontSize === 'number') {
    base.fontSize = clampFontSize(w.fontSize);
  }
  if (typeof w.lineHeight === 'number' && w.lineHeight > 0) {
    base.lineHeight = w.lineHeight;
  }
  if (typeof w.letterSpacing === 'number') {
    base.letterSpacing = w.letterSpacing;
  }
  if (typeof w.ligatures === 'boolean') {
    base.ligatures = w.ligatures;
  }
  if (isCursorShape(w.cursorShape)) {
    base.cursorShape = w.cursorShape;
  }
  if (isCursorBlink(w.cursorBlink)) {
    base.cursorBlink = w.cursorBlink;
  }
  if (typeof w.cursorColor === 'string' && w.cursorColor.trim()) {
    base.cursorColor = w.cursorColor.trim();
  }
  if (isBellBehavior(w.bellBehavior)) {
    base.bellBehavior = w.bellBehavior;
  }
  if (typeof w.highContrastEnabled === 'boolean') {
    base.highContrastEnabled = w.highContrastEnabled;
  }
  if (typeof w.reducedMotionEnabled === 'boolean') {
    base.reducedMotionEnabled = w.reducedMotionEnabled;
  }
  if (
    typeof w.cliDefaultModels === 'object' &&
    w.cliDefaultModels !== null &&
    !Array.isArray(w.cliDefaultModels)
  ) {
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(w.cliDefaultModels as Record<string, unknown>)) {
      if (typeof v === 'string' && v.trim()) out[k] = v.trim();
    }
    if (Object.keys(out).length > 0) base.cliDefaultModels = out;
  }

  return base;
}

export async function loadAppearanceSettings(): Promise<AppearanceSettings> {
  const wire = await invoke<AppearanceWire>('load_appearance_settings');
  const parsed = parseAppearanceSettings(wire);
  committedSettings = parsed;
  return parsed;
}

export async function saveAppearanceSettings(
  settings: AppearanceSettings,
): Promise<void> {
  const normalized = parseAppearanceSettings(settings);
  await invoke('save_appearance_settings', { settings: normalized });
  committedSettings = normalized;
}

export function getCommittedAppearanceSettings(): AppearanceSettings {
  return committedSettings;
}

export function subscribeAppearanceSettings(
  listener: (settings: AppearanceSettings) => void,
): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function applyDocumentAppearance(settings: AppearanceSettings): void {
  const root = document.documentElement;

  root.style.setProperty('--font-mono', settings.fontFamily);
  root.style.fontSize = `${clampFontSize(settings.fontSize)}px`;
  root.style.lineHeight = String(settings.lineHeight);
  root.style.letterSpacing = `${settings.letterSpacing}px`;

  root.dataset.highContrast = settings.highContrastEnabled ? 'true' : 'false';
  root.dataset.reducedMotion = settings.reducedMotionEnabled ? 'true' : 'false';
  root.dataset.cursorShape = settings.cursorShape;
  root.dataset.cursorBlink = settings.cursorBlink;
  root.dataset.bellBehavior = settings.bellBehavior;

  root.classList.toggle('reduced-motion', settings.reducedMotionEnabled);
}

/** Apply settings to document, theme high-contrast overlay, and live terminals. */
export function applyAppearanceSettings(settings: AppearanceSettings): void {
  const normalized = parseAppearanceSettings(settings);
  committedSettings = normalized;

  applyDocumentAppearance(normalized);
  applyThemeToRuntime(getCommittedTheme(), {
    highContrast: normalized.highContrastEnabled,
  });
  applyAppearanceToAllTerminals(normalized);

  for (const listener of listeners) {
    listener(normalized);
  }
}

/** Test-only reset. */
export function _resetAppearanceForTest(): void {
  committedSettings = { ...DEFAULT_APPEARANCE_SETTINGS };
  listeners.clear();
  document.documentElement.classList.remove('reduced-motion');
}

import type { BellBehavior, CursorBlink, CursorShape } from './profiles';

export const MIN_FONT_SIZE = 10;

export interface AppearanceSettings {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
  ligatures: boolean;
  cursorShape: CursorShape;
  cursorBlink: CursorBlink;
  cursorColor?: string;
  bellBehavior: BellBehavior;
  highContrastEnabled: boolean;
  reducedMotionEnabled: boolean;
/**
 * CLI chosen default model, keyed by CLI binary
 * (`claude`/`codex`/...) → model alias/id. Absent → preset built-in default
 */
  cliDefaultModels?: Record<string, string>;
}

export const DEFAULT_APPEARANCE_SETTINGS: AppearanceSettings = {
  fontFamily: 'JetBrains Mono',
  fontSize: 13,
  lineHeight: 1.5,
  letterSpacing: 0,
  ligatures: false,
  cursorShape: 'block',
  cursorBlink: 'fast',
  bellBehavior: 'visual',
  highContrastEnabled: false,
  reducedMotionEnabled: false,
};

export function clampFontSize(size: number): number {
  if (!Number.isFinite(size)) {
    return DEFAULT_APPEARANCE_SETTINGS.fontSize;
  }
  return Math.max(MIN_FONT_SIZE, Math.round(size));
}

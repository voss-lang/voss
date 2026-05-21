import { invoke } from '@tauri-apps/api/core';

/** A8 UI-SPEC error copy when a font is unavailable. */
export const FONT_UNAVAILABLE = 'Font unavailable: using JetBrains Mono';

export const FALLBACK_FONT = 'JetBrains Mono';

/** List system monospace fonts via Tauri (always includes JetBrains Mono). */
export async function listSystemFonts(): Promise<string[]> {
  return invoke<string[]>('list_system_fonts');
}

/**
 * Return `name` when present in `available`, otherwise JetBrains Mono.
 * Emits `FONT_UNAVAILABLE` to console for diagnostics.
 */
export function validateFontFamily(
  name: string,
  available: readonly string[],
): string {
  const trimmed = name.trim();
  if (!trimmed) {
    return FALLBACK_FONT;
  }
  const match = available.find(
    (f) => f.localeCompare(trimmed, undefined, { sensitivity: 'accent' }) === 0,
  );
  if (match) {
    return match;
  }
  console.warn(FONT_UNAVAILABLE);
  return FALLBACK_FONT;
}

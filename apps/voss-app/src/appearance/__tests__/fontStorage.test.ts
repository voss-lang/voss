import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
}));

vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  FALLBACK_FONT,
  FONT_UNAVAILABLE,
  listSystemFonts,
  validateFontFamily,
} from '../fontStorage';

describe('fontStorage', () => {
  beforeEach(() => {
    h.invoke.mockReset();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  it('listSystemFonts invokes list_system_fonts', async () => {
    h.invoke.mockResolvedValueOnce(['JetBrains Mono', 'Menlo']);
    const fonts = await listSystemFonts();
    expect(h.invoke).toHaveBeenCalledWith('list_system_fonts');
    expect(fonts).toEqual(['JetBrains Mono', 'Menlo']);
  });

  it('validateFontFamily returns requested font when available', () => {
    const available = ['JetBrains Mono', 'Menlo', 'SF Mono'];
    expect(validateFontFamily('Menlo', available)).toBe('Menlo');
  });

  it('validateFontFamily falls back to JetBrains Mono when unavailable', () => {
    const warn = vi.spyOn(console, 'warn');
    const available = ['JetBrains Mono', 'Menlo'];
    expect(validateFontFamily('Missing Font', available)).toBe(FALLBACK_FONT);
    expect(warn).toHaveBeenCalledWith(FONT_UNAVAILABLE);
  });

  it('validateFontFamily treats empty name as fallback', () => {
    expect(validateFontFamily('  ', ['JetBrains Mono'])).toBe(FALLBACK_FONT);
  });
});

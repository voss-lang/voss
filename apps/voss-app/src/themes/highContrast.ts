import type { RequiredCssVar } from './schema';

/** High-contrast overlay applied after the active theme (A8 UI-SPEC). */
export const HIGH_CONTRAST_OVERLAY: Partial<Record<RequiredCssVar, string>> = {
  '--bg-0': '#000',
  '--bg-1': '#050505',
  '--bg-2': '#101010',
  '--bg-3': '#181818',
  '--fg-0': '#fff',
  '--fg-1': '#f5f5f5',
  '--fg-2': '#d8d8d8',
  '--fg-3': '#b8b8b8',
  '--focus': '#ffff00',
  '--border-bright': '#fff',
};

import { getCurrentWindow, Effect } from '@tauri-apps/api/window';
import { platform } from '@tauri-apps/plugin-os';
import type { AppearanceSnapshot } from './profiles';

/** Linux never receives native window effects — CSS opacity only (A8-RESEARCH). */
export const LINUX_CSS_OPACITY_ONLY = true as const;

export type WindowPlatform = 'macos' | 'windows' | 'linux' | 'unknown';

let cachedPlatform: WindowPlatform | null = null;

function normalizePlatform(value: string): WindowPlatform {
  switch (value.toLowerCase()) {
    case 'macos':
    case 'darwin':
      return 'macos';
    case 'windows':
      return 'windows';
    case 'linux':
      return 'linux';
    default:
      return 'unknown';
  }
}

/** Sync platform hint from navigator when Tauri plugin is unavailable. */
function detectPlatformFromNavigator(): WindowPlatform {
  if (typeof navigator === 'undefined') {
    return 'unknown';
  }

  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('mac os') || ua.includes('macintosh')) {
    return 'macos';
  }
  if (ua.includes('windows')) {
    return 'windows';
  }
  if (ua.includes('linux') || ua.includes('x11')) {
    return 'linux';
  }

  const legacy = navigator.platform?.toLowerCase() ?? '';
  if (legacy.includes('mac')) return 'macos';
  if (legacy.includes('win')) return 'windows';
  if (legacy.includes('linux')) return 'linux';

  return 'unknown';
}

/** Detect host OS; uses cached Tauri `platform()` when available. */
export function detectPlatform(): WindowPlatform {
  if (cachedPlatform) {
    return cachedPlatform;
  }
  return detectPlatformFromNavigator();
}

async function resolvePlatform(): Promise<WindowPlatform> {
  if (cachedPlatform) {
    return cachedPlatform;
  }
  try {
    cachedPlatform = normalizePlatform(await platform());
  } catch {
    cachedPlatform = detectPlatformFromNavigator();
  }
  return cachedPlatform;
}

function clampOpacity(opacity: number | undefined): number | undefined {
  if (opacity === undefined || !Number.isFinite(opacity)) {
    return undefined;
  }
  return Math.min(1, Math.max(0.5, opacity));
}

/** Token-driven semi-transparent background for CSS-only platforms. */
function applyCssWindowOpacity(opacity: number | undefined): void {
  const root = document.documentElement;
  const clamped = clampOpacity(opacity);

  if (clamped === undefined) {
    root.style.removeProperty('--window-opacity-bg');
    root.style.background = 'var(--bg-0)';
    document.body.style.background = 'var(--bg-0)';
    return;
  }

  const mix = `color-mix(in srgb, var(--bg-0) ${Math.round(clamped * 100)}%, transparent)`;
  root.style.setProperty('--window-opacity-bg', mix);
  root.style.background = 'var(--window-opacity-bg)';
  document.body.style.background = 'var(--window-opacity-bg)';
}

function clearCssWindowOpacity(): void {
  const root = document.documentElement;
  root.style.removeProperty('--window-opacity-bg');
  root.style.background = 'var(--bg-0)';
  document.body.style.background = 'var(--bg-0)';
}

async function applyNativeWindowEffects(plat: WindowPlatform): Promise<void> {
  if (plat !== 'macos' && plat !== 'windows') {
    return;
  }

  try {
    const win = getCurrentWindow();
    const effects: Effect[] =
      plat === 'macos' ? [Effect.UnderWindowBackground] : [Effect.Tabbed];
    await win.setEffects({ effects });
  } catch (error) {
    console.warn('[voss-app] window effects unavailable:', error);
  }
}

async function clearNativeWindowEffects(): Promise<void> {
  try {
    const win = getCurrentWindow();
    await win.clearEffects();
  } catch {
    // Non-Tauri or unsupported — no-op.
  }
}

export interface WindowEffectsOptions {
  opacity?: number;
  /** When false, clears native effects and restores opaque `--bg-0`. */
  enabled?: boolean;
}

/**
 * Apply platform-gated window opacity / vibrancy.
 * macOS and Windows try native effects (fail soft). Linux uses CSS tokens only.
 */
export async function applyWindowEffects(
  options: WindowEffectsOptions = {},
): Promise<void> {
  const { opacity, enabled = true } = options;
  const plat = await resolvePlatform();

  if (!enabled) {
    await clearWindowEffects();
    return;
  }

  applyCssWindowOpacity(opacity);

  if (LINUX_CSS_OPACITY_ONLY && (plat === 'linux' || plat === 'unknown')) {
    return;
  }

  await applyNativeWindowEffects(plat);
}

/** Reset opaque CSS backgrounds and clear native effects when possible. */
export async function clearWindowEffects(): Promise<void> {
  clearCssWindowOpacity();
  await clearNativeWindowEffects();
}

/** Hook for profile / appearance apply paths. */
export async function initWindowEffectsFromAppearance(
  appearance: AppearanceSnapshot = {},
): Promise<void> {
  const opacity =
    typeof appearance.windowOpacity === 'number'
      ? appearance.windowOpacity
      : undefined;

  await applyWindowEffects({
    opacity,
    enabled: opacity === undefined ? true : opacity < 1,
  });
}

/** Test-only reset of cached platform detection. */
export function _resetWindowEffectsForTest(): void {
  cachedPlatform = null;
  clearCssWindowOpacity();
}

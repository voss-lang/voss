/**
 * Apply CSS variable overrides to :root.
 * Called once on boot from index.tsx (from get_theme_overrides result).
 * Called again by A8 settings UI on runtime theme change.
 */
export function applyThemeOverrides(overrides: Record<string, string>): void {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(overrides)) {
    root.style.setProperty(key, value);
  }
}

/**
 * A7-02 Task 1 — quick-open item builders for ⌘P palette mode (D-05).
 *
 * Converts saved layout names and recent project paths into palette rows
 * with `Layouts` and `Recent Projects` sections. No Tauri or Solid.
 */

export interface QuickOpenItem {
  id: string;
  label: string;
  section: 'Layouts' | 'Recent Projects';
  glyph: string;
  secondary?: string;
}

export function buildQuickOpenItems(
  layouts: readonly string[],
  recents: readonly string[],
): QuickOpenItem[] {
  const items: QuickOpenItem[] = [];
  for (const name of layouts) {
    items.push({
      id: `layout:${name}`,
      label: name,
      section: 'Layouts',
      glyph: 'L',
    });
  }
  for (const path of recents) {
    const name = path.split('/').pop() || path;
    items.push({
      id: `recent:${path}`,
      label: name,
      section: 'Recent Projects',
      glyph: 'R',
      secondary: path,
    });
  }
  return items;
}

/** Simple case-insensitive filter for quick-open items. */
export function filterQuickItems(
  items: readonly QuickOpenItem[],
  query: string,
): QuickOpenItem[] {
  if (!query) return [...items];
  const q = query.toLowerCase();
  return items.filter(
    (item) =>
      item.label.toLowerCase().includes(q) ||
      (item.secondary?.toLowerCase().includes(q) ?? false),
  );
}

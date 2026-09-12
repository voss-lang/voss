export interface QuickOpenItem {
  id: string;
  label: string;
  section: 'Layouts' | 'Recent Projects';
  glyph: string;
  secondary?: string;
}

export interface DirEntryLike {
  name: string;
  is_dir: boolean;
  children?: DirEntryLike[];
}

/** Workspace-relative file paths from a `list_dir` result, depth first */
export function flattenFiles(entries: readonly DirEntryLike[], prefix = ''): string[] {
  const out: string[] = [];
  for (const e of entries) {
    const path = prefix ? `${prefix}/${e.name}` : e.name;
    if (e.is_dir) out.push(...flattenFiles(e.children ?? [], path));
    else out.push(path);
  }
  return out;
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

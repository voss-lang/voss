// V24-02 (VADE2-02) — PortalView contract. Wave-0 interface consumed by
// PortalRail, PortalShell, App.tsx, and every downstream V24 surface
// (V24-03 chrome, V24-05 mission control, V24-06 Swarm Map).
//
// The 9-member union widens the old binary `orgViewOpen` toggle into the
// left-portal navigation model. `'grid'` is now the FIRST portal item
// ("Workspaces") and remains the terminal canvas-swap default (D-01/D-02).
// Selecting Workspaces routes back to activeView='grid' without remounting the
// grid host. Labels use the locked vocabulary from apps/voss-app/PRODUCT.md
// §Locked Vocabulary ("Tasks" not "Runs", "Swarm Map").

export type PortalView =
  | 'grid'
  | 'overview'
  | 'tasks'
  | 'agents'
  | 'swarm-map'
  | 'review'
  | 'context'
  | 'memory'
  | 'settings';

export interface PortalItem {
  id: PortalView;
  label: string;
  glyph: string;
}

// The 9 navigable portal items in UI-SPEC §Component Inventory 1 order.
// The first item returns to the canvas-swap grid host.
export const PORTAL_ITEMS: readonly PortalItem[] = [
  { id: 'grid', label: 'Workspaces', glyph: '▦' },
  { id: 'overview', label: 'Overview', glyph: '⊞' },
  { id: 'tasks', label: 'Tasks', glyph: '✓' },
  { id: 'agents', label: 'Agents', glyph: '⬡' },
  { id: 'swarm-map', label: 'Swarm Map', glyph: '◈' },
  { id: 'review', label: 'Review', glyph: '※' },
  { id: 'context', label: 'Context', glyph: '≡' },
  { id: 'memory', label: 'Memory', glyph: '◉' },
  { id: 'settings', label: 'Settings', glyph: '⚙' },
];
// V24-02 (VADE2-02) — PortalView contract. Wave-0 interface consumed by
// PortalRail, PortalShell, App.tsx, and every downstream V24 surface
// (V24-03 chrome, V24-05 mission control, V24-06 Swarm Map).
//
// The 9-member union widens the old binary `orgViewOpen` toggle into the
// 8-way left-portal navigation model. `'grid'` is the underlying terminal
// canvas (canvas-swap default, D-01/D-02) — it is NOT a portal nav item, so
// it is excluded from PORTAL_ITEMS. Labels use the locked vocabulary from
// apps/voss-app/PRODUCT.md §Locked Vocabulary ("Tasks" not "Runs", "Swarm Map").

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

// The 8 navigable portal items in UI-SPEC §Component Inventory 1 order.
// 'grid' is intentionally absent — it is the canvas behind the portal, not a tab.
export const PORTAL_ITEMS: readonly PortalItem[] = [
  { id: 'overview', label: 'Overview', glyph: '⊞' },
  { id: 'tasks', label: 'Tasks', glyph: '✓' },
  { id: 'agents', label: 'Agents', glyph: '⬡' },
  { id: 'swarm-map', label: 'Swarm Map', glyph: '◈' },
  { id: 'review', label: 'Review', glyph: '※' },
  { id: 'context', label: 'Context', glyph: '≡' },
  { id: 'memory', label: 'Memory', glyph: '◉' },
  { id: 'settings', label: 'Settings', glyph: '⚙' },
];

// Identify swarm categories for ingestion into the swarm map to be tracked and presented to the user
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

export const PORTAL_ITEMS: readonly PortalItem[] = [
  { id: 'grid', label: 'Workspaces', glyph: '▦' },
  { id: 'overview', label: 'Overview', glyph: '⊞' },
  { id: 'tasks', label: 'Tasks', glyph: '✓' },
  { id: 'agents', label: 'Agents', glyph: '⬡' },
  { id: 'swarm-map', label: 'Orchestra', glyph: '◈' },
  { id: 'review', label: 'Review', glyph: '※' },
  { id: 'context', label: 'Context', glyph: '≡' },
  { id: 'memory', label: 'Memory', glyph: '◉' },
  { id: 'settings', label: 'Settings', glyph: '⚙' },
];

import { For, Show } from 'solid-js';
import type { RunData, SessionTreeNode } from '../types';

// VADE-01 — team roster: role rows with role-color dots + status badges,
// derived from audit.team_config.roster_ids ∪ distinct node roles.

export interface RosterRow {
  role: string;
  status: 'active' | 'idle' | 'done';
}

function roleColor(role: string): string {
  switch (role) {
    case 'planner':
    case 'pm':
      return 'var(--role-planner)';
    case 'reviewer':
    case 'reviewer-a':
    case 'reviewer-b':
      return 'var(--role-reviewer)';
    case 'watcher':
      return 'var(--role-watcher)';
    case 'user':
      return 'var(--role-user)';
    default:
      return 'var(--role-executor)';
  }
}

function statusForRole(
  role: string,
  nodes: SessionTreeNode[],
): RosterRow['status'] {
  const node = nodes.find((n) => n.role === role);
  if (!node) return 'idle';
  const ts = node.terminal_state;
  if (ts?.exit_reason === 'done') return 'done';
  if (!ts) return 'active';
  return 'idle';
}

// Exported for the V14 cockpit team sidebar (chunk B): the sidebar reuses this
// derivation (audit.team_config.roster_ids ∪ distinct node roles + status) but
// renders the mockup .arow visual instead of this panel's row style.
export function rosterRows(data: RunData): RosterRow[] {
  const rosterIds = data.audit?.team_config?.roster_ids ?? [];
  const nodeRoles = data.session_tree.nodes
    .map((n) => n.role)
    .filter((r): r is string => r != null);
  const roles = [...new Set([...rosterIds, ...nodeRoles])];
  return roles.map((role) => ({ role, status: statusForRole(role, data.session_tree.nodes) }));
}

function badgeStyle(status: RosterRow['status']) {
  const isActive = status === 'active';
  return {
    color: isActive ? 'var(--accent-green)' : 'var(--fg-3)',
    background: isActive ? 'rgba(94,194,106,0.12)' : 'var(--bg-2)',
    'border-radius': '9999px',
    padding: '0 4px',
    height: '16px',
    display: 'inline-flex',
    'align-items': 'center',
    'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
    'font-size': '11px',
    'font-weight': '500',
  } as const;
}

export default function RosterPanel(props: { data: RunData | null }) {
  const rows = () => (props.data ? rosterRows(props.data) : []);

  return (
    <div class="org-panel">
      <Show
        when={rows().length > 0}
        fallback={<div class="org-empty">No roster data for this run.</div>}
      >
        <div
          style={{
            'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
            'font-size': '11px',
            'font-weight': '500',
            'text-transform': 'uppercase',
            'letter-spacing': '0.08em',
            color: 'var(--fg-3)',
            padding: '8px 16px 4px',
          }}
        >
          ROSTER
        </div>
        <For each={rows()}>
          {(row) => (
            <div
              style={{
                display: 'flex',
                'align-items': 'center',
                gap: '8px',
                height: '36px',
                padding: '0 16px',
                'border-bottom': '1px solid var(--border)',
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  'border-radius': '50%',
                  background: roleColor(row.role),
                  'flex-shrink': '0',
                }}
              />
              <span
                style={{
                  'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                  'font-size': '11px',
                  'font-weight': '500',
                  'text-transform': 'uppercase',
                  color: 'var(--fg-1)',
                  overflow: 'hidden',
                  'text-overflow': 'ellipsis',
                  'white-space': 'nowrap',
                }}
              >
                {row.role}
              </span>
              <span
                style={{
                  'font-family': 'var(--font-mono), monospace',
                  'font-size': '11px',
                  color: 'var(--fg-2)',
                }}
              >
                {row.role}
              </span>
              <span style={{ 'margin-left': 'auto', ...badgeStyle(row.status) }}>
                {row.status}
              </span>
            </div>
          )}
        </For>
      </Show>
    </div>
  );
}

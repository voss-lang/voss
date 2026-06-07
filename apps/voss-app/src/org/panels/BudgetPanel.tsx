import { For, Show, createSignal } from 'solid-js';
import type { RunData, SessionTreeNode } from '../types';

// VADE-06 — budget allocation/consumption per root / per card / per agent.
// Bar thresholds match the grid BudgetBar (<70 green / 70-90 amber / >90 red);
// logic is inlined (the grid component expects a different prop shape).

interface BudgetRow {
  name: string;
  limit: number;
  spent: number;
}

function pctOf(row: BudgetRow): number {
  return row.limit > 0 ? (row.spent / row.limit) * 100 : 0;
}

function barColor(pct: number): string {
  return pct >= 90
    ? 'var(--accent-red)'
    : pct >= 70
      ? 'var(--accent-amber)'
      : 'var(--accent-green)';
}

function rootRows(nodes: SessionTreeNode[]): BudgetRow[] {
  return nodes
    .filter((n) => n.parent_run_id === null)
    .map((n) => ({ name: n.id, limit: n.envelope.limit, spent: n.envelope.spent }));
}

function cardRows(nodes: SessionTreeNode[]): BudgetRow[] {
  return nodes
    .filter((n) => n.parent_run_id !== null)
    .map((n) => ({ name: n.id, limit: n.envelope.limit, spent: n.envelope.spent }));
}

function agentRows(nodes: SessionTreeNode[]): BudgetRow[] {
  const byRole = new Map<string, BudgetRow>();
  for (const n of nodes) {
    const role = n.role ?? 'unknown';
    const cur = byRole.get(role) ?? { name: role, limit: 0, spent: 0 };
    cur.limit += n.envelope.limit;
    cur.spent += n.envelope.spent;
    byRole.set(role, cur);
  }
  return [...byRole.values()];
}

const monoMeta = {
  'font-family': 'var(--font-mono), monospace',
  'font-size': '11px',
  color: 'var(--fg-2)',
} as const;

function BudgetSection(props: { title: string; rows: BudgetRow[] }) {
  const [open, setOpen] = createSignal(true);
  const totalLimit = () => props.rows.reduce((s, r) => s + r.limit, 0);
  const totalSpent = () => props.rows.reduce((s, r) => s + r.spent, 0);
  return (
    <div>
      <div
        onClick={() => setOpen((o) => !o)}
        style={{
          display: 'flex',
          'align-items': 'center',
          gap: '6px',
          height: '32px',
          padding: '0 16px',
          cursor: 'pointer',
          'border-bottom': '1px solid var(--border)',
        }}
      >
        <span style={{ ...monoMeta, color: 'var(--fg-3)' }}>{open() ? '▾' : '▸'}</span>
        <span
          style={{
            'font-family': 'var(--font-display), Poppins, system-ui, sans-serif',
            'font-size': '11px',
            'font-weight': '500',
            'text-transform': 'uppercase',
            'letter-spacing': '0.08em',
            color: 'var(--fg-3)',
          }}
        >
          {props.title}
        </span>
        <span style={{ ...monoMeta, 'margin-left': 'auto' }}>
          {totalSpent()} / {totalLimit()}
        </span>
      </div>
      <Show when={open()}>
        <For each={props.rows}>
          {(row) => {
            const pct = pctOf(row);
            const over = row.spent >= row.limit && row.limit > 0;
            return (
              <div
                style={{
                  display: 'flex',
                  'align-items': 'center',
                  gap: '8px',
                  height: '28px',
                  padding: '0 16px',
                  background: over ? 'rgba(232,123,123,0.06)' : 'transparent',
                }}
              >
                <span
                  style={{
                    flex: '1',
                    'min-width': '0',
                    'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                    'font-size': '12px',
                    color: 'var(--fg-1)',
                    overflow: 'hidden',
                    'text-overflow': 'ellipsis',
                    'white-space': 'nowrap',
                  }}
                >
                  {row.name}
                </span>
                <span style={monoMeta}>{row.limit}</span>
                <div style={{ width: '80px', height: '4px', background: 'var(--bg-3)' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, pct)}%`,
                      background: barColor(pct),
                    }}
                  />
                </div>
                <span style={{ ...monoMeta, 'min-width': '40px', 'text-align': 'right' }}>
                  {pct.toFixed(0)}%
                </span>
              </div>
            );
          }}
        </For>
      </Show>
    </div>
  );
}

export default function BudgetPanel(props: { data: RunData | null }) {
  const nodes = () => props.data?.session_tree.nodes ?? [];

  return (
    <div class="org-panel">
      <Show
        when={nodes().length > 0}
        fallback={<div class="org-empty">No budget data for this run.</div>}
      >
        <div style={{ flex: '1', 'overflow-y': 'auto' }}>
          <BudgetSection title="Per Root" rows={rootRows(nodes())} />
          <BudgetSection title="Per Card" rows={cardRows(nodes())} />
          <BudgetSection title="Per Agent" rows={agentRows(nodes())} />
        </div>
      </Show>
    </div>
  );
}

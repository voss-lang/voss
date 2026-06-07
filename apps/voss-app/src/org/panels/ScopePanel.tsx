import { For, Show, createSignal } from 'solid-js';
import type { RunData, SessionTreeNode } from '../types';

// VADE-07 — declared scope per role / per card.
// NOTE: out-of-scope detection has no persisted source in the V2-V7 substrate
// (confirmed in RESEARCH). The ⚑ flag is therefore data-driven and currently
// inert — `isOutOfScope` returns false until a harness field exists.

function isOutOfScope(_node: SessionTreeNode): boolean {
  return false;
}

interface ScopeRow {
  name: string;
  scope: string | null;
  node: SessionTreeNode;
}

function roleRows(nodes: SessionTreeNode[]): ScopeRow[] {
  const byRole = new Map<string, SessionTreeNode>();
  for (const n of nodes) {
    const role = n.role ?? 'unknown';
    if (!byRole.has(role)) byRole.set(role, n);
  }
  return [...byRole.entries()].map(([role, node]) => ({
    name: role,
    scope: node.scope,
    node,
  }));
}

function cardRows(nodes: SessionTreeNode[]): ScopeRow[] {
  return nodes
    .filter((n) => n.parent_run_id !== null)
    .map((n) => ({ name: n.id, scope: n.scope, node: n }));
}

const monoMeta = {
  'font-family': 'var(--font-mono), monospace',
  'font-size': '11px',
  color: 'var(--fg-3)',
} as const;

function ScopeTags(props: { scope: string | null }) {
  return (
    <Show when={props.scope} fallback={<span style={monoMeta}>—</span>}>
      <span
        style={{
          'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
          'font-size': '11px',
          'font-weight': '500',
          color: 'var(--fg-2)',
          background: 'var(--bg-3)',
          'border-radius': '3px',
          padding: '0 4px',
        }}
      >
        {props.scope}
      </span>
    </Show>
  );
}

function ScopeSection(props: { title: string; rows: ScopeRow[] }) {
  const [open, setOpen] = createSignal(true);
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
        <span style={monoMeta}>{open() ? '▾' : '▸'}</span>
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
      </div>
      <Show when={open()}>
        <For each={props.rows}>
          {(row) => (
            <div
              style={{
                display: 'flex',
                'align-items': 'center',
                gap: '8px',
                'min-height': '28px',
                padding: '4px 16px',
              }}
            >
              <span
                style={{
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
              <Show when={isOutOfScope(row.node)}>
                <span
                  aria-label="Out of scope"
                  style={{ color: 'var(--accent-red)', 'font-size': '13px' }}
                >
                  ⚑
                </span>
              </Show>
              <span style={{ 'margin-left': 'auto' }}>
                <ScopeTags scope={row.scope} />
              </span>
            </div>
          )}
        </For>
      </Show>
    </div>
  );
}

export default function ScopePanel(props: { data: RunData | null }) {
  const nodes = () => props.data?.session_tree.nodes ?? [];

  return (
    <div class="org-panel">
      <Show
        when={nodes().length > 0}
        fallback={<div class="org-empty">No scope data for this run.</div>}
      >
        <div style={{ flex: '1', 'overflow-y': 'auto' }}>
          <ScopeSection title="Per Role" rows={roleRows(nodes())} />
          <ScopeSection title="Per Card" rows={cardRows(nodes())} />
        </div>
      </Show>
    </div>
  );
}

import { For, Show, createSignal } from 'solid-js';
import type { RunData, SessionTreeNode } from '../types';
import { buildTree, type TreeNode } from '../treeBuild';

// VADE-03 — navigable parent→child session tree with expand/collapse,
// selection, and a metadata strip for the selected node.

function roleColor(role: string | null): string {
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

function statusOf(node: SessionTreeNode): string {
  const ts = node.terminal_state;
  if (!ts) return 'active';
  if (ts.exit_reason === 'done') return 'done';
  return 'blocked';
}

function statusColor(status: string): string {
  return status === 'done'
    ? 'var(--accent-green)'
    : status === 'blocked'
      ? 'var(--accent-red)'
      : 'var(--fg-3)';
}

function ellipsis(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

export default function SessionTreePanel(props: { data: RunData | null }) {
  const [expanded, setExpanded] = createSignal<Set<string>>(new Set());
  const [selectedId, setSelectedId] = createSignal<string | null>(null);

  const roots = () => buildTree(props.data?.session_tree.nodes ?? []);
  const flatNodes = () => props.data?.session_tree.nodes ?? [];
  const selectedNode = () =>
    flatNodes().find((n) => n.id === selectedId()) ?? null;

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  function Row(rowProps: { node: TreeNode; depth: number }) {
    const node = rowProps.node;
    const isExpandable = node.children.length > 0;
    const isOpen = () => expanded().has(node.id);
    const status = statusOf(node);
    return (
      <>
        <div
          data-node-id={node.id}
          role="treeitem"
          aria-expanded={isExpandable ? isOpen() : undefined}
          onClick={() => setSelectedId(node.id)}
          style={{
            display: 'flex',
            'align-items': 'center',
            gap: '6px',
            height: '28px',
            'padding-right': '8px',
            'padding-left': `${8 + rowProps.depth * 16}px`,
            cursor: 'pointer',
            background: selectedId() === node.id ? 'var(--focus-soft)' : 'transparent',
            'border-left':
              selectedId() === node.id ? '2px solid var(--focus)' : '2px solid transparent',
          }}
        >
          <Show
            when={isExpandable}
            fallback={
              <span style={{ color: 'var(--fg-3)', 'font-size': '8px', width: '11px' }}>●</span>
            }
          >
            <span
              class="org-tree-toggle"
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                toggle(node.id);
              }}
              style={{
                'font-family': 'var(--font-mono), monospace',
                'font-size': '11px',
                color: 'var(--fg-3)',
                width: '11px',
                cursor: 'pointer',
              }}
            >
              {isOpen() ? '▾' : '▸'}
            </span>
          </Show>
          <span
            style={{
              'font-family': 'var(--font-mono), monospace',
              'font-size': '11px',
              color: 'var(--fg-1)',
            }}
          >
            {ellipsis(node.id, 20)}
          </span>
          <Show when={node.role}>
            <span
              style={{
                'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                'font-size': '11px',
                'font-weight': '500',
                color: roleColor(node.role),
                background: 'color-mix(in srgb, currentColor 20%, transparent)',
                'border-radius': '3px',
                padding: '0 4px',
              }}
            >
              {node.role}
            </span>
          </Show>
          <span
            style={{
              width: '6px',
              height: '6px',
              'border-radius': '50%',
              background: statusColor(status),
            }}
          />
          <span
            style={{
              'margin-left': 'auto',
              'font-family': 'var(--font-mono), monospace',
              'font-size': '11px',
              color: 'var(--fg-3)',
            }}
          >
            {node.envelope.spent}
          </span>
        </div>
        <Show when={isExpandable && isOpen()}>
          <For each={node.children}>
            {(child) => <Row node={child} depth={rowProps.depth + 1} />}
          </For>
        </Show>
      </>
    );
  }

  return (
    <div class="org-panel">
      <Show
        when={roots().length > 0}
        fallback={
          <div class="org-empty">No session tree data for this run.</div>
        }
      >
        <div role="tree" style={{ flex: '1', 'overflow-y': 'auto' }}>
          <For each={roots()}>{(r) => <Row node={r} depth={0} />}</For>
        </div>
        <Show when={selectedNode()}>
          {(node) => (
            <div
              class="org-tree-meta"
              style={{
                height: '72px',
                'box-sizing': 'border-box',
                background: 'var(--bg-1)',
                'border-top': '1px solid var(--border)',
                padding: '8px 16px',
                'font-family': 'var(--font-ui), Inter, system-ui, sans-serif',
                'font-size': '12px',
                color: 'var(--fg-2)',
                display: 'flex',
                'flex-direction': 'column',
                gap: '2px',
                overflow: 'hidden',
              }}
            >
              <div>id: {node().id}</div>
              <div>role: {node().role ?? '—'}</div>
              <div>
                budget: {node().envelope.spent} / {node().envelope.limit}
              </div>
              <div>status: {statusOf(node())}</div>
              <div>parent: {node().parent_run_id ?? '—'}</div>
            </div>
          )}
        </Show>
      </Show>
    </div>
  );
}

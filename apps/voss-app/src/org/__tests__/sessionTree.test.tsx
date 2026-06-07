import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import { buildTree } from '../treeBuild';
import SessionTreePanel from '../panels/SessionTreePanel';
import type { RunData, SessionTreeNode } from '../types';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';

const FIXTURE_RUN_DATA = {
  run_id: nodeRoot.root_id,
  session_tree: { root_id: nodeRoot.root_id, nodes: [nodeRoot, nodeChild] },
  review: {},
  audit: null,
  run_final: null,
} as unknown as RunData;

const ROOT = nodeRoot as unknown as SessionTreeNode;
const CHILD = nodeChild as unknown as SessionTreeNode;

function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T;
}

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

// --- VADE-03: buildTree -------------------------------------------------------

describe('buildTree — flat nodes → parent→child', () => {
  it('root + child fixture → 1 root with 1 child', () => {
    const roots = buildTree([ROOT, CHILD]);
    expect(roots).toHaveLength(1);
    expect(roots[0].id).toBe(ROOT.id);
    expect(roots[0].children).toHaveLength(1);
    expect(roots[0].children[0].id).toBe(CHILD.id);
  });

  it('empty array → []', () => {
    expect(buildTree([])).toEqual([]);
  });

  it('orphan (unknown parent) is not lost — attached at root level', () => {
    const orphan = clone(CHILD);
    orphan.parent_run_id = 'nonexistent999';
    const roots = buildTree([ROOT, orphan]);
    const ids = roots.map((r) => r.id).sort();
    expect(ids).toEqual([ROOT.id, orphan.id].sort());
  });
});

// --- VADE-03: SessionTreePanel render ----------------------------------------

function rowFor(root: HTMLElement, id: string): HTMLElement | null {
  return root.querySelector(`[data-node-id="${id}"]`);
}

describe('SessionTreePanel — navigable tree', () => {
  it('renders the root node; child hidden until expanded', () => {
    const root = mount(() => <SessionTreePanel data={FIXTURE_RUN_DATA} />);
    expect(rowFor(root, ROOT.id)).toBeTruthy();
    expect(rowFor(root, CHILD.id)).toBeNull(); // collapsed by default
  });

  it('expanding the root reveals the child', () => {
    const root = mount(() => <SessionTreePanel data={FIXTURE_RUN_DATA} />);
    const toggle = root.querySelector(
      `[data-node-id="${ROOT.id}"] .org-tree-toggle`,
    ) as HTMLElement;
    toggle.click();
    expect(rowFor(root, CHILD.id)).toBeTruthy();
  });

  it('selecting a node shows its metadata', () => {
    const root = mount(() => <SessionTreePanel data={FIXTURE_RUN_DATA} />);
    (rowFor(root, ROOT.id) as HTMLElement).click();
    const meta = root.querySelector('.org-tree-meta') as HTMLElement;
    expect(meta).toBeTruthy();
    expect(meta.textContent).toContain(ROOT.id);
    expect(meta.textContent).toContain('user'); // root role
  });

  it('null data → empty-state copy', () => {
    const root = mount(() => <SessionTreePanel data={null} />);
    expect(root.textContent).toContain('No session tree data for this run.');
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  loadWorkspacesIndex: vi.fn(),
  saveWorkspacesIndex: vi.fn(),
}));
vi.mock('../workspaceStorage', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../workspaceStorage')>();
  return {
    ...actual,
    loadWorkspacesIndex: h.loadWorkspacesIndex,
    saveWorkspacesIndex: h.saveWorkspacesIndex,
  };
});

import { closeGuardFor, createWorkspaceStore } from '../workspaceStore';
import { CURRENT_WORKSPACES_VERSION } from '../workspaceStorage';

describe('workspaceStore — add / activate', () => {
  it('add appends a workspace, activates it, and assigns order', () => {
    const store = createWorkspaceStore();
    const added = store.add({ id: 'b', name: 'Beta' });
    expect(added.id).toBe('b');
    expect(added.order).toBe(1);
    expect(store.workspaces()).toHaveLength(2);
    expect(store.activeId()).toBe('b');
  });

  it('activate switches activeId without changing workspace count', () => {
    const store = createWorkspaceStore();
    store.add({ id: 'b', name: 'Beta' });
    store.activate('default');
    expect(store.activeId()).toBe('default');
  });
});

describe('workspaceStore — reorder', () => {
  it('reorder moves tabs and renumbers order fields', () => {
    const store = createWorkspaceStore();
    store.add({ id: 'b', name: 'Beta' });
    store.add({ id: 'c', name: 'Gamma' });
    store.reorder(2, 0);
    expect(store.workspaces().map((w) => w.id)).toEqual(['c', 'default', 'b']);
    expect(store.workspaces().map((w) => w.order)).toEqual([0, 1, 2]);
  });
});

describe('workspaceStore — close guard (UXP-08)', () => {
  it('last workspace cannot close', () => {
    const store = createWorkspaceStore();
    const guard = store.closeGuardFor('default');
    expect(guard.isLastWorkspace).toBe(true);
    expect(guard.canClose).toBe(false);
    expect(store.canClose('default')).toBe(false);
  });

  it('multi-workspace allows close', () => {
    const store = createWorkspaceStore();
    store.add({ id: 'b', name: 'Beta' });
    const guard = store.closeGuardFor('default');
    expect(guard.isLastWorkspace).toBe(false);
    expect(guard.canClose).toBe(true);
    expect(store.canClose('default')).toBe(true);
  });

  it('closeGuardFor helper matches store metadata', () => {
    const workspaces = [
      { id: 'a', name: 'A', accentColor: 'blue', order: 0 },
      { id: 'b', name: 'B', accentColor: 'red', order: 1 },
    ];
    expect(closeGuardFor(workspaces, 'a').canClose).toBe(true);
    expect(closeGuardFor([workspaces[0]], 'a').canClose).toBe(false);
  });
});

describe('workspaceStore — persist / load', () => {
  beforeEach(() => {
    h.loadWorkspacesIndex.mockReset();
    h.saveWorkspacesIndex.mockReset();
    h.saveWorkspacesIndex.mockResolvedValue(undefined);
  });

  it('persist writes snapshot via saveWorkspacesIndex', async () => {
    const store = createWorkspaceStore();
    store.rename('default', 'Main');
    await store.persist();
    expect(h.saveWorkspacesIndex).toHaveBeenCalledWith({
      version: CURRENT_WORKSPACES_VERSION,
      activeWorkspaceId: 'default',
      workspaces: expect.arrayContaining([
        expect.objectContaining({ id: 'default', name: 'Main' }),
      ]),
    });
  });

  it('load hydrates workspaces and active id from disk', async () => {
    h.loadWorkspacesIndex.mockResolvedValueOnce({
      version: CURRENT_WORKSPACES_VERSION,
      activeWorkspaceId: 'b',
      workspaces: [
        { id: 'a', name: 'A', accentColor: 'blue', order: 0 },
        { id: 'b', name: 'B', accentColor: 'red', order: 1 },
      ],
    });
    const store = createWorkspaceStore();
    await store.load();
    expect(store.activeId()).toBe('b');
    expect(store.workspaces()).toHaveLength(2);
  });
});

describe('workspaceStore — rename, accent, pinned profile', () => {
  it('rename and setAccentColor update the targeted record', () => {
    const store = createWorkspaceStore();
    store.rename('default', 'Main');
    store.setAccentColor('default', 'purple');
    store.setPinnedProfile('default', 'work');
    const w = store.workspaces()[0];
    expect(w.name).toBe('Main');
    expect(w.accentColor).toBe('purple');
    expect(w.pinnedProfile).toBe('work');
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { makePane, makeSplit } from '../../grid/tree';

const h = vi.hoisted(() => ({
  onCloseRequested: vi.fn(),
  close: vi.fn(),
  saveSession: vi.fn(),
  saveProjectLessSession: vi.fn(),
  saveIndex: vi.fn(),
  buildSessionFile: vi.fn(),
  getScrollbackSnapshot: vi.fn(),
}));

vi.mock('@tauri-apps/api/window', () => ({
  getCurrentWindow: vi.fn(() => ({
    onCloseRequested: h.onCloseRequested,
    close: h.close,
  })),
}));

vi.mock('../../grid/sessionStorage', () => ({
  saveSession: h.saveSession,
}));

vi.mock('../../grid/sessionCommands', () => ({
  buildSessionFile: h.buildSessionFile,
}));

vi.mock('../../pane/scrollbackRegistry', () => ({
  getScrollbackSnapshot: h.getScrollbackSnapshot,
}));

vi.mock('../workspaceStorage', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../workspaceStorage')>();
  return {
    ...actual,
    saveProjectLessSession: h.saveProjectLessSession,
  };
});

import {
  installAllWorkspacesCloseSave,
  type WorkspaceSessionContext,
} from '../workspaceSessionPersist';
import { CURRENT_WORKSPACES_VERSION } from '../workspaceStorage';

function mockController(id: string) {
  const pane = makePane({ cwd: `/tmp/${id}` });
  return {
    snapshot: () => ({
      root: makeSplit('H', pane, makePane({ cwd: `/tmp/${id}-b` })),
      focusedId: pane.id,
    }),
  };
}

describe('installAllWorkspacesCloseSave', () => {
  let closeHandler: ((event: { preventDefault: () => void }) => Promise<void>) | undefined;

  beforeEach(async () => {
    h.onCloseRequested.mockReset();
    h.close.mockReset();
    h.saveSession.mockReset();
    h.saveProjectLessSession.mockReset();
    h.saveIndex.mockReset();
    h.buildSessionFile.mockReset();
    h.getScrollbackSnapshot.mockReset();

    h.onCloseRequested.mockImplementation((cb) => {
      closeHandler = cb;
      return Promise.resolve(() => {});
    });
    h.saveSession.mockResolvedValue(undefined);
    h.saveProjectLessSession.mockResolvedValue(undefined);
    h.saveIndex.mockResolvedValue(undefined);
    h.buildSessionFile.mockReturnValue({
      version: 1,
      activePreset: null,
      grid: { root: {}, focusedId: 'x' },
      panes: [],
      projectLessAccepted: true,
    });
    h.getScrollbackSnapshot.mockReturnValue(new Map());

    const contexts: WorkspaceSessionContext[] = [
      {
        workspaceId: 'ws-a',
        getController: () => mockController('a') as never,
        getActiveLayout: () => 'custom',
        getProjectLessAccepted: () => true,
        projectPath: '/proj/a',
      },
      {
        workspaceId: 'ws-b',
        getController: () => mockController('b') as never,
        getActiveLayout: () => 'custom',
        getProjectLessAccepted: () => true,
        projectPath: null,
      },
    ];

    await installAllWorkspacesCloseSave(
      () => contexts,
      () => ({
        version: CURRENT_WORKSPACES_VERSION,
        activeWorkspaceId: 'ws-a',
        workspaces: [],
      }),
      h.saveIndex,
    );
  });

  afterEach(() => {
    closeHandler = undefined;
  });

  it('saves each workspace session once on close, then persists index', async () => {
    const preventDefault = vi.fn();
    await closeHandler!({ preventDefault });

    expect(preventDefault).toHaveBeenCalledTimes(1);
    expect(h.buildSessionFile).toHaveBeenCalledTimes(2);
    expect(h.saveSession).toHaveBeenCalledTimes(1);
    expect(h.saveSession).toHaveBeenCalledWith(
      '/proj/a',
      expect.objectContaining({ projectLessAccepted: true }),
    );
    expect(h.saveProjectLessSession).toHaveBeenCalledTimes(1);
    expect(h.saveProjectLessSession).toHaveBeenCalledWith(
      'ws-b',
      expect.objectContaining({ projectLessAccepted: true }),
    );
    expect(h.saveIndex).toHaveBeenCalledTimes(1);
    expect(h.close).toHaveBeenCalledTimes(1);
  });

  it('reentry guard allows second close without duplicate saves', async () => {
    const preventDefault = vi.fn();
    await closeHandler!({ preventDefault });
    h.buildSessionFile.mockClear();
    h.saveSession.mockClear();
    h.saveProjectLessSession.mockClear();
    h.saveIndex.mockClear();

    await closeHandler!({ preventDefault });

    expect(h.buildSessionFile).not.toHaveBeenCalled();
    expect(h.saveSession).not.toHaveBeenCalled();
    expect(h.saveProjectLessSession).not.toHaveBeenCalled();
    expect(h.saveIndex).not.toHaveBeenCalled();
    expect(preventDefault).not.toHaveBeenCalled();
  });
});

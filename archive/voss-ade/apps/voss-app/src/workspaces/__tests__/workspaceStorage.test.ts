import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({ invoke: vi.fn() }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));

import {
  WORKSPACES_SAVE_FAILED,
  CURRENT_WORKSPACES_VERSION,
  loadWorkspacesIndex,
  saveWorkspacesIndex,
  listWorkspaces,
  saveProjectLessSession,
  loadProjectLessSession,
  type WorkspacesIndex,
} from '../workspaceStorage';
import type { SessionFile } from '../../grid/sessionStorage';

function makeIndex(): WorkspacesIndex {
  return {
    version: CURRENT_WORKSPACES_VERSION,
    activeWorkspaceId: 'default',
    workspaces: [
      {
        id: 'default',
        name: 'Workspace',
        accentColor: 'blue',
        order: 0,
      },
    ],
  };
}

function makeSession(): SessionFile {
  return {
    version: 1,
    activePreset: null,
    grid: {
      root: {
        kind: 'pane',
        id: 'a',
        cwd: '/tmp',
        shell: 'zsh',
        index: 1,
      },
      focusedId: 'a',
    },
    panes: [],
    projectLessAccepted: true,
  };
}

describe('workspaceStorage — error copy constants', () => {
  it('matches Rust WorkspacesError::Display strings', () => {
    expect(WORKSPACES_SAVE_FAILED).toBe('could not save workspaces index');
  });
});

describe('workspaceStorage — workspace index commands', () => {
  beforeEach(() => h.invoke.mockReset());

  it('loadWorkspacesIndex → invoke("load_workspaces_index")', async () => {
    const index = makeIndex();
    h.invoke.mockResolvedValueOnce(index);
    const got = await loadWorkspacesIndex();
    expect(h.invoke).toHaveBeenCalledWith('load_workspaces_index');
    expect(got).toBe(index);
  });

  it('saveWorkspacesIndex → invoke("save_workspaces_index", { index })', async () => {
    h.invoke.mockResolvedValueOnce(undefined);
    const index = makeIndex();
    await saveWorkspacesIndex(index);
    expect(h.invoke).toHaveBeenCalledWith('save_workspaces_index', { index });
  });

  it('listWorkspaces → invoke("list_workspaces")', async () => {
    const workspaces = makeIndex().workspaces;
    h.invoke.mockResolvedValueOnce(workspaces);
    const got = await listWorkspaces();
    expect(h.invoke).toHaveBeenCalledWith('list_workspaces');
    expect(got).toBe(workspaces);
  });
});

describe('workspaceStorage — project-less session commands', () => {
  beforeEach(() => h.invoke.mockReset());

  it('saveProjectLessSession → invoke with workspaceId + session', async () => {
    h.invoke.mockResolvedValueOnce(undefined);
    const session = makeSession();
    await saveProjectLessSession('ws-1', session);
    expect(h.invoke).toHaveBeenCalledWith('save_project_less_session', {
      workspaceId: 'ws-1',
      session,
    });
  });

  it('loadProjectLessSession → invoke with workspaceId', async () => {
    h.invoke.mockResolvedValueOnce(null);
    const missing = await loadProjectLessSession('ws-1');
    expect(h.invoke).toHaveBeenCalledWith('load_project_less_session', {
      workspaceId: 'ws-1',
    });
    expect(missing).toBeNull();

    const session = makeSession();
    h.invoke.mockResolvedValueOnce(session);
    const present = await loadProjectLessSession('ws-1');
    expect(present).toBe(session);
  });
});

describe('workspaceStorage — propagates Rust error strings', () => {
  beforeEach(() => h.invoke.mockReset());

  it('saveWorkspacesIndex surfaces save failure', async () => {
    h.invoke.mockRejectedValueOnce(WORKSPACES_SAVE_FAILED);
    await expect(saveWorkspacesIndex(makeIndex())).rejects.toBe(
      WORKSPACES_SAVE_FAILED,
    );
  });
});

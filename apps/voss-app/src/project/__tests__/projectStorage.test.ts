import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
  openDialog: vi.fn(),
}));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('@tauri-apps/plugin-dialog', () => ({ open: h.openDialog }));

import {
  OPEN_PROJECT_LABEL,
  RECENTS_HEADING,
  START_PROJECT_LESS_LABEL,
  defaultCwd,
  listRecents,
  openProject,
  pickFolder,
  type ProjectInfo,
} from '../projectStorage';

/**
 * A5-03 Task 1 — dialog picker + invoke wrappers + exact setup-window copy.
 *
 * Command names and payload keys must match
 * `apps/voss-app/src-tauri/src/lib.rs` (A5-02) exactly, otherwise Tauri's
 * camelCase param mapping fails silently at runtime.
 */

function makeProject(): ProjectInfo {
  return {
    path: '/repo/voss',
    name: 'voss',
    gitBranch: 'dev',
  };
}

describe('projectStorage — setup-window copy constants', () => {
  it('matches A5 setup copy verbatim', () => {
    expect(OPEN_PROJECT_LABEL).toBe('Open project');
    expect(START_PROJECT_LESS_LABEL).toBe('Start without project');
    expect(RECENTS_HEADING).toBe('Recent projects');
  });
});

describe('projectStorage — dialog and Tauri invoke bridges', () => {
  beforeEach(() => {
    h.invoke.mockReset();
    h.openDialog.mockReset();
  });

  it('pickFolder → open({ directory: true, multiple: false }) and returns selected path', async () => {
    h.openDialog.mockResolvedValueOnce('/repo/voss');
    const path = await pickFolder();
    expect(h.openDialog).toHaveBeenCalledTimes(1);
    expect(h.openDialog).toHaveBeenCalledWith({
      directory: true,
      multiple: false,
    });
    expect(path).toBe('/repo/voss');
  });

  it('pickFolder returns null when the user cancels', async () => {
    h.openDialog.mockResolvedValueOnce(null);
    await expect(pickFolder()).resolves.toBeNull();
  });

  it('pickFolder returns null for array-shaped dialog results', async () => {
    h.openDialog.mockResolvedValueOnce(['/repo/a', '/repo/b']);
    await expect(pickFolder()).resolves.toBeNull();
  });

  it('openProject → invoke("open_project", { path }) and returns ProjectInfo', async () => {
    const project = makeProject();
    h.invoke.mockResolvedValueOnce(project);
    const got = await openProject('/repo/voss');
    expect(h.invoke).toHaveBeenCalledWith('open_project', {
      path: '/repo/voss',
    });
    expect(got).toBe(project);
  });

  it('listRecents → invoke("load_recents") and returns string[]', async () => {
    h.invoke.mockResolvedValueOnce(['/repo/voss', '/repo/other']);
    const recents = await listRecents();
    expect(h.invoke).toHaveBeenCalledWith('load_recents');
    expect(recents).toEqual(['/repo/voss', '/repo/other']);
  });

  it('defaultCwd(null) → invoke("default_cwd", { projectPath: null })', async () => {
    h.invoke.mockResolvedValueOnce('/Users/ben');
    const cwd = await defaultCwd(null);
    expect(h.invoke).toHaveBeenCalledWith('default_cwd', {
      projectPath: null,
    });
    expect(cwd).toBe('/Users/ben');
  });

  it('defaultCwd(path) → invoke("default_cwd", { projectPath: path })', async () => {
    h.invoke.mockResolvedValueOnce('/repo/voss');
    const cwd = await defaultCwd('/repo/voss');
    expect(h.invoke).toHaveBeenCalledWith('default_cwd', {
      projectPath: '/repo/voss',
    });
    expect(cwd).toBe('/repo/voss');
  });
});

describe('projectStorage — propagates Rust error strings verbatim', () => {
  beforeEach(() => h.invoke.mockReset());

  it('openProject surfaces Rust ProjectError Display strings unchanged', async () => {
    h.invoke.mockRejectedValueOnce('project not found');
    await expect(openProject('/missing')).rejects.toBe('project not found');
  });
});

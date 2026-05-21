import { describe, it, expect, vi, beforeEach } from 'vitest';

const h = vi.hoisted(() => ({
  invoke: vi.fn(),
  listen: vi.fn(() => Promise.resolve(() => {})),
}));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('@tauri-apps/api/event', () => ({ listen: h.listen }));

import {
  KEYMAP_SAVE_FAILED,
  KEYMAP_LOAD_FAILED,
  loadKeymapProfile,
  saveKeymapProfile,
  loadKeymapOverrides,
  validateKeymapOverrides,
  watchWorkspaceKeymap,
} from '../keymapStorage';

/**
 * A7-03 Task 2 — keymapStorage invoke wrapper tests.
 */

describe('keymapStorage — profile commands', () => {
  beforeEach(() => h.invoke.mockReset());

  it('loadKeymapProfile invokes load_keymap_profile', async () => {
    h.invoke.mockResolvedValueOnce('"vscode"');
    const profile = await loadKeymapProfile();
    expect(h.invoke).toHaveBeenCalledWith('load_keymap_profile');
    expect(profile).toBe('vscode');
  });

  it('saveKeymapProfile("tmux") invokes save_keymap_profile', async () => {
    h.invoke.mockResolvedValueOnce(undefined);
    await saveKeymapProfile('tmux');
    expect(h.invoke).toHaveBeenCalledWith('save_keymap_profile', {
      profile: 'tmux',
    });
  });
});

describe('keymapStorage — override commands', () => {
  beforeEach(() => h.invoke.mockReset());

  it('loadKeymapOverrides invokes load_keymap_overrides with workspacePath', async () => {
    h.invoke.mockResolvedValueOnce(null);
    const result = await loadKeymapOverrides('/ws');
    expect(h.invoke).toHaveBeenCalledWith('load_keymap_overrides', {
      workspacePath: '/ws',
    });
    expect(result).toBeNull();
  });

  it('validateKeymapOverrides invokes with correct payload', async () => {
    const validation = { valid: {}, issues: [] };
    h.invoke.mockResolvedValueOnce(validation);
    const overrides = { version: 1 as const, bindings: {} };
    await validateKeymapOverrides(overrides, ['pane.splitRight'], ['Cmd+D']);
    expect(h.invoke).toHaveBeenCalledWith('validate_keymap_overrides', {
      overrides,
      knownCommandIds: ['pane.splitRight'],
      knownChords: ['Cmd+D'],
    });
  });
});

describe('keymapStorage — watch event', () => {
  beforeEach(() => {
    h.invoke.mockReset();
    h.listen.mockReset();
  });

  it('watchWorkspaceKeymap starts Rust watcher and listens on voss://keymap-updated', async () => {
    let capturedHandler: ((e: unknown) => void) | undefined;
    h.listen.mockImplementation(
      ((_event: string, handler: (e: unknown) => void) => {
        capturedHandler = handler;
        return Promise.resolve(() => {});
      }) as typeof h.listen,
    );
    h.invoke.mockResolvedValueOnce({ valid: {}, issues: [] });

    const onUpdate = vi.fn();
    const unlisten = await watchWorkspaceKeymap(
      '/ws',
      ['pane.splitRight'],
      ['Cmd+D'],
      onUpdate,
    );

    expect(h.listen).toHaveBeenCalledWith(
      'voss://keymap-updated',
      expect.any(Function),
    );
    expect(h.invoke).toHaveBeenCalledWith('watch_keymap_overrides', {
      workspacePath: '/ws',
      knownCommandIds: ['pane.splitRight'],
      knownChords: ['Cmd+D'],
    });

    // Simulate event
    const payload = { valid: {}, issues: [{ commandId: 'bad', reason: 'unknown' }] };
    capturedHandler!({ payload });
    expect(onUpdate).toHaveBeenNthCalledWith(1, { valid: {}, issues: [] });
    expect(onUpdate).toHaveBeenNthCalledWith(2, payload);

    expect(typeof unlisten).toBe('function');
  });

  it('invalid update payload routes issues to callback', async () => {
    let capturedHandler: ((e: unknown) => void) | undefined;
    h.listen.mockImplementation(
      ((_event: string, handler: (e: unknown) => void) => {
        capturedHandler = handler;
        return Promise.resolve(() => {});
      }) as typeof h.listen,
    );
    h.invoke.mockResolvedValueOnce({ valid: {}, issues: [] });

    const onUpdate = vi.fn();
    await watchWorkspaceKeymap('/ws', ['pane.splitRight'], ['Cmd+D'], onUpdate);

    const payload = {
      valid: { 'pane.splitRight': { key: 'Cmd+X' } },
      issues: [{ commandId: 'bad.cmd', reason: 'unknown command "bad.cmd"' }],
    };
    capturedHandler!({ payload });
    expect(onUpdate).toHaveBeenCalledWith(payload);
    expect(onUpdate.mock.calls[1][0].issues).toHaveLength(1);
  });

  it('cleans up the listener if starting the Rust watcher fails', async () => {
    const unlisten = vi.fn();
    h.listen.mockResolvedValueOnce(unlisten);
    h.invoke.mockRejectedValueOnce(new Error('watch failed'));

    await expect(
      watchWorkspaceKeymap('/ws', [], [], vi.fn()),
    ).rejects.toThrow('watch failed');

    expect(unlisten).toHaveBeenCalledTimes(1);
  });
});

describe('keymapStorage — error copy', () => {
  it('matches Rust KeymapError::Display', () => {
    expect(KEYMAP_SAVE_FAILED).toBe('could not save keymap settings');
    expect(KEYMAP_LOAD_FAILED).toBe('could not load keymap settings');
  });
});

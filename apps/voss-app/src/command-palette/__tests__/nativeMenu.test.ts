import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  buildNativeMenuModel,
  chordToAccelerator,
} from '../nativeMenu';
import {
  createCommandRegistry,
  v0Commands,
  workspaceCommands,
  appearanceCommands,
} from '../registry';

/**
 * A7-05 Task 1 + A8-05 Task 3 — native menu model tests.
 *
 * Verifies the pure menu model generation — no Tauri runtime needed.
 * The Tauri `setAsAppMenu` installation is manual-only verification except
 * for the non-Tauri no-op guard tested below.
 */

const registry = createCommandRegistry([
  ...v0Commands(),
  ...workspaceCommands(),
  ...appearanceCommands(),
]);

describe('buildNativeMenuModel — category groups', () => {
  const model = buildNativeMenuModel(registry);

  it('produces groups for Window, Workspace, Pane, Layout, Project, Settings, Help', () => {
    const labels = model.map((g) => g.label);
    expect(labels).toEqual([
      'Window',
      'Workspace',
      'Pane',
      'Layout',
      'Project',
      'Settings',
      'Help',
    ]);
  });

  it('every menu item id equals a registry command id', () => {
    const allIds = model.flatMap((g) => g.items.map((i) => i.id));
    for (const id of allIds) {
      expect(registry.commands.has(id)).toBe(true);
    }
  });

  it('every menu item label equals its registry command label', () => {
    for (const group of model) {
      for (const item of group.items) {
        const cmd = registry.commands.get(item.id)!;
        expect(item.label).toBe(cmd.label);
      }
    }
  });

  it('keybinding-bearing commands produce accelerators', () => {
    const splitRight = model
      .flatMap((g) => g.items)
      .find((i) => i.id === 'pane.splitRight');
    expect(splitRight).toBeDefined();
    expect(splitRight!.accelerator).toBe('CmdOrCtrl+D');
  });

  it('commands without keybindings have no accelerator', () => {
    const open = model
      .flatMap((g) => g.items)
      .find((i) => i.id === 'project.open');
    expect(open).toBeDefined();
    expect(open!.accelerator).toBeUndefined();
  });
});

describe('buildNativeMenuModel — A8 workspace commands', () => {
  const model = buildNativeMenuModel(registry);
  const workspaceGroup = model.find((g) => g.label === 'Workspace')!;

  it('includes workspace.new and workspace.close', () => {
    const ids = workspaceGroup.items.map((i) => i.id);
    expect(ids).toContain('workspace.new');
    expect(ids).toContain('workspace.close');
  });

  it('maps Ctrl+Tab workspace shortcuts to accelerators', () => {
    const next = workspaceGroup.items.find((i) => i.id === 'workspace.next');
    const prev = workspaceGroup.items.find((i) => i.id === 'workspace.prev');
    expect(next?.accelerator).toBe('Ctrl+Tab');
    expect(prev?.accelerator).toBe('Ctrl+Shift+Tab');
  });

  it('menu item ids match registry ids for workspace commands', () => {
    for (const item of workspaceGroup.items) {
      expect(registry.commands.get(item.id)?.id).toBe(item.id);
    }
  });
});

describe('buildNativeMenuModel — A8 settings / appearance commands', () => {
  const model = buildNativeMenuModel(registry);
  const settingsGroup = model.find((g) => g.label === 'Settings')!;

  it('includes theme, font, high contrast, and bell commands', () => {
    const ids = settingsGroup.items.map((i) => i.id);
    expect(ids).toContain('theme.switch');
    expect(ids).toContain('appearance.font');
    expect(ids).toContain('appearance.highContrast');
    expect(ids).toContain('appearance.bell');
  });

  it('uses UI-SPEC labels for appearance commands', () => {
    const byId = Object.fromEntries(settingsGroup.items.map((i) => [i.id, i]));
    expect(byId['theme.switch'].label).toBe('Switch Theme');
    expect(byId['appearance.font'].label).toBe('Switch Font');
    expect(byId['appearance.highContrast'].label).toBe('Toggle High Contrast');
    expect(byId['appearance.bell'].label).toBe('Set Bell Behavior');
  });

  it('menu item ids match registry ids for settings commands', () => {
    for (const item of settingsGroup.items) {
      expect(registry.commands.get(item.id)?.id).toBe(item.id);
    }
  });
});

describe('chordToAccelerator', () => {
  it('Cmd+D → CmdOrCtrl+D', () => {
    expect(chordToAccelerator('Cmd+D')).toBe('CmdOrCtrl+D');
  });

  it('Cmd+Shift+D → CmdOrCtrl+Shift+D', () => {
    expect(chordToAccelerator('Cmd+Shift+D')).toBe('CmdOrCtrl+Shift+D');
  });

  it('Cmd+Alt+ArrowRight → CmdOrCtrl+Alt+Right', () => {
    expect(chordToAccelerator('Cmd+Alt+ArrowRight')).toBe(
      'CmdOrCtrl+Alt+Right',
    );
  });

  it('Ctrl+Tab workspace shortcut maps to accelerator', () => {
    expect(chordToAccelerator('Ctrl+Tab')).toBe('Ctrl+Tab');
  });

  it('Cmd+Alt+Shift+ArrowUp → CmdOrCtrl+Alt+Shift+Up', () => {
    expect(chordToAccelerator('Cmd+Alt+Shift+ArrowUp')).toBe(
      'CmdOrCtrl+Alt+Shift+Up',
    );
  });
});

describe('buildNativeMenuModel — no duplicate command list', () => {
  it('total menu items equals total registry commands', () => {
    const model = buildNativeMenuModel(registry);
    const menuCount = model.reduce((sum, g) => sum + g.items.length, 0);
    expect(menuCount).toBe(registry.all().length);
  });
});

describe('setAsAppMenu — non-Tauri fallback', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.doMock('@tauri-apps/api/menu', () =>
      Promise.reject(new Error('Tauri unavailable')),
    );
  });

  afterEach(() => {
    vi.doUnmock('@tauri-apps/api/menu');
  });

  it('does not throw when dynamic import fails', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const { setAsAppMenu: setMenu } = await import('../nativeMenu');

    await expect(setMenu(registry, vi.fn())).resolves.toBeUndefined();
    expect(warn).toHaveBeenCalled();

    warn.mockRestore();
  });
});

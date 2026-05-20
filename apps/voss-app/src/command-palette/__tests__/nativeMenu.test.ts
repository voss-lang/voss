import { describe, it, expect } from 'vitest';
import {
  buildNativeMenuModel,
  chordToAccelerator,
} from '../nativeMenu';
import { createCommandRegistry, v0Commands } from '../registry';

/**
 * A7-05 Task 1 — native menu model tests.
 *
 * Verifies the pure menu model generation — no Tauri runtime needed.
 * The Tauri `setAsAppMenu` installation is manual-only verification.
 */

const registry = createCommandRegistry(v0Commands());

describe('buildNativeMenuModel — category groups', () => {
  const model = buildNativeMenuModel(registry);

  it('produces groups for Window, Pane, Layout, Project, Settings, Help', () => {
    const labels = model.map((g) => g.label);
    expect(labels).toEqual([
      'Window',
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

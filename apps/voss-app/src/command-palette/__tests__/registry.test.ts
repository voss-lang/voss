import { describe, it, expect, vi } from 'vitest';
import {
  createCommandRegistry,
  v0Commands,
  type AppContext,
  type CommandCategory,
} from '../registry';

/**
 * A7-01 Task 2 — command registry tests.
 *
 * Verifies:
 * - v0 catalog covers all six categories
 * - Command ids are unique
 * - Dispatch returns true for handled chords, false for unmatched
 * - Registry metadata is accessible by chord and category
 * - Alias chords dispatch to the same command
 */

function mockCtx(): AppContext {
  return {
    splitFocused: vi.fn(),
    closeFocused: vi.fn(),
    equalizePanes: vi.fn(),
    cycleLayout: vi.fn(),
    focusNext: vi.fn(),
    focusPrev: vi.fn(),
    focusIndex: vi.fn(),
    focusDirection: vi.fn(),
    resizeDirection: vi.fn(),
    openQuickPalette: vi.fn(),
    openFullPalette: vi.fn(),
    openProject: vi.fn(),
    saveLayout: vi.fn(),
    loadLayout: vi.fn(),
    switchProfile: vi.fn(),
    showKeybindings: vi.fn(),
  };
}

describe('v0 command catalog', () => {
  const defs = v0Commands();
  const registry = createCommandRegistry(defs);

  it('exposes Window, Pane, Layout, Project, Settings, and Help categories', () => {
    const categories = new Set(defs.map((d) => d.category));
    expect(categories).toEqual(
      new Set<CommandCategory>([
        'Window',
        'Pane',
        'Layout',
        'Project',
        'Settings',
        'Help',
      ]),
    );
  });

  it('all command ids are unique', () => {
    const ids = defs.map((d) => d.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('contains at least 25 commands (A3/A4 full migration)', () => {
    expect(defs.length).toBeGreaterThanOrEqual(25);
  });

  it('every command has id, label, category, and handler', () => {
    for (const def of defs) {
      expect(def.id).toBeTruthy();
      expect(def.label).toBeTruthy();
      expect(def.category).toBeTruthy();
      expect(typeof def.handler).toBe('function');
    }
  });

  it('byCategory returns commands for each category', () => {
    const panes = registry.byCategory('Pane');
    expect(panes.length).toBeGreaterThan(0);
    expect(panes.every((c) => c.category === 'Pane')).toBe(true);

    const layouts = registry.byCategory('Layout');
    expect(layouts.length).toBeGreaterThan(0);
  });
});

describe('CommandRegistry — dispatch', () => {
  const registry = createCommandRegistry(v0Commands());

  it('returns true and calls handler for matched chord', () => {
    const ctx = mockCtx();
    expect(registry.dispatch('Cmd+D', ctx)).toBe(true);
    expect(ctx.splitFocused).toHaveBeenCalledWith('H');
  });

  it('returns false for unmatched chord', () => {
    const ctx = mockCtx();
    expect(registry.dispatch('Cmd+Z', ctx)).toBe(false);
  });

  it('alias chord dispatches to the same command as primary', () => {
    const ctx = mockCtx();
    expect(registry.dispatch('Cmd+\\', ctx)).toBe(true);
    expect(ctx.splitFocused).toHaveBeenCalledWith('H');
  });

  it('Cmd+Shift+D dispatches split below', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+Shift+D', ctx);
    expect(ctx.splitFocused).toHaveBeenCalledWith('V');
  });

  it('Cmd+W dispatches close', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+W', ctx);
    expect(ctx.closeFocused).toHaveBeenCalled();
  });

  it('Cmd+G dispatches cycle layout', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+G', ctx);
    expect(ctx.cycleLayout).toHaveBeenCalled();
  });

  it('Cmd+3 dispatches focus index 3', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+3', ctx);
    expect(ctx.focusIndex).toHaveBeenCalledWith(3);
  });

  it('Cmd+Alt+ArrowRight dispatches focus direction right', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+Alt+ArrowRight', ctx);
    expect(ctx.focusDirection).toHaveBeenCalledWith('right');
  });

  it('Cmd+Alt+Shift+ArrowUp dispatches resize direction up', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+Alt+Shift+ArrowUp', ctx);
    expect(ctx.resizeDirection).toHaveBeenCalledWith('up');
  });

  it('Cmd+P dispatches quick palette', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+P', ctx);
    expect(ctx.openQuickPalette).toHaveBeenCalled();
  });

  it('Cmd+Shift+P dispatches full palette', () => {
    const ctx = mockCtx();
    registry.dispatch('Cmd+Shift+P', ctx);
    expect(ctx.openFullPalette).toHaveBeenCalled();
  });
});

describe('CommandRegistry — metadata', () => {
  const registry = createCommandRegistry(v0Commands());

  it('findByChord returns command for known chord', () => {
    const cmd = registry.findByChord('Cmd+D');
    expect(cmd).toBeDefined();
    expect(cmd!.id).toBe('pane.splitRight');
    expect(cmd!.label).toBe('Split Right');
    expect(cmd!.category).toBe('Pane');
    expect(cmd!.keybinding).toBe('Cmd+D');
  });

  it('findByChord returns undefined for unknown chord', () => {
    expect(registry.findByChord('Cmd+Z')).toBeUndefined();
  });

  it('all() returns every registered command', () => {
    const all = registry.all();
    expect(all.length).toBe(v0Commands().length);
  });
});

describe('createCommandRegistry — validation', () => {
  it('throws on duplicate command id', () => {
    const dupe = [
      { id: 'test', label: 'A', category: 'Pane' as CommandCategory, handler: () => {} },
      { id: 'test', label: 'B', category: 'Pane' as CommandCategory, handler: () => {} },
    ];
    expect(() => createCommandRegistry(dupe)).toThrow('Duplicate command id: test');
  });
});

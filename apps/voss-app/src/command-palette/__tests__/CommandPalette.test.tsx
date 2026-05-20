import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
import CommandPalette from '../CommandPalette';
import type { Command } from '../registry';
import type { QuickOpenItem } from '../quickOpen';

/**
 * A7-02 Task 1 — CommandPalette component tests.
 *
 * Verifies exact UI-SPEC copy, chord hints, empty states,
 * keyboard navigation, and dismiss behavior.
 */

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

const noop = () => {};

function makeCommands(): Command[] {
  return [
    {
      id: 'pane.splitRight',
      label: 'Split Right',
      category: 'Pane',
      keybinding: 'Cmd+D',
      handler: noop,
    },
    {
      id: 'pane.close',
      label: 'Close Pane',
      category: 'Pane',
      keybinding: 'Cmd+W',
      handler: noop,
    },
    {
      id: 'layout.cycle',
      label: 'Cycle Layout',
      category: 'Layout',
      keybinding: 'Cmd+G',
      handler: noop,
    },
  ];
}

function makeQuickItems(): QuickOpenItem[] {
  return [
    { id: 'layout:build-watch', label: 'build-watch', section: 'Layouts', glyph: 'L' },
    { id: 'recent:/repo/project-a', label: 'project-a', section: 'Recent Projects', glyph: 'R', secondary: '/repo/project-a' },
  ];
}

describe('CommandPalette — quick mode', () => {
  it('input placeholder is "Open layout or recent project"', () => {
    mount(() => (
      <CommandPalette
        mode="quick"
        commands={[]}
        quickItems={makeQuickItems()}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]') as HTMLInputElement;
    expect(input.placeholder).toBe('Open layout or recent project');
  });

  it('renders quick items with section headers', () => {
    mount(() => (
      <CommandPalette
        mode="quick"
        commands={[]}
        quickItems={makeQuickItems()}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const rows = document.querySelectorAll('[data-testid="palette-row"]');
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain('build-watch');
    expect(rows[1].textContent).toContain('project-a');
  });

  it('empty quick mode shows exact empty copy', () => {
    mount(() => (
      <CommandPalette
        mode="quick"
        commands={[]}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const empty = document.querySelector('[data-testid="palette-empty"]')!;
    expect(empty.textContent).toContain('No layouts or recent projects');
    expect(empty.textContent).toContain(
      'Save a layout or open a project to add quick-open targets.',
    );
  });
});

describe('CommandPalette — full mode', () => {
  it('input placeholder is "Run command"', () => {
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]') as HTMLInputElement;
    expect(input.placeholder).toBe('Run command');
  });

  it('rows display chord hints from registry metadata', () => {
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const hints = document.querySelectorAll('[data-testid="chord-hint"]');
    const hintTexts = Array.from(hints).map((h) => h.textContent);
    expect(hintTexts).toContain('⌘D');
    expect(hintTexts).toContain('⌘W');
    expect(hintTexts).toContain('⌘G');
  });

  it('empty full mode shows exact empty copy', () => {
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]') as HTMLInputElement;
    fireEvent.input(input, { target: { value: 'xyznonexistent' } });
    const empty = document.querySelector('[data-testid="palette-empty"]')!;
    expect(empty.textContent).toContain('No matching commands');
    expect(empty.textContent).toContain(
      'Refine the query or press Esc to return to the focused pane.',
    );
  });
});

describe('CommandPalette — keyboard', () => {
  it('Esc calls onDismiss', () => {
    const onDismiss = vi.fn();
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={onDismiss}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]')!;
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('Enter calls onExecute with selected row id', () => {
    const onExecute = vi.fn();
    const onDismiss = vi.fn();
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={onExecute}
        onDismiss={onDismiss}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]')!;
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onExecute).toHaveBeenCalledWith('pane.splitRight');
    expect(onDismiss).toHaveBeenCalled();
  });

  it('outside click calls onDismiss', () => {
    const onDismiss = vi.fn();
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={onDismiss}
      />
    ));
    // Click the backdrop (parent of the panel)
    const backdrop = document.querySelector('[data-testid="command-palette"]')!.parentElement!;
    fireEvent.click(backdrop);
    expect(onDismiss).toHaveBeenCalled();
  });
});

describe('CommandPalette — ARIA', () => {
  it('dialog role and aria-modal', () => {
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const dialog = document.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(dialog!.getAttribute('aria-modal')).toBe('true');
  });

  it('quick mode input has aria-label "Quick open search"', () => {
    mount(() => (
      <CommandPalette
        mode="quick"
        commands={[]}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]')!;
    expect(input.getAttribute('aria-label')).toBe('Quick open search');
  });

  it('full mode input has aria-label "Command search"', () => {
    mount(() => (
      <CommandPalette
        mode="full"
        commands={makeCommands()}
        quickItems={[]}
        recentCommandIds={new Set()}
        onExecute={noop}
        onDismiss={noop}
      />
    ));
    const input = document.querySelector('[data-testid="palette-input"]')!;
    expect(input.getAttribute('aria-label')).toBe('Command search');
  });
});

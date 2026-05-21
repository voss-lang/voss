import { describe, expect, it } from 'vitest';
import {
  parseWorkspaceShortcut,
  workspaceIndexForFocusAction,
} from '../workspaceShortcuts';

function key(
  init: KeyboardEventInit & { key: string },
): KeyboardEvent {
  return new KeyboardEvent('keydown', init);
}

describe('parseWorkspaceShortcut', () => {
  it('maps Ctrl+1 to focus1', () => {
    expect(parseWorkspaceShortcut(key({ key: '1', ctrlKey: true }))).toBe(
      'focus1',
    );
  });

  it('maps Ctrl+9 to focus9', () => {
    expect(parseWorkspaceShortcut(key({ key: '9', ctrlKey: true }))).toBe(
      'focus9',
    );
  });

  it('maps Ctrl+Tab to next', () => {
    expect(parseWorkspaceShortcut(key({ key: 'Tab', ctrlKey: true }))).toBe(
      'next',
    );
  });

  it('maps Ctrl+Shift+Tab to prev', () => {
    expect(
      parseWorkspaceShortcut(key({ key: 'Tab', ctrlKey: true, shiftKey: true })),
    ).toBe('prev');
  });

  it('returns null for Cmd+1 (pane focus)', () => {
    expect(
      parseWorkspaceShortcut(key({ key: '1', metaKey: true })),
    ).toBeNull();
  });

  it('returns null for Ctrl+Meta+1', () => {
    expect(
      parseWorkspaceShortcut(
        key({ key: '1', ctrlKey: true, metaKey: true }),
      ),
    ).toBeNull();
  });

  it('returns null for bare Tab', () => {
    expect(parseWorkspaceShortcut(key({ key: 'Tab' }))).toBeNull();
  });
});

describe('workspaceIndexForFocusAction', () => {
  it('focus1 is index 0', () => {
    expect(workspaceIndexForFocusAction('focus1')).toBe(0);
  });

  it('focus9 is index 8', () => {
    expect(workspaceIndexForFocusAction('focus9')).toBe(8);
  });

  it('next has no index', () => {
    expect(workspaceIndexForFocusAction('next')).toBeNull();
  });
});

/**
 * A8-03 Task 3 — workspace keyboard shortcuts (UXP-03).
 *
 * Ctrl+1..9, Ctrl+Tab, Ctrl+Shift+Tab. Mac uses Control (not Cmd) so
 * Cmd+1..9 pane focus stays on the A7 registry / grid keymap path.
 */

export type WorkspaceShortcutAction =
  | 'focus1'
  | 'focus2'
  | 'focus3'
  | 'focus4'
  | 'focus5'
  | 'focus6'
  | 'focus7'
  | 'focus8'
  | 'focus9'
  | 'next'
  | 'prev';

const FOCUS_ACTIONS: readonly WorkspaceShortcutAction[] = [
  'focus1',
  'focus2',
  'focus3',
  'focus4',
  'focus5',
  'focus6',
  'focus7',
  'focus8',
  'focus9',
];

/**
 * Parse a workspace shortcut from a keydown event.
 * Returns null when the event is not a workspace chord (including Cmd+1..9).
 */
export function parseWorkspaceShortcut(
  e: KeyboardEvent,
): WorkspaceShortcutAction | null {
  if (!e.ctrlKey || e.metaKey) return null;

  if (e.key === 'Tab') {
    return e.shiftKey ? 'prev' : 'next';
  }

  if (!e.shiftKey && !e.altKey && e.key >= '1' && e.key <= '9') {
    return FOCUS_ACTIONS[Number(e.key) - 1] ?? null;
  }

  return null;
}

/** Zero-based workspace index for a focus action (focus1 → 0). */
export function workspaceIndexForFocusAction(
  action: WorkspaceShortcutAction,
): number | null {
  if (!action.startsWith('focus')) return null;
  const n = Number(action.slice('focus'.length));
  if (n < 1 || n > 9) return null;
  return n - 1;
}

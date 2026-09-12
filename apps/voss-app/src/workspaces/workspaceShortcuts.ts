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

export function workspaceIndexForFocusAction(
  action: WorkspaceShortcutAction,
): number | null {
  if (!action.startsWith('focus')) return null;
  const n = Number(action.slice('focus'.length));
  if (n < 1 || n > 9) return null;
  return n - 1;
}

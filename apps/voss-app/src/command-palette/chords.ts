/**
 * A7-01 Task 1 — chord normalization and display formatting.
 *
 * Converts KeyboardEvents into canonical chord strings (`Cmd+D`,
 * `Cmd+Shift+D`, `Cmd+Alt+ArrowRight`) and formats them for palette
 * row display (`⌘D`, `⌘⇧D`, `⌘⌥→`). Pure — no DOM state, no Solid.
 */

// --- Code → key-name map (layout-independent via KeyboardEvent.code) --------

const CODE_MAP: Record<string, string> = {
  KeyA: 'A', KeyB: 'B', KeyC: 'C', KeyD: 'D', KeyE: 'E', KeyF: 'F',
  KeyG: 'G', KeyH: 'H', KeyI: 'I', KeyJ: 'J', KeyK: 'K', KeyL: 'L',
  KeyM: 'M', KeyN: 'N', KeyO: 'O', KeyP: 'P', KeyQ: 'Q', KeyR: 'R',
  KeyS: 'S', KeyT: 'T', KeyU: 'U', KeyV: 'V', KeyW: 'W', KeyX: 'X',
  KeyY: 'Y', KeyZ: 'Z',
  Digit0: '0', Digit1: '1', Digit2: '2', Digit3: '3', Digit4: '4',
  Digit5: '5', Digit6: '6', Digit7: '7', Digit8: '8', Digit9: '9',
  Backslash: '\\', Equal: '=', Minus: '-', Slash: '/',
  BracketLeft: '[', BracketRight: ']',
  Comma: ',', Period: '.', Semicolon: ';', Quote: "'", Backquote: '`',
  ArrowLeft: 'ArrowLeft', ArrowRight: 'ArrowRight',
  ArrowUp: 'ArrowUp', ArrowDown: 'ArrowDown',
  Enter: 'Enter', Escape: 'Escape', Tab: 'Tab', Space: 'Space',
  Backspace: 'Backspace', Delete: 'Delete',
};

// --- Display symbols --------------------------------------------------------

const DISPLAY: Record<string, string> = {
  Cmd: '⌘', Shift: '⇧', Alt: '⌥',
  ArrowLeft: '←', ArrowRight: '→', ArrowUp: '↑', ArrowDown: '↓',
  Backspace: '⌫', Delete: '⌦', Enter: '↩', Tab: '⇥', Space: '␣',
  Escape: 'Esc',
};

// --- Public API --------------------------------------------------------------

/**
 * Normalize a KeyboardEvent to a canonical chord string.
 * Returns `null` for bare modifier presses and unrecognized codes.
 * Bare keys (no modifier) return `null` — those belong to the PTY.
 */
export function normalizeChord(evt: KeyboardEvent): string | null {
  // Ignore bare modifier key presses
  if (['Meta', 'Shift', 'Alt', 'Control'].includes(evt.key)) return null;

  const keyName = CODE_MAP[evt.code] ?? null;
  if (!keyName) return null;

  const parts: string[] = [];
  if (evt.metaKey) parts.push('Cmd');
  if (evt.altKey) parts.push('Alt');
  if (evt.shiftKey) parts.push('Shift');

  // No modifiers = bare key → PTY pass-through in normal mode
  if (parts.length === 0) return null;

  parts.push(keyName);
  return parts.join('+');
}

/**
 * Normalize a KeyboardEvent for tmux prefix mode dispatch.
 * Returns the bare printable character or `Escape`. Ignores events
 * with Cmd/Alt/Ctrl modifiers (those aren't valid prefix keys).
 */
export function normalizePrefixKey(evt: KeyboardEvent): string | null {
  if (evt.metaKey || evt.altKey || evt.ctrlKey) return null;
  if (evt.key === 'Escape') return 'Escape';
  if (evt.key.length === 1) return evt.key;
  return null;
}

/**
 * Format a canonical chord string for display in palette rows.
 * `Cmd+D` → `⌘D`, `Cmd+Shift+D` → `⌘⇧D`, `Cmd+Alt+ArrowRight` → `⌘⌥→`.
 */
export function formatChord(chord: string): string {
  return chord
    .split('+')
    .map((p) => DISPLAY[p] ?? p)
    .join('');
}

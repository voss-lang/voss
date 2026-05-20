import { describe, it, expect } from 'vitest';
import { normalizeChord, normalizePrefixKey, formatChord } from '../chords';

/**
 * A7-01 Task 1 — chord normalization tests.
 *
 * Every A3/A4 chord must round-trip through normalizeChord so the
 * registry dispatch can replace the old switch-based keymap. Unmatched
 * events must return null — PTY pass-through is never broken.
 */

function key(init: KeyboardEventInit): KeyboardEvent {
  return new KeyboardEvent('keydown', init);
}

describe('normalizeChord — A3/A4 migration chords', () => {
  it('Cmd+D → "Cmd+D"', () => {
    expect(normalizeChord(key({ code: 'KeyD', key: 'd', metaKey: true }))).toBe('Cmd+D');
  });

  it('Cmd+Shift+D → "Cmd+Shift+D"', () => {
    expect(normalizeChord(key({ code: 'KeyD', key: 'D', metaKey: true, shiftKey: true }))).toBe('Cmd+Shift+D');
  });

  it('Cmd+Backslash → "Cmd+\\\\"', () => {
    expect(normalizeChord(key({ code: 'Backslash', key: '\\', metaKey: true }))).toBe('Cmd+\\');
  });

  it('Cmd+Shift+Backslash → "Cmd+Shift+\\\\"', () => {
    expect(normalizeChord(key({ code: 'Backslash', key: '|', metaKey: true, shiftKey: true }))).toBe('Cmd+Shift+\\');
  });

  it('Cmd+W → "Cmd+W"', () => {
    expect(normalizeChord(key({ code: 'KeyW', key: 'w', metaKey: true }))).toBe('Cmd+W');
  });

  it('Cmd+= → "Cmd+="', () => {
    expect(normalizeChord(key({ code: 'Equal', key: '=', metaKey: true }))).toBe('Cmd+=');
  });

  it('Cmd+G → "Cmd+G"', () => {
    expect(normalizeChord(key({ code: 'KeyG', key: 'g', metaKey: true }))).toBe('Cmd+G');
  });

  it('Cmd+[ and Cmd+] → "Cmd+[" and "Cmd+]"', () => {
    expect(normalizeChord(key({ code: 'BracketLeft', key: '[', metaKey: true }))).toBe('Cmd+[');
    expect(normalizeChord(key({ code: 'BracketRight', key: ']', metaKey: true }))).toBe('Cmd+]');
  });

  it('Cmd+1..Cmd+9 → "Cmd+1".."Cmd+9"', () => {
    for (let i = 1; i <= 9; i++) {
      expect(normalizeChord(key({ code: `Digit${i}`, key: `${i}`, metaKey: true }))).toBe(`Cmd+${i}`);
    }
  });

  it('Cmd+P → "Cmd+P"; Cmd+Shift+P → "Cmd+Shift+P"', () => {
    expect(normalizeChord(key({ code: 'KeyP', key: 'p', metaKey: true }))).toBe('Cmd+P');
    expect(normalizeChord(key({ code: 'KeyP', key: 'P', metaKey: true, shiftKey: true }))).toBe('Cmd+Shift+P');
  });

  it('Cmd+B → "Cmd+B" (tmux prefix trigger)', () => {
    expect(normalizeChord(key({ code: 'KeyB', key: 'b', metaKey: true }))).toBe('Cmd+B');
  });
});

describe('normalizeChord — directional focus/resize', () => {
  it('Cmd+Alt+ArrowRight → "Cmd+Alt+ArrowRight"', () => {
    expect(normalizeChord(key({ code: 'ArrowRight', key: 'ArrowRight', metaKey: true, altKey: true }))).toBe('Cmd+Alt+ArrowRight');
  });

  it('Cmd+Alt+Shift+ArrowUp → "Cmd+Alt+Shift+ArrowUp"', () => {
    expect(normalizeChord(key({
      code: 'ArrowUp', key: 'ArrowUp', metaKey: true, altKey: true, shiftKey: true,
    }))).toBe('Cmd+Alt+Shift+ArrowUp');
  });
});

describe('normalizeChord — PTY pass-through', () => {
  it('bare letter key → null', () => {
    expect(normalizeChord(key({ code: 'KeyA', key: 'a' }))).toBeNull();
  });

  it('bare modifier press → null', () => {
    expect(normalizeChord(key({ key: 'Meta', code: 'MetaLeft', metaKey: true }))).toBeNull();
    expect(normalizeChord(key({ key: 'Shift', code: 'ShiftLeft', shiftKey: true }))).toBeNull();
  });

  it('unrecognized code → null', () => {
    expect(normalizeChord(key({ code: 'Unidentified', key: 'x', metaKey: true }))).toBeNull();
  });
});

describe('normalizePrefixKey — tmux prefix dispatch', () => {
  it('bare % → "%"', () => {
    expect(normalizePrefixKey(key({ key: '%', code: 'Digit5', shiftKey: true }))).toBe('%');
  });

  it('bare " → "\\""', () => {
    expect(normalizePrefixKey(key({ key: '"', code: 'Quote', shiftKey: true }))).toBe('"');
  });

  it('bare o → "o"', () => {
    expect(normalizePrefixKey(key({ key: 'o', code: 'KeyO' }))).toBe('o');
  });

  it('Escape → "Escape"', () => {
    expect(normalizePrefixKey(key({ key: 'Escape', code: 'Escape' }))).toBe('Escape');
  });

  it('Cmd+o → null (modifier disqualifies prefix key)', () => {
    expect(normalizePrefixKey(key({ key: 'o', code: 'KeyO', metaKey: true }))).toBeNull();
  });
});

describe('formatChord — display rendering', () => {
  it('Cmd+D → ⌘D', () => {
    expect(formatChord('Cmd+D')).toBe('⌘D');
  });

  it('Cmd+Shift+D → ⌘⇧D', () => {
    expect(formatChord('Cmd+Shift+D')).toBe('⌘⇧D');
  });

  it('Cmd+Alt+ArrowRight → ⌘⌥→', () => {
    expect(formatChord('Cmd+Alt+ArrowRight')).toBe('⌘⌥→');
  });

  it('Cmd+Alt+Shift+ArrowUp → ⌘⌥⇧↑', () => {
    expect(formatChord('Cmd+Alt+Shift+ArrowUp')).toBe('⌘⌥⇧↑');
  });

  it('Cmd+\\ → ⌘\\', () => {
    expect(formatChord('Cmd+\\')).toBe('⌘\\');
  });

  it('Cmd+= → ⌘=', () => {
    expect(formatChord('Cmd+=')).toBe('⌘=');
  });
});

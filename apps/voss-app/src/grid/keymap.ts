import type { GridStore } from './tree';
import { splitFocused, equalizeAll } from './operations';
import { focusByIndex, cycleFocus, focusByDirection } from './focus';
import { resizeByKeyboard } from './resize';

/**
 * Pure keystroke → grid-operation dispatch (GRD-02/03/04). NO DOM listener
 * registration here — GridRoot owns the single `window` keydown listener and
 * calls this. A matched A3 chord consumes the event (preventDefault + return
 * true); ANY unmatched chord returns false WITHOUT preventDefault so the raw
 * keystroke reaches the focused A2 PTY (terminal must stay usable — T-A3-09).
 *
 * `⌘W` is NOT wired to `closeFocused` directly: it calls the injected
 * `onCloseRequest` so A3-05 can interpose the foreground-detection-gated
 * close-confirm without this module knowing about it (separation of concern
 * per A3-PATTERNS). GridRoot defaults `onCloseRequest` to `closeFocused`.
 */
export function dispatchKey(
  store: GridStore,
  evt: KeyboardEvent,
  winW: number,
  winH: number,
  cw: number,
  ch: number,
  onCloseRequest: (store: GridStore) => void,
): boolean {
  if (!evt.metaKey) return false; // every A3 chord requires ⌘ — pass through

  const geom = { winW, winH, cw, ch };
  const shift = evt.shiftKey;
  const alt = evt.altKey;
  const key = evt.key;
  const code = evt.code;

  const hit = (): boolean => {
    // ⌘⌥arrow (focus) vs ⌘⌥⇧arrow (resize) — both need Alt.
    if (alt) {
      const dir =
        code === 'ArrowLeft'
          ? 'left'
          : code === 'ArrowRight'
            ? 'right'
            : code === 'ArrowUp'
              ? 'up'
              : code === 'ArrowDown'
                ? 'down'
                : null;
      if (!dir) return false;
      if (shift) resizeByKeyboard(store, dir, winW, winH, cw, ch);
      else focusByDirection(store, dir, winW, winH);
      return true;
    }

    // ⌘D split right (H) / ⌘⇧D split below (V) — Warp parity (memory
    // voss-app-grid-warp-parity). ⌘\ / ⌘⇧\ kept as layout-stable aliases.
    if (code === 'KeyD' || code === 'Backslash') {
      splitFocused(store, shift ? 'V' : 'H', geom);
      return true;
    }

    if (shift) return false; // remaining chords are all un-shifted

    // ⌘W close (gated), ⌘= equalize.
    if (code === 'KeyW') {
      onCloseRequest(store);
      return true;
    }
    if (code === 'Equal' || key === '=') {
      equalizeAll(store);
      return true;
    }

    // ⌘[ / ⌘] cycle prev/next.
    if (key === '[' || code === 'BracketLeft') {
      cycleFocus(store, 'prev');
      return true;
    }
    if (key === ']' || code === 'BracketRight') {
      cycleFocus(store, 'next');
      return true;
    }

    // ⌘1–⌘9 numeric focus (⌘0 is intentionally unmatched).
    if (key >= '1' && key <= '9') {
      focusByIndex(store, Number(key));
      return true;
    }

    return false;
  };

  if (hit()) {
    evt.preventDefault();
    return true;
  }
  return false;
}

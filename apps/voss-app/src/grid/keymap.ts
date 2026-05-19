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
 *
 * `⌘G` (A4-02) routes to the injected `onCycleLayout` so this module stays
 * decoupled from `layoutPresets.ts` and L2 semantics. `onStructuralEdit`
 * fires before any A3 structural mutation (split / close / equalize /
 * resize) so the caller can flip `activeLayout` back to `custom` — this is
 * how A4-UI-SPEC's "manual edits surface custom state" rule is enforced
 * without leaking preset state into the keymap.
 */
export function dispatchKey(
  store: GridStore,
  evt: KeyboardEvent,
  winW: number,
  winH: number,
  cw: number,
  ch: number,
  onCloseRequest: (store: GridStore) => void,
  onCycleLayout?: (store: GridStore) => void,
  onStructuralEdit?: (store: GridStore) => void,
): boolean {
  if (!evt.metaKey) return false; // every A3 chord requires ⌘ — pass through

  const geom = { winW, winH, cw, ch };
  const shift = evt.shiftKey;
  const alt = evt.altKey;
  const key = evt.key;
  const code = evt.code;
  const markStructural = () => onStructuralEdit?.(store);

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
      if (shift) {
        markStructural();
        resizeByKeyboard(store, dir, winW, winH, cw, ch);
      } else {
        focusByDirection(store, dir, winW, winH);
      }
      return true;
    }

    // ⌘D split right (H) / ⌘⇧D split below (V) — Warp parity (memory
    // voss-app-grid-warp-parity). ⌘\ / ⌘⇧\ kept as layout-stable aliases.
    if (code === 'KeyD' || code === 'Backslash') {
      markStructural();
      splitFocused(store, shift ? 'V' : 'H', geom);
      return true;
    }

    if (shift) return false; // remaining chords are all un-shifted

    // ⌘W close (gated), ⌘= equalize, ⌘G layout cycle.
    if (code === 'KeyW') {
      markStructural();
      onCloseRequest(store);
      return true;
    }
    if (code === 'Equal' || key === '=') {
      markStructural();
      equalizeAll(store);
      return true;
    }
    if (code === 'KeyG') {
      // ⌘G is NOT structural — pane ids are preserved by A4-01.
      if (!onCycleLayout) return false;
      onCycleLayout(store);
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

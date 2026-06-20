import { onCleanup, onMount } from 'solid-js';
import { produce, type SetStoreFunction, type Store } from 'solid-js/store';
import type { GridStore } from './tree';
import { closeFocused } from './operations';

/**
 * GRD-02 close gate (A3-UI-SPEC "Close Confirm Contract", A2 D-07 reuse).
 *
 * `isForegroundRunning` is INJECTED — A3 never reimplements detection; it
 * consumes A2's foreground signal as a black box (A3-PATTERNS "A2 Foreground
 * Detection Reuse"). Synchronous boolean: the realistic source is A2's cached
 * fg signal, not an awaited Rust round-trip (keeps the close commit inside
 * the Solid `produce` frame — see A3-05 SUMMARY). `_paneId` is part of the
 * locked signature for the caller's intent though the focused pane is the
 * close target (D-04).
 */
export function requestCloseGated(
  store: GridStore,
  _paneId: string,
  isForegroundRunning: () => boolean,
  showBanner: () => void,
): void {
  if (isForegroundRunning()) {
    showBanner();
    return;
  }
  closeFocused(store); // idle shell → close immediately, no confirm
}

/**
 * 22px inline banner flush below the header. Copy is character-exact from the
 * A3-UI-SPEC Copywriting Contract. Enter/"Close anyway" → closeFocused;
 * Escape/"Keep open" → dismiss (pane + focus stay). Non-modal: any other key
 * passes through to the PTY. Auto-dismiss is the parent's job (it watches the
 * A2 fg signal and unmounts this on process exit) — no timeout dismiss.
 */
export default function CloseConfirmBanner(props: {
  store: Store<GridStore>;
  setStore: SetStoreFunction<GridStore>;
  process: string;
  onKeepOpen: () => void;
}) {
  const confirm = () => {
    props.setStore(produce((s) => closeFocused(s)));
    props.onKeepOpen(); // remove the banner after the close commits
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.stopPropagation();
      confirm();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      props.onKeepOpen();
    }
    // any other key falls through to the PTY (non-modal)
  };
  onMount(() => document.addEventListener('keydown', onKey, true));
  onCleanup(() => document.removeEventListener('keydown', onKey, true));

  return (
    <div
      class="font-ui bg-bg-3"
      role="alertdialog"
      style={{
        display: 'flex',
        'align-items': 'center',
        width: '100%',
        height: '22px',
        padding: '0 10px',
        'border-bottom': '1px solid var(--border)',
        'font-size': '11px',
        'font-weight': 400,
      }}
    >
      <span class="text-accent-red" style={{ 'font-size': '8px' }} aria-hidden="true">
        ●
      </span>
      <span class="text-fg-1" style={{ 'margin-left': '8px' }}>
        "{props.process}" is running. Close anyway?
      </span>
      <span style={{ flex: 1 }} />
      <button
        type="button"
        class="text-fg-0"
        style={{
          background: 'transparent',
          border: 'none',
          padding: '0 8px',
          cursor: 'default',
          'font-size': '11px',
        }}
        onClick={() => props.onKeepOpen()}
      >
        Keep open
      </button>
      <button
        type="button"
        class="text-accent-red"
        style={{
          background: 'transparent',
          border: 'none',
          padding: '0 8px',
          cursor: 'default',
          'font-size': '11px',
        }}
        onClick={confirm}
      >
        Close anyway
      </button>
    </div>
  );
}

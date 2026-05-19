import { Show } from 'solid-js';

/** UI-SPEC §5 / D-04 / D-05 — inline non-modal multi-line paste banner. */
export interface PasteGuardProps {
  pendingText: string;
  onSend: () => void;
  onDiscard: () => void;
}

const PREVIEW_MAX = 80;

export default function PasteGuard(props: PasteGuardProps) {
  const lines = () => props.pendingText.split('\n');
  const lineCount = () => lines().length;
  const preview = () => {
    const first = lines()[0] ?? '';
    return first.length > PREVIEW_MAX
      ? first.slice(0, PREVIEW_MAX) + '…'
      : first;
  };

  return (
    <div class="paste-guard">
      <div class="pg-row pg-preview">
        <span class="pg-glyph">⏵</span>
        <span class="pg-text">{preview()}</span>
        <Show when={lineCount() > 1}>
          <span class="pg-count">({lineCount()} lines)</span>
        </Show>
      </div>
      <div class="pg-row pg-actions">
        <button class="pg-send" type="button" onClick={() => props.onSend()}>
          Send <span class="pg-hint">⏎</span>
        </button>
        <button
          class="pg-discard"
          type="button"
          onClick={() => props.onDiscard()}
        >
          Discard <span class="pg-hint">Esc</span>
        </button>
        <span class="pg-spacer" />
        <span class="pg-bypass">⌘⇧V skips this</span>
      </div>
    </div>
  );
}

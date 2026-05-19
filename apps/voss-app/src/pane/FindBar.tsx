import { createSignal } from 'solid-js';

/** UI-SPEC §8 / PTY-03 — ⌘F scrollback search overlay (SearchAddon-wired). */
export interface FindBarProps {
  onNext: (query: string) => void;
  onPrev: (query: string) => void;
  onClose: () => void;
}

export default function FindBar(props: FindBarProps) {
  const [query, setQuery] = createSignal('');

  const findNext = () => props.onNext(query());
  const findPrev = () => props.onPrev(query());

  return (
    <div class="find-bar">
      <input
        class="fb-input"
        type="text"
        placeholder="Find…"
        value={query()}
        onInput={(e) => setQuery(e.currentTarget.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') (e.shiftKey ? findPrev : findNext)();
          else if (e.key === 'Escape') props.onClose();
        }}
        autofocus
      />
      <button class="fb-btn" type="button" title="previous" onClick={findPrev}>
        ↑
      </button>
      <button class="fb-btn" type="button" title="next" onClick={findNext}>
        ↓
      </button>
      <button
        class="fb-btn fb-close"
        type="button"
        title="close"
        onClick={() => props.onClose()}
      >
        ✕
      </button>
    </div>
  );
}

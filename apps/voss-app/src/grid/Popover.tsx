import { onMount, onCleanup } from 'solid-js';
import type { JSX } from 'solid-js';

interface PopoverProps {
  anchor: HTMLElement;
  onClose: () => void;
  children: JSX.Element;
}

export default function Popover(props: PopoverProps) {
  let rootRef!: HTMLDivElement;
  const rect = props.anchor.getBoundingClientRect();

  const onDocClick = (e: MouseEvent) => {
    if (!rootRef.contains(e.target as Node)) props.onClose();
  };
  const onDocKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') props.onClose();
  };

  onMount(() => {
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', onDocKey);
  });
  onCleanup(() => {
    document.removeEventListener('click', onDocClick, true);
    document.removeEventListener('keydown', onDocKey);
  });

  return (
    <div
      ref={rootRef}
      style={{
        position: 'fixed',
        top: `${rect.bottom + 2}px`,
        left: `${rect.right - 220}px`,
        'z-index': 20,
        background: 'var(--bg-3)',
        border: '1px solid var(--border)',
        'font-size': '11px',
        'min-width': '220px',
      }}
    >
      {props.children}
    </div>
  );
}

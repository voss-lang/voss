import { createSignal } from 'solid-js';
import { KNOWN_AGENT_CLIS } from './agentDetect';

let _counter = 0;

export function mintSlug(cliBinary?: string): string {
  _counter += 1;
  const name = cliBinary?.trim().toLowerCase().split('/').pop() ?? '';
  const prefix = KNOWN_AGENT_CLIS.has(name) ? name : 'pane';
  return `${prefix}-${_counter}`;
}

const [slugByPaneId, setSlugByPaneId] = createSignal<Record<string, string>>(
  {},
);

export function registerSlug(paneId: string, slug: string): void {
  setSlugByPaneId((prev) => ({ ...prev, [paneId]: slug }));
}

export function unregisterSlug(paneId: string): void {
  setSlugByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { slugByPaneId };

export function __resetSlugs(): void {
  setSlugByPaneId({});
  _counter = 0;
}

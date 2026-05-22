/**
 * Shared reactive registry: pane id → context data (F4).
 * PaneComponent writes; App.tsx reads for the focused pane.
 */
import { createSignal } from 'solid-js';
import type { ContextData } from './pty-ipc';

const [contextByPaneId, setContextByPaneId] = createSignal<
  Record<string, ContextData>
>({});

export function registerPaneContext(paneId: string, data: ContextData): void {
  setContextByPaneId((prev) => ({ ...prev, [paneId]: data }));
}

export function unregisterPaneContext(paneId: string): void {
  setContextByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { contextByPaneId };

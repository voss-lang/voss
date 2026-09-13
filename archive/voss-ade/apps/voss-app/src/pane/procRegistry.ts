import { createSignal } from 'solid-js';

const [procByPaneId, setProcByPaneId] = createSignal<Record<string, string>>(
  {},
);

export function registerPaneProc(paneId: string, proc: string): void {
  setProcByPaneId((prev) => {
    if (prev[paneId] === proc) return prev;
    return { ...prev, [paneId]: proc };
  });
}

export function unregisterPaneProc(paneId: string): void {
  setProcByPaneId((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { procByPaneId };

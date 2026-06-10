/**
 * V17-04 (VBUS-03): pane agent-identity slugs.
 *
 * Every pane spawn mints a readable slug (D-12: `claude-1` for agent CLIs,
 * `pane-3` for plain shells) that is injected into the child env as
 * VOSS_AGENT_ID (D-11: ALL panes, before any agent runs). Registered here
 * in-memory per paneId; exported for A6 to persist into the pane config when
 * session-restore ships (D-13 best-effort stability — no on-disk persistence
 * in V17). Mirrors adoptionRegistry.ts (module signal, immutable spread).
 */
import { createSignal } from 'solid-js';
import { KNOWN_AGENT_CLIS } from './agentDetect';

let _counter = 0;

/**
 * Mint a readable agent-identity slug. Agent CLIs get `<cli>-<n>`
 * (basename, lowercased); plain shells / non-agent binaries get `pane-<n>`.
 * The counter is shared across both forms so slugs are globally unique.
 */
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

/** Test-only reset (module signal + counter are global). */
export function __resetSlugs(): void {
  setSlugByPaneId({});
  _counter = 0;
}

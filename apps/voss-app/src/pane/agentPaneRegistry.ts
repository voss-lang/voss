/**
 * Latching agent detection registry: once a pane's foreground process
 * matches a known agent CLI name (via exact or fuzzy match), the pane
 * is permanently marked as an agent pane until cleanup.
 *
 * This solves the pgid-poll problem: Claude Code's OS process is "node",
 * but its OSC title briefly says "claude" — the latch captures that.
 */
import { createSignal } from 'solid-js';
import { looksLikeAgent } from './agentDetect';

export type DetectedAgent = {
  cliBinary: string;
};

const [agentPaneById, setAgentPaneById] = createSignal<
  Record<string, DetectedAgent>
>({});

/**
 * Call on every proc/title update. If the name looks like an agent CLI
 * and the pane isn't already latched, record it.
 */
export function maybeLatchAgent(paneId: string, proc: string): void {
  setAgentPaneById((prev) => {
    if (prev[paneId]) return prev; // already latched
    if (!looksLikeAgent(proc)) return prev;
    // Extract the canonical CLI name from the proc string
    const lower = proc.toLowerCase();
    const cli =
      lower.includes('claude') ? 'claude'
        : lower.includes('codex') ? 'codex'
        : lower.includes('gemini') ? 'gemini'
        : lower.includes('opencode') ? 'opencode'
        : lower.includes('aider') ? 'aider'
        : lower.includes('cursor') ? 'cursor'
        : proc;
    return { ...prev, [paneId]: { cliBinary: cli } };
  });
}

export function unregisterAgentPane(paneId: string): void {
  setAgentPaneById((prev) => {
    if (!(paneId in prev)) return prev;
    const next = { ...prev };
    delete next[paneId];
    return next;
  });
}

export { agentPaneById };

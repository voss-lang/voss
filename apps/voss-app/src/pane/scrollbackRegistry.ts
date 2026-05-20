/**
 * A6-03 Task 1 — per-pane scrollback provider registry.
 *
 * Each PaneComponent registers a callback that extracts the last N lines
 * from its xterm `buffer.normal` (D-03). The session lifecycle calls
 * `getScrollbackSnapshot()` on quit to collect all pane scrollback in one
 * pass. Providers that throw are skipped with a stderr warning (T-A6-04).
 */

/** A provider returns plain-text lines from the pane's normal buffer. */
export type ScrollbackProvider = () => string[];

const providers = new Map<string, ScrollbackProvider>();

export function registerScrollbackProvider(
  paneId: string,
  provider: ScrollbackProvider,
): void {
  providers.set(paneId, provider);
}

export function unregisterScrollbackProvider(paneId: string): void {
  providers.delete(paneId);
}

/**
 * Collect scrollback from every registered pane. Each result is capped to
 * the last `limit` lines (PER-01: default 2,000). A failing provider is
 * skipped — other panes are unaffected.
 */
export function getScrollbackSnapshot(
  limit = 2000,
): Map<string, string[]> {
  const result = new Map<string, string[]>();
  for (const [id, provider] of providers) {
    try {
      const lines = provider();
      result.set(id, lines.slice(-limit));
    } catch (e) {
      console.warn(`[voss-app] scrollback provider "${id}" failed:`, e);
    }
  }
  return result;
}

/** Test-only: clear all providers for hermetic tests. */
export function _resetForTest(): void {
  providers.clear();
}

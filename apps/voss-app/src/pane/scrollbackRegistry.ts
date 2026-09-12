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

/** Test-only: clear all providers for hermetic tests */
export function _resetForTest(): void {
  providers.clear();
}

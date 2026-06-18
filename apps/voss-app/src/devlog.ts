// Frontend → dev-terminal logger. The webview's console.* only reaches
// devtools; this mirrors a line to the Rust `ui_log` command so it surfaces in
// the `pnpm tauri dev` terminal alongside the sidecar + Tauri output. Use it to
// trace user-action chains (e.g. the composer create → dispatch → fetch path)
// without opening devtools.
//
// SECURITY: never pass the serve token or any secret — `ui_log` prints to the
// shared dev console (mirrors T-V15-10).

import { invoke } from '@tauri-apps/api/core';

type Level = 'info' | 'warn' | 'error';

/** JSON-stringify a value for a log line, tolerating cycles / non-serializable
 *  inputs and normalizing Errors to name+message+stack. */
function fmt(data: unknown): string {
  if (data === undefined) return '';
  if (data instanceof Error) {
    return ` ${data.name}: ${data.message}${data.stack ? `\n${data.stack}` : ''}`;
  }
  try {
    return ` ${JSON.stringify(data)}`;
  } catch {
    return ` ${String(data)}`;
  }
}

/**
 * Log to the webview console AND the dev terminal (via `ui_log`).
 * `scope` is a dotted tag (e.g. "composer.create"). `data` is appended as JSON
 * (or normalized Error). The invoke is fire-and-forget — failures are swallowed
 * so logging never breaks the action it traces (e.g. outside the Tauri shell).
 */
export function devlog(
  level: Level,
  scope: string,
  message: string,
  data?: unknown,
): void {
  const detail = `${message}${fmt(data)}`;
  const sink = level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;
  sink(`[${scope}] ${detail}`);
  // Defensive: `invoke` throws synchronously outside a Tauri shell (e.g. unit
  // tests / a browser). Logging must never break the action it traces.
  try {
    const p = invoke('ui_log', { level, scope, detail });
    if (p && typeof (p as Promise<unknown>).catch === 'function') {
      (p as Promise<unknown>).catch(() => {});
    }
  } catch {
    /* not in a Tauri shell — the console mirror above already fired */
  }
}

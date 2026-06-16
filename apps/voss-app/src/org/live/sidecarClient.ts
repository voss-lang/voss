// V15-01 (VLIVE-01) sidecar invoke wrapper. The webview cannot start
// `voss serve` itself (V14 Pitfall 4 — the V13.1 launcher imports
// node:child_process); only the Tauri side can spawn it. This module is the
// single frontend entry: `start_voss_serve` lazily spawns one server per
// workspace cwd, reuses it while alive, and returns the {port, token}
// handshake. Thin and side-effect-free — client construction is Plan 02.

import { invoke } from '@tauri-apps/api/core';
import { devlog } from '../../devlog';

/** The `voss serve` startup handshake returned through Tauri IPC. */
export interface ServeHandshake {
  port: number;
  token: string;
}

/**
 * Start (or reuse) the `voss serve` sidecar for `cwd` and return its
 * `{port, token}` handshake.
 *
 * The returned `token` is in-memory only: it is the sole auth for the
 * loopback server and must never be logged, persisted, or stringified
 * (T-V15-10).
 */
export async function startVossServe(cwd: string): Promise<ServeHandshake> {
  devlog('info', 'sidecar.serve', 'start_voss_serve invoke', { cwd });
  try {
    const h = await invoke<ServeHandshake>('start_voss_serve', { cwd });
    // T-V15-10: log the port only — the token is never logged or stringified.
    devlog('info', 'sidecar.serve', 'handshake ok', { port: h.port });
    return h;
  } catch (e) {
    devlog('error', 'sidecar.serve', 'start_voss_serve failed', e);
    throw e;
  }
}

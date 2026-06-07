// Runtime validation boundary for `load_run` output (D-02).
//
// types.ts declares the assumed CLI-JSON shapes; this guard is where contract
// drift surfaces as an EXPLICIT error rather than a silent render miss. Keep
// the checks structural and cheap — they run on every run load at the Tauri
// boundary, not in a hot loop.

import type { RunData } from './types';

/** Structural type-guard: true when `o` has the load-bearing RunData shape. */
export function isRunData(o: unknown): o is RunData {
  if (typeof o !== 'object' || o === null) return false;
  const r = o as Record<string, unknown>;
  if (typeof r.run_id !== 'string') return false;
  const st = r.session_tree;
  if (typeof st !== 'object' || st === null) return false;
  if (!Array.isArray((st as Record<string, unknown>).nodes)) return false;
  return true;
}

/**
 * Assert + narrow `o` to RunData, throwing an Error that names the failing
 * field. This is the D-02 drift detector: malformed `load_run` output is
 * rejected loudly instead of half-rendering.
 */
export function assertRunData(o: unknown): RunData {
  if (typeof o !== 'object' || o === null) {
    throw new Error(
      `assertRunData: expected an object, got ${o === null ? 'null' : typeof o}`,
    );
  }
  const r = o as Record<string, unknown>;
  if (typeof r.run_id !== 'string') {
    throw new Error('assertRunData: missing or non-string field "run_id"');
  }
  const st = r.session_tree;
  if (typeof st !== 'object' || st === null) {
    throw new Error('assertRunData: missing or invalid field "session_tree"');
  }
  if (!Array.isArray((st as Record<string, unknown>).nodes)) {
    throw new Error('assertRunData: field "session_tree.nodes" must be an array');
  }
  return o as RunData;
}

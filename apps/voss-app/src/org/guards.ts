import type { RunData } from './types';

export function isRunData(o: unknown): o is RunData {
  if (typeof o !== 'object' || o === null) return false;
  const r = o as Record<string, unknown>;
  if (typeof r.run_id !== 'string') return false;
  const st = r.session_tree;
  if (typeof st !== 'object' || st === null) return false;
  if (!Array.isArray((st as Record<string, unknown>).nodes)) return false;
  return true;
}

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

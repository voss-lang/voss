import { describe, it, expect, vi } from 'vitest';

// Tauri mock — guards have no invoke calls, but keep the import chain inert.
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import { isRunData, assertRunData } from '../guards';
import type { RunData } from '../types';
import nodeRoot from './fixtures/node-root.json';
import nodeChild from './fixtures/node-child.json';
import reviewSidecar from './fixtures/review-sidecar.json';
import runFinal from './fixtures/run-final.json';
import auditReport from './fixtures/audit-report.json';

// Assemble a valid RunData from the golden fixtures (the shape load_run returns).
const VALID = {
  run_id: nodeRoot.root_id,
  session_tree: { root_id: nodeRoot.root_id, nodes: [nodeRoot, nodeChild] },
  review: { [nodeChild.id]: reviewSidecar },
  audit: auditReport,
  run_final: runFinal,
} as unknown as RunData;

describe('guards — D-02 Tauri boundary', () => {
  it('isRunData returns true for assembled fixture RunData', () => {
    expect(isRunData(VALID)).toBe(true);
  });

  it('isRunData returns false when run_id missing or nodes is not an array', () => {
    const noId: Record<string, unknown> = { ...(VALID as unknown as Record<string, unknown>) };
    delete noId.run_id;
    expect(isRunData(noId)).toBe(false);

    const badNodes = {
      ...(VALID as unknown as Record<string, unknown>),
      session_tree: { root_id: 'x', nodes: 'not-an-array' },
    };
    expect(isRunData(badNodes)).toBe(false);

    expect(isRunData(null)).toBe(false);
    expect(isRunData(42)).toBe(false);
  });

  it('assertRunData throws an Error naming the missing/wrong field (drift → explicit error)', () => {
    const noId: Record<string, unknown> = { ...(VALID as unknown as Record<string, unknown>) };
    delete noId.run_id;
    expect(() => assertRunData(noId)).toThrow(/run_id/);

    const badNodes = {
      ...(VALID as unknown as Record<string, unknown>),
      session_tree: { root_id: 'x', nodes: 'not-an-array' },
    };
    expect(() => assertRunData(badNodes)).toThrow(/nodes/);

    // a valid payload passes through and narrows to RunData
    expect(assertRunData(VALID).run_id).toBe(nodeRoot.root_id);
  });
});

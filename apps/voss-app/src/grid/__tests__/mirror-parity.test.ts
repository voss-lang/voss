import { describe, it, expect, vi } from 'vitest';

/**
 * GRD-08 Solid↔Rust mirror parity. `invoke` is mocked to a fake in-memory
 * Rust store that applies the SAME semantics as `grid::overwrite` /
 * `grid::snapshot` (sync_grid overwrites; get_grid clones back). After every
 * structural op the fake mirror must deep-equal the Solid tree, and no IPC
 * payload may carry a filesystem path / `.voss` (GRD-08 no-disk-IO).
 */

const rust = vi.hoisted(() => {
  const calls: { cmd: string; args: unknown }[] = [];
  let store: unknown = null;
  const invoke = vi.fn((cmd: string, args?: Record<string, unknown>) => {
    calls.push({ cmd, args });
    if (cmd === 'sync_grid') store = JSON.parse(JSON.stringify(args!.newState));
    if (cmd === 'get_grid') return Promise.resolve(store);
    return Promise.resolve(undefined);
  });
  return { invoke, calls, get: () => store };
});
vi.mock('@tauri-apps/api/core', () => ({ invoke: rust.invoke }));

import { type GridStore, makePane } from '../tree';
import { splitFocused, forkFocused, closeFocused } from '../operations';
import { focusByIndex } from '../focus';
import { resizeByKeyboard } from '../resize';
import { invoke } from '@tauri-apps/api/core';

const W = 1200;
const Hh = 800;
const CW = 8;
const CH = 16;

function snapshot(s: GridStore) {
  return JSON.parse(JSON.stringify(s));
}
function assertParity(s: GridStore) {
  // Mirror structurally equals the Solid tree after the change settles.
  expect(rust.get()).toEqual(snapshot(s));
  // No IPC payload ever carries a disk path / .voss (GRD-08).
  const blob = JSON.stringify(rust.calls);
  expect(blob).not.toMatch(/\.voss/);
  expect(blob).not.toMatch(/\/(Users|home|tmp|private)\//);
}

describe('GRD-08 — Rust mirror tracks the Solid tree, zero disk I/O', () => {
  it('split-H → split-V → fork → focus → keyboard-resize → close all stay parity', async () => {
    const p = makePane();
    const s: GridStore = { root: p, focusedId: p.id };

    splitFocused(s, 'H', { winW: W, winH: Hh, cw: CW, ch: CH });
    assertParity(s);

    splitFocused(s, 'V', { winW: W, winH: Hh, cw: CW, ch: CH });
    assertParity(s);

    forkFocused(s, { winW: W, winH: Hh, cw: CW, ch: CH });
    assertParity(s);

    focusByIndex(s, 1);
    assertParity(s);

    resizeByKeyboard(s, 'right', W, Hh, CW, CH);
    assertParity(s);

    closeFocused(s);
    assertParity(s);

    // get_grid read-back equals the final Solid tree (parity command).
    const back = await invoke('get_grid');
    expect(back).toEqual(snapshot(s));
    expect(rust.calls.some((c) => c.cmd === 'sync_grid')).toBe(true);
  });
});

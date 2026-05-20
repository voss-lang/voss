import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';
// Source-content guards moved out of this file — the A4-01/A4-02 plan
// `grep` verify commands enforce them at the build harness level; this
// suite keeps acceptance focused on integrated runtime behavior.

/**
 * A4-05 Task 1 — requirement-level acceptance for LAY-01..LAY-08.
 *
 * Each describe block names exactly one LAY requirement so a failure
 * traces back to the spec line in `.planning/ROADMAP.md`. This file
 * intentionally exercises the integrated UI (real `PresetSwitcher`,
 * real `dispatchKey`, real `GridRoot`) so contract drift between layers
 * surfaces here even when each layer's own tests stay green.
 *
 * Mocked: `@tauri-apps/api/core` (no live IPC) and the A2 PTY component
 * (lightweight DOM stub — matches the existing GridRoot test fixture).
 */

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('../../pane/PaneComponent', () => ({
  default: (p: { index?: number }) => {
    const d = document.createElement('div');
    d.setAttribute('data-testid', 'pane');
    d.setAttribute('data-idx', String(p.index ?? 1));
    return d;
  },
}));

import {
  applyPreset,
  applyPresetFromLeaves,
  LAYOUT_PRESETS,
  nextPreset,
  type ActiveLayout,
  type LayoutPreset,
} from '../layoutPresets';
import {
  collectLeaves,
  makePane,
  makeSplit,
  recomputeIndices,
  type PaneLeaf,
  type TreeNode,
} from '../tree';
import { applyLoadedLayout, serializeLayout } from '../layoutCommands';
import {
  EMPTY_LIST,
  INVALID_FILE,
  INVALID_NAME,
  LOAD_FAILED,
  LOAD_LAYOUT_LABEL,
  LOAD_SUCCESS,
  NAME_EXISTS_CONFIRM,
  NOT_FOUND,
  SAVE_FAILED,
  SAVE_LAYOUT_LABEL,
  SAVE_SUCCESS,
  UNSUPPORTED_VERSION,
  type LayoutFile,
} from '../layoutStorage';
import PresetSwitcher from '../../components/titlebar/PresetSwitcher';
import GridRoot from '../GridRoot';

// --- Test harness -----------------------------------------------------------

let dispose: (() => void) | undefined;
function mount(ui: () => unknown) {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}
afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

function makePanes(n: number, ctx?: { cwd?: string; shell?: string }): PaneLeaf[] {
  return Array.from({ length: n }, () => makePane(ctx));
}
function chain(orientation: 'H' | 'V', leaves: PaneLeaf[]): TreeNode {
  if (leaves.length === 1) return leaves[0];
  return makeSplit(orientation, leaves[0], chain(orientation, leaves.slice(1)));
}

// ---------------------------------------------------------------------------
// LAY-01 — Four preset transforms exist and apply cleanly
// ---------------------------------------------------------------------------

describe('LAY-01 — four layout presets are visual transforms over the pane tree', () => {
  it('exposes exactly fanout, pipeline, swarm, watchers in cycle order', () => {
    expect([...LAYOUT_PRESETS]).toEqual([
      'fanout',
      'pipeline',
      'swarm',
      'watchers',
    ]);
  });

  it('applyPreset returns a tree with the same leaf count for every preset', () => {
    for (const n of [1, 2, 4, 9, 16, 17]) {
      const root = chain('H', makePanes(n));
      for (const preset of LAYOUT_PRESETS) {
        const next = applyPreset(root, preset);
        expect(collectLeaves(next)).toHaveLength(n);
      }
    }
  });

  it('applyPreset works without any DOM or Tauri context', () => {
    // Runtime proof of purity — if `layoutPresets.ts` ever picked up a
    // DOM/Tauri/solid-js dependency by accident the import alone (in
    // this jsdom-but-no-Tauri environment) would not catch it, but
    // calling applyPreset over plain inputs and getting plain outputs
    // does. The static guard lives in the A4-01 plan verify line.
    const leaves = makePanes(3);
    const result = applyPreset(chain('H', leaves), 'pipeline');
    expect(result.kind).toBe('split');
    expect(collectLeaves(result)).toHaveLength(3);
  });
});

// ---------------------------------------------------------------------------
// LAY-02 — Titlebar switcher is controlled + 'custom' state rendered
// ---------------------------------------------------------------------------

describe('LAY-02 — titlebar preset switcher is controlled', () => {
  it('aria-pressed reflects the activeLayout prop, no local state', () => {
    let layout: ActiveLayout = 'fanout';
    const el = mount(() => (
      <PresetSwitcher activeLayout={layout} onSelect={() => {}} />
    ));
    const fanout = el.querySelector(
      'button[aria-label="Switch layout to fanout"]',
    ) as HTMLButtonElement;
    expect(fanout.getAttribute('aria-pressed')).toBe('true');
    // Clicking another preset must NOT change aria-pressed (controlled).
    const pipeline = el.querySelector(
      'button[aria-label="Switch layout to pipeline"]',
    ) as HTMLButtonElement;
    fireEvent.click(pipeline);
    expect(fanout.getAttribute('aria-pressed')).toBe('true');
    expect(pipeline.getAttribute('aria-pressed')).toBe('false');
  });

  it("renders the 'custom' label only when activeLayout === 'custom'", () => {
    const elActive = mount(() => (
      <PresetSwitcher activeLayout="swarm" onSelect={() => {}} />
    ));
    expect(elActive.querySelector('[data-preset-state="custom"]')).toBeNull();
    dispose?.();
    dispose = undefined;
    document.body.innerHTML = '';

    const elCustom = mount(() => (
      <PresetSwitcher activeLayout="custom" onSelect={() => {}} />
    ));
    const custom = elCustom.querySelector('[data-preset-state="custom"]');
    expect(custom).not.toBeNull();
    expect(custom!.textContent?.trim()).toBe('custom');
    expect(custom!.tagName).not.toBe('BUTTON');
  });
});

// ---------------------------------------------------------------------------
// LAY-03 — Cmd+G fixed cycle order and live grid integration
// ---------------------------------------------------------------------------

describe('LAY-03 — Cmd+G cycles presets in fixed order', () => {
  it('nextPreset cycles custom → fanout → pipeline → swarm → watchers → fanout', () => {
    expect(nextPreset('custom')).toBe('fanout');
    expect(nextPreset('fanout')).toBe('pipeline');
    expect(nextPreset('pipeline')).toBe('swarm');
    expect(nextPreset('swarm')).toBe('watchers');
    expect(nextPreset('watchers')).toBe('fanout');
  });

  it('GridRoot ⌘G drives onLayoutChange through the full cycle', () => {
    let active: ActiveLayout = 'custom';
    const onLayoutChange = vi.fn((next: ActiveLayout) => {
      active = next;
    });
    const el = mount(() => (
      <GridRoot
        activeLayout={() => active}
        onLayoutChange={onLayoutChange}
      />
    ));
    // Grow to 3 panes so transform geometry actually changes.
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    fireEvent.keyDown(window, { code: 'KeyD', key: 'd', metaKey: true });
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(3);
    onLayoutChange.mockClear();

    const cycle: LayoutPreset[] = [
      'fanout',
      'pipeline',
      'swarm',
      'watchers',
      'fanout',
    ];
    for (const expected of cycle) {
      fireEvent.keyDown(window, { code: 'KeyG', key: 'g', metaKey: true });
      expect(onLayoutChange).toHaveBeenLastCalledWith(expected);
    }
    // Panes preserved through five cycles.
    expect(el.querySelectorAll('[data-testid="pane"]')).toHaveLength(3);
  });
});

// ---------------------------------------------------------------------------
// LAY-04 — No existing pane id is destroyed on preset switch or layout load
// ---------------------------------------------------------------------------

describe('LAY-04 — preset switches and layout loads preserve every pane id', () => {
  it('applyPreset on 1..17 panes preserves the exact id set for every preset', () => {
    for (const n of [1, 2, 3, 4, 6, 9, 16, 17]) {
      const leaves = makePanes(n);
      const before = new Set(leaves.map((l) => l.id));
      const root = chain('H', leaves);
      recomputeIndices(root);
      for (const preset of LAYOUT_PRESETS) {
        const next = applyPreset(root, preset);
        const after = new Set(collectLeaves(next).map((l) => l.id));
        expect(after).toEqual(before);
      }
    }
  });

  it('applyLoadedLayout preserves every existing id when saved < current', () => {
    const current = makePanes(7);
    const beforeIds = new Set(current.map((l) => l.id));
    const saved = makePanes(2);
    const file: LayoutFile = {
      version: 1,
      activePreset: 'watchers',
      grid: {
        root: makeSplit('V', saved[0], saved[1]),
        focusedId: saved[0].id,
      },
    };
    const result = applyLoadedLayout([...current], file);
    const afterIds = new Set(collectLeaves(result.root).map((l) => l.id));
    expect(afterIds).toEqual(beforeIds);
  });
});

// ---------------------------------------------------------------------------
// LAY-05 — Capacity-mismatch behavior (under/over)
// ---------------------------------------------------------------------------

describe('LAY-05 — capacity mismatch: spill on under, spawn on over, no fillers', () => {
  it('under-capacity preset (1 pane → swarm) yields exactly 1 leaf — no fillers', () => {
    const next = applyPresetFromLeaves(makePanes(1), 'swarm');
    expect(collectLeaves(next)).toHaveLength(1);
  });

  it('swarm at n=17 keeps every id and spills through the last cell', () => {
    const leaves = makePanes(17);
    const before = new Set(leaves.map((l) => l.id));
    const next = applyPresetFromLeaves(leaves, 'swarm');
    const after = collectLeaves(next);
    expect(after).toHaveLength(17);
    expect(new Set(after.map((l) => l.id))).toEqual(before);
  });

  it('applyLoadedLayout with saved > current spawns net-new with saved cwd/shell', () => {
    const current = makePanes(2);
    const saved = [
      makePane({ cwd: '/s0', shell: 'bash' }),
      makePane({ cwd: '/s1', shell: 'bash' }),
      makePane({ cwd: '/s2', shell: 'fish' }),
    ];
    const file: LayoutFile = {
      version: 1,
      activePreset: 'pipeline',
      grid: { root: chain('H', saved), focusedId: saved[0].id },
    };
    const result = applyLoadedLayout([...current], file);
    const out = collectLeaves(result.root);
    expect(out).toHaveLength(3);
    expect(out[2].cwd).toBe('/s2');
    expect(out[2].shell).toBe('fish');
  });
});

// ---------------------------------------------------------------------------
// LAY-06 — Save callable stub + exact UI-SPEC copy
// ---------------------------------------------------------------------------

describe('LAY-06 — save layout callable stub and exact copy', () => {
  it('exposes the exact A4-UI-SPEC save copy', () => {
    expect(SAVE_LAYOUT_LABEL).toBe('Save layout as...');
    expect(SAVE_SUCCESS).toBe('layout saved');
    expect(SAVE_FAILED).toBe('could not save layout');
    expect(NAME_EXISTS_CONFIRM).toBe('replace existing layout?');
    expect(INVALID_NAME).toBe('layout name cannot contain /, \\ or ..');
  });

  it('serializeLayout produces a version-1 LayoutFile with cwd/shell only', () => {
    const leaves = makePanes(2, { cwd: '/repo', shell: 'zsh' });
    const root = chain('H', leaves);
    recomputeIndices(root);
    const file = serializeLayout(root, leaves[0].id, 'fanout');
    expect(file.version).toBe(1);
    expect(file.activePreset).toBe('fanout');
    // Round-trip JSON proves serializability.
    const json = JSON.stringify(file);
    const back = JSON.parse(json) as LayoutFile;
    expect(back).toEqual(file);
    // Canonical fields only — no runtime junk.
    expect(json).not.toMatch(/ptySessionId|scrollback|processName|"env"/);
  });
});

// ---------------------------------------------------------------------------
// LAY-07 — Load callable stub + versioned schema
// ---------------------------------------------------------------------------

describe('LAY-07 — load layout callable stub and versioned schema', () => {
  it('exposes the exact A4-UI-SPEC load copy', () => {
    expect(LOAD_LAYOUT_LABEL).toBe('Load layout...');
    expect(LOAD_SUCCESS).toBe('layout loaded');
    expect(LOAD_FAILED).toBe('could not load layout');
    expect(EMPTY_LIST).toBe('no saved layouts');
    expect(NOT_FOUND).toBe('layout not found');
    expect(INVALID_FILE).toBe('layout ignored: invalid file');
    expect(UNSUPPORTED_VERSION).toBe('layout ignored: unsupported version');
  });

  it("LayoutFile shape carries integer version and activePreset/grid keys", () => {
    const leaves = makePanes(1, { cwd: '/repo', shell: 'zsh' });
    const file = serializeLayout(leaves[0], leaves[0].id, 'custom');
    const json = JSON.parse(JSON.stringify(file)) as Record<string, unknown>;
    expect(json.version).toBe(1);
    expect('activePreset' in json).toBe(true);
    expect('grid' in json).toBe(true);
    // activePreset === null when off-cycle.
    expect(json.activePreset).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// LAY-08 — No L2 semantic strings leak into A4 UI
// ---------------------------------------------------------------------------

describe('LAY-08 — A4 surface carries NO L2 semantic labels', () => {
  it('rendered PresetSwitcher contains only the four preset labels', () => {
    const el = mount(() => (
      <PresetSwitcher activeLayout="fanout" onSelect={() => {}} />
    ));
    const labels = Array.from(el.querySelectorAll('button')).map(
      (b) => b.textContent?.trim(),
    );
    expect(labels).toEqual(['fanout', 'pipeline', 'swarm', 'watchers']);
  });

  it('PresetSwitcher renders no L2 vocabulary in any of its three states', () => {
    const FORBIDDEN = /\b(agent|worktree|reviewer|model|cost|token)\b/i;
    for (const state of ['custom', 'fanout', 'swarm'] as const) {
      const el = mount(() => (
        <PresetSwitcher activeLayout={state} onSelect={() => {}} />
      ));
      expect(el.textContent ?? '').not.toMatch(FORBIDDEN);
      dispose?.();
      dispose = undefined;
      document.body.innerHTML = '';
    }
  });

  it('UI-SPEC copy constants carry no L2 vocabulary', () => {
    const FORBIDDEN = /\b(agent|worktree|reviewer|model|cost|token)\b/i;
    for (const literal of [
      SAVE_LAYOUT_LABEL,
      LOAD_LAYOUT_LABEL,
      SAVE_SUCCESS,
      LOAD_SUCCESS,
      EMPTY_LIST,
      NAME_EXISTS_CONFIRM,
      INVALID_NAME,
      NOT_FOUND,
      INVALID_FILE,
      UNSUPPORTED_VERSION,
      SAVE_FAILED,
      LOAD_FAILED,
    ]) {
      expect(literal).not.toMatch(FORBIDDEN);
    }
  });
});

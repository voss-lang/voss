// VCKP-10 — keyboard navigation + reduced motion + monospace numerics.
//
// Focus order: the three cockpit regions carry tabindex="0" in DOM order
// Board -> detail drawer -> timeline rail, so Tab traverses them in that
// order (tab order == document order for tabindex=0).
//
// Reduced motion: cockpitStyles.css must carry a
// `@media (prefers-reduced-motion: reduce)` block that disables cockpit
// animations INCLUDING the AttentionQueue pill pulse (.attn-pill--pulse).
// jsdom does not evaluate media queries, so the gate is asserted on the
// stylesheet source (?raw) — the same grep-style discipline as the token gate.

import { describe, it, expect, vi, afterEach } from 'vitest';

// CockpitShell's onMount load path: enumerate_runs -> [] keeps the snapshot
// empty (loading=false, no error) so the 4-region grid renders immediately.
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn((cmd: string) => {
    if (cmd === 'enumerate_runs') return Promise.resolve([]);
    return Promise.resolve(undefined);
  }),
}));

import { render } from 'solid-js/web';
import CockpitShell from '../CockpitShell';
// Source files are read via fs (NOT a vite `?raw` import): the css is also a
// regular style import, and the transformed-module cache can serve stale
// content for the `?raw` variant.
// @ts-ignore -- node builtin available in the vitest runtime; the app tsconfig is browser-lib only.
import { readFileSync } from 'node:fs';

// Paths are relative to the vitest root (apps/voss-app — vitest.config.ts).
const rawCockpitCss: string = readFileSync(
  'src/org/cockpit/cockpitStyles.css',
  'utf8',
);
const rawGateBar: string = readFileSync('src/org/cockpit/GateBar.tsx', 'utf8');

let dispose: (() => void) | undefined;
async function mountCockpit(): Promise<HTMLElement> {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(
    () =>
      (
        <CockpitShell cwd="/tmp" cliBinary="voss" onClose={() => {}} />
      ) as never,
    root,
  );
  // Flush the onMount enumerate_runs microtask chain.
  await Promise.resolve();
  await Promise.resolve();
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
});

describe('VCKP-10 — keyboard focus order Board → drawer → timeline', () => {
  it('the three regions are tabbable (tabindex=0) and appear in document order', async () => {
    const el = await mountCockpit();
    const board = el.querySelector('.cockpit-board') as HTMLElement;
    const drawer = el.querySelector('.cockpit-drawer') as HTMLElement;
    const rail = el.querySelector('.cockpit-rail') as HTMLElement;
    expect(board).toBeTruthy();
    expect(drawer).toBeTruthy();
    expect(rail).toBeTruthy();

    // Tabbable.
    expect(board.getAttribute('tabindex')).toBe('0');
    expect(drawer.getAttribute('tabindex')).toBe('0');
    expect(rail.getAttribute('tabindex')).toBe('0');

    // Document order == tab order for tabindex=0: board precedes drawer
    // precedes rail.
    expect(
      board.compareDocumentPosition(drawer) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      drawer.compareDocumentPosition(rail) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('the tabbable sequence inside the grid starts at the Board region', async () => {
    const el = await mountCockpit();
    const grid = el.querySelector('.cockpit-grid') as HTMLElement;
    const tabbables = Array.from(
      grid.querySelectorAll<HTMLElement>(
        '[tabindex="0"], button:not([disabled]), textarea:not([disabled]), input:not([disabled])',
      ),
    );
    expect(tabbables.length).toBeGreaterThanOrEqual(3);
    expect(tabbables[0].classList.contains('cockpit-board')).toBe(true);
    const drawerIdx = tabbables.findIndex((t) =>
      t.classList.contains('cockpit-drawer'),
    );
    const railIdx = tabbables.findIndex((t) =>
      t.classList.contains('cockpit-rail'),
    );
    expect(drawerIdx).toBeGreaterThan(0);
    expect(railIdx).toBeGreaterThan(drawerIdx);
  });
});

describe('VCKP-10 — reduced motion disables cockpit animation', () => {
  it('cockpitStyles.css has a prefers-reduced-motion block covering the AttentionQueue pulse', () => {
    const media = rawCockpitCss.match(
      /@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)/,
    );
    expect(media, 'reduced-motion media query present').toBeTruthy();
    const block = rawCockpitCss.slice(media!.index!);
    // The pulse + spinner selectors are inside the block, and animation is
    // forced off (assertions tolerate minified whitespace).
    expect(block).toContain('.attn-pill--pulse');
    expect(block).toContain('.org-refresh-glyph--spinning');
    expect(block).toMatch(/animation:\s*none\s*!important/);
    expect(block).toMatch(/transition:\s*none\s*!important/);
    // The cockpit-wide kill switch covers every animated descendant.
    expect(block).toMatch(/\.org-view-shell\s*\*/);
  });
});

describe('VCKP-10 — monospace numerics', () => {
  it('the gate bar renders budget/cost/confidence in var(--font-mono)', () => {
    expect(rawGateBar).toContain('var(--font-mono)');
  });
});

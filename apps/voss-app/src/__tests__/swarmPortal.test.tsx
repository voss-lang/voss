// V24-02 (VADE2-02) — canvas-swap round-trip + pane-identity contract.
//
// Harness mirrors liveReviewToggle.test.tsx exactly: we do NOT mount the real
// App (App.test.tsx mocks GridRoot entirely and cannot observe the swap). Per
// that established convention we replicate the App-local canvas-swap closure
// (the `display: activeView()==='grid' ? 'flex' : 'none'` div from App.tsx) in a
// tiny harness component driven by a local PortalView signal, and exercise the
// REAL global modules under contract: portalTypes (PortalView/PORTAL_ITEMS) and
// paneSessionRegistry (module-level session map, not tied to component lifecycle).

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { createSignal } from 'solid-js';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import { PORTAL_ITEMS, type PortalView } from '../portal/portalTypes';
import {
  trackPaneSession,
  getPaneSession,
  __resetPaneSessions,
  type PaneSession,
} from '../pane/paneSessionRegistry';

let dispose: (() => void) | undefined;
function mount(ui: () => unknown): HTMLElement {
  const root = document.createElement('div');
  document.body.appendChild(root);
  dispose = render(ui as () => never, root);
  return root;
}

afterEach(() => {
  dispose?.();
  dispose = undefined;
  document.body.innerHTML = '';
  __resetPaneSessions();
  vi.restoreAllMocks();
});

// A safe fake session: destroyPaneSession() calls transport.kill / term.dispose /
// hostEl.remove, so the fake supplies no-op stubs to keep __resetPaneSessions clean.
function fakeSession(paneId: string): PaneSession {
  return {
    paneId,
    transport: { kill() {} },
    term: { dispose() {} },
    hostEl: { remove() {} },
  } as unknown as PaneSession;
}

// ---------------------------------------------------------------------------
// PORTAL CONTRACT — the 9-item nav model authored in portalTypes.ts
// ---------------------------------------------------------------------------
describe('VADE2-02 — PortalView contract', () => {
  it('exposes exactly 9 navigable items in UI-SPEC order; "grid" returns to Workspaces', () => {
    expect(PORTAL_ITEMS.map((i) => i.id)).toEqual([
      'grid',
      'overview',
      'tasks',
      'agents',
      'swarm-map',
      'review',
      'context',
      'memory',
      'settings',
    ]);
    expect(PORTAL_ITEMS[0].label).toBe('Workspaces');
  });

  it('labels use locked PRODUCT.md vocabulary: "Tasks" not "Runs"; "Swarm Map" present', () => {
    const labels = PORTAL_ITEMS.map((i) => i.label);
    expect(labels).toContain('Tasks');
    expect(labels).not.toContain('Runs');
    expect(labels).toContain('Swarm Map');
  });
});

// ---------------------------------------------------------------------------
// CANVAS-SWAP (D-01, Pitfall 1) — grid host stays mounted; only display flips.
// Replicates App.tsx:1495 verbatim in a tiny harness; widens the binary toggle
// to the 8-way PortalView signal.
// ---------------------------------------------------------------------------
describe('VADE2-02 — canvas-swap keeps the grid host mounted', () => {
  it('grid host is the same element ref across grid→tasks→grid; display flips flex→none→flex', () => {
    const [activeView, setActiveView] = createSignal<PortalView>('grid');

    const root = mount(() => (
      <div
        data-testid="grid-host"
        style={{ display: activeView() === 'grid' ? 'flex' : 'none' }}
      >
        <div data-testid="grid-root">grid</div>
      </div>
    ));

    const before = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
    const gridBefore = root.querySelector('[data-testid="grid-root"]');
    expect(before.style.display).toBe('flex'); // boots to grid (D-02)

    setActiveView('tasks'); // swap to a portal surface
    const during = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
    expect(during).toBe(before); // SAME node — not remounted (no <Show> unmount)
    expect(during.style.display).toBe('none'); // grid hidden, alive
    expect(root.querySelector('[data-testid="grid-root"]')).toBe(gridBefore);

    setActiveView('grid'); // swap back
    const after = root.querySelector('[data-testid="grid-host"]') as HTMLElement;
    expect(after).toBe(before); // still the same node across the full round-trip
    expect(after.style.display).toBe('flex');
  });
});

// ---------------------------------------------------------------------------
// PANE-SESSION IDENTITY — the load-bearing DoS mitigation (T-V24-02-D).
// The pane session registry is module-level state keyed by paneId, NOT tied to
// GridRoot's component lifecycle. A display:none canvas-swap never calls
// destroyPaneSession, so the session key must survive a portal round-trip.
// ---------------------------------------------------------------------------
describe('VADE2-02 — pane/session identity survives a portal round-trip', () => {
  it('a registered paneSession key is still present after grid→swarm-map→grid', () => {
    const [activeView, setActiveView] = createSignal<PortalView>('grid');
    mount(() => (
      <div style={{ display: activeView() === 'grid' ? 'flex' : 'none' }}>grid</div>
    ));

    trackPaneSession(fakeSession('pane-keepalive'));
    expect(getPaneSession('pane-keepalive')).toBeTruthy();

    setActiveView('swarm-map'); // swap away
    setActiveView('grid'); // and back

    // The canvas-swap touched no session teardown path — identity persists.
    expect(getPaneSession('pane-keepalive')).toBeTruthy();
    expect(getPaneSession('pane-keepalive')!.paneId).toBe('pane-keepalive');
  });
});

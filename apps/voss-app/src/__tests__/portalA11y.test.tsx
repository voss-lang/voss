// V24-08 (VADE2-08) — cross-surface accessibility phase gate.
//
// One automated assertion of the V24 a11y contract authored across V24-02..07,
// re-checked here as the single gate before /gsd-verify-work:
//   (a) PortalRail — role="tablist" with role="tab" items carrying aria-selected
//       and aria-label, plus the V24-09 Workspaces tab and collapsible toggle;
//   (b) VossComposer — a <dialog aria-modal="true"> with an aria-label and an
//       aria-label="Safety mode" control (V24-04);
//   (c) Tasks mission-control rows are <button aria-label="Open Task: …"> (not
//       anchors), so the deep-link is keyboard-operable (V24-05);
//   (d) the reduced-motion contract holds — swarmMap.css carries no bare
//       animation declaration outside the sentinel-delimited guard (V24-07),
//       re-asserted from source (complementary to swarmA11y).
//
// jsdom does not evaluate media queries, so (d) is a source assertion read via
// fs (the same grep discipline as cockpit a11y.test.tsx + the swarm token gate).

import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
// @ts-ignore -- node builtin available in the vitest runtime; the app tsconfig is browser-lib only.
import { readFileSync } from 'node:fs';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import PortalRail from '../portal/PortalRail';
import { PORTAL_ITEMS } from '../portal/portalTypes';
import VossComposer from '../composer/VossComposer';
import TasksSurface from '../surfaces/tasks/TasksSurface';
import SettingsSurface from '../surfaces/settings/SettingsSurface';
import MemorySurface from '../surfaces/memory/MemorySurface';
import ContextSurface from '../surfaces/context/ContextSurface';
import { setRunData, setLoading, setLoadError } from '../org/orgStore';
import { __resetBridgeMaps } from '../org/model/bridge';
import { __resetAttentionQueue } from '../org/attention/attentionQueue';
import type { RunData, SessionTreeNode, Transition } from '../org/types';

// --- Tasks fixture (mirrors TasksSurface.test.tsx) ---
function node(partial: Partial<SessionTreeNode> & { id: string }): SessionTreeNode {
  return {
    root_id: 'root',
    parent_run_id: 'root',
    envelope: { limit: 100, spent: 10 },
    terminal_state: null,
    created_at: '2026-06-07T10:00:00Z',
    ended_at: null,
    transitions: [],
    scope: null,
    role: null,
    ...partial,
  };
}
function boardTo(to: string): Transition {
  return { kind: 'board.transition', from: 'Backlog', to, outcome: '', verdict_snapshot: null };
}
function makeRun(): RunData {
  return {
    run_id: 'run-1',
    session_tree: {
      root_id: 'root',
      nodes: [
        node({ id: 'root', parent_run_id: null, scope: 'root run', role: null }),
        node({ id: 'c-active', scope: 'active task', role: 'executor', transitions: [boardTo('InProgress')] }),
      ],
    },
    review: {},
    audit: null,
    run_final: null,
  };
}

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
  setRunData(null);
  setLoading(false);
  setLoadError(null);
  __resetBridgeMaps();
  __resetAttentionQueue();
  vi.restoreAllMocks();
});

describe('V24-08 a11y gate — PortalRail tablist', () => {
  it('renders a collapsible tablist with Workspaces and accessible icon-only tabs', () => {
    const el = mount(() => (
      <PortalRail activeView={PORTAL_ITEMS[0].id} expanded={false} onNavTo={() => {}} />
    ));
    const rail = el.querySelector('.portal-rail');
    expect(rail).toBeTruthy();
    expect(rail!.classList.contains('portal-rail--expanded')).toBe(false);

    const toggle = el.querySelector('button.portal-toggle');
    expect(toggle).toBeTruthy();
    expect(toggle!.getAttribute('aria-expanded')).toBe('false');
    expect(toggle!.getAttribute('aria-label')).toBe('Expand portal');

    const tablist = el.querySelector('[role="tablist"]');
    expect(tablist).toBeTruthy();

    const tabs = Array.from(el.querySelectorAll('[role="tab"]'));
    expect(tabs.length).toBe(PORTAL_ITEMS.length);
    expect(tabs).toHaveLength(9);
    expect(el.querySelector('[role="tab"][aria-label="Workspaces"]')).toBeTruthy();
    for (const tab of tabs) {
      expect(tab.getAttribute('aria-selected')).toMatch(/^(true|false)$/);
      expect(tab.getAttribute('aria-label')?.trim()).not.toBe('');
    }
    // Exactly the active view's tab reports aria-selected="true".
    const selected = tabs.filter((t) => t.getAttribute('aria-selected') === 'true');
    expect(selected).toHaveLength(1);
    expect(selected[0].getAttribute('aria-label')).toBe(PORTAL_ITEMS[0].label);
  });

  it('announces the expanded toggle state', () => {
    const el = mount(() => (
      <PortalRail activeView={PORTAL_ITEMS[0].id} expanded={true} onNavTo={() => {}} />
    ));
    const toggle = el.querySelector('button.portal-toggle');
    expect(toggle).toBeTruthy();
    expect(toggle!.getAttribute('aria-expanded')).toBe('true');
    expect(toggle!.getAttribute('aria-label')).toBe('Collapse portal');
  });
});

describe('V24-10 a11y gate — Context/Settings/Memory surfaces wired (no stale placeholder)', () => {
  it('Settings renders a real tabpanel — not the stale V24 placeholder', () => {
    const el = mount(() => <SettingsSurface />);
    expect(el.querySelector('[role="tabpanel"][aria-label="Settings"]')).toBeTruthy();
    expect(el.textContent).not.toContain('Coming in a later V24 plan');
  });

  it('Memory renders an honest tabpanel — not the stale V24 placeholder', () => {
    const el = mount(() => <MemorySurface />);
    expect(el.querySelector('[role="tabpanel"][aria-label="Memory"]')).toBeTruthy();
    expect(el.textContent).not.toContain('Coming in a later V24 plan');
    // Honest-signal: points to the real entry point, no fabricated rows.
    expect(el.textContent).toContain('/memory');
  });

  it('Context renders a real tabpanel — not the stale V24 placeholder', () => {
    const el = mount(() => <ContextSurface context={null} isAgentPane={false} />);
    expect(el.querySelector('[role="tabpanel"][aria-label="Context"]')).toBeTruthy();
    expect(el.textContent).not.toContain('Coming in a later V24 plan');
  });
});

describe('V24-08 a11y gate — VossComposer dialog', () => {
  it('renders a <dialog aria-modal="true"> with an aria-label and a Safety mode control', () => {
    const el = mount(() => <VossComposer open={true} onClose={() => {}} />);
    const dialog = el.querySelector('dialog');
    expect(dialog).toBeTruthy();
    expect(dialog!.getAttribute('aria-modal')).toBe('true');
    expect(dialog!.getAttribute('aria-label')).toBeTruthy();

    const safety = el.querySelector('[aria-label="Safety mode"]');
    expect(safety).toBeTruthy();
    expect(safety!.tagName.toLowerCase()).toBe('select');
  });
});

describe('V24-08 a11y gate — Tasks rows are keyboard-operable buttons', () => {
  it('renders mission-control rows as <button aria-label="Open Task: …"> (not anchors)', () => {
    setRunData(makeRun());
    const el = mount(() => <TasksSurface />);
    const row = el.querySelector('button.surface-row');
    expect(row).toBeTruthy();
    expect(row!.tagName.toLowerCase()).toBe('button');
    expect(row!.getAttribute('aria-label')).toMatch(/^Open Task: /);
    // Deep-link must NOT be an anchor (no href navigation in a webview app).
    expect(el.querySelector('a.surface-row')).toBeNull();
  });
});

describe('V24-08 a11y gate — reduced-motion CSS contract (source assertion)', () => {
  it('swarmMap.css has no bare animation declaration outside the reduced-motion guard', () => {
    // Path is relative to the vitest root (apps/voss-app — vitest.config.ts).
    const css: string = readFileSync('src/surfaces/swarm-map/swarmMap.css', 'utf8');

    const guardStart = css.indexOf('@media (not (prefers-reduced-motion: reduce))');
    const endMarker = '} /* end-reduced-motion-guard */';
    const endIdx = css.indexOf(endMarker);
    expect(guardStart, 'reduced-motion guard present').toBeGreaterThanOrEqual(0);
    expect(endIdx, 'guard sentinel present').toBeGreaterThan(guardStart);

    // Strip the entire guard block, then assert nothing animates outside it.
    const outside = css.slice(0, guardStart) + css.slice(endIdx + endMarker.length);
    // `animation-play-state` (the pause hook) intentionally survives — it is not a
    // bare `animation:` declaration, so the regex below leaves it alone.
    expect(outside).not.toMatch(/animation:/);
  });
});

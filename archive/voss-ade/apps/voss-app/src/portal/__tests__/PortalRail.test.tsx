import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

import { PORTAL_ITEMS } from '../portalTypes';
import PortalRail from '../PortalRail';

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
  vi.restoreAllMocks();
});

function portalToggle(root: HTMLElement): HTMLButtonElement {
  const toggle = Array.from(root.querySelectorAll('button')).find((button) =>
    /(Collapse|Expand) (the )?portal/i.test(button.getAttribute('aria-label') ?? ''),
  );
  expect(toggle).toBeTruthy();
  return toggle as HTMLButtonElement;
}

describe('PortalRail data contract', () => {
  it('starts with Workspaces as the grid canvas-swap default', () => {
    expect(PORTAL_ITEMS[0]).toEqual({ id: 'grid', label: 'Workspaces', glyph: '▦' });
  });

  it('exposes exactly 9 portal items with unique ids and non-empty labels', () => {
    expect(PORTAL_ITEMS.length).toBe(9);

    const ids = PORTAL_ITEMS.map((item) => item.id);
    expect(new Set(ids).size).toBe(PORTAL_ITEMS.length);

    for (const item of PORTAL_ITEMS) {
      expect(item.label.trim().length).toBeGreaterThan(0);
    }
  });
});

describe('PortalRail presentation contract', () => {
  it('renders a controlled expand/collapse toggle', () => {
    const onToggleExpanded = vi.fn();
    const collapsed = mount(() => (
      <PortalRail
        activeView="overview"
        expanded={false}
        onToggleExpanded={onToggleExpanded}
        onNavTo={() => {}}
      />
    ));

    const collapsedToggle = portalToggle(collapsed);
    expect(collapsedToggle.getAttribute('aria-label')).toBe('Expand portal');
    expect(collapsedToggle.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(collapsedToggle);
    expect(onToggleExpanded).toHaveBeenCalledTimes(1);
  });

  it('applies the expanded rail class only when expanded', () => {
    const collapsed = mount(() => (
      <PortalRail activeView="overview" expanded={false} onNavTo={() => {}} />
    ));
    expect(collapsed.querySelector('.portal-rail')?.classList.contains('portal-rail--expanded')).toBe(
      false,
    );
    dispose?.();
    dispose = undefined;
    document.body.innerHTML = '';

    const expanded = mount(() => (
      <PortalRail activeView="overview" expanded={true} onNavTo={() => {}} />
    ));
    const rail = expanded.querySelector('.portal-rail');
    expect(rail?.classList.contains('portal-rail--expanded')).toBe(true);
    expect(portalToggle(expanded).getAttribute('aria-label')).toBe('Collapse portal');
    expect(portalToggle(expanded).getAttribute('aria-expanded')).toBe('true');
  });

  it('renders every portal item with an svg icon and label text in both states', () => {
    for (const expanded of [false, true]) {
      const el = mount(() => (
        <PortalRail activeView="overview" expanded={expanded} onNavTo={() => {}} />
      ));
      const items = Array.from(el.querySelectorAll('.portal-item'));
      expect(items).toHaveLength(PORTAL_ITEMS.length);

      items.forEach((itemEl, index) => {
        const item = PORTAL_ITEMS[index];
        expect(itemEl.querySelector('svg')).toBeTruthy();
        expect(itemEl.textContent?.trim()).not.toBe(item.glyph);
        const label = itemEl.querySelector('.portal-item__label');
        expect(label).toBeTruthy();
        expect(label?.textContent).toBe(item.label);
      });

      dispose?.();
      dispose = undefined;
      document.body.innerHTML = '';
    }
  });

  it("routes Workspaces clicks back to the grid view", () => {
    const onNavTo = vi.fn();
    const el = mount(() => <PortalRail activeView="overview" onNavTo={onNavTo} />);
    const workspaces = el.querySelector('[role="tab"][aria-label="Workspaces"]');
    expect(workspaces).toBeTruthy();

    fireEvent.click(workspaces!);
    expect(onNavTo).toHaveBeenCalledWith('grid');
  });

  it('keeps tablist semantics for all 9 portal items', () => {
    const el = mount(() => <PortalRail activeView="tasks" onNavTo={() => {}} />);
    expect(el.querySelector('[role="tablist"]')).toBeTruthy();

    const tabs = Array.from(el.querySelectorAll('[role="tab"]'));
    expect(tabs).toHaveLength(9);
    for (const tab of tabs) {
      expect(tab.getAttribute('aria-selected')).toMatch(/^(true|false)$/);
      expect(tab.getAttribute('aria-label')?.trim()).not.toBe('');
    }
    expect(tabs.filter((tab) => tab.getAttribute('aria-selected') === 'true')).toHaveLength(1);
  });
});

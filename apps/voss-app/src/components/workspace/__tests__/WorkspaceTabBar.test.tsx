import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import { fireEvent } from '@testing-library/dom';

import WorkspaceTabBar, {
  COPY_CLOSE_RUNNING_CONFIRM,
  COPY_CLOSE_WORKSPACE,
  COPY_COLOR,
  COPY_LAST_WORKSPACE_BLOCKED,
  COPY_NEW_WORKSPACE,
  COPY_RENAME_WORKSPACE,
  WORKSPACE_ACCENT_COLORS,
  WORKSPACE_BAR_HEIGHT_PX,
  WORKSPACE_TAB_HEIGHT_PX,
} from '../WorkspaceTabBar';
import type { WorkspaceRecord } from '../../../workspaces/workspaceStore';

/**
 * A8-03 Task 1 — WorkspaceTabBar + context menu (TDD).
 *
 * Contract: A8-UI-SPEC Workspace Tab Bar + Copywriting sections.
 */

const WS1: WorkspaceRecord = {
  id: 'ws-1',
  name: 'Alpha',
  accentColor: 'blue',
  order: 0,
};
const WS2: WorkspaceRecord = {
  id: 'ws-2',
  name: 'Beta',
  accentColor: 'green',
  order: 1,
};

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

function defaultProps(overrides: Partial<Parameters<typeof WorkspaceTabBar>[0]> = {}) {
  return {
    workspaces: [WS1, WS2] as readonly WorkspaceRecord[],
    activeId: 'ws-1',
    onActivate: vi.fn(),
    onNew: vi.fn(),
    onRename: vi.fn(),
    onColor: vi.fn(),
    onClose: vi.fn(),
    onReorder: vi.fn(),
    closeGuardFor: (id: string) =>
      id === 'ws-1' && overrides.workspaces?.length === 1
        ? { canClose: false, isLastWorkspace: true }
        : { canClose: true, isLastWorkspace: false },
    ...overrides,
  };
}

function tab(root: HTMLElement, id: string): HTMLElement {
  const el = root.querySelector(`[data-workspace-tab="${id}"]`);
  if (!el) throw new Error(`tab ${id} not found`);
  return el as HTMLElement;
}

function openContextMenu(root: HTMLElement, id: string) {
  fireEvent.contextMenu(tab(root, id));
}

describe('WorkspaceTabBar — active/inactive tab markers', () => {
  it('marks active tab with data-tab-state=active and inactive with inactive', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    expect(tab(el, 'ws-1').getAttribute('data-tab-state')).toBe('active');
    expect(tab(el, 'ws-2').getAttribute('data-tab-state')).toBe('inactive');
  });
});

describe('WorkspaceTabBar — fixed dimensions contract', () => {
  it('tab bar is 28px and tabs are 24px via CSS contract classes', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    const bar = el.querySelector('[data-workspace-tabbar]') as HTMLElement;
    expect(bar).not.toBeNull();
    expect(bar.dataset.barHeight).toBe(String(WORKSPACE_BAR_HEIGHT_PX));
    expect(tab(el, 'ws-1').dataset.tabHeight).toBe(String(WORKSPACE_TAB_HEIGHT_PX));
  });

  it('tab height does not change on hover (close reveal uses opacity, not layout)', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    const t = tab(el, 'ws-1');
    expect(t.dataset.tabHeight).toBe(String(WORKSPACE_TAB_HEIGHT_PX));
    const before = t.offsetHeight;
    fireEvent.mouseEnter(t);
    expect(t.offsetHeight).toBe(before);
    expect(t.querySelector('[data-workspace-tab-close]')).not.toBeNull();
  });
});

describe('WorkspaceTabBar — add workspace button', () => {
  it('renders + with aria-label New workspace', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    const btn = el.querySelector('[aria-label="New workspace"]') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    expect(btn.textContent?.trim()).toBe('+');
  });
});

describe('WorkspaceTabBar — context menu rename', () => {
  it('shows Rename workspace in context menu', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    openContextMenu(el, 'ws-1');
    const menu = el.querySelector('[data-workspace-context-menu]');
    expect(menu).not.toBeNull();
    expect(menu!.textContent).toContain(COPY_RENAME_WORKSPACE);
  });

  it('Rename workspace starts inline rename on the tab', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    openContextMenu(el, 'ws-1');
    fireEvent.click(
      el.querySelector(`[data-menu-action="rename"]`) as HTMLButtonElement,
    );
    const input = tab(el, 'ws-1').querySelector('[data-workspace-rename-input]');
    expect(input).not.toBeNull();
  });
});

describe('WorkspaceTabBar — fixed eight-color palette', () => {
  it('renders exactly eight workspace color dots and no hex/custom input', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    openContextMenu(el, 'ws-1');
    fireEvent.click(el.querySelector(`[data-menu-action="color"]`) as HTMLButtonElement);
    const dots = el.querySelectorAll('[data-workspace-color]');
    expect(dots).toHaveLength(WORKSPACE_ACCENT_COLORS.length);
    expect(Array.from(dots).map((d) => d.getAttribute('data-workspace-color'))).toEqual([
      ...WORKSPACE_ACCENT_COLORS,
    ]);
    expect(el.querySelector('input[type="color"]')).toBeNull();
    expect(el.querySelector('[data-workspace-hex-input]')).toBeNull();
    expect(el.textContent).toContain(COPY_COLOR);
  });
});

describe('WorkspaceTabBar — last workspace close blocked', () => {
  it('blocks close with Last workspace stays open and calls onCloseBlocked', () => {
    const onCloseBlocked = vi.fn();
    const onClose = vi.fn();
    const el = mount(() => (
      <WorkspaceTabBar
        {...defaultProps({
          workspaces: [WS1],
          activeId: 'ws-1',
          onClose,
          onCloseBlocked,
          closeGuardFor: () => ({ canClose: false, isLastWorkspace: true }),
        })}
      />
    ));
    openContextMenu(el, 'ws-1');
    fireEvent.click(
      el.querySelector(`[data-menu-action="close"]`) as HTMLButtonElement,
    );
    expect(el.textContent).toContain(COPY_LAST_WORKSPACE_BLOCKED);
    expect(onCloseBlocked).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });

  it('close tab button on last workspace shows blocked copy', () => {
    const onCloseBlocked = vi.fn();
    const el = mount(() => (
      <WorkspaceTabBar
        {...defaultProps({
          workspaces: [WS1],
          activeId: 'ws-1',
          onCloseBlocked,
          closeGuardFor: () => ({ canClose: false, isLastWorkspace: true }),
        })}
      />
    ));
    fireEvent.click(
      tab(el, 'ws-1').querySelector('[data-workspace-tab-close]') as HTMLButtonElement,
    );
    expect(el.textContent).toContain(COPY_LAST_WORKSPACE_BLOCKED);
    expect(onCloseBlocked).toHaveBeenCalled();
  });
});

describe('WorkspaceTabBar — running process close confirmation', () => {
  it('shows Processes are running. Close workspace? before closing', () => {
    const onCloseConfirm = vi.fn();
    const onClose = vi.fn();
    const el = mount(() => (
      <WorkspaceTabBar
        {...defaultProps({
          hasRunningProcesses: () => true,
          onCloseConfirm,
          onClose,
        })}
      />
    ));
    openContextMenu(el, 'ws-2');
    fireEvent.click(
      el.querySelector(`[data-menu-action="close"]`) as HTMLButtonElement,
    );
    expect(el.textContent).toContain(COPY_CLOSE_RUNNING_CONFIRM);
    fireEvent.click(
      el.querySelector('[data-workspace-close-confirm]') as HTMLButtonElement,
    );
    expect(onCloseConfirm).toHaveBeenCalledWith('ws-2');
    expect(onClose).not.toHaveBeenCalled();
  });

  it('Close workspace menu row uses UI-SPEC copy', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    openContextMenu(el, 'ws-1');
    expect(el.textContent).toContain(COPY_CLOSE_WORKSPACE);
  });
});

describe('WorkspaceTabBar — popover dismiss', () => {
  it('Escape dismisses context menu', () => {
    const el = mount(() => <WorkspaceTabBar {...defaultProps()} />);
    openContextMenu(el, 'ws-1');
    expect(el.querySelector('[data-workspace-context-menu]')).not.toBeNull();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(el.querySelector('[data-workspace-context-menu]')).toBeNull();
  });
});

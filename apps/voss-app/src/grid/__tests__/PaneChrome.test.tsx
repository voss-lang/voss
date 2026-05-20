import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render } from 'solid-js/web';
import { createStore } from 'solid-js/store';
import { fireEvent } from '@testing-library/dom';

const h = vi.hoisted(() => ({ invoke: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@tauri-apps/api/core', () => ({ invoke: h.invoke }));
vi.mock('../../pane/PaneComponent', () => ({
  default: () => {
    const d = document.createElement('div');
    d.setAttribute('data-testid', 'pane');
    return d;
  },
}));
const ops = vi.hoisted(() => ({
  forkFocused: vi.fn(),
  splitFocused: vi.fn(),
  closeFocused: vi.fn(),
  equalizeAll: vi.fn(),
}));
vi.mock('../operations', () => ops);

import { type GridStore, makePane, makeSplit, recomputeIndices } from '../tree';
import PaneHeader from '../PaneHeader';
import DotMenu from '../DotMenu';
import CloseConfirmBanner, { requestCloseGated } from '../CloseConfirmBanner';
import SplitNodeView from '../SplitNode';

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

describe('PaneHeader — 22px Variant B header (GRD-06, GRD-07)', () => {
  it('renders the locked segment order, index digit, aria-labels', () => {
    const toggle = vi.fn();
    const el = mount(() => (
      <PaneHeader
        index={3}
        focused={true}
        cwd="voss-app"
        shell="zsh"
        process="vim"
        onToggleMenu={toggle}
      />
    ));
    const hdr = el.firstElementChild as HTMLElement;
    expect(hdr.style.height).toBe('22px');
    expect(hdr.className).toContain('bg-bg-2'); // focused bg-lift
    expect(el.querySelector('[data-pane-index="3"]')?.textContent).toBe('3');
    expect(el.querySelector('[aria-label="Pane menu"]')).toBeTruthy();
    expect(el.querySelector('[aria-label="Shell running"]')).toBeTruthy();
    expect(el.textContent).toContain('voss-app');
    expect(el.textContent).toContain('zsh');
    expect(el.textContent).toContain('vim');
    fireEvent.click(el.querySelector('[aria-label="Pane menu"]')!);
    expect(toggle).toHaveBeenCalled();
  });

  it('unfocused → bg-bg-1; empty process is hidden (not a dash)', () => {
    const el = mount(() => (
      <PaneHeader
        index={1}
        focused={false}
        cwd="x"
        shell="bash"
        process=""
        onToggleMenu={() => {}}
      />
    ));
    expect((el.firstElementChild as HTMLElement).className).toContain('bg-bg-1');
    expect(el.textContent).not.toContain('vim');
    expect(el.textContent).not.toContain('-'); // no dash placeholder
  });
});

describe('DotMenu — exactly 5 locked items (GRD-06)', () => {
  beforeEach(() => Object.values(ops).forEach((f) => f.mockClear()));

  it('renders Fork/Split right/Split below/separator/Close pane — no 6th', () => {
    const [store, setStore] = createStore<GridStore>({
      root: makePane(),
      focusedId: 'x',
    });
    const close = vi.fn();
    const el = mount(() => (
      <DotMenu
        store={store}
        setStore={setStore}
        onDismiss={() => {}}
        onRequestClose={close}
      />
    ));
    const labels = Array.from(el.querySelectorAll('[role="menuitem"] span')).map(
      (s) => s.textContent,
    );
    expect(labels).toContain('Fork pane');
    expect(labels).toContain('Split right');
    expect(labels).toContain('Split below');
    expect(labels).toContain('Close pane');
    expect(el.querySelectorAll('[role="menuitem"]')).toHaveLength(4); // 4 + sep
    fireEvent.click(
      Array.from(el.querySelectorAll('[role="menuitem"]')).find((b) =>
        b.textContent?.includes('Fork pane'),
      )!,
    );
    expect(ops.forkFocused).toHaveBeenCalled();
    fireEvent.click(
      Array.from(el.querySelectorAll('[role="menuitem"]')).find((b) =>
        b.textContent?.includes('Split below'),
      )!,
    );
    expect(ops.splitFocused).toHaveBeenCalledWith(expect.anything(), 'V');
    fireEvent.click(
      Array.from(el.querySelectorAll('[role="menuitem"]')).find((b) =>
        b.textContent?.includes('Close pane'),
      )!,
    );
    expect(close).toHaveBeenCalled();
  });
});

describe('CloseConfirmBanner + requestCloseGated (GRD-02, A2 D-07)', () => {
  beforeEach(() => Object.values(ops).forEach((f) => f.mockClear()));

  it('character-exact copy; Close anyway/Enter → closeFocused, Keep/Esc → keep', () => {
    const [store, setStore] = createStore<GridStore>({
      root: makePane(),
      focusedId: 'x',
    });
    const keep = vi.fn();
    const el = mount(() => (
      <CloseConfirmBanner
        store={store}
        setStore={setStore}
        process="vim"
        onKeepOpen={keep}
      />
    ));
    expect(el.textContent).toContain('"vim" is running. Close anyway?');
    expect(el.textContent).toContain('Keep open');
    expect(el.textContent).toContain('Close anyway');
    fireEvent.click(
      Array.from(el.querySelectorAll('button')).find((b) =>
        b.textContent?.includes('Close anyway'),
      )!,
    );
    expect(ops.closeFocused).toHaveBeenCalled();
    ops.closeFocused.mockClear();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(ops.closeFocused).not.toHaveBeenCalled();
    expect(keep).toHaveBeenCalled();
  });

  it('requestCloseGated: idle → close now; fg running → banner, no close', () => {
    const store = { root: makePane(), focusedId: 'x' } as unknown as GridStore;
    const banner = vi.fn();
    requestCloseGated(store, 'x', () => false, banner);
    expect(ops.closeFocused).toHaveBeenCalledTimes(1);
    expect(banner).not.toHaveBeenCalled();
    ops.closeFocused.mockClear();
    requestCloseGated(store, 'x', () => true, banner);
    expect(banner).toHaveBeenCalledTimes(1);
    expect(ops.closeFocused).not.toHaveBeenCalled();
  });
});

describe('PaneHeader — tmux prefix indicator (A7-04)', () => {
  it('renders [Cmd+B...] when prefixActive and prefixReserved are true', () => {
    const el = mount(() => (
      <PaneHeader
        index={1}
        focused={true}
        cwd="/repo"
        shell="zsh"
        prefixActive={true}
        prefixReserved={true}
        onToggleMenu={() => {}}
      />
    ));
    const indicator = el.querySelector('[data-testid="prefix-indicator"]')!;
    expect(indicator.textContent).toBe('[Cmd+B...]');
  });

  it('does not render indicator text when prefixActive is false', () => {
    const el = mount(() => (
      <PaneHeader
        index={1}
        focused={true}
        cwd="/repo"
        shell="zsh"
        prefixActive={false}
        prefixReserved={true}
        onToggleMenu={() => {}}
      />
    ));
    const indicator = el.querySelector('[data-testid="prefix-indicator"]')!;
    expect(indicator.textContent).toBe('');
  });

  it('does not render indicator element when prefixReserved is false', () => {
    const el = mount(() => (
      <PaneHeader
        index={1}
        focused={true}
        cwd="/repo"
        shell="zsh"
        prefixActive={true}
        prefixReserved={false}
        onToggleMenu={() => {}}
      />
    ));
    expect(el.querySelector('[data-testid="prefix-indicator"]')).toBeNull();
  });

  it('reserves 72px width for indicator', () => {
    const el = mount(() => (
      <PaneHeader
        index={1}
        focused={true}
        cwd="/repo"
        shell="zsh"
        prefixActive={false}
        prefixReserved={true}
        onToggleMenu={() => {}}
      />
    ));
    const indicator = el.querySelector('[data-testid="prefix-indicator"]') as HTMLElement;
    expect(indicator.style.width).toBe('72px');
  });
});

describe('SplitNode seam — chrome mounted per leaf (GRD-06)', () => {
  beforeEach(() => Object.values(ops).forEach((f) => f.mockClear()));

  it('2-pane tree: per-pane PaneHeader index; ⋯→Fork calls forkFocused', () => {
    const a = makePane();
    const b = makePane();
    const root = makeSplit('H', a, b);
    recomputeIndices(root);
    const [store, setStore] = createStore<GridStore>({ root, focusedId: a.id });
    const el = mount(() => (
      <SplitNodeView
        node={store.root}
        store={store}
        setStore={setStore}
        path=""
        dims={() => ({ winW: 1024, winH: 768, cw: 8, ch: 20 })}
        closeUI={{ isFg: () => false, fgName: () => 'proc' }}
      />
    ));
    const idx = Array.from(el.querySelectorAll('[data-pane-index]')).map(
      (n) => n.textContent,
    );
    expect(idx).toEqual(['1', '2']);
    fireEvent.click(el.querySelectorAll('[aria-label="Pane menu"]')[1]);
    fireEvent.click(
      Array.from(el.querySelectorAll('[role="menuitem"]')).find((m) =>
        m.textContent?.includes('Fork pane'),
      )!,
    );
    expect(ops.forkFocused).toHaveBeenCalled();
  });

  it('⋯ Close pane: idle → closeFocused; fg → confirm banner', () => {
    const p = makePane();
    const [store, setStore] = createStore<GridStore>({
      root: p,
      focusedId: p.id,
    });
    let running = false;
    const el = mount(() => (
      <SplitNodeView
        node={store.root}
        store={store}
        setStore={setStore}
        path=""
        dims={() => ({ winW: 1024, winH: 768, cw: 8, ch: 20 })}
        closeUI={{ isFg: () => running, fgName: () => 'npm' }}
      />
    ));
    const openClose = () => {
      fireEvent.click(el.querySelector('[aria-label="Pane menu"]')!);
      fireEvent.click(
        Array.from(el.querySelectorAll('[role="menuitem"]')).find((m) =>
          m.textContent?.includes('Close pane'),
        )!,
      );
    };
    openClose();
    expect(ops.closeFocused).toHaveBeenCalledTimes(1); // idle path
    running = true;
    openClose();
    expect(el.textContent).toContain('"npm" is running. Close anyway?');
    expect(ops.closeFocused).toHaveBeenCalledTimes(1); // banner, not closed
  });
});

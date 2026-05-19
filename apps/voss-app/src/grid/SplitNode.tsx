import { Switch, Match, Show, createSignal } from 'solid-js';
import { produce, type SetStoreFunction, type Store } from 'solid-js/store';
import type { GridStore, TreeNode, PaneLeaf, SplitNode } from './tree';
import { focusByClick } from './focus';
import PaneComponent from '../pane/PaneComponent';
import DragHandle, { type Dims } from './DragHandle';
import PaneHeader from './PaneHeader';
import DotMenu from './DotMenu';
import CloseConfirmBanner, { requestCloseGated } from './CloseConfirmBanner';

/**
 * A3-05 close gate injection (A2 D-07 black box). A2's `PaneComponent` does
 * not surface its foreground signal yet, so `isFg` defaults to "idle" ⇒ ⌘W
 * and "Close pane" close immediately (unchanged from A3-04). A3-06/A8 wires
 * the real per-pane A2 fg signal here.
 */
export interface CloseUI {
  isFg: (paneId: string) => boolean;
  fgName: (paneId: string) => string;
}

/**
 * Recursive binary-split renderer (GRD-01). `H` = flex row (side-by-side),
 * `V` = flex column (stacked); each leaf wraps the A2 `PaneComponent` (a
 * black box — A2 owns its xterm sizing via its own ResizeObserver, so sizing
 * THIS wrapper drives the fit; A2's PaneProps has no focused/size prop so the
 * focus visual lives on the wrapper per A3-UI-SPEC).
 *
 * Focus (GRD-07): the focused leaf wrapper carries exactly the inset focus
 * shadow `shadow-[inset_0_0_0_1px_var(--focus)]` INSIDE the 1px split border
 * (A3-UI-SPEC forbids any boundary stroke/colour change). Instant repaint,
 * no CSS animation (Variant B perf budget).
 */
export default function SplitNodeView(props: {
  node: TreeNode;
  store: Store<GridStore>;
  setStore: SetStoreFunction<GridStore>;
  path: string;
  dims: () => Dims;
  closeUI?: CloseUI;
}) {
  const asSplit = () => props.node as SplitNode;
  const asLeaf = () => props.node as PaneLeaf;

  // Per-leaf chrome state (inert on split nodes).
  const [menuOpen, setMenuOpen] = createSignal(false);
  const [banner, setBanner] = createSignal<string | null>(null);
  const isFg = (id: string) => props.closeUI?.isFg(id) ?? false;
  const fgName = (id: string) => props.closeUI?.fgName(id) ?? 'process';

  // Single close entry (T-A3-13): idle ⇒ closeFocused now; fg ⇒ banner.
  const requestClose = () =>
    props.setStore(
      produce((s) =>
        requestCloseGated(s, asLeaf().id, () => isFg(asLeaf().id), () =>
          setBanner(fgName(asLeaf().id)),
        ),
      ),
    );

  const isFocused = () =>
    props.node.kind === 'pane' && asLeaf().id === props.store.focusedId;

  const focus = () =>
    props.setStore(produce((s) => focusByClick(s, asLeaf().id)));

  // Drag-handle hover brightens the divider (instant, no transition).
  const [hot, setHot] = createSignal(false);
  let wrap: HTMLDivElement | undefined;
  const dividerColor = () =>
    hot() ? 'var(--border-bright)' : 'var(--border)';

  return (
    <Switch>
      <Match when={props.node.kind === 'pane'}>
        <div
          data-pane-id={asLeaf().id}
          classList={{
            'relative w-full h-full bg-bg-0': true,
            'shadow-[inset_0_0_0_1px_var(--focus)]': isFocused(),
          }}
          onClick={focus}
        >
          {/* A3-05 mount: PaneHeader index + ⋯ menu + CloseConfirmBanner overlay here */}
          <PaneComponent
            cwd={asLeaf().cwd}
            shell={asLeaf().shell}
            index={asLeaf().index}
          />
        </div>
      </Match>

      <Match when={props.node.kind === 'split'}>
        <div
          ref={wrap}
          style={{
            position: 'relative',
            display: 'flex',
            'flex-direction':
              asSplit().orientation === 'H' ? 'row' : 'column',
            width: '100%',
            height: '100%',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'relative',
              ...(asSplit().orientation === 'H'
                ? {
                    width: `${asSplit().ratio * 100}%`,
                    height: '100%',
                    'border-right': `1px solid ${dividerColor()}`,
                  }
                : {
                    width: '100%',
                    height: `${asSplit().ratio * 100}%`,
                    'border-bottom': `1px solid ${dividerColor()}`,
                  }),
            }}
          >
            <SplitNodeView
              node={asSplit().left}
              store={props.store}
              setStore={props.setStore}
              path={`${props.path}L`}
              dims={props.dims}
            />
            <DragHandle
              store={props.store}
              setStore={props.setStore}
              path={props.path}
              orientation={asSplit().orientation}
              spanRect={() => wrap?.getBoundingClientRect()}
              dims={props.dims}
              onHover={setHot}
            />
          </div>
          <div
            style={
              asSplit().orientation === 'H'
                ? { width: `${(1 - asSplit().ratio) * 100}%`, height: '100%' }
                : { width: '100%', height: `${(1 - asSplit().ratio) * 100}%` }
            }
          >
            <SplitNodeView
              node={asSplit().right}
              store={props.store}
              setStore={props.setStore}
              path={`${props.path}R`}
              dims={props.dims}
            />
          </div>
        </div>
      </Match>
    </Switch>
  );
}

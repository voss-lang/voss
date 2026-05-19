import { Switch, Match, createSignal } from 'solid-js';
import { produce, type SetStoreFunction, type Store } from 'solid-js/store';
import type { GridStore, TreeNode, PaneLeaf, SplitNode } from './tree';
import { focusByClick } from './focus';
import PaneComponent from '../pane/PaneComponent';
import DragHandle, { type Dims } from './DragHandle';

/**
 * Recursive binary-split renderer (GRD-01). `H` = flex row (side-by-side),
 * `V` = flex column (stacked); each leaf wraps the A2 `PaneComponent` (a
 * black box — A2 owns its xterm sizing via its own ResizeObserver, so sizing
 * THIS wrapper drives the fit; A2's PaneProps has no focused/size prop so the
 * focus visual lives on the wrapper per A3-UI-SPEC).
 *
 * Focus (GRD-07): the focused leaf wrapper carries exactly the inset focus
 * shadow `shadow-[inset_0_0_0_1px_var(--focus)]` INSIDE the 1px split border
 * — never an outline/border colour change (A3-UI-SPEC "No border ring");
 * instant repaint, no CSS transition (Variant B perf budget).
 */
export default function SplitNodeView(props: {
  node: TreeNode;
  store: Store<GridStore>;
  setStore: SetStoreFunction<GridStore>;
  path: string;
  dims: () => Dims;
}) {
  const asSplit = () => props.node as SplitNode;
  const asLeaf = () => props.node as PaneLeaf;

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

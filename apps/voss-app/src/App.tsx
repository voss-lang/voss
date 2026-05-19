import { createSignal } from 'solid-js';
import Titlebar from './components/titlebar/Titlebar';
import GridRoot from './grid/GridRoot';
import type {
  ActiveLayout,
  LayoutPreset,
} from './grid/layoutPresets';

/**
 * App composition root.
 *
 * A4-02 lifts `activeLayout` ownership to this component so the titlebar
 * preset switcher (`PresetSwitcher`) and the grid keyboard handler
 * (`GridRoot` → `dispatchKey`) share a single source of truth. The grid
 * owns the pane tree and reports back the new layout through
 * `onLayoutChange`; titlebar clicks bubble back into the grid via
 * `onLayoutSelect` → `<GridRoot>` controller hook (here: a callback ref
 * the grid populates on mount).
 *
 * Default `activeLayout` is `'custom'` — the app boots with a single
 * default pane (A3) which is, by definition, off-cycle until the user
 * applies a preset.
 */
type GridController = { applyPreset: (preset: LayoutPreset) => void };

export default function App() {
  const [activeLayout, setActiveLayout] =
    createSignal<ActiveLayout>('custom');
  let gridController: GridController | undefined;

  const onLayoutSelect = (preset: LayoutPreset) => {
    gridController?.applyPreset(preset);
  };

  return (
    <div
      style={{
        display: 'flex',
        'flex-direction': 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
      }}
    >
      <Titlebar
        activeLayout={activeLayout()}
        onLayoutSelect={onLayoutSelect}
      />
      {/* A3: the binary-split grid fills the body (leaves are A2 panes). */}
      <div style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}>
        <GridRoot
          activeLayout={activeLayout}
          onLayoutChange={(next) => setActiveLayout(next)}
          controllerRef={(c) => {
            gridController = c;
          }}
        />
      </div>
    </div>
  );
}

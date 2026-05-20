import { createSignal } from 'solid-js';
import Titlebar from './components/titlebar/Titlebar';
import GridRoot, { type GridController } from './grid/GridRoot';
import type {
  ActiveLayout,
  LayoutPreset,
} from './grid/layoutPresets';
import { serializeLayout } from './grid/layoutCommands';
import {
  loadDefaultLayout,
  loadLayout,
  saveLayout,
} from './grid/layoutStorage';

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
 *
 * A4-04 wires the layout persistence seam. `saveCurrentLayout`,
 * `loadLayoutByName`, and `applyDefaultLayout` are callable closures
 * that bridge the Rust Tauri commands (via `layoutStorage`) to the live
 * grid (via the `GridController`). They are exposed for A7's command
 * palette to invoke; A4 itself does not ship UI for them.
 */

export default function App() {
  const [activeLayout, setActiveLayout] =
    createSignal<ActiveLayout>('custom');
  let gridController: GridController | undefined;

  const onLayoutSelect = (preset: LayoutPreset) => {
    gridController?.applyPreset(preset);
  };

  // --- A7 callable seam (LAY-06/07) ----------------------------------------
  // A5 owns the workspace folder picker; until it lands, callers must
  // supply `workspacePath` explicitly. These closures intentionally avoid
  // a global `window.__voss` registration — A7's palette will import them
  // directly from this module once it exists.

  const saveCurrentLayout = async (
    workspacePath: string,
    name: string,
  ): Promise<void> => {
    if (!gridController) return;
    const snap = gridController.snapshot();
    const file = serializeLayout(snap.root, snap.focusedId, activeLayout());
    await saveLayout(workspacePath, name, file);
  };

  const loadLayoutByName = async (
    workspacePath: string,
    name: string,
  ): Promise<void> => {
    if (!gridController) return;
    const file = await loadLayout(workspacePath, name);
    gridController.applyLoadedLayout(file);
  };

  const applyDefaultLayout = async (
    workspacePath: string,
  ): Promise<boolean> => {
    if (!gridController) return false;
    const file = await loadDefaultLayout(workspacePath);
    if (!file) return false;
    gridController.applyLoadedLayout(file);
    return true;
  };

  // Suppress unused warnings while keeping the symbols live for A7 wiring.
  void saveCurrentLayout;
  void loadLayoutByName;
  void applyDefaultLayout;

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

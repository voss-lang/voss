import { batch, createSignal, onMount, onCleanup, Show } from 'solid-js';
import Titlebar from './components/titlebar/Titlebar';
import GridRoot, { type GridController } from './grid/GridRoot';
import SetupWindow from './components/setup/SetupWindow';
import CommandPalette from './command-palette/CommandPalette';
import {
  createCommandRegistry,
  v0Commands,
  type AppContext,
} from './command-palette/registry';
import { normalizeChord } from './command-palette/chords';
import { buildQuickOpenItems } from './command-palette/quickOpen';
import type {
  ActiveLayout,
  LayoutPreset,
} from './grid/layoutPresets';
import { serializeLayout } from './grid/layoutCommands';
import { layoutToSession } from './grid/sessionCommands';
import {
  listLayouts,
  loadDefaultLayout,
  loadLayout,
  saveLayout,
} from './grid/layoutStorage';
import {
  loadSession,
  loadGlobalSession,
  type SessionFile,
} from './grid/sessionStorage';
import {
  installStructuralSessionAutosave,
  installCloseSessionSave,
  type SessionContext,
} from './grid/sessionPersist';
import {
  defaultCwd,
  listRecents,
  openProject,
  pickFolder,
  type ProjectInfo,
} from './project/projectStorage';

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
  const [project, setProject] = createSignal<ProjectInfo | null>(null);
  const [projectLessAccepted, setProjectLessAccepted] = createSignal(false);
  const [recents, setRecents] = createSignal<string[]>([]);
  const [projectLessCwd, setProjectLessCwd] = createSignal<string | undefined>();
  const [initialSession, setInitialSession] = createSignal<SessionFile | null>(null);
  const [paletteMode, setPaletteMode] = createSignal<'quick' | 'full' | null>(null);
  const [layoutNames, setLayoutNames] = createSignal<string[]>([]);
  const [recentCommandIds] = createSignal<Set<string>>(new Set());
  let gridController: GridController | undefined;
  let sessionCleanup: (() => void) | undefined;

  // --- Command registry (D-01) -----------------------------------------------
  const registry = createCommandRegistry(v0Commands());

  const onLayoutSelect = (preset: LayoutPreset) => {
    gridController?.applyPreset(preset);
  };

  const showGrid = () => project() !== null || projectLessAccepted();

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
  void applyDefaultLayout; // A7 callable seam — kept live for palette wiring

  const openSelectedProject = async (
    path: string,
    errorPrefix: string,
  ): Promise<void> => {
    try {
      const info = await openProject(path);
      setRecents(await listRecents());

      // D-10: restore priority — session → default layout → fresh pane.
      // Resolved BEFORE setting project/projectLessAccepted so GridRoot
      // mounts with the correct initial state and no throwaway PTY spawns.
      let session: SessionFile | null = null;
      session = await loadSession(info.path).catch(() => null);
      if (!session) {
        const layout = await loadDefaultLayout(info.path).catch(() => null);
        if (layout) {
          session = layoutToSession(layout, false);
        }
      }

      batch(() => {
        setInitialSession(session);
        setProject(info);
        setProjectLessAccepted(true);
      });
    } catch (e) {
      console.error(errorPrefix, e);
    }
  };

  const handleOpenFolder = async () => {
    const picked = await pickFolder();
    if (!picked) return;
    await openSelectedProject(picked, 'open_project failed:');
  };

  const handleOpenRecent = (path: string) => {
    void openSelectedProject(path, 'open_recent failed:');
  };

  // --- Palette lifecycle (D-06/D-08) ------------------------------------------

  const openPalette = (mode: 'quick' | 'full') => {
    setPaletteMode(mode);
    if (mode === 'quick' && project()) {
      void listLayouts(project()!.path)
        .then(setLayoutNames)
        .catch(() => setLayoutNames([]));
    }
  };

  const dismissPalette = () => setPaletteMode(null);

  const quickItems = () =>
    buildQuickOpenItems(layoutNames(), recents());

  const handlePaletteExecute = (id: string) => {
    if (id.startsWith('layout:')) {
      const name = id.slice('layout:'.length);
      if (project() && gridController) {
        void loadLayoutByName(project()!.path, name);
      }
    } else if (id.startsWith('recent:')) {
      const path = id.slice('recent:'.length);
      void openSelectedProject(path, 'palette open_recent failed:');
    } else {
      // Full-mode command — dispatch through registry
      const cmd = registry.commands.get(id);
      if (cmd) cmd.handler(appCtx);
    }
  };

  // --- AppContext (D-03) — built once, threaded to registry handlers ----------

  const appCtx: AppContext = {
    splitFocused: () => {},
    closeFocused: () => {},
    equalizePanes: () => {},
    cycleLayout: () => {
      // Cycle is special — needs activeLayout + applyPreset
      // Handled below via the existing GridRoot flow
    },
    focusNext: () => {},
    focusPrev: () => {},
    focusIndex: () => {},
    focusDirection: () => {},
    resizeDirection: () => {},
    openQuickPalette: () => openPalette('quick'),
    openFullPalette: () => openPalette('full'),
    openProject: () => void handleOpenFolder(),
    saveLayout: () => {
      // Placeholder — A7 palette wires prompt UI later
    },
    loadLayout: () => {
      // Placeholder — opens quick palette as fallback
      openPalette('quick');
    },
    switchProfile: () => {
      // Placeholder — A7-03 wires profile switching
    },
    showKeybindings: () => {
      // Placeholder — A7-04 wires keybindings display
    },
  };

  // --- Global keyboard routing (D-02/D-08) -----------------------------------
  // Capture phase: intercepts ⌘P/⌘⇧P before GridRoot sees them.
  // While palette is open, suppresses all ⌘ chords from reaching the grid.

  const onAppKey = (e: KeyboardEvent) => {
    // While palette open: suppress grid chords (T-A7-03)
    if (paletteMode() !== null) {
      if (e.metaKey) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
      return;
    }

    const chord = normalizeChord(e);
    if (chord === 'Cmd+P') {
      e.preventDefault();
      e.stopImmediatePropagation();
      openPalette('quick');
    } else if (chord === 'Cmd+Shift+P') {
      e.preventDefault();
      e.stopImmediatePropagation();
      openPalette('full');
    }
  };

  onMount(() => {
    window.addEventListener('keydown', onAppKey, true); // capture phase
    void listRecents()
      .then(setRecents)
      .catch(() => setRecents([]));
    void defaultCwd(null)
      .then(setProjectLessCwd)
      .catch(() => setProjectLessCwd(undefined));

    // D-12: check global session for project-less bypass on launch.
    void loadGlobalSession()
      .then((globalSession) => {
        if (globalSession?.projectLessAccepted && !projectLessAccepted()) {
          batch(() => {
            setInitialSession(globalSession);
            setProjectLessAccepted(true);
          });
        }
      })
      .catch(() => {
        // No global session — show setup window as normal.
      });
  });

  onCleanup(() => {
    window.removeEventListener('keydown', onAppKey, true);
  });

  // Suppress unused warnings while keeping the symbols live.
  void saveCurrentLayout;
  void sessionCleanup;

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
        projectName={project()?.name}
        activeLayout={activeLayout()}
        onLayoutSelect={onLayoutSelect}
      />
      <Show
        when={showGrid()}
        fallback={
          <SetupWindow
            recents={recents()}
            onOpenProject={handleOpenFolder}
            onOpenRecent={handleOpenRecent}
            onStartProjectLess={() => setProjectLessAccepted(true)}
          />
        }
      >
        {/* A3: the binary-split grid fills the body (leaves are A2 panes). */}
        <div
          style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}
        >
          <GridRoot
            activeLayout={activeLayout}
            onLayoutChange={(next) => setActiveLayout(next)}
            controllerRef={(c) => {
              gridController = c;
              // A6: install session lifecycle once grid is mounted.
              const ctx: SessionContext = {
                getRoot: () => c.snapshot().root,
                getFocusedId: () => c.snapshot().focusedId,
                getActiveLayout: () => activeLayout(),
                getProjectLessAccepted: () => projectLessAccepted(),
                projectPath: project()?.path ?? null,
              };
              sessionCleanup = installStructuralSessionAutosave(ctx);
              void installCloseSessionSave(ctx);
            }}
            projectCwd={project()?.path ?? projectLessCwd()}
            initialSession={initialSession() ?? undefined}
          />
        </div>
      </Show>

      {/* A7: command palette overlay */}
      <Show when={paletteMode() !== null}>
        <CommandPalette
          mode={paletteMode()!}
          commands={registry.all()}
          quickItems={quickItems()}
          recentCommandIds={recentCommandIds()}
          onExecute={handlePaletteExecute}
          onDismiss={dismissPalette}
        />
      </Show>
    </div>
  );
}

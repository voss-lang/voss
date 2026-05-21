import { batch, createMemo, createSignal, onMount, onCleanup, Show } from 'solid-js';
import Titlebar from './components/titlebar/Titlebar';
import GridRoot, { type GridController } from './grid/GridRoot';
import SetupWindow from './components/setup/SetupWindow';
import CommandPalette from './command-palette/CommandPalette';
import ToastStack from './command-palette/toast';
import {
  createCommandRegistry,
  v0Commands,
  type AppContext,
  type KeyBindingOverrides,
} from './command-palette/registry';
import { normalizeChord, normalizePrefixKey } from './command-palette/chords';
import {
  loadKeymapProfile,
  saveKeymapProfile,
  watchWorkspaceKeymap,
  type KeymapProfile,
  type KeymapUpdatePayload,
} from './command-palette/keymapStorage';
import { createPrefixMode } from './command-palette/prefixMode';
import { setAsAppMenu } from './command-palette/nativeMenu';
import { showToast } from './command-palette/toast';
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
  const [keymapProfile, setKeymapProfile] = createSignal<KeymapProfile>('vscode');
  const [keymapOverrides, setKeymapOverrides] =
    createSignal<KeyBindingOverrides>({});
  const [prefixActive, setPrefixActive] = createSignal(false);
  const [recentCommandIds] = createSignal<Set<string>>(new Set());
  let gridController: GridController | undefined;
  let sessionCleanup: (() => void) | undefined;
  let keymapUnlisten: (() => void) | undefined;

  // --- Command registry (D-01) -----------------------------------------------
  const baseCommands = v0Commands();
  const registry = createMemo(() =>
    createCommandRegistry(baseCommands, keymapOverrides()),
  );
  const knownCommandIds = () => baseCommands.map((cmd) => cmd.id);
  const knownChords = () =>
    baseCommands.flatMap((cmd) => [
      ...(cmd.keybinding ? [cmd.keybinding] : []),
      ...(cmd.aliases ?? []),
    ]);

  const onLayoutSelect = (preset: LayoutPreset) => {
    gridController?.applyPreset(preset);
  };

  const showGrid = () => project() !== null || projectLessAccepted();
  const workspacePath = () => project()?.path ?? projectLessCwd();

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
      void installWorkspaceKeymap(info.path);
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
    const path = workspacePath();
    if (mode === 'quick' && path) {
      void listLayouts(path)
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
      const path = workspacePath();
      if (path && gridController) {
        void loadLayoutByName(path, name);
      }
    } else if (id.startsWith('recent:')) {
      const path = id.slice('recent:'.length);
      void openSelectedProject(path, 'palette open_recent failed:');
    } else {
      dispatchCommandId(id);
    }
  };

  const applyKeymapUpdate = (payload: KeymapUpdatePayload) => {
    setKeymapOverrides(payload.valid);
    for (const issue of payload.issues) {
      showToast('warning', `${issue.commandId}: ${issue.reason}`);
    }
  };

  const installWorkspaceKeymap = async (workspacePath: string) => {
    keymapUnlisten?.();
    keymapUnlisten = undefined;
    try {
      keymapUnlisten = await watchWorkspaceKeymap(
        workspacePath,
        knownCommandIds(),
        knownChords(),
        applyKeymapUpdate,
      );
    } catch (e) {
      console.error('watch_keymap_overrides failed:', e);
      setKeymapOverrides({});
      showToast('error', 'could not load keymap settings');
    }
  };

  // --- AppContext (D-03) — built once, threaded to registry handlers ----------

  const appCtx: AppContext = {
    splitFocused: (orientation) => gridController?.splitFocused(orientation),
    closeFocused: () => gridController?.closeFocused(),
    equalizePanes: () => gridController?.equalizePanes(),
    cycleLayout: () => gridController?.cycleLayout(),
    focusNext: () => gridController?.focusNext(),
    focusPrev: () => gridController?.focusPrev(),
    focusIndex: (n) => gridController?.focusIndex(n),
    focusDirection: (dir) => gridController?.focusDirection(dir),
    resizeDirection: (dir) => gridController?.resizeDirection(dir),
    openQuickPalette: () => openPalette('quick'),
    openFullPalette: () => openPalette('full'),
    openProject: () => void handleOpenFolder(),
    saveLayout: () => {
      const path = workspacePath();
      if (!path) return;
      const name = window.prompt('Save layout as');
      const trimmed = name?.trim();
      if (!trimmed) return;
      void saveCurrentLayout(path, trimmed)
        .then(() => listLayouts(path))
        .then(setLayoutNames)
        .catch((e) => console.error('save_layout failed:', e));
    },
    loadLayout: () => {
      openPalette('quick');
    },
    switchProfile: () => {
      const next: KeymapProfile =
        keymapProfile() === 'tmux' ? 'vscode' : 'tmux';
      void saveKeymapProfile(next)
        .then(() => {
          setKeymapProfile(next);
          showToast('info', `Keymap profile: ${next}`);
        })
        .catch((e) => {
          console.error('save_keymap_profile failed:', e);
          showToast('error', 'could not save keymap settings');
        });
    },
    showKeybindings: () => {
      openPalette('full');
    },
  };

  const dispatchCommandId = (id: string): boolean => {
    const cmd = registry().commands.get(id);
    if (!cmd) return false;
    cmd.handler(appCtx);
    return true;
  };

  const prefixMode = createPrefixMode({
    onActivate: () => setPrefixActive(true),
    onDeactivate: () => setPrefixActive(false),
    dispatch: (commandId) => {
      void dispatchCommandId(commandId);
    },
    setTimeout: (fn, ms) => window.setTimeout(fn, ms),
    clearTimeout: (id) => window.clearTimeout(id),
  });

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

    if (prefixMode.isActive()) {
      const prefixKey = normalizePrefixKey(e);
      if (prefixKey) {
        const result = prefixMode.handleKey(prefixKey);
        if (result.action !== 'passthrough') {
          e.preventDefault();
          e.stopImmediatePropagation();
        }
        return;
      }
      if (chord === 'Cmd+B') {
        e.preventDefault();
        e.stopImmediatePropagation();
        prefixMode.tryEnter(keymapProfile());
        return;
      }
    }

    if (chord === 'Cmd+B' && prefixMode.tryEnter(keymapProfile())) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }

    if (chord && registry().dispatch(chord, appCtx)) {
      e.preventDefault();
      e.stopImmediatePropagation();
    }
  };

  onMount(() => {
    window.addEventListener('keydown', onAppKey, true); // capture phase
    void setAsAppMenu(registry(), (id) => {
      void dispatchCommandId(id);
    });
    void loadKeymapProfile()
      .then(setKeymapProfile)
      .catch(() => setKeymapProfile('vscode'));
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
    keymapUnlisten?.();
    prefixMode.cancel();
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
            externalKeymap={true}
            prefixActive={prefixActive()}
            prefixReserved={keymapProfile() === 'tmux'}
          />
        </div>
      </Show>

      {/* A7: toast stack (keymap validation, profile switch feedback) */}
      <ToastStack />

      {/* A7: command palette overlay */}
      <Show when={paletteMode() !== null}>
        <CommandPalette
          mode={paletteMode()!}
          commands={registry().all()}
          quickItems={quickItems()}
          recentCommandIds={recentCommandIds()}
          onExecute={handlePaletteExecute}
          onDismiss={dismissPalette}
        />
      </Show>
    </div>
  );
}

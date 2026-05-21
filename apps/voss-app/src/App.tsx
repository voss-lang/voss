import {
  batch,
  createMemo,
  createSignal,
  onMount,
  onCleanup,
  Show,
  For,
  type Accessor,
} from 'solid-js';
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
  defaultCwd,
  listRecents,
  openProject,
  pickFolder,
  type ProjectInfo,
} from './project/projectStorage';
import {
  createWorkspaceStore,
  type WorkspaceRecord,
} from './workspaces/workspaceStore';
import {
  DEFAULT_WORKSPACE_ID,
  loadProjectLessSession,
} from './workspaces/workspaceStorage';
import {
  installAllWorkspacesCloseSave,
  installWorkspaceStructuralAutosave,
  type WorkspaceSessionContext,
} from './workspaces/workspaceSessionPersist';

/**
 * App composition root (A4-02, A8-02).
 *
 * Owns the workspace index, one mounted `GridRoot` per workspace (hidden via
 * CSS when inactive — D-01), and a single all-workspace close-save handler.
 */

export type MountedWorkspace = {
  id: string;
  activeLayout: Accessor<ActiveLayout>;
  setActiveLayout: (next: ActiveLayout) => void;
  project: Accessor<ProjectInfo | null>;
  setProject: (next: ProjectInfo | null) => void;
  projectLessAccepted: Accessor<boolean>;
  setProjectLessAccepted: (next: boolean) => void;
  initialSession: Accessor<SessionFile | null>;
  setInitialSession: (next: SessionFile | null) => void;
  projectLessCwd: Accessor<string | undefined>;
  setProjectLessCwd: (next: string | undefined) => void;
  /** Once true, GridRoot stays mounted when switching away (D-01). */
  everMounted: Accessor<boolean>;
  setEverMounted: (next: boolean) => void;
  gridController?: GridController;
  sessionCleanup?: () => void;
};

function createMountedWorkspace(id: string): MountedWorkspace {
  const [activeLayout, setActiveLayout] =
    createSignal<ActiveLayout>('custom');
  const [project, setProject] = createSignal<ProjectInfo | null>(null);
  const [projectLessAccepted, setProjectLessAccepted] = createSignal(false);
  const [initialSession, setInitialSession] = createSignal<SessionFile | null>(
    null,
  );
  const [projectLessCwd, setProjectLessCwd] = createSignal<string | undefined>();
  const [everMounted, setEverMounted] = createSignal(false);

  return {
    id,
    activeLayout,
    setActiveLayout,
    project,
    setProject,
    projectLessAccepted,
    setProjectLessAccepted,
    initialSession,
    setInitialSession,
    projectLessCwd,
    setProjectLessCwd,
    everMounted,
    setEverMounted,
  };
}

function workspaceIsReady(ws: MountedWorkspace): boolean {
  return ws.project() !== null || ws.projectLessAccepted();
}

function sessionContextFor(ws: MountedWorkspace): WorkspaceSessionContext {
  return {
    workspaceId: ws.id,
    getController: () => ws.gridController,
    getActiveLayout: () => ws.activeLayout(),
    getProjectLessAccepted: () => ws.projectLessAccepted(),
    projectPath: ws.project()?.path ?? null,
  };
}

function seedMountedMap(
  records: readonly WorkspaceRecord[],
): Map<string, MountedWorkspace> {
  const next = new Map<string, MountedWorkspace>();
  for (const record of records) {
    next.set(record.id, createMountedWorkspace(record.id));
  }
  return next;
}

export default function App() {
  const workspaceStore = createWorkspaceStore();
  const [mountedById, setMountedById] = createSignal<Map<string, MountedWorkspace>>(
    seedMountedMap(workspaceStore.workspaces()),
  );

  const [recents, setRecents] = createSignal<string[]>([]);
  const [paletteMode, setPaletteMode] = createSignal<'quick' | 'full' | null>(
    null,
  );
  const [layoutNames, setLayoutNames] = createSignal<string[]>([]);
  const [keymapProfile, setKeymapProfile] = createSignal<KeymapProfile>('vscode');
  const [keymapOverrides, setKeymapOverrides] =
    createSignal<KeyBindingOverrides>({});
  const [prefixActive, setPrefixActive] = createSignal(false);
  const [recentCommandIds] = createSignal<Set<string>>(new Set());
  let closeSaveUnlisten: (() => void) | undefined;
  let keymapUnlisten: (() => void) | undefined;

  const activeId = () => workspaceStore.activeId();
  const activeMounted = createMemo(() => {
    const id = activeId();
    return id ? mountedById().get(id) : undefined;
  });

  const gridController = () => activeMounted()?.gridController;

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
    gridController()?.applyPreset(preset);
  };

  const showGrid = () => {
    const ws = activeMounted();
    return ws != null && workspaceIsReady(ws);
  };

  const workspacePath = () => {
    const ws = activeMounted();
    return ws?.project()?.path ?? ws?.projectLessCwd();
  };

  const saveCurrentLayout = async (
    path: string,
    name: string,
  ): Promise<void> => {
    const ctrl = gridController();
    const ws = activeMounted();
    if (!ctrl || !ws) return;
    const snap = ctrl.snapshot();
    const file = serializeLayout(snap.root, snap.focusedId, ws.activeLayout());
    await saveLayout(path, name, file);
  };

  const loadLayoutByName = async (
    path: string,
    name: string,
  ): Promise<void> => {
    const ctrl = gridController();
    if (!ctrl) return;
    const file = await loadLayout(path, name);
    ctrl.applyLoadedLayout(file);
  };

  const applyDefaultLayout = async (path: string): Promise<boolean> => {
    const ctrl = gridController();
    if (!ctrl) return false;
    const file = await loadDefaultLayout(path);
    if (!file) return false;
    ctrl.applyLoadedLayout(file);
    return true;
  };
  void applyDefaultLayout;

  const restoreWorkspaceFromRecord = async (
    ws: MountedWorkspace,
    record: WorkspaceRecord,
  ): Promise<void> => {
    if (record.projectPath) {
      try {
        const info = await openProject(record.projectPath);
        let session: SessionFile | null = null;
        session = await loadSession(info.path).catch(() => null);
        if (!session) {
          const layout = await loadDefaultLayout(info.path).catch(() => null);
          if (layout) {
            session = layoutToSession(layout, false);
          }
        }
        batch(() => {
          ws.setInitialSession(session);
          ws.setProject(info);
          ws.setProjectLessAccepted(true);
          ws.setEverMounted(true);
        });
        workspaceStore.setProjectPath(record.id, info.path);
        void installWorkspaceKeymap(info.path);
      } catch (e) {
        console.error('restore workspace project failed:', e);
      }
      return;
    }

    let session: SessionFile | null = await loadProjectLessSession(
      record.id,
    ).catch(() => null);

    if (!session && record.id === DEFAULT_WORKSPACE_ID) {
      session = await loadGlobalSession().catch(() => null);
    }

    if (session?.projectLessAccepted) {
      batch(() => {
        ws.setInitialSession(session);
        ws.setProjectLessAccepted(true);
        ws.setEverMounted(true);
      });
    }
  };

  const openSelectedProject = async (
    path: string,
    errorPrefix: string,
  ): Promise<void> => {
    const ws = activeMounted();
    if (!ws) return;
    try {
      const info = await openProject(path);
      setRecents(await listRecents());

      let session: SessionFile | null = null;
      session = await loadSession(info.path).catch(() => null);
      if (!session) {
        const layout = await loadDefaultLayout(info.path).catch(() => null);
        if (layout) {
          session = layoutToSession(layout, false);
        }
      }

      batch(() => {
        ws.setInitialSession(session);
        ws.setProject(info);
        ws.setProjectLessAccepted(true);
        ws.setEverMounted(true);
      });
      workspaceStore.setProjectPath(ws.id, info.path);
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

  const handleStartProjectLess = () => {
    const ws = activeMounted();
    if (!ws) return;
    batch(() => {
      ws.setProjectLessAccepted(true);
      ws.setEverMounted(true);
    });
  };

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
      const ctrl = gridController();
      if (path && ctrl) {
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

  const installWorkspaceKeymap = async (path: string) => {
    keymapUnlisten?.();
    keymapUnlisten = undefined;
    try {
      keymapUnlisten = await watchWorkspaceKeymap(
        path,
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

  const appCtx: AppContext = {
    splitFocused: (orientation) => gridController()?.splitFocused(orientation),
    closeFocused: () => gridController()?.closeFocused(),
    equalizePanes: () => gridController()?.equalizePanes(),
    cycleLayout: () => gridController()?.cycleLayout(),
    focusNext: () => gridController()?.focusNext(),
    focusPrev: () => gridController()?.focusPrev(),
    focusIndex: (n) => gridController()?.focusIndex(n),
    focusDirection: (dir) => gridController()?.focusDirection(dir),
    resizeDirection: (dir) => gridController()?.resizeDirection(dir),
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

  const onAppKey = (e: KeyboardEvent) => {
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

  const allSessionContexts = (): WorkspaceSessionContext[] =>
    [...mountedById().values()].map(sessionContextFor);

  onMount(() => {
    window.addEventListener('keydown', onAppKey, true);
    void setAsAppMenu(registry(), (id) => {
      void dispatchCommandId(id);
    });
    void loadKeymapProfile()
      .then(setKeymapProfile)
      .catch(() => setKeymapProfile('vscode'));
    void listRecents()
      .then(setRecents)
      .catch(() => setRecents([]));

    void (async () => {
      await workspaceStore.load();
      const nextMounted = new Map(mountedById());
      for (const record of workspaceStore.workspaces()) {
        if (!nextMounted.has(record.id)) {
          nextMounted.set(record.id, createMountedWorkspace(record.id));
        }
      }
      setMountedById(nextMounted);

      for (const record of workspaceStore.workspaces()) {
        const ws = nextMounted.get(record.id);
        if (!ws) continue;
        void defaultCwd(record.projectPath ?? null)
          .then(ws.setProjectLessCwd)
          .catch(() => ws.setProjectLessCwd(undefined));
        void restoreWorkspaceFromRecord(ws, record);
      }

      closeSaveUnlisten = await installAllWorkspacesCloseSave(
        allSessionContexts,
        () => workspaceStore.snapshotIndex(),
        async () => {
          await workspaceStore.persist();
        },
      );
    })();
  });

  onCleanup(() => {
    window.removeEventListener('keydown', onAppKey, true);
    keymapUnlisten?.();
    prefixMode.cancel();
    closeSaveUnlisten?.();
    for (const ws of mountedById().values()) {
      ws.sessionCleanup?.();
    }
  });

  void saveCurrentLayout;

  const bindController = (ws: MountedWorkspace, c: GridController) => {
    ws.gridController = c;
    ws.sessionCleanup?.();
    ws.sessionCleanup = installWorkspaceStructuralAutosave(sessionContextFor(ws));
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
        projectName={activeMounted()?.project()?.name}
        activeLayout={activeMounted()?.activeLayout() ?? 'custom'}
        onLayoutSelect={onLayoutSelect}
      />
      <Show
        when={showGrid()}
        fallback={
          <SetupWindow
            recents={recents()}
            onOpenProject={handleOpenFolder}
            onOpenRecent={handleOpenRecent}
            onStartProjectLess={handleStartProjectLess}
          />
        }
      >
        <div
          style={{
            flex: '1',
            'min-height': '0',
            background: 'var(--bg-0)',
            display: 'flex',
            'flex-direction': 'column',
          }}
        >
          <For each={workspaceStore.workspaces()}>
            {(record) => {
              const ws = () => mountedById().get(record.id);
              const shouldMount = () => {
                const m = ws();
                return m != null && (m.everMounted() || workspaceIsReady(m));
              };
              return (
                <Show when={shouldMount()}>
                  <div
                    data-workspace-id={record.id}
                    style={{
                      display: activeId() === record.id ? 'flex' : 'none',
                      flex: '1',
                      'min-height': '0',
                      'flex-direction': 'column',
                    }}
                  >
                    <GridRoot
                      active={() => activeId() === record.id}
                      activeLayout={ws()!.activeLayout}
                      onLayoutChange={(next) => ws()!.setActiveLayout(next)}
                      controllerRef={(c) => bindController(ws()!, c)}
                      projectCwd={
                        ws()!.project()?.path ?? ws()!.projectLessCwd()
                      }
                      initialSession={ws()!.initialSession() ?? undefined}
                      externalKeymap={true}
                      prefixActive={prefixActive()}
                      prefixReserved={keymapProfile() === 'tmux'}
                    />
                  </div>
                </Show>
              );
            }}
          </For>
        </div>
      </Show>

      <ToastStack />

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

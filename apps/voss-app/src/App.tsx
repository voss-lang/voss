import { invoke } from '@tauri-apps/api/core';
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
import WorkspaceTabBar, {
  COPY_LAST_WORKSPACE_BLOCKED,
} from './components/workspace/WorkspaceTabBar';
import NewWorkspacePicker, {
  type NewWorkspacePickerCreatePayload,
  type NewWorkspacePickerStartEmptyPayload,
} from './components/workspace/NewWorkspacePicker';
import './components/workspace/workspace.css';
import GridRoot, { type GridController } from './grid/GridRoot';
import StatusBar from './components/StatusBar';
import ContextPanel from './components/ContextPanel';
import { collectLeaves } from './grid/tree';
import type { AgentConfig } from './pane/pty-ipc';
import { contextByPaneId } from './pane/contextRegistry';
import { budgetByPaneId } from './pane/budgetRegistry';
import { isKnownAgentCli } from './pane/agentDetect';
import AgentSidebar from './components/sidebar/AgentSidebar';
import SetupWindow from './components/setup/SetupWindow';
import CommandPalette from './command-palette/CommandPalette';
import ToastStack from './command-palette/toast';
import {
  createCommandRegistry,
  v0Commands,
  workspaceCommands,
  appearanceCommands,
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
import { applyWindowEffects } from './appearance/windowEffects';
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
import {
  parseWorkspaceShortcut,
  workspaceIndexForFocusAction,
} from './workspaces/workspaceShortcuts';

/**
 * App composition root (A4-02, A8-02).
 *
 * Owns the workspace index, one mounted `GridRoot` per workspace (hidden via
 * CSS when inactive — D-01), and a single all-workspace close-save handler.
 */

interface AgentEntry {
  paneId: string;
  sessionId: string;
  cliBinary: string;
  cliArgs: string;
  cwd: string;
  status: string;
  lastSeen: number;
}

async function fetchAgentConfigs(
  workspacePath: string | null,
): Promise<Record<string, AgentConfig>> {
  const entries = await invoke<AgentEntry[]>('get_active_agents', {
    workspacePath,
  }).catch(() => []);
  const out: Record<string, AgentConfig> = {};
  for (const entry of entries) {
    let cliArgs: string[] = [];
    try {
      cliArgs = JSON.parse(entry.cliArgs) as string[];
    } catch {
      cliArgs = [];
    }
    out[entry.paneId] = {
      cliBinary: entry.cliBinary,
      cliArgs,
      sessionId: entry.sessionId,
    };
  }
  return out;
}

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
  agentConfigByPaneId: Accessor<Record<string, AgentConfig>>;
  setAgentConfigByPaneId: (next: Record<string, AgentConfig>) => void;
  orphanSweepDone: boolean;
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
  const [agentConfigByPaneId, setAgentConfigByPaneId] = createSignal<
    Record<string, AgentConfig>
  >({});

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
    agentConfigByPaneId,
    setAgentConfigByPaneId,
    orphanSweepDone: false,
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
  const [newWorkspacePickerOpen, setNewWorkspacePickerOpen] = createSignal(false);
  const [focusedPaneId, setFocusedPaneId] = createSignal<string | undefined>();
  const [paneCount, setPaneCount] = createSignal(0);
  const [contextPanelOpen, setContextPanelOpen] = createSignal(
    localStorage.getItem('voss:contextPanelOpen') === 'true',
  );
  const toggleContextPanel = () => {
    setContextPanelOpen((prev) => {
      const next = !prev;
      localStorage.setItem('voss:contextPanelOpen', String(next));
      return next;
    });
  };
  const [sidebarCollapsed, setSidebarCollapsed] = createSignal(
    localStorage.getItem('voss:sidebarCollapsed') === 'true',
  );
  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('voss:sidebarCollapsed', String(next));
      return next;
    });
  };
  const [recentCommandIds] = createSignal<Set<string>>(new Set());
  let closeSaveUnlisten: (() => void) | undefined;
  let keymapUnlisten: (() => void) | undefined;

  const activeId = () => workspaceStore.activeId();
  let cachedWorkspaceIds: string[] = [];
  const workspaceIds = createMemo(() => {
    const next = workspaceStore.workspaces().map((w) => w.id);
    if (
      next.length === cachedWorkspaceIds.length &&
      next.every((id, i) => id === cachedWorkspaceIds[i])
    ) {
      return cachedWorkspaceIds;
    }
    cachedWorkspaceIds = next;
    return next;
  });
  const activeMounted = createMemo(() => {
    const id = activeId();
    return id ? mountedById().get(id) : undefined;
  });

  const gridController = () => activeMounted()?.gridController;

  const agentListForSidebar = createMemo(() => {
    const ws = activeMounted();
    if (!ws) return [];
    const configs = ws.agentConfigByPaneId();
    const budgets = budgetByPaneId();
    return Object.entries(configs)
      .filter(([, cfg]) => isKnownAgentCli(cfg.cliBinary))
      .map(([paneId, cfg]) => {
        const b = budgets[paneId];
        const model = cfg.cliArgs.find((a) => a.startsWith('--model'))?.split('=')[1] ?? 'default';
        const role = cfg.cliBinary === 'claude' ? 'planner'
          : cfg.cliBinary === 'codex' ? 'executor'
          : cfg.cliBinary === 'gemini' ? 'reviewer'
          : cfg.cliBinary === 'aider' ? 'executor'
          : 'user';
        return {
          paneId,
          cliBinary: cfg.cliBinary,
          model,
          role,
          costUsd: b?.cost_usd ?? 0,
          isStreaming: b ? Date.now() - b.lastSeenMs < 3000 : false,
        };
      });
  });

  // --- Command registry (D-01) -----------------------------------------------
  const baseCommands = [
    ...v0Commands(),
    ...workspaceCommands(),
    ...appearanceCommands(),
  ];
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
    // Read controller directly from the mounted workspace to avoid
    // stale memo / optional-chaining swallowing undefined silently.
    const id = activeId();
    const ws = id ? mountedById().get(id) : undefined;
    const ctrl = ws?.gridController;
    if (!ctrl) {
      console.warn(
        '[voss-app] onLayoutSelect: gridController unavailable',
        { activeId: id, hasMounted: !!ws, hasCtrl: !!ctrl },
      );
      return;
    }
    ctrl.applyPreset(preset);
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

  const restoreWorkspaceFromRecord = async (
    ws: MountedWorkspace,
    record: WorkspaceRecord,
  ): Promise<void> => {
    if (record.projectPath) {
      try {
        const info = await openProject(record.projectPath);
        const agentConfigs = await fetchAgentConfigs(info.path);
        let session: SessionFile | null = null;
        session = await loadSession(info.path).catch(() => null);
        if (!session) {
          const layout = await loadDefaultLayout(info.path).catch(() => null);
          if (layout) {
            session = layoutToSession(layout, false);
          }
        }
        batch(() => {
          ws.setAgentConfigByPaneId(agentConfigs);
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
      const agentConfigs = await fetchAgentConfigs(null);
      batch(() => {
        ws.setAgentConfigByPaneId(agentConfigs);
        ws.setInitialSession(session);
        ws.setProjectLessAccepted(true);
        ws.setEverMounted(true);
      });
    }
  };

  const bootstrapWorkspaceProject = async (
    ws: MountedWorkspace,
    workspaceId: string,
    path: string,
    layoutName?: string | null,
  ): Promise<void> => {
    try {
      const info = await openProject(path);
      setRecents(await listRecents());
      const agentConfigs = await fetchAgentConfigs(info.path);

      let session: SessionFile | null = await loadSession(info.path).catch(
        () => null,
      );
      if (!session && layoutName) {
        const layout = await loadLayout(info.path, layoutName).catch(() => null);
        if (layout) {
          session = layoutToSession(layout, false);
        }
      }
      if (!session) {
        const layout = await loadDefaultLayout(info.path).catch(() => null);
        if (layout) {
          session = layoutToSession(layout, false);
        }
      }

      batch(() => {
        ws.setAgentConfigByPaneId(agentConfigs);
        ws.setInitialSession(session);
        ws.setProject(info);
        ws.setProjectLessAccepted(true);
        ws.setEverMounted(true);
      });
      workspaceStore.setProjectPath(workspaceId, info.path);
      void installWorkspaceKeymap(info.path);
      void defaultCwd(info.path)
        .then(ws.setProjectLessCwd)
        .catch(() => ws.setProjectLessCwd(undefined));
    } catch (e) {
      console.error('bootstrap workspace project failed:', e);
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

      const agentConfigs = !ws.everMounted()
        ? await fetchAgentConfigs(info.path)
        : {};

      batch(() => {
        if (!ws.everMounted()) {
          ws.setAgentConfigByPaneId(agentConfigs);
          ws.setInitialSession(session);
        }
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

  const ensureMountedRecord = (id: string): MountedWorkspace => {
    const existing = mountedById().get(id);
    if (existing) return existing;
    const ws = createMountedWorkspace(id);
    setMountedById((prev) => new Map(prev).set(id, ws));
    return ws;
  };

  const handleNewWorkspace = () => {
    setNewWorkspacePickerOpen(true);
  };

  const handleCreateWorkspace = async (
    payload: NewWorkspacePickerCreatePayload,
  ) => {
    setNewWorkspacePickerOpen(false);
    const record = workspaceStore.add({
      name: payload.name,
      projectPath: payload.folderPath,
      accentColor: payload.accentColor,
    });
    const ws = ensureMountedRecord(record.id);
    if (payload.folderPath) {
      await bootstrapWorkspaceProject(
        ws,
        record.id,
        payload.folderPath,
        payload.layoutName,
      );
    }
    void workspaceStore.persist();
  };

  const handleStartEmptyWorkspace = async (
    payload: NewWorkspacePickerStartEmptyPayload,
  ) => {
    setNewWorkspacePickerOpen(false);
    const record = workspaceStore.add({
      name: payload.name,
      accentColor: payload.accentColor,
    });
    const ws = ensureMountedRecord(record.id);
    batch(() => {
      ws.setProjectLessAccepted(true);
      ws.setEverMounted(true);
    });
    void defaultCwd(null)
      .then(ws.setProjectLessCwd)
      .catch(() => ws.setProjectLessCwd(undefined));
    void workspaceStore.persist();
  };

  const handleActivateWorkspace = (id: string) => {
    workspaceStore.activate(id);
    void workspaceStore.persist();
  };

  const handleRenameWorkspace = (id: string, name: string) => {
    workspaceStore.rename(id, name);
    void workspaceStore.persist();
  };

  const handleColorWorkspace = (id: string, color: string) => {
    workspaceStore.setAccentColor(id, color);
    void workspaceStore.persist();
  };

  const handleReorderWorkspaces = (fromIndex: number, toIndex: number) => {
    workspaceStore.reorder(fromIndex, toIndex);
    void workspaceStore.persist();
  };

  const handleCloseWorkspace = (id: string) => {
    if (!workspaceStore.canClose(id)) return;
    const ws = mountedById().get(id);
    ws?.sessionCleanup?.();
    if (ws) {
      ws.gridController = undefined;
    }
    setMountedById((prev) => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
    workspaceStore.remove(id);
    void workspaceStore.persist();
  };

  const handleCloseBlocked = () => {
    showToast('info', COPY_LAST_WORKSPACE_BLOCKED);
  };

  const handleNextWorkspace = () => {
    const list = workspaceStore.workspaces();
    const current = activeId();
    if (!current || list.length === 0) return;
    const idx = list.findIndex((w) => w.id === current);
    if (idx < 0) return;
    handleActivateWorkspace(list[(idx + 1) % list.length]!.id);
  };

  const handlePrevWorkspace = () => {
    const list = workspaceStore.workspaces();
    const current = activeId();
    if (!current || list.length === 0) return;
    const idx = list.findIndex((w) => w.id === current);
    if (idx < 0) return;
    handleActivateWorkspace(list[(idx - 1 + list.length) % list.length]!.id);
  };

  const handleFocusWorkspaceByIndex = (index: number) => {
    const list = workspaceStore.workspaces();
    if (index < 0 || index >= list.length) return;
    handleActivateWorkspace(list[index]!.id);
  };

  const handleCloseActiveWorkspace = () => {
    const id = activeId();
    if (!id) return;
    if (!workspaceStore.canClose(id)) {
      handleCloseBlocked();
      return;
    }
    handleCloseWorkspace(id);
  };

  const handleRenameActiveWorkspace = () => {
    const id = activeId();
    if (!id) return;
    const current = workspaceStore.workspaces().find((w) => w.id === id);
    const name = window.prompt('Rename workspace', current?.name ?? '');
    const trimmed = name?.trim();
    if (trimmed) handleRenameWorkspace(id, trimmed);
  };

  const handleColorActiveWorkspace = () => {
    const id = activeId();
    if (!id) return;
    const tab = document.querySelector(
      `[data-workspace-tab="${id}"]`,
    ) as HTMLElement | null;
    tab?.dispatchEvent(
      new MouseEvent('contextmenu', { bubbles: true, cancelable: true }),
    );
  };

  const handleWorkspaceShortcut = (
    action: NonNullable<ReturnType<typeof parseWorkspaceShortcut>>,
  ) => {
    if (action === 'next') {
      handleNextWorkspace();
      return;
    }
    if (action === 'prev') {
      handlePrevWorkspace();
      return;
    }
    const index = workspaceIndexForFocusAction(action);
    if (index != null) handleFocusWorkspaceByIndex(index);
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
    newWorkspace: () => handleNewWorkspace(),
    closeWorkspace: () => handleCloseActiveWorkspace(),
    nextWorkspace: () => handleNextWorkspace(),
    prevWorkspace: () => handlePrevWorkspace(),
    focusWorkspace: (index) => handleFocusWorkspaceByIndex(index),
    renameWorkspace: () => handleRenameActiveWorkspace(),
    colorWorkspace: () => handleColorActiveWorkspace(),
    switchTheme: () => openPalette('full'),
    switchFont: () => openPalette('full'),
    toggleHighContrast: () => openPalette('full'),
    setBellBehavior: () => openPalette('full'),
    toggleSidebar,
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
    if (newWorkspacePickerOpen()) {
      if (e.key === 'Escape') return;
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }

    if (paletteMode() !== null) {
      if (e.metaKey) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
      return;
    }

    const workspaceAction = parseWorkspaceShortcut(e);
    if (workspaceAction) {
      handleWorkspaceShortcut(workspaceAction);
      e.preventDefault();
      e.stopImmediatePropagation();
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

    // Cmd+Shift+B: toggle sidebar
    if (e.metaKey && e.shiftKey && (e.key === 'b' || e.key === 'B')) {
      toggleSidebar();
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }

    // F4: toggle context panel (D-01, D-06 persisted)
    if ((e.metaKey || e.ctrlKey) && e.key === 'i') {
      toggleContextPanel();
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
    void applyWindowEffects({ enabled: true });
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
        () => activeMounted()?.project()?.path ?? null,
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

  const bindController = (ws: MountedWorkspace, c: GridController) => {
    ws.gridController = c;
    ws.sessionCleanup?.();
    ws.sessionCleanup = installWorkspaceStructuralAutosave(sessionContextFor(ws));
    if (!ws.orphanSweepDone) {
      ws.orphanSweepDone = true;
      const session = ws.initialSession();
      if (session) {
        const leafIds = collectLeaves(session.grid.root).map((l) => l.id);
        const wp = ws.project()?.path ?? null;
        void invoke('sweep_orphan_agents', {
          validPaneIds: leafIds,
          workspacePath: wp,
        }).catch((e) =>
          console.error('[voss-app] agent orphan sweep failed:', e),
        );
      }
    }
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
      <WorkspaceTabBar
        workspaces={workspaceStore.workspaces()}
        activeId={activeId()}
        onActivate={handleActivateWorkspace}
        onNew={handleNewWorkspace}
        onRename={handleRenameWorkspace}
        onColor={handleColorWorkspace}
        onClose={handleCloseWorkspace}
        onReorder={handleReorderWorkspaces}
        closeGuardFor={(id) => workspaceStore.closeGuardFor(id)}
        onCloseBlocked={handleCloseBlocked}
        onCloseConfirm={handleCloseWorkspace}
      />
      <div
        style={{
          flex: '1',
          'min-height': '0',
          display: 'flex',
          'flex-direction': 'column',
          overflow: 'hidden',
        }}
      >
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
            'flex-direction': 'row',
            position: 'relative',
          }}
        >
          <AgentSidebar
            collapsed={sidebarCollapsed()}
            onToggle={toggleSidebar}
            agents={agentListForSidebar()}
            focusedPaneId={focusedPaneId()}
            onAgentClick={(paneId) => gridController()?.focusPaneById(paneId)}
            onAgentContextMenu={() => {}}
            onLaunchAgent={() => {}}
            sessions={[]}
            projectPath={activeMounted()?.project()?.path ?? null}
            workspacePath={workspacePath() ?? null}
          />
          <div style={{ flex: '1', 'min-height': '0', 'min-width': '0', display: 'flex', 'flex-direction': 'column', position: 'relative' }}>
            <For each={workspaceIds()}>
              {(workspaceId) => {
                const ws = () => mountedById().get(workspaceId);
                const shouldMount = () => {
                  const m = ws();
                  return m != null && (m.everMounted() || workspaceIsReady(m));
                };
                return (
                  <Show when={shouldMount()}>
                    <div
                      data-workspace-id={workspaceId}
                      style={{
                        display: activeId() === workspaceId ? 'flex' : 'none',
                        flex: '1',
                        'min-height': '0',
                        'flex-direction': 'column',
                      }}
                    >
                      <GridRoot
                        active={() => activeId() === workspaceId}
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
                        agentConfigByPaneId={ws()!.agentConfigByPaneId()}
                        workspacePath={ws()!.project()?.path ?? undefined}
                        onFocusChange={(id) => {
                          if (activeId() === workspaceId) setFocusedPaneId(id);
                        }}
                        onLeafCountChange={(count) => {
                          if (activeId() === workspaceId) setPaneCount(count);
                        }}
                      />
                    </div>
                  </Show>
                );
              }}
            </For>
            {/* F4: Context heatmap side panel (D-01, D-03 overlay) */}
            <ContextPanel
              open={contextPanelOpen()}
              context={(() => {
                const id = focusedPaneId();
                return id ? contextByPaneId()[id] ?? null : null;
              })()}
              isAgentPane={(() => {
                const id = focusedPaneId();
                if (!id) return false;
                const m = activeMounted();
                return m?.agentConfigByPaneId()?.[id] != null;
              })()}
              onTogglePin={(path, pinned) => {
                const id = focusedPaneId();
                const ctx = id ? contextByPaneId()[id] : null;
                if (!ctx) return;
                const currentPinned = ctx.files.filter((f) => f.pinned).map((f) => f.path);
                const next = pinned
                  ? [...new Set([...currentPinned, path])]
                  : currentPinned.filter((p) => p !== path);
                const wp = activeMounted()?.project()?.path;
                if (wp) {
                  void invoke('write_context_pins', {
                    workspacePath: wp,
                    pinnedPaths: next,
                  }).catch((e: unknown) =>
                    console.error('[voss-app] write_context_pins failed:', e),
                  );
                }
              }}
            />
          </div>
        </div>
        <StatusBar
          workspaceName={
            workspaceStore.workspaces().find((w) => w.id === activeId())?.name
          }
          paneCount={paneCount()}
          focusedPaneId={focusedPaneId()}
          gitBranch={activeMounted()?.project()?.gitBranch}
          contextPanelOpen={contextPanelOpen()}
          onToggleContextPanel={toggleContextPanel}
        />
      </Show>
      </div>

      <Show when={newWorkspacePickerOpen()}>
        <NewWorkspacePicker
          onDismiss={() => setNewWorkspacePickerOpen(false)}
          onCreate={handleCreateWorkspace}
          onStartEmpty={handleStartEmptyWorkspace}
        />
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

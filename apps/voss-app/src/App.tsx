import { batch, createSignal, onMount, Show } from 'solid-js';
import Titlebar from './components/titlebar/Titlebar';
import GridRoot, { type GridController } from './grid/GridRoot';
import SetupWindow from './components/setup/SetupWindow';
import type {
  ActiveLayout,
  LayoutPreset,
} from './grid/layoutPresets';
import { serializeLayout } from './grid/layoutCommands';
import { layoutToSession } from './grid/sessionCommands';
import {
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
  let gridController: GridController | undefined;
  let sessionCleanup: (() => void) | undefined;

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

  onMount(() => {
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

  // Suppress unused warnings while keeping the symbols live for A7 wiring.
  void saveCurrentLayout;
  void loadLayoutByName;
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
    </div>
  );
}

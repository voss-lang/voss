import { invoke } from '@tauri-apps/api/core';
import { open as openDialog } from '@tauri-apps/plugin-dialog';

/**
 * Frontend bridge for the A5 project-open IPC surface. These wrappers carry no
 * app composition logic — `App.tsx` owns setup-window branching and default
 * layout application.
 *
 * Tauri converts snake_case Rust param names to camelCase on the JS side;
 * payload keys here MUST match the Rust function signatures from
 * `apps/voss-app/src-tauri/src/lib.rs`. In particular, `default_cwd` receives
 * `projectPath`, not `project_path`.
 *
 * `pickFolder` is the only wrapper that touches the dialog plugin. Dialog
 * cancel resolves to null, and any non-string result is treated as cancel so
 * callers do not need to handle plugin return-shape edge cases.
 *
 * The setup-window copy constants live here as the single source of truth until
 * a dedicated A5-UI-SPEC exists.
 */

/** Wire-level project shape — mirrors Rust `voss_app_core::project::ProjectInfo`. */
export type ProjectInfo = {
  path: string;
  name: string;
  gitBranch: string | null;
};

/** Wire-level recents shape — mirrors Rust `voss_app_core::project::RecentsFile`. */
export type RecentsFile = {
  version: 1;
  recents: string[];
};

// --- Exact setup-window copy ----------------------------------------------
// Single source of truth for the renderer and tests; renaming any of these
// is a deliberate spec change.

export const OPEN_PROJECT_LABEL = 'Open project';
export const START_PROJECT_LESS_LABEL = 'Start without project';
export const RECENTS_HEADING = 'Recent projects';

// --- Tauri command bridges -------------------------------------------------

export async function pickFolder(): Promise<string | null> {
  const result = await openDialog({ directory: true, multiple: false });
  return typeof result === 'string' ? result : null;
}

export async function openProject(path: string): Promise<ProjectInfo> {
  return invoke<ProjectInfo>('open_project', { path });
}

export async function listRecents(): Promise<string[]> {
  return invoke<string[]>('load_recents');
}

export async function defaultCwd(projectPath: string | null): Promise<string> {
  return invoke<string>('default_cwd', { projectPath });
}

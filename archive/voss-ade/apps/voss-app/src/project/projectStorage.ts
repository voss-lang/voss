import { invoke } from '@tauri-apps/api/core';
import { open as openDialog } from '@tauri-apps/plugin-dialog';

/**
 * Frontend bridge for the project-open IPC surface. These wrappers carry no
 * app composition logic `App.tsx` owns setup-window branching and default
 */

export type ProjectInfo = {
  path: string;
  name: string;
  gitBranch: string | null;
};

export type RecentsFile = {
  version: 1;
  recents: string[];
};

// Exact setup-window copy
// Single source of truth for the renderer and tests; renaming any of these

export const OPEN_PROJECT_LABEL = 'Open project';
export const START_PROJECT_LESS_LABEL = 'Start without project';
export const RECENTS_HEADING = 'Recent projects';

// Tauri command bridges

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

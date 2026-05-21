import { invoke } from '@tauri-apps/api/core';
import type { SessionFile } from '../grid/sessionStorage';

/**
 * Frontend bridge for A8-02 Rust workspace index + project-less session commands.
 * Mirrors `sessionStorage.ts` — thin invoke wrappers, no remap logic.
 *
 * Tauri converts snake_case Rust param names to camelCase on the JS side;
 * payload keys here MUST match the Rust function signatures from
 * `apps/voss-app/src-tauri/src/lib.rs`.
 */

export const CURRENT_WORKSPACES_VERSION = 1 as const;
export const DEFAULT_WORKSPACE_ID = 'default';
export const DEFAULT_ACCENT_COLOR = 'blue';

/** One workspace tab's persisted metadata — mirrors Rust `WorkspaceEntry`. */
export type WorkspaceEntry = {
  id: string;
  name: string;
  projectPath?: string | null;
  accentColor: string;
  order: number;
  activeLayoutPreset?: string | null;
  pinnedProfile?: string | null;
};

/** On-disk workspace index — mirrors Rust `WorkspacesIndex`. */
export type WorkspacesIndex = {
  version: typeof CURRENT_WORKSPACES_VERSION;
  activeWorkspaceId?: string | null;
  workspaces: WorkspaceEntry[];
};

// --- Error copy constants (match Rust WorkspacesError::Display) ------------

export const WORKSPACES_SAVE_FAILED = 'could not save workspaces index';

// --- Tauri command bridges ---------------------------------------------------

export async function loadWorkspacesIndex(): Promise<WorkspacesIndex> {
  return invoke<WorkspacesIndex>('load_workspaces_index');
}

export async function saveWorkspacesIndex(
  index: WorkspacesIndex,
): Promise<void> {
  await invoke('save_workspaces_index', { index });
}

export async function listWorkspaces(): Promise<WorkspaceEntry[]> {
  return invoke<WorkspaceEntry[]>('list_workspaces');
}

export async function saveProjectLessSession(
  workspaceId: string,
  session: SessionFile,
): Promise<void> {
  await invoke('save_project_less_session', { workspaceId, session });
}

export async function loadProjectLessSession(
  workspaceId: string,
): Promise<SessionFile | null> {
  return invoke<SessionFile | null>('load_project_less_session', {
    workspaceId,
  });
}

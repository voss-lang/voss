import { invoke } from '@tauri-apps/api/core';
import type { GridStore } from './tree';
import type { LayoutPreset } from './layoutPresets';

/**
 * Frontend bridge for Rust session persistence commands. Mirrors
 * `layoutStorage.ts` thin invoke wrappers, no remap logic
 */

export type SessionPane = {
  id: string;
  scrollback: string[] | null;
};

/** (split tree) still loadable; migrated to on first save */
export type SessionFileV1 = {
  version: 1;
  activePreset: LayoutPreset | null;
  grid: GridStore;
  panes: SessionPane[];
  projectLessAccepted: boolean;
};

export type SessionFileV2 = {
  version: 2;
  activePreset: LayoutPreset | null;
    /** Absent only for files Rust wrote from a legacy tree; `grid` is set then */
  canvas?: CanvasState;
  grid?: LegacyGridStore;
  panes: SessionPane[];
  projectLessAccepted: boolean;
};

export type SessionFile = SessionFileV1 | SessionFileV2;

// Error copy constants (match Rust SessionError::Display)

export const SESSION_SAVE_FAILED = 'could not save session';
export const SESSION_LOAD_FAILED = 'could not load session';

// Tauri command bridges

export async function saveSession(
  workspacePath: string,
  session: SessionFile,
): Promise<void> {
  await invoke('save_session', { workspacePath, session });
}

export async function loadSession(
  workspacePath: string,
): Promise<SessionFile | null> {
  return invoke<SessionFile | null>('load_session', { workspacePath });
}

export async function saveGlobalSession(
  session: SessionFile,
): Promise<void> {
  await invoke('save_global_session', { session });
}

export async function loadGlobalSession(): Promise<SessionFile | null> {
  return invoke<SessionFile | null>('load_global_session');
}

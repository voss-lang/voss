import { invoke } from '@tauri-apps/api/core';
import type { GridStore } from './tree';
import type { LayoutPreset } from './layoutPresets';

/**
 * Frontend bridge for the Rust layout persistence commands. These
 * wrappers carry no remap or geometry logic that lives in
 */

export type LayoutFile = {
  version: 1;
  activePreset: LayoutPreset | null;
    /** split tree; files written from the canvas omit it */
  grid?: LegacyGridStore;
    
  nodes?: CanvasNode[];
  view?: CanvasView;
  focusedId?: string;
};

// Exact copy
// Single source of truth for the renderer and tests; renaming any of these

export const SAVE_LAYOUT_LABEL = 'Save layout as...';
export const LOAD_LAYOUT_LABEL = 'Load layout...';
export const LAYOUT_NAME_PLACEHOLDER = 'layout name';
export const SAVE_SUCCESS = 'layout saved';
export const LOAD_SUCCESS = 'layout loaded';
export const EMPTY_LIST = 'no saved layouts';
export const NAME_EXISTS_CONFIRM = 'replace existing layout?';
export const INVALID_NAME = 'layout name cannot contain /, \\ or ..';
export const NOT_FOUND = 'layout not found';
export const INVALID_FILE = 'layout ignored: invalid file';
export const UNSUPPORTED_VERSION = 'layout ignored: unsupported version';
export const SAVE_FAILED = 'could not save layout';
export const LOAD_FAILED = 'could not load layout';

// Tauri command bridges

export async function saveLayout(
  workspacePath: string,
  name: string,
  layout: LayoutFile,
): Promise<void> {
  await invoke('save_layout', { workspacePath, name, layout });
}

export async function loadLayout(
  workspacePath: string,
  name: string,
): Promise<LayoutFile> {
  return invoke<LayoutFile>('load_layout', { workspacePath, name });
}

export async function listLayouts(workspacePath: string): Promise<string[]> {
  return invoke<string[]>('list_layouts', { workspacePath });
}

export async function loadDefaultLayout(
  workspacePath: string,
): Promise<LayoutFile | null> {
  return invoke<LayoutFile | null>('load_default_layout', { workspacePath });
}

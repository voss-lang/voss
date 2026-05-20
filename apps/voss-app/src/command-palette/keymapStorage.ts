import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

/**
 * A7-03 Task 2 — frontend bridge for keymap profile and override persistence.
 *
 * Thin invoke wrappers + Tauri event listener for workspace keymap hot-reload.
 * Event name: `voss://keymap-updated`.
 */

// --- Types -------------------------------------------------------------------

export type KeymapProfile = 'vscode' | 'tmux';

export interface KeyBindingOverride {
  key: string;
}

export interface KeymapOverrideFile {
  version: 1;
  bindings: Record<string, KeyBindingOverride | null>;
}

export interface KeymapValidationIssue {
  commandId: string;
  reason: string;
}

export interface KeymapValidationResult {
  valid: Record<string, KeyBindingOverride | null>;
  issues: KeymapValidationIssue[];
}

export interface KeymapUpdatePayload {
  valid: Record<string, KeyBindingOverride | null>;
  issues: KeymapValidationIssue[];
}

// --- Error copy --------------------------------------------------------------

export const KEYMAP_SAVE_FAILED = 'could not save keymap settings';
export const KEYMAP_LOAD_FAILED = 'could not load keymap settings';

// --- Tauri command bridges ---------------------------------------------------

export async function loadKeymapProfile(): Promise<KeymapProfile> {
  const raw = await invoke<string>('load_keymap_profile');
  return JSON.parse(raw) as KeymapProfile;
}

export async function saveKeymapProfile(
  profile: KeymapProfile,
): Promise<void> {
  await invoke('save_keymap_profile', { profile });
}

export async function loadKeymapOverrides(
  workspacePath: string,
): Promise<KeymapOverrideFile | null> {
  return invoke<KeymapOverrideFile | null>('load_keymap_overrides', {
    workspacePath,
  });
}

export async function validateKeymapOverrides(
  overrides: KeymapOverrideFile,
  knownCommandIds: string[],
  knownChords: string[],
): Promise<KeymapValidationResult> {
  return invoke<KeymapValidationResult>('validate_keymap_overrides', {
    overrides,
    knownCommandIds,
    knownChords,
  });
}

// --- Hot-reload event listener (D-14) ----------------------------------------

/**
 * Listen for workspace keymap changes from the Rust file watcher.
 * Returns an unlisten function for cleanup.
 */
export async function watchWorkspaceKeymap(
  onUpdate: (payload: KeymapUpdatePayload) => void,
): Promise<UnlistenFn> {
  return listen<KeymapUpdatePayload>('voss://keymap-updated', (event) => {
    onUpdate(event.payload);
  });
}

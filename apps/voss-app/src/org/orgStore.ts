import { createSignal } from 'solid-js';
import { invoke } from '@tauri-apps/api/core';
import { assertRunData } from './guards';
import type { RunData, RunEntry } from './types';

export const [runData, setRunData] = createSignal<RunData | null>(null);
export const [runEntries, setRunEntries] = createSignal<RunEntry[]>([]);
export const [loadError, setLoadError] = createSignal<string | null>(null);
export const [loading, setLoading] = createSignal(false);
export const [currentRunId, setCurrentRunId] = createSignal<string | null>(null);
export const [currentCwd, setCurrentCwd] = createSignal<string>('');
export const [currentCliBinary, setCurrentCliBinary] = createSignal<string>('voss');

export async function loadRun(
  runId: string,
  cwd: string,
  cliBinary: string,
): Promise<void> {
  setLoading(true);
  setLoadError(null);
  setCurrentRunId(runId);
  setCurrentCwd(cwd);
  setCurrentCliBinary(cliBinary);
  try {
    const raw = await invoke<RunData>('load_run', { runId });
    const data = assertRunData(raw);
    setRunData(data);
  } catch (e) {
    setLoadError(String(e));
    setRunData(null);
  } finally {
    setLoading(false);
  }
}

export async function enumerateRuns(_cwd: string): Promise<RunEntry[]> {
  const entries = await invoke<RunEntry[]>('enumerate_runs');
  setRunEntries(entries);
  return entries;
}

export async function refreshRun(cwd: string, cliBinary: string): Promise<void> {
  const id = currentRunId();
  if (!id) return;
  await loadRun(id, cwd, cliBinary);
}

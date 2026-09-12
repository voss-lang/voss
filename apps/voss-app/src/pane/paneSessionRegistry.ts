import type { Terminal } from '@xterm/xterm';
import type { FitAddon } from '@xterm/addon-fit';
import type { SearchAddon } from '@xterm/addon-search';
import type { PtyTransport, AgentConfig, BudgetState } from './pty-ipc';
import { unregisterTerminal } from '../themes/themeRuntime';
import { unregisterScrollbackProvider } from './scrollbackRegistry';
import { unregisterPaneProc } from './procRegistry';
import { unregisterPaneContext } from './contextRegistry';
import { unregisterPaneBudget } from './budgetRegistry';
import { unregisterAgentPane } from './agentPaneRegistry';
import { unregisterSlug } from './slugRegistry';

export type DotState = 'loading' | 'running' | 'exited';

/**
 * Mutable adoption handler set. The session's long-lived transport/xterm
 * callbacks delegate ONLY through `session.sink` never component closures
 */
export interface PaneSink {
  setDot(d: DotState): void;
  setExitCode(code: number | null): void;
  setBudget(b: BudgetState): void;
  setProc(name: string): void;
  bell(): void;
  markStreaming(): void;
/** One-shot per session via session.firstInputFired ( restore banner) */
  onFirstInput(): void;
}

export const NOOP_SINK: PaneSink = {
  setDot: () => {},
  setExitCode: () => {},
  setBudget: () => {},
  setProc: () => {},
  bell: () => {},
  markStreaming: () => {},
  onFirstInput: () => {},
};

export interface PaneSession {
  paneId: string;
/** Permanent xterm host; `term.open`ed exactly once (first adoption) */
  hostEl: HTMLDivElement;
  term: Terminal;
  fitAddon: FitAddon;
  searchAddon: SearchAddon;
  transport: PtyTransport;
/** Reassigned per adoption; NOOP_SINK while detached */
  sink: PaneSink;
/** Adoption token a stale component's release is a no-op (swap safety) */
  owner: symbol | null;
/** term.open + CanvasAddon done (first adoption) */
  opened: boolean;
/** doSpawn ran (double-spawn guard) */
  spawned: boolean;
  firstInputFired: boolean;
/** ms; OSC-vs-pgid arbitration the component fgPoll reads this */
  lastOscTitleAt: number;
  // Canonical mirrors hydrate component signals on adopt
  dot: DotState;
  lastExitCode: number | null;
  lastBudget: BudgetState | null;
  lastProc: string;
/** Creation-time config frozen for (re)spawn */
  cfg: {
    cwd?: string;
    agentConfig?: AgentConfig;
    workspacePath?: string;
  };
}

// Non-reactive on purpose: nothing renders the map itself; components read
// their session once on mount and the sink pushes updates
const sessions = new Map<string, PaneSession>();
const destroyHooks = new Map<string, (() => void)[]>();

export function getPaneSession(paneId: string): PaneSession | undefined {
  return sessions.get(paneId);
}

/** Internal called by createPaneSession (paneSession.ts) */
export function trackPaneSession(s: PaneSession): void {
  sessions.set(s.paneId, s);
}

/**
 * Couple extra teardown to a pane's destruction (e.g. native ProtocolPane
 * panes abort their SSE stream + drop the nativeSessionByPaneId entry)
 */
export function registerPaneDestroyHook(paneId: string, fn: () => void): void {
  const list = destroyHooks.get(paneId) ?? [];
  list.push(fn);
  destroyHooks.set(paneId, list);
}

/**
 * THE kill path (besides budget-kill, which kills the process but keeps the
 * session for ExitBanner/restart). Safe no-op on unknown ids grid tests
 */
export function destroyPaneSession(paneId: string): void {
  const s = sessions.get(paneId);
  if (s) {
    s.sink = NOOP_SINK;
    s.transport.kill();
    s.term.dispose();
    s.hostEl.remove();
    unregisterTerminal(paneId);
    unregisterScrollbackProvider(paneId);
    unregisterPaneProc(paneId);
    unregisterPaneContext(paneId);
    unregisterPaneBudget(paneId);
    unregisterAgentPane(paneId);
    unregisterSlug(paneId);
    sessions.delete(paneId);
  }
  const hooks = destroyHooks.get(paneId);
  if (hooks) {
    destroyHooks.delete(paneId);
    for (const fn of hooks) fn();
  }
}

/**
 * Destroy every session whose id is in `before` but not `after` (a root
 * replacement orphaned it). STRICTLY a diff never whole-set: the map is
 */
export function reapOrphanPaneSessions(
  before: readonly string[],
  after: readonly string[],
): void {
  const live = new Set(after);
  for (const id of before) {
    if (!live.has(id)) destroyPaneSession(id);
  }
}

export function __resetPaneSessions(): void {
  for (const id of [...sessions.keys()]) destroyPaneSession(id);
  destroyHooks.clear();
}

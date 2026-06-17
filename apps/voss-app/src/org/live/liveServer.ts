// V24 Swarm Map — module accessor for the live `voss serve` connection.
//
// The Swarm Map (and its command bar) are mounted prop-less, so they reach the
// live server through this module signal instead of props. App sets it from the
// BuiltVossClient inside ensureVossClient; surfaces read baseUrl/token (swarm
// snapshot fetch) and followUpClient (directing live agents). The token rides the
// Authorization header only — never logged (T-V15-10). Immutable updates only.

import { createSignal } from 'solid-js';

export interface FollowUpLike {
  postMessage(sessionId: string, text: string): Promise<unknown>;
}

export interface LiveServer {
  baseUrl: string;
  token: string;
  /** Workspace cwd — needed to discover the active swarm from the agent registry. */
  cwd?: string | null;
  followUpClient?: FollowUpLike;
}

const [liveServer, setLiveServer] = createSignal<LiveServer | null>(null);

export { liveServer, setLiveServer };

/** Test-only reset. */
export function __resetLiveServer(): void {
  setLiveServer(null);
}

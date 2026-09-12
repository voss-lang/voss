import { createSignal } from 'solid-js';

export interface FollowUpLike {
  postMessage(sessionId: string, text: string): Promise<unknown>;
}

export interface LiveServer {
  sidecarId: string;

  cwd?: string | null;
  followUpClient?: FollowUpLike;
}

const [liveServer, setLiveServer] = createSignal<LiveServer | null>(null);

export { liveServer, setLiveServer };

export type LiveServerConnector = () => Promise<unknown>;

let connector: LiveServerConnector | null = null;

export function setLiveServerConnector(fn: LiveServerConnector | null): void {
  connector = fn;
}

export function canConnectLiveServer(): boolean {
  return connector != null;
}

export async function connectLiveServer(): Promise<LiveServer | null> {
  const current = liveServer();
  if (current) return current;
  if (!connector) return null;
  await connector();
  return liveServer();
}

export function __resetLiveServer(): void {
  setLiveServer(null);
  connector = null;
}

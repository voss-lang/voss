export type SwarmAgentStatus =
  | 'pending'
  | 'running'
  | 'complete'
  | 'stuck'
  | 'error';

export interface SubTask {
  id: string;
  cli: string;
  goal: string;
  fileScope: string[];
  excludeScope: string[];
}

export interface SwarmAgent {
  id: string;
  paneId: string;
  ptyId: string;
  cli: string;
  status: SwarmAgentStatus;
  taskSummary: string;
}

export interface SwarmManifest {
  id: string;
  goal: string;
  status: 'running' | 'complete' | 'cancelled';
  created: number;
  agents: SwarmAgent[];
}

export interface TaskFileContent {
  swarmId: string;
  agentId: string;
  cli: string;
  goal: string;
  fileScope: string[];
  excludeScope: string[];
  sharedContextPath: string;
}

export interface ResultFileParsed {
  agentId: string;
  status: 'complete' | 'error';
  filesModified: string[];
  durationSecs: number | null;
  summary: string;
}

export const SWARM_DIR = '.voss/swarm';
export const MAX_CONCURRENT_AGENTS = 6;
export const SWARM_RESULT_EVENT = 'voss://swarm-result-added';
export const SWARM_POLL_MS = 500;

/** Known agent CLI binary names for foreground process detection. */
export const KNOWN_AGENT_CLIS = new Set([
  'claude',
  'codex',
  'gemini',
  'opencode',
  'aider',
  'cursor',
]);

/** Substrings in OSC titles or process names that indicate an agent CLI. */
const AGENT_TITLE_PATTERNS = [
  'claude code',
  'claude',
  'codex',
  'gemini',
  'opencode',
  'aider',
  'cursor',
];

/** Exact match on binary name. */
export function isKnownAgentCli(proc: string): boolean {
  return KNOWN_AGENT_CLIS.has(proc.toLowerCase());
}

/** Fuzzy match — checks if a process name or OSC title contains an agent name. */
export function looksLikeAgent(proc: string): boolean {
  if (isKnownAgentCli(proc)) return true;
  const lower = proc.toLowerCase();
  return AGENT_TITLE_PATTERNS.some((p) => lower.includes(p));
}
